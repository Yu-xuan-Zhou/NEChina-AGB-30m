# -*- coding: utf-8 -*-
r"""Build the release copies of the 30 m AGB and AGB-change maps.

Source: Float32 GeoTIFFs on I:\AGB_models (never modified).
Output: Int16 cloud-optimised GeoTIFFs, stored value = round(10 x Mg ha-1), NoData -32768,
        DEFLATE level 9 with predictor 2, 512 px tiles, overviews (average), metadata tags,
        plus <name>.json (statistics of source and output, checksum) and sha256sums.txt.

Usage:
  python -X utf8 -I build_release_maps.py --out C:\AGB_NE_release --jobs RF_2005,RF_2015,RF_2024
  python -X utf8 -I build_release_maps.py --out C:\AGB_NE_release\_test --jobs RF_2005 --test-rows 6144

Valid-pixel rules (as in the figure packages):
  AGB maps    : finite and > 0 are values; NaN and <= 0 become NoData (counts are reported)
  change maps : finite values are kept (zero included); NaN becomes NoData

The JSON means are pixel arithmetic means for encoding QC. Regional forest area and
carbon stock require latitude-dependent WGS 84 ellipsoidal pixel areas; the geographic
grid has nominal 30 m resolution, not a constant 0.09 ha area per pixel.
"""
import argparse, hashlib, json, os, subprocess, sys, time
import numpy as np
import rasterio
from rasterio.windows import Window

GDAL_TRANSLATE = r"C:\ProgramData\anaconda3\Library\bin\gdal_translate.exe"
SRC_DIR = r"I:\AGB_models"
SCALE = 10
NODATA = -32768
STRIP = 1024
REFERENCE = ("Zhou Y. et al., Integrating Multi-Source Data with Machine Learning to Estimate Forest Aboveground "
             "Biomass Dynamics in Northeast China, Journal of Plant Ecology, manuscript JPE-2026-0380; "
             "code: AGB_NE figure packages (Model_training_bootstrap, Figure5_agb_maps)")
FOREST = ("China Annual Tree Cover Dataset (CATCD, Cai et al. 2024) tree cover > 10 % of the same year; "
          "pixels outside the forest mask are NoData")

JOBS = {
    "RF_2005": dict(src="RF_2005.tif", out="NEChina_AGB_30m_RF_2005.tif", kind="agb", year="2005", band="AGB_2005",
        desc="Forest aboveground biomass (AGB) of Northeast China in 2005, 30 m, random forest model on Landsat 5 TM and ALOS PALSAR predictors"),
    "RF_2015": dict(src="RF_2015.tif", out="NEChina_AGB_30m_RF_2015.tif", kind="agb", year="2015", band="AGB_2015",
        desc="Forest aboveground biomass (AGB) of Northeast China in 2015, 30 m, random forest model on Landsat 8 OLI and ALOS-2 PALSAR-2 predictors"),
    "RF_2024": dict(src="RF_2024.tif", out="NEChina_AGB_30m_RF_2024.tif", kind="agb", year="2024", band="AGB_2024",
        desc="Forest aboveground biomass (AGB) of Northeast China in 2024, 30 m, the 2015 random forest model applied to Landsat 9 OLI and ALOS-2 PALSAR-2 predictors of 2024"),
    "Change_05-15": dict(src="Change_05-15.tif", out="NEChina_AGBchange_30m_2005_2015.tif", kind="change", year="2005-2015", band="dAGB_2005_2015",
        desc="Change of forest AGB in Northeast China, 2005 to 2015 (AGB 2015 minus AGB 2005), 30 m; covers the union of the forest pixels of both years (Figure 5 d)"),
    "Change_15-24": dict(src="Change_15-24.tif", out="NEChina_AGBchange_30m_2015_2024.tif", kind="change", year="2015-2024", band="dAGB_2015_2024",
        desc="Change of forest AGB in Northeast China, 2015 to 2024 (AGB 2024 minus AGB 2015), 30 m; covers the union of the forest pixels of both years (Figure 5 e)"),
    "Change_05-24": dict(src="Change_05-24.tif", out="NEChina_AGBchange_30m_2005_2024.tif", kind="change", year="2005-2024", band="dAGB_2005_2024",
        desc="Change of forest AGB in Northeast China, 2005 to 2024 (AGB 2024 minus AGB 2005), 30 m; covers the union of the forest pixels of both years (Figure 5 f)"),
}

def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()

def convert(job, src_path, tmp_path, threads, test_rows):
    """Float32 source -> Int16 x10 tiled GeoTIFF (fast LZW; the COG step re-encodes). Returns source statistics."""
    st = dict(n_valid=0, sum=0.0, min=np.inf, max=-np.inf, n_nan=0, n_zero=0, n_neg=0, max_abs_round=0.0)
    with rasterio.open(src_path) as S:
        height = S.height if not test_rows else min(test_rows, S.height)
        profile = dict(driver="GTiff", dtype="int16", count=1, width=S.width, height=height, crs=S.crs,
                       transform=S.transform, nodata=NODATA, tiled=True, blockxsize=512, blockysize=512,
                       compress="lzw", predictor=2, num_threads=threads, bigtiff="IF_SAFER")
        with rasterio.open(tmp_path, "w", **profile) as D:
            for r0 in range(0, height, STRIP):
                h = min(STRIP, height - r0)
                w = Window(0, r0, S.width, h)
                a = S.read(1, window=w)
                fin = np.isfinite(a)
                if job["kind"] == "agb":
                    valid = fin & (a > 0)
                else:
                    valid = fin
                st["n_nan"] += int((~fin).sum())
                st["n_zero"] += int((fin & (a == 0)).sum())
                st["n_neg"] += int((fin & (a < 0)).sum())
                q = np.rint(a.astype("float64") * SCALE)
                qv = q[valid]
                if qv.size:
                    if qv.max() > 32767 or qv.min() < -32767:
                        raise ValueError(f"scaled value out of Int16 range in rows {r0}-{r0+h}: {qv.min()}..{qv.max()}")
                    v = a[valid].astype("float64")
                    st["n_valid"] += int(valid.sum()); st["sum"] += float(v.sum())
                    st["min"] = min(st["min"], float(v.min())); st["max"] = max(st["max"], float(v.max()))
                    st["max_abs_round"] = max(st["max_abs_round"], float(np.abs(qv / SCALE - v).max()))
                out = np.full(a.shape, NODATA, dtype="int16")
                out[valid] = qv.astype("int16")
                D.write(out, 1, window=w)
                if (r0 // STRIP) % 10 == 0:
                    log(f"  {job['out']}: rows {r0 + h}/{height}")
            D.descriptions = (job["band"],)
            D.scales = (1.0 / SCALE,)
            D.offsets = (0.0,)
            D.units = ("Mg ha-1",)
            D.update_tags(TIFFTAG_IMAGEDESCRIPTION=job["desc"], TITLE=job["desc"], YEAR=job["year"],
                          UNITS="Mg ha-1 (stored value x 0.1)", SCALE_FACTOR="0.1", NODATA_VALUE=str(NODATA),
                          VALUE_RULE=("source Float32 values <= 0 or NaN set to NoData; values rounded to 0.1 Mg ha-1" if job["kind"] == "agb"
                                      else "source Float32 NaN set to NoData, zero kept; values rounded to 0.1 Mg ha-1"),
                          FOREST_MASK=FOREST, MODEL=("Random forest (R randomForest, 500 trees) on Landsat and PALSAR predictors; "
                                                     "see the Model_training_bootstrap package" if job["kind"] == "agb"
                                                     else "difference of the random-forest AGB maps of the two years"),
                          SOURCE_FILE=f"I:\\AGB_models\\{job['src']} (Float32, exported 2026-06)",
                          CRS=("EPSG:4326 (WGS 84), pixel 0.000269494585 deg (nominal 30 m resolution); "
                               "pixel area varies with latitude; use WGS 84 ellipsoidal pixel areas for regional statistics"),
                          CREATED=time.strftime("%Y-%m-%d"), REFERENCE=REFERENCE)
            D.update_tags(1, UNITS="Mg ha-1", SCALE_FACTOR="0.1", DESCRIPTION=job["band"])
    st["mean"] = st["sum"] / st["n_valid"] if st["n_valid"] else None
    return st

def to_cog(tmp_path, out_path, threads):
    cmd = [GDAL_TRANSLATE, "-of", "COG", "-co", "COMPRESS=DEFLATE", "-co", "LEVEL=9", "-co", "PREDICTOR=YES",
           "-co", "BLOCKSIZE=512", "-co", "OVERVIEW_RESAMPLING=AVERAGE", "-co", f"NUM_THREADS={threads}",
           "-co", "BIGTIFF=IF_SAFER", tmp_path, out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gdal_translate failed ({r.returncode}): {r.stderr[-2000:]}")
    return r.stdout[-500:]

def verify(job, out_path, src_path, src_stats, test_rows):
    """Read the COG back: structure, tags, full statistics, pixel-level comparison with the source."""
    rep = {}
    with rasterio.open(out_path) as D:
        rep["dtype"] = D.dtypes[0]; rep["nodata"] = D.nodata; rep["scales"] = list(D.scales); rep["units"] = list(D.units)
        rep["overviews"] = D.overviews(1); rep["blocks"] = list(D.block_shapes[0]); rep["compression"] = str(D.compression)
        rep["crs"] = str(D.crs); rep["size"] = [D.width, D.height]; rep["tags_ok"] = all(k in D.tags() for k in ("YEAR", "SCALE_FACTOR", "FOREST_MASK", "REFERENCE"))
        assert rep["dtype"] == "int16" and D.nodata == NODATA and abs(D.scales[0] - 0.1) < 1e-12, "structure wrong"
        n = 0; s = 0.0; mn = np.inf; mx = -np.inf
        for r0 in range(0, D.height, STRIP):
            h = min(STRIP, D.height - r0)
            q = D.read(1, window=Window(0, r0, D.width, h))
            v = q != NODATA
            if v.any():
                qv = q[v].astype("float64") / SCALE
                n += int(v.sum()); s += float(qv.sum()); mn = min(mn, float(qv.min())); mx = max(mx, float(qv.max()))
        rep["out_n_valid"] = n; rep["out_mean"] = s / n if n else None; rep["out_min"] = mn; rep["out_max"] = mx
        # pixel-level comparison on a 4096 x 4096 window in the north-centre (forest in Daxing'anling)
        c0, r0 = 28000, 2048
        hh = min(4096, D.height - r0)
        with rasterio.open(src_path) as S:
            a = S.read(1, window=Window(c0, r0, 4096, hh)); q = D.read(1, window=Window(c0, r0, 4096, hh))
        fin = np.isfinite(a); valid_src = (fin & (a > 0)) if job["kind"] == "agb" else fin
        valid_out = q != NODATA
        rep["cmp_mask_equal"] = bool((valid_src == valid_out).all())
        rep["cmp_n"] = int(valid_src.sum())
        rep["cmp_max_abs_err"] = float(np.abs(q[valid_src] / SCALE - a[valid_src]).max()) if valid_src.any() else 0.0
    rep["n_valid_equal"] = (rep["out_n_valid"] == src_stats["n_valid"])
    rep["mean_diff"] = (rep["out_mean"] - src_stats["mean"]) if src_stats["mean"] is not None else None
    rep["ok"] = bool(rep["n_valid_equal"] and rep["cmp_mask_equal"] and rep["cmp_max_abs_err"] <= 0.05 + 1e-9
                     and abs(rep["mean_diff"] or 0) < 1e-3 and len(rep["overviews"]) >= (1 if test_rows else 5) and rep["tags_ok"])
    return rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True); ap.add_argument("--jobs", required=True)
    ap.add_argument("--threads", type=int, default=8); ap.add_argument("--test-rows", type=int, default=0)
    ap.add_argument("--keep-tmp", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True); tmp_dir = os.path.join(args.out, "_tmp"); os.makedirs(tmp_dir, exist_ok=True)
    with rasterio.Env(GDAL_NUM_THREADS=str(args.threads), GDAL_CACHEMAX=2048):
        for name in args.jobs.split(","):
            job = JOBS[name]; t0 = time.time()
            src_path = os.path.join(SRC_DIR, job["src"]); out_path = os.path.join(args.out, job["out"])
            tmp_path = os.path.join(tmp_dir, job["out"].replace(".tif", "_tmp.tif"))
            log(f"== {name}: {src_path} -> {out_path}")
            st = convert(job, src_path, tmp_path, args.threads, args.test_rows)
            log(f"  source stats: n_valid={st['n_valid']:,} mean={st['mean']} min={st['min']} max={st['max']} "
                f"nan={st['n_nan']:,} zero={st['n_zero']:,} neg={st['n_neg']:,} max_abs_round={st['max_abs_round']:.4f} "
                f"({time.time()-t0:.0f} s)")
            t1 = time.time(); to_cog(tmp_path, out_path, args.threads)
            log(f"  COG written: {os.path.getsize(out_path)/1e9:.3f} GB ({time.time()-t1:.0f} s)")
            t2 = time.time(); rep = verify(job, out_path, src_path, st, args.test_rows)
            log(f"  verify: ok={rep['ok']} n_valid_equal={rep['n_valid_equal']} mean_diff={rep['mean_diff']} "
                f"cmp_max_abs_err={rep['cmp_max_abs_err']:.4f} overviews={rep['overviews']} ({time.time()-t2:.0f} s)")
            digest = sha256(out_path)
            report = dict(job=name, source=src_path, output=out_path, output_bytes=os.path.getsize(out_path), sha256=digest,
                          source_stats=st, output_check=rep, test_rows=args.test_rows, created=time.strftime("%Y-%m-%d %H:%M:%S"),
                          encoding="Int16, value x 10, NoData -32768, COG, DEFLATE level 9, predictor 2, 512 px tiles, overviews average")
            with open(out_path.replace(".tif", ".json"), "w", encoding="utf-8") as f:
                json.dump(report, f, indent=1)
            with open(os.path.join(args.out, "sha256sums.txt"), "a", encoding="utf-8") as f:
                f.write(f"{digest}  {job['out']}\n")
            if not args.keep_tmp:
                os.remove(tmp_path)
            log(f"== {name} done in {time.time()-t0:.0f} s, ok={rep['ok']}")

if __name__ == "__main__":
    main()
