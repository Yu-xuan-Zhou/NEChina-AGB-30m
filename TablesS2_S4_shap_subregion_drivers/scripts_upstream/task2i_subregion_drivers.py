#!/usr/bin/env python3
"""
TASK 2i -- per-subregion decomposition of the Figure 7 driver models (supplement).

Same models, same factors, same estimator as the aggregate Figure 7 (task2h) -- only
the spatial domain changes: each model is refit within one subregion. Parameter
consistency is GUARANTEED because the factor definitions are imported from task2h and
the feature list is asserted against variable_config (single source of truth).

For every subregion x outcome (density / area) x period (05_15 / 15_24):
  - RandomForest grouped joint-permutation importance (relative %), and
  - bootstrap standardized-regression sign (+ / - / 0).

Outputs (R3_revision/tables/):
  subregion_fig7_importance_long.csv   tidy: region x outcome x period x factor
  subregion_fig7_model_r2.csv          per-model R2 + n
  subregion_fig7_density_wide_<period>.csv / _area_wide_<period>.csv   rel-importance pivots
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from rasterio.features import rasterize

import task2f_joint_permutation_models as base
import task2h_hybrid_structure_models as t2h
import variable_config as vc

OUT = Path(r"E:\DATA\Python\AGB_NE\R3_revision\tables")
MIN_PIX = 800   # skip a region/outcome/period with fewer usable pixels

REGIONS = {
    "NE":    r"I:\Shp\SHP\dongbei.shp",
    "DXAL":  r"I:\Shp\SHP\daxing\daxing.shp",
    "XXAL":  r"I:\Shp\SHP\xiaoxing\xiaoxing.shp",
    "CBS":   r"I:\Shp\SHP\changbai\changbai.shp",
    "SJP":   r"I:\Shp\SHP\sanjiang\sanjiang.shp",
    "PERMA": r"I:\Shp\SHP\2000frozen\2000frozen.shp",
}
REG_LAB = {"NE": "NE China (all)", "DXAL": "Daxing'an Mts.", "XXAL": "Xiaoxing'an Mts.",
           "CBS": "Changbai Mts.", "SJP": "Sanjiang Plain", "PERMA": "Permafrost zone"}


def grid():
    import rasterio
    with rasterio.open(base.TEMPLATE) as t:
        return t.height, t.width, t.transform, t.crs


def region_raster(shp, H, W, transform, crs):
    g = gpd.read_file(shp).to_crs(crs)
    return rasterize([(geom, 1) for geom in g.geometry], out_shape=(H, W),
                     transform=transform, fill=0, dtype="uint8").ravel()


def full_density(period, static):
    p = base.PERIOD[period]
    data = dict(static)
    data.update(base.period_climate(period))
    data["dLST"] = base.read1(vc.dlst_raster(base.DF, period))
    data["treecover2000"] = base.read1(base.COV / "hansen_treecover2000.tif")
    data["initAGB"] = base.read1(p["init_agb"])
    data["target"] = base.read1(p["density_target"])
    data["forest"] = base.read1(p["forest"])
    data["sig"] = base.read1(base.GAT / "sig_mask_k1.0_1km.tif") if p["gated"] else np.ones_like(data["target"])
    return pd.DataFrame(data)


def full_area(period, static):
    p = base.PERIOD[period]
    data = dict(static)
    data.update(base.period_climate(period))
    data["dLST"] = base.read1(vc.dlst_raster(base.DF, period))
    data["treecover2000"] = base.read1(base.COV / "hansen_treecover2000.tif")
    data["fracstart"] = base.read1(p["fracstart"])
    data["dist_to_forest"] = base.read1(p["dist_to_forest"])
    data["target"] = base.read1(p["area_target"])
    return pd.DataFrame(data)


def summarize_region(perm, beta, region, outcome, period):
    env = (perm.groupby(["factor", "factor_label"], as_index=False)
           .agg(delta_r2_mean=("delta_r2", "mean"),
                delta_r2_lo=("delta_r2", lambda x: np.percentile(x, 2.5)),
                delta_r2_hi=("delta_r2", lambda x: np.percentile(x, 97.5))))
    bsum = (beta.groupby(["factor", "factor_label"], as_index=False)
            .agg(beta_mean=("beta_mean", "mean"),
                 beta_lo=("beta_lo", "min"), beta_hi=("beta_hi", "max")))
    bsum["direction"] = np.where(bsum.beta_lo > 0, "+", np.where(bsum.beta_hi < 0, "-", "0"))
    out = env.merge(bsum[["factor", "factor_label", "direction"]], on=["factor", "factor_label"], how="left")
    pos = out["delta_r2_mean"].clip(lower=0)
    out["rel_importance_pct"] = 100 * pos / pos.sum() if pos.sum() > 0 else 0.0
    out.insert(0, "region", region); out.insert(1, "region_label", REG_LAB[region])
    out.insert(2, "outcome", outcome)
    out.insert(3, "period", period); out.insert(4, "period_label", base.PERIOD_LABEL[period])
    out["plot_order"] = [t2h.FACTOR_ORDER.get((outcome, f), 99) for f in out["factor"]]
    return out.sort_values("plot_order")


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    H, W, transform, crs = grid()
    static = base.common_static()
    dfac = t2h.feature_list(t2h.DENSITY_FACTORS)
    afac = t2h.feature_list(t2h.AREA_FACTORS)
    vc.assert_matches(dfac, vc.DENSITY_FEATURES, "Subregion density")
    vc.assert_matches(afac, vc.AREA_FEATURES, "Subregion area")

    long_rows, r2_rows = [], []
    for period in ["05_15", "15_24"]:
        dfull = full_density(period, static)
        afull = full_area(period, static)
        for reg, shp in REGIONS.items():
            rmask = region_raster(shp, H, W, transform, crs)
            # ---- density ----
            m = (dfull["forest"].values == 1) & (dfull["sig"].values == 1) & (rmask == 1)
            sub = base.sample_frame(dfull.loc[m, dfac + ["target"]].dropna(), 10 if period == "05_15" else 20)
            if len(sub) >= MIN_PIX:
                perm, beta, r2 = t2h.run_one("density", period, sub, t2h.DENSITY_FACTORS)
                long_rows.append(summarize_region(perm, beta, reg, "density", period))
                r2_rows.append({"region": reg, "region_label": REG_LAB[reg], "outcome": "density",
                                "period": period, "period_label": base.PERIOD_LABEL[period],
                                "r2": float(r2["hybrid_r2"].iloc[0]), "n": len(sub)})
                print(f"  density {reg} {period}: n={len(sub):,} R2={float(r2['hybrid_r2'].iloc[0]):.3f}")
            else:
                print(f"  density {reg} {period}: n={len(sub)} < {MIN_PIX}, skip")
            # ---- area ----
            m = (rmask == 1) & (afull["fracstart"].values < 0.95)
            sub = base.sample_frame(afull.loc[m, afac + ["target"]].dropna(), 30 if period == "05_15" else 40)
            if len(sub) >= MIN_PIX:
                perm, beta, r2 = t2h.run_one("area", period, sub, t2h.AREA_FACTORS)
                long_rows.append(summarize_region(perm, beta, reg, "area", period))
                r2_rows.append({"region": reg, "region_label": REG_LAB[reg], "outcome": "area",
                                "period": period, "period_label": base.PERIOD_LABEL[period],
                                "r2": float(r2["hybrid_r2"].iloc[0]), "n": len(sub)})
                print(f"  area    {reg} {period}: n={len(sub):,} R2={float(r2['hybrid_r2'].iloc[0]):.3f}")
            else:
                print(f"  area    {reg} {period}: n={len(sub)} < {MIN_PIX}, skip")

    long = pd.concat(long_rows, ignore_index=True)
    long.to_csv(OUT / "subregion_fig7_importance_long.csv", index=False, encoding="utf-8")
    pd.DataFrame(r2_rows).to_csv(OUT / "subregion_fig7_model_r2.csv", index=False, encoding="utf-8")
    # convenience wide pivots (relative importance %) for figure building
    for outcome in ["density", "area"]:
        for period in ["05_15", "15_24"]:
            d = long[(long.outcome == outcome) & (long.period == period)]
            if d.empty:
                continue
            wide = d.pivot_table(index="factor_label", columns="region_label",
                                 values="rel_importance_pct")
            wide.to_csv(OUT / f"subregion_fig7_{outcome}_wide_{period}.csv", encoding="utf-8")
    print("wrote subregion_fig7_* tables")


if __name__ == "__main__":
    run()
