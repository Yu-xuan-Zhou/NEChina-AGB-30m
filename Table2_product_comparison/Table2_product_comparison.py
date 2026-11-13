"""Table 2 - Comparison of AGB products (density, forest area, total carbon).

With the cached raster statistics in data/ it runs in a
second; set FORCE_RESCAN = True to re-read the rasters (hours).

# Northeast China AGB product comparison

Compares forest aboveground-biomass products across **methods** (RF / Cubist / MLR), **years** (2005 / 2015 / 2024), **external** datasets (Su, Saatchi, Chang, Huang, CFATD, and a 10 m Zenodo reference map), plus **literature-only** entries (Zhao, Xu).

For every raster, over the valid-forest mask (`value > 0`, finite, `!= nodata`):

| quantity | formula | unit |
|---|---|---|
| Density | area-weighted mean AGB | Mg/ha |
| Forest area | sum of the areas of the valid pixels | Mha |
| Total carbon | Density × Forest_area_ha × `CARBON_FRAC` × 1e-9 | Pg C |

Pixel area: geographic rasters use the area of each pixel on the WGS84 ellipsoid; projected (metre) rasters use their native cell size (e.g. the 10 m reference = 0.01 ha/pixel).

The scan over the 30 m / 10 m maps is billions of pixels — it caches to `model_comparison_rawstats.csv` and reloads unless `FORCE_RESCAN = True`.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import io

import numpy as np
import pandas as pd
import rasterio

# ------------------------- Configuration -------------------------
HERE = Path.cwd()
RAW_PATH = HERE / "data" / "model_comparison_rawstats.csv"
TABLE_PATH = HERE / "output" / "model_comparison_table_all_products.csv"

CARBON_FRAC = 0.5                      # AGB -> carbon fraction (matches Figure 6)
WGS84_A = 6378137.0                     # semi-major axis (m)
WGS84_E2 = 0.00669437999014             # first eccentricity squared
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
    "CFATD_2023":   (r"I:/AGB_models/external/2024/CFATD_AGBD_2023_Northeast_China_30m.tif", 2023, "CFATD", "external", "30m"),
    "reference_10m": (r"I:/AGB_models/external/2024/AGB_2022_LIU.tif", 0, "Reference", "external", "10m"),
}

# Xu et al. (2018), doi:10.1038/s41598-018-20764-9, Supplementary Table S2.
# Forest-only totals for ecological regions R1-R3, not our raster mask.
# The period describes literature publication years; area uses 2010 land cover.
# Preserve reported AGBC. Its mixed measured/converted carbon records do not
# support a unique inverse conversion to aggregate AGB density (reported as NR).
XU_FOREST = pd.read_csv(HERE / "data" / "xu2018_forest_ecoregions.csv")
if list(XU_FOREST["Region"]) != ["R1", "R2", "R3"]:
    raise ValueError("Xu comparison requires exactly the forest rows R1-R3")
XU_ENTRY = {
    "Data source": "Xu", "Method": "Field synthesis", "Year": "2004-2014",
    "Resolution": "NA", "Density_Mg_ha": np.nan,
    "Forest_area_Mha": XU_FOREST["Forest_area_Mha"].sum(),
    "Total_C_PgC": XU_FOREST["AGBC_TgC"].sum() / 1000,
}

# Literature-only products retain source accounting rather than CARBON_FRAC.
LITERATURE = [
    {"Data source": "Zhao", "Method": "Zhao", "Year": 2005, "Resolution": "NA",
     "Density_Mg_ha": 92.44, "Forest_area_Mha": 46.80, "Total_C_PgC": 2.17},
    XU_ENTRY,
]

# ------------------------- Raster scan -------------------------
def pixel_area_ha(ds, win):
    """Area (ha) of one pixel in each row of the window."""
    rx, ry = abs(ds.res[0]), abs(ds.res[1])
    if ds.crs and ds.crs.is_geographic:
        s = np.sin(np.radians(ds.transform.f - ry * (win.row_off + np.arange(win.height + 1))))
        e = np.sqrt(WGS84_E2)
        q = (1 - WGS84_E2) * (s / (1 - WGS84_E2 * s * s) - np.log((1 - e * s) / (1 + e * s)) / (2 * e))
        return WGS84_A ** 2 / 2 * np.radians(rx) * np.abs(np.diff(q)) / 1e4
    return np.full(win.height, rx * ry / 1e4)  # projected metres


def scan(path):
    """Streaming valid-pixel count / area / sum / range over a single raster."""
    n, a, s, vmin, vmax = 0, 0.0, 0.0, np.inf, -np.inf
    with rasterio.open(path) as ds:
        nd = ds.nodata
        for _, win in ds.block_windows(1):
            b = ds.read(1, window=win).astype("float64")
            m = np.isfinite(b) & (b > 0)
            if nd is not None and np.isfinite(nd):
                m &= (b != nd)
            if m.any():
                pa = pixel_area_ha(ds, win)
                v = b[m]
                n += v.size
                a += float((m.sum(axis=1) * pa).sum())
                s += float((np.where(m, b, 0.0).sum(axis=1) * pa).sum())
                vmin = min(vmin, float(v.min()))
                vmax = max(vmax, float(v.max()))
    return {"n_pixels": n, "sum_agb": s, "min": vmin, "max": vmax, "area_ha": a}


def build_rawstats():
    rows = []
    print(f"Scanning {len(PRODUCTS)} rasters ...", flush=True)
    with ThreadPoolExecutor(max_workers=N_WORKERS) as pool:
        fut = {pool.submit(scan, meta[0]): (key, meta) for key, meta in PRODUCTS.items()}
        for f in as_completed(fut):
            key, meta = fut[f]
            r = f.result()
            mean = r["sum_agb"] / r["area_ha"] if r["n_pixels"] else np.nan
            area_mha = r["area_ha"] / 1e6
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
    # Sort a literature synthesis by the end of its period.
    df["_y"] = pd.to_numeric(df["Year"].astype(str).str[-4:]).replace(0, 9999)
    df = df.sort_values(["_k", "_y", "Method"]).drop(columns=["_k", "_y"]).reset_index(drop=True)
    df = df[["Data source", "Method", "Year", "Kind", "Resolution",
             "Density_Mg_ha", "Forest_area_Mha", "Total_C_PgC"]]
    return df


table = assemble(raw)
table_rounded = table.round({"Density_Mg_ha": 2, "Forest_area_Mha": 2, "Total_C_PgC": 2})
table_rounded.to_csv(TABLE_PATH, index=False, na_rep="NR")
print(f"Carbon fraction = {CARBON_FRAC}")
print(f"Wrote {TABLE_PATH}")
table_rounded


def update_xu_manuscript_row():
    """Synchronize Xu while preserving every other manuscript CSV line."""
    path = HERE / "output" / "Table2_manuscript.csv"
    if not path.exists():
        return
    lines = path.read_bytes().decode("utf-8").splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines)
               if next(csv.reader([line]))[0] == "Xu"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one Xu row in Table2_manuscript.csv")
    i = matches[0]
    newline = "\r\n" if lines[i].endswith("\r\n") else "\n"
    buf = io.StringIO(newline="")
    csv.writer(buf, lineterminator=newline).writerow([
        "Xu", XU_ENTRY["Year"], XU_ENTRY["Method"], "NA", "NR",
        f"{XU_ENTRY['Forest_area_Mha']:.2f}",
        f"{XU_ENTRY['Total_C_PgC']:.2f}",
    ])
    lines[i] = buf.getvalue()
    path.write_bytes("".join(lines).encode("utf-8"))


update_xu_manuscript_row()
