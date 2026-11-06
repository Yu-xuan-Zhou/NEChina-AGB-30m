"""Table 2 - Comparison of AGB products (density, forest area, total carbon).

With the cached raster statistics in data/ it runs in a
second; set FORCE_RESCAN = True to re-read the rasters (hours).

# Northeast China AGB product comparison

Compares forest aboveground-biomass products across **methods** (RF / Cubist / MLR), **years** (2005 / 2015 / 2024), **external** datasets (Su, Saatchi, Chang, Huang, CFATD, and a 10 m Zenodo reference map), plus **literature-only** entries (Zhao, Xu).

For every raster, over the valid-forest mask (`value > 0`, finite, `!= nodata`):

| quantity | formula | unit |
|---|---|---|
| Density | mean AGB | Mg/ha |
| Forest area | valid pixels × pixel area | Mha |
| Total carbon | Density × Forest_area_ha × `CARBON_FRAC` × 1e-9 | Pg C |

Pixel area is derived per raster from its own resolution / CRS, calibrated so a 30 m geographic pixel (0.0002695°) = 0.09 ha (the RF / Figure-6 grid). Projected (metre) rasters use their native cell size (e.g. the 10 m reference = 0.01 ha/pixel).

The scan over the 30 m / 10 m maps is billions of pixels — it caches to `model_comparison_rawstats.csv` and reloads unless `FORCE_RESCAN = True`.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import rasterio

# ------------------------- Configuration -------------------------
HERE = Path.cwd()
RAW_PATH = HERE / "data" / "model_comparison_rawstats.csv"
TABLE_PATH = HERE / "output" / "model_comparison_table_all_products.csv"

CARBON_FRAC = 0.5                      # AGB -> carbon fraction (matches Figure 6)
REF_RES = 0.00026949458523585647        # deg per 30 m pixel  -> 0.09 ha
N_WORKERS = 3
FORCE_RESCAN = False                    # True -> re-read rasters even if the raw cache exists

# name: (path, year, method, kind, resolution_label)
# Year = 0 marks an epoch-less reference layer (shown without a year, sorted last).
PRODUCTS = {
    "RF_2005":      (r"I:/AGB_models/RF_2005.tif",     2005, "RF",      "internal", "30m"),
    "RF_2015":      (r"I:/AGB_models/RF_2015.tif",     2015, "RF",      "internal", "30m"),
    "RF_2024":      (r"I:/AGB_models/RF_2024.tif",     2024, "RF",      "internal", "30m"),
    "cubist_2005":  (r"I:/AGB_models/cubist_2005.tif", 2005, "Cubist",  "internal", "30m"),
    "cubist_2015":  (r"I:/AGB_models/cubist_2015.tif", 2015, "Cubist",  "internal", "30m"),
    "MLR_2005":     (r"I:/AGB_models/MLR_2005.tif",    2005, "MLR",     "internal", "30m"),
    "MLR_2015":     (r"I:/AGB_models/MLR_2015.tif",    2015, "MLR",     "internal", "30m"),
    "Su_2005":      (r"I:/AGB_models/external/Su_2005.tif",      2005, "Su",      "external", "500m"),
    "Saatchi_2015": (r"I:/AGB_models/external/Saatchi_2015.tif", 2015, "Saatchi", "external", "1km"),
    "Chang_2015":   (r"I:/AGB_models/external/Chang_2015.tif",   2015, "Chang",   "external", "1km"),
    "Huang_2005":   (r"I:/AGB_models/external/Huang_2005.tif",   2005, "Huang",   "external", "30m"),
    "CFATD_2005":   (r"I:/AGB_models/external/CFATD_AGBD_2005_Northeast_China_30m.tif", 2005, "CFATD", "external", "30m"),
    "CFATD_2015":   (r"I:/AGB_models/external/CFATD_AGBD_2015_Northeast_China_30m.tif", 2015, "CFATD", "external", "30m"),
    "CFATD_2023":   (r"I:/AGB_models/external/CFATD_AGBD_2023_Northeast_China_30m.tif", 2023, "CFATD", "external", "30m"),
    "reference_10m": (r"I:/AGB_models/external/reference_AGB_Northeast_China_10m.tif", 0, "Reference", "external", "10m"),
}

# Literature-only products (no raster; values from the source figure).
LITERATURE = [
    {"Data source": "Zhao", "Method": "Zhao", "Year": 2005, "Resolution": "NA",
     "Density_Mg_ha": 92.44, "Forest_area_Mha": 46.80, "Total_C_PgC": 2.17},
    {"Data source": "Xu", "Method": "Xu", "Year": 2015, "Resolution": "NA",
     "Density_Mg_ha": 90.08, "Forest_area_Mha": 97.02, "Total_C_PgC": 2.96},
]

# ------------------------- Raster scan -------------------------
def pixel_area_ha(ds):
    rx, ry = abs(ds.res[0]), abs(ds.res[1])
    if ds.crs and ds.crs.is_geographic:
        return 0.09 * (rx / REF_RES) * (ry / REF_RES)
    return rx * ry / 1e4  # projected metres


def scan(path):
    """Streaming valid-pixel count / sum / range over a single raster."""
    n, s, vmin, vmax = 0, 0.0, np.inf, -np.inf
    with rasterio.open(path) as ds:
        pa = pixel_area_ha(ds)
        nd = ds.nodata
        for _, win in ds.block_windows(1):
            b = ds.read(1, window=win).astype("float64")
            m = np.isfinite(b) & (b > 0)
            if nd is not None and np.isfinite(nd):
                m &= (b != nd)
            if m.any():
                v = b[m]
                n += v.size
                s += float(v.sum())
                vmin = min(vmin, float(v.min()))
                vmax = max(vmax, float(v.max()))
    return {"n_pixels": n, "sum_agb": s, "min": vmin, "max": vmax, "pixel_area_ha": pa}


def build_rawstats():
    rows = []
    print(f"Scanning {len(PRODUCTS)} rasters ...", flush=True)
    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        fut = {pool.submit(scan, meta[0]): (key, meta) for key, meta in PRODUCTS.items()}
        for f in as_completed(fut):
            key, meta = fut[f]
            r = f.result()
            mean = r["sum_agb"] / r["n_pixels"] if r["n_pixels"] else np.nan
            area_mha = r["n_pixels"] * r["pixel_area_ha"] / 1e6
            rows.append({"Key": key, "Method": meta[2], "Year": meta[1], "Kind": meta[3],
                         "Resolution": meta[4], **r, "mean_density": mean, "area_Mha": area_mha})
            print(f"  {key:14s} n={r['n_pixels']:>12,} mean={mean:7.2f} "
                  f"area={area_mha:7.2f}Mha range=[{r['min']:.2f},{r['max']:.2f}]", flush=True)
    raw = pd.DataFrame(rows)
    raw.to_csv(RAW_PATH, index=False)
    print(f"Wrote {RAW_PATH}")
    return raw

if RAW_PATH.exists() and not FORCE_RESCAN:
    print(f"Loading cached raw stats -> {RAW_PATH}")
    raw = pd.read_csv(RAW_PATH)
else:
    raw = build_rawstats()

raw

def assemble(raw):
    rows = []
    for _, r in raw.iterrows():
        area_ha = r["area_Mha"] * 1e6
        year = int(r["Year"])
        rows.append({
            "Data source": f"{r['Method']} {year}" if year else r["Method"],
            "Method": r["Method"], "Year": year, "Kind": r["Kind"], "Resolution": r["Resolution"],
            "Density_Mg_ha": r["mean_density"], "Forest_area_Mha": r["area_Mha"],
            "Total_C_PgC": r["mean_density"] * area_ha * CARBON_FRAC * 1e-9,
        })
    for lit in LITERATURE:
        rows.append({**lit, "Kind": "literature"})

    df = pd.DataFrame(rows)
    df["_k"] = df["Kind"].map({"internal": 0, "external": 1, "literature": 2})
    df["_y"] = df["Year"].replace(0, 9999)  # epoch-less reference sorts last
    df = df.sort_values(["_k", "_y", "Method"]).drop(columns=["_k", "_y"]).reset_index(drop=True)
    df = df[["Data source", "Method", "Year", "Kind", "Resolution",
             "Density_Mg_ha", "Forest_area_Mha", "Total_C_PgC"]]
    return df


table = assemble(raw)
table_rounded = table.round({"Density_Mg_ha": 2, "Forest_area_Mha": 2, "Total_C_PgC": 2})
table_rounded.to_csv(TABLE_PATH, index=False)
print(f"Carbon fraction = {CARBON_FRAC}")
print(f"Wrote {TABLE_PATH}")
table_rounded