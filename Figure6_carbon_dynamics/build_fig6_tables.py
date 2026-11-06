#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
One-time rebuild of the Figure 6 data tables directly from the RF AGB rasters.

Recomputes, per region and year:
  - forest area  (valid pixels x 0.09 ha)
  - AGB density  (mean Mg/ha over valid pixels)
  - carbon stock (area_ha x density x 1e-9 x CARBON_FRAC  ->  Pg C; CARBON_FRAC = 0.5)

Writes three CSVs into this folder so the notebook can just load + plot.
Run once; the notebook reads the cache.

  python build_fig6_tables.py                 full raster pass (several minutes, reads the RF maps)
  python build_fig6_tables.py --from-cache    rewrite the two summary CSVs from figure6_yearly_raster_stats.csv
                                              (pixel counts and densities kept, carbon stocks recomputed
                                              with CARBON_FRAC)
"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd
import rasterio

AGB_ROOT = Path(r"I:\AGB_models")
REGION_ROOT = AGB_ROOT / "regiona"
OUTPUT_DIR = Path(__file__).resolve().parent   # the three CSVs are written next to this script
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIGURE_TABLE_PATH = OUTPUT_DIR / "figure6_raster_summary.csv"
DECOMP_TABLE_PATH = OUTPUT_DIR / "figure6_decomposition_summary.csv"
YEARLY_STATS_PATH = OUTPUT_DIR / "figure6_yearly_raster_stats.csv"

ROOT_RASTERS = {
    2005: AGB_ROOT / "RF_2005.tif",
    2015: AGB_ROOT / "RF_2015.tif",
    2024: AGB_ROOT / "RF_2024.tif",
}

REGION_MAP = {
    "2000frozen_cropped.tif": "Permafrost",
    "changbai_cropped.tif": "Changbai Mt.",
    "daxing_cropped.tif": "Daxing'anling",
    "dongbei_cropped.tif": "Northeast China",
    "xiaoxing_cropped.tif": "Xiaoxing'anling",
}
REGION_FILES = {Path(f).stem.replace("_cropped", ""): f for f in REGION_MAP}
REGION_LABELS = {Path(f).stem.replace("_cropped", ""): l for f, l in REGION_MAP.items()}

REGION_ORDER = ["Northeast China", "Permafrost", "Changbai Mt.", "Daxing'anling", "Xiaoxing'anling"]
PERIODS = ["2005-2015", "2015-2024"]
YEARS = [2005, 2015, 2024]

REGIONAL_RASTERS = {
    region: {year: REGION_ROOT / f"RF_{year}" / filename for year in YEARS}
    for region, filename in REGION_FILES.items()
}

PIXEL_HA = 0.09
MG2PG = 1e-9
CARBON_FRAC = 0.5      # carbon fraction of AGB, as in the paper
VALID_MIN = 0


def compute_stats(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    n_pix = 0
    total_bm = 0.0
    with rasterio.open(path) as src:
        for _, win in src.block_windows(1):
            block = src.read(1, window=win, masked=True)
            valid = (block.data > VALID_MIN) & (~block.mask) & np.isfinite(block.data)
            if valid.any():
                vals = block.data[valid].astype("float64")
                n_pix += vals.size
                total_bm += vals.sum()
    area_ha = n_pix * PIXEL_HA
    density = total_bm / n_pix if n_pix else np.nan
    stock_pg = area_ha * density * MG2PG * CARBON_FRAC if n_pix else np.nan
    return {"n_pixels": n_pix, "area_ha": area_ha, "density": density, "stock_pg": stock_pg}


def decompose(s0, s1):
    dA = s1["area_ha"] - s0["area_ha"]
    dRho = s1["density"] - s0["density"]
    area_c = s0["density"] * dA * MG2PG * CARBON_FRAC
    density_c = s0["area_ha"] * dRho * MG2PG * CARBON_FRAC
    interact_c = dA * dRho * MG2PG * CARBON_FRAC
    total_c = s1["stock_pg"] - s0["stock_pg"]
    return area_c, density_c, interact_c, total_c


def collect_tasks():
    tasks = []
    for year, path in ROOT_RASTERS.items():
        tasks.append({"Scope": "root", "RegionKey": "dongbei", "Region": "Northeast China",
                      "Year": year, "Raster": str(path)})
    for region, by_year in REGIONAL_RASTERS.items():
        for year, path in by_year.items():
            tasks.append({"Scope": "regional", "RegionKey": region, "Region": REGION_LABELS[region],
                          "Year": year, "Raster": str(path)})
    return tasks


def summarise(yearly):
    """Writes the three CSVs from the per-raster statistics; stock_pg is (re)computed with CARBON_FRAC."""
    yearly = yearly.copy()
    yearly["stock_pg"] = yearly["area_ha"] * yearly["density"] * MG2PG * CARBON_FRAC
    yearly.to_csv(YEARLY_STATS_PATH, index=False)

    regional = yearly[yearly["Scope"] == "regional"].copy()
    figure_rows = []
    for region in REGION_FILES:
        by_year = regional[regional["RegionKey"] == region].set_index("Year")
        for y0, y1 in [(2005, 2015), (2015, 2024)]:
            s0, s1 = by_year.loc[y0], by_year.loc[y1]
            figure_rows.append({
                "RegionKey": region, "Region": REGION_LABELS[region], "Period": f"{y0}-{y1}",
                "Density_Mg_per_ha": s1["density"] - s0["density"],
                "Total_AGB_PgC": s1["stock_pg"] - s0["stock_pg"],
                "Area_Mha": (s1["area_ha"] - s0["area_ha"]) / 1e6,
                "Area_ha_t0": s0["area_ha"], "Area_ha_t1": s1["area_ha"],
                "Density_t0": s0["density"], "Density_t1": s1["density"],
                "Stock_PgC_t0": s0["stock_pg"], "Stock_PgC_t1": s1["stock_pg"],
            })
    figure_df = pd.DataFrame(figure_rows)
    figure_df["Region"] = pd.Categorical(figure_df["Region"], REGION_ORDER, ordered=True)
    figure_df["Period"] = pd.Categorical(figure_df["Period"], PERIODS, ordered=True)
    figure_df = figure_df.sort_values(["Period", "Region"])
    figure_df.to_csv(FIGURE_TABLE_PATH, index=False)

    root = yearly[yearly["Scope"] == "root"].set_index("Year")
    decomp_rows = []
    for y0, y1 in [(2005, 2015), (2015, 2024)]:
        area_c, density_c, interact_c, total_c = decompose(root.loc[y0], root.loc[y1])
        decomp_rows.append({"Period": f"{y0}-{y1}", "AreaDriven_PgC": area_c,
                            "DensityDriven_PgC": density_c, "Interaction_PgC": interact_c,
                            "Total_PgC": total_c})
    pd.DataFrame(decomp_rows).to_csv(DECOMP_TABLE_PATH, index=False)

    print("\nWrote:")
    print(" ", YEARLY_STATS_PATH)
    print(" ", FIGURE_TABLE_PATH)
    print(" ", DECOMP_TABLE_PATH)
    print("\nDONE")


def main():
    if "--from-cache" in sys.argv:
        yearly = pd.read_csv(YEARLY_STATS_PATH)
        print(f"Recomputing the summary tables from {YEARLY_STATS_PATH.name} with carbon fraction "
              f"{CARBON_FRAC} (no raster pass)", flush=True)
        summarise(yearly)
        return
    rows = []
    tasks = collect_tasks()
    print(f"Computing stats for {len(tasks)} rasters ...", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        fut = {pool.submit(compute_stats, t["Raster"]): t for t in tasks}
        for f in as_completed(fut):
            t = fut[f]
            stats = f.result()
            rows.append({**t, **stats})
            print(f"  done: {t['Scope']:8s} {t['Year']} {t['Region']:16s} "
                  f"area={stats['area_ha']/1e6:8.3f} Mha  rho={stats['density']:7.3f}  "
                  f"stock={stats['stock_pg']:7.4f} PgC", flush=True)
    yearly = pd.DataFrame(rows).sort_values(["Scope", "Region", "Year"])
    summarise(yearly)


if __name__ == "__main__":
    main()
