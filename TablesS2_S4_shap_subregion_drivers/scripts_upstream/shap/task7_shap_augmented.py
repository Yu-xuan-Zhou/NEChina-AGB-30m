"""
SHAP circularity check with the feature set of ../variable_config.py (the density
drivers of Figure 7 plus the four model-internal deltas):

  EXOGENOUS (explanatory): initial AGB, tree cover 2000, period climate-water
    (precipitation, soil moisture, water deficit, VPD, dLST=ΔLST), terrain
    (elevation, slope).
  OBSERVED RS (model-internal, circular): dNDVI, dNDWI, dHH, dHV.

Purpose: this is NOT a driver figure. It quantifies the circularity (the four
Landsat/PALSAR deltas dominate mean|SHAP|), which is why Figure 7 excludes them.

Per region x period: RandomForestRegressor + shap.TreeExplainer on the 1 km grid.
Period 05_15 is fit on GATED-significant forest pixels (sig_mask_k1.0); period
15_24 has no gating product, so it is fit on forest pixels (documented).

Outputs (R3_revision/tables/shap/):
  shap_importance_<region>_<period>.csv   per-feature mean|SHAP|, group
  shap_importance_all.csv                 long table region x period x feature
  shap_values_<region>_<period>.npy + X_<region>_<period>.csv  (for beeswarm)
Figure (R3_revision/figures/):
  Figure_SHAP_augmented_<period>.png/.pdf  grouped region x driver heatmap + NE beeswarm
"""
from pathlib import Path
import numpy as np, pandas as pd, rasterio, geopandas as gpd
from rasterio.features import rasterize
from sklearn.ensemble import RandomForestRegressor
import shap
import matplotlib.pyplot as plt
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo scripts/ on path
import nature_style as NS
import variable_config as vc
import warnings; warnings.filterwarnings("ignore")
NS.apply()

RES = Path(r"I:\AGB_models\Res"); DF = RES / "df"
COV = Path(r"E:\DATA\Python\AGB_NE\R3_revision\covariates_1km")
GAT = Path(r"I:\AGB_models\Res\gating")
OUTT = Path(r"E:\DATA\Python\AGB_NE\R3_revision\tables\shap"); OUTT.mkdir(parents=True, exist_ok=True)
OUTF = Path(r"E:\DATA\Python\AGB_NE\R3_revision\figures")
TEMPLATE = RES / "RF_2005_res1km.tif"
SEED = 42; SAMPLE = 50_000; SHAP_N = 4_000; NODATA = -9999

REGIONS = {"NE": r"I:\Shp\SHP\dongbei.shp", "DXAL": r"I:\Shp\SHP\daxing\daxing.shp",
           "XXAL": r"I:\Shp\SHP\xiaoxing\xiaoxing.shp", "CBS": r"I:\Shp\SHP\changbai\changbai.shp",
           "SJP": r"I:\Shp\SHP\sanjiang\sanjiang.shp", "PERMA": r"I:\Shp\SHP\2000frozen\2000frozen.shp"}
# --- canonical LEAN feature set, sourced from variable_config (single source of truth) ---
# SHAP = the Figure 7 density-driver set  +  the four model-internal Landsat/PALSAR deltas.
# Dropped vs. the old augmented set: period_pdsi, period_burnfreq, permafrost_flag,
# hansen_disturb, forest-type dummies, and period_lst (LST is now dLST = change).
RS_ALL = ["dNDVI", "dNDWI", "dHH", "dHV", "dLST"]   # delta rasters to read
RS_INTERNAL = vc.RS_INTERNAL                          # the 4 circular AGB-map inputs
EXO = vc.SHAP_EXO                                     # exogenous = Fig 7 density drivers (incl. dLST)
FEATS = vc.SHAP_FEATS                                 # EXO + the 4 deltas
PRETTY = vc.PRETTY
CLIM_PERIOD = ["period_pr", "period_soil", "period_def", "period_vpd"]


def read1(path):
    with rasterio.open(path) as r:
        a = r.read(1).astype("float64"); nd = r.nodata
    if nd is not None:
        a = np.where(a == nd, np.nan, a)
    a = np.where(np.abs(a) >= 1e30, np.nan, a)   # catch undeclared float32 sentinels (±3.4e38)
    return a.ravel()


def grid():
    with rasterio.open(TEMPLATE) as t:
        return t.height, t.width, t.transform, t.crs


def build_period_stack(period):
    """Return DataFrame of the canonical (lean) features + target + masks for one period."""
    cols = {}
    # target + the 5 delta rasters (4 model-internal + dLST exogenous)
    cols["target"] = read1(DF / f"RF_d{period}_res1km.tif")
    for rs, var in zip(RS_ALL, ["NDVI", "NDWI", "HH", "HV", "LST"]):
        cols[rs] = read1(DF / f"{var}_d{period}_res1km.tif")
    # initial AGB + forest mask differ by period
    init_year = "2005" if period == "05_15" else "2015"
    cols["initAGB"] = read1(RES / f"RF_{init_year}_res1km.tif")
    cols["forest"] = read1(RES / f"forest_mask_{init_year}.tif")
    cols["treecover2000"] = read1(COV / "hansen_treecover2000.tif")
    for c in CLIM_PERIOD:
        cols[c] = read1(COV / f"{c}_{period}.tif")
    cols["Elevation"] = read1(RES / "Elevation_res1km.tif")
    cols["Slope"] = read1(RES / "Slope_res1km.tif")
    # gating significance (only 05_15)
    cols["sig"] = (read1(GAT / "sig_mask_k1.0_1km.tif") if period == "05_15"
                   else np.ones_like(cols["target"]))
    return pd.DataFrame(cols)


def run_period(period, H, W, transform, crs):
    print(f"\n=== period {period} ===")
    feats = FEATS
    vc.assert_matches(feats, vc.SHAP_FEATS, "SHAP")
    df = build_period_stack(period)
    rows_all = []
    for reg, shp in REGIONS.items():
        g = gpd.read_file(shp).to_crs(crs)
        rmask = rasterize([(geom, 1) for geom in g.geometry], out_shape=(H, W),
                          transform=transform, fill=0, dtype="uint8").ravel()
        sel = (rmask == 1) & (df["forest"].values == 1) & (df["sig"].values == 1)
        sub = df.loc[sel, feats + ["target"]].dropna()
        if len(sub) < 800:
            print(f"  {reg}/{period}: {len(sub)} px, skip"); continue
        if len(sub) > SAMPLE:
            sub = sub.sample(SAMPLE, random_state=SEED)
        X, y = sub[feats], sub["target"].values
        rf = RandomForestRegressor(n_estimators=300, n_jobs=-1, random_state=SEED,
                                   min_samples_leaf=20)
        rf.fit(X, y)
        Xs = X.sample(min(SHAP_N, len(X)), random_state=SEED)
        sv = shap.TreeExplainer(rf).shap_values(Xs, check_additivity=False)
        mabs = pd.Series(np.abs(sv).mean(0), index=feats)
        np.save(OUTT / f"shap_values_{reg}_{period}.npy", sv)
        Xs.to_csv(OUTT / f"X_{reg}_{period}.csv", index=False)
        imp = pd.DataFrame({"driver": mabs.index, "mean_abs_shap": mabs.values})
        imp["group"] = np.where(imp.driver.isin(RS_INTERNAL), "OBSERVED RS (model-internal)", "EXOGENOUS")
        imp["driver_label"] = imp.driver.map(PRETTY).fillna(imp.driver)
        imp["region"] = reg; imp["period"] = period
        imp = imp.sort_values("mean_abs_shap", ascending=False)
        imp.to_csv(OUTT / f"shap_importance_{reg}_{period}.csv", index=False, encoding="utf-8")
        rows_all.append(imp)
        r2 = rf.score(X, y)
        top_exo = imp[imp.group == "EXOGENOUS"].iloc[0]
        print(f"  {reg}/{period}: {len(sub):,} px  R2={r2:.2f}  top-exo={top_exo.driver}")
    return pd.concat(rows_all, ignore_index=True) if rows_all else pd.DataFrame()


REG_LAB = {"NE": "NE China", "DXAL": "Daxing'an.", "XXAL": "Xiaoxing'an.",
           "CBS": "Changbai", "SJP": "Sanjiang", "PERMA": "Permafrost"}


def figure(allimp, period):
    d = allimp[allimp.period == period]
    if d.empty:
        return
    mat = d.pivot_table(index="driver_label", columns="region", values="mean_abs_shap")
    # order rows by ecological process (succession→climate→disturbance→topography→RS)
    order = sorted(mat.index, key=lambda lab: (NS.ECO_ORDER.index(NS.eco_group(lab)),
                                               -mat.loc[lab].mean()))
    mat = mat.loc[order]
    regs = [r for r in ["NE", "DXAL", "XXAL", "CBS", "SJP", "PERMA"] if r in mat.columns]
    mat = mat[regs]
    fig, ax = plt.subplots(figsize=(NS.SINGLE * 1.55, 5.0))
    matn = mat / mat.max(axis=0)
    im = ax.imshow(matn.values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_xticks(range(len(regs)))
    ax.set_xticklabels([REG_LAB.get(r, r) for r in regs], rotation=35, ha="right")
    ax.set_yticks(range(len(mat.index)))
    ax.set_yticklabels([NS.eco_label(lab) for lab in mat.index])
    # colour each driver label by its ecological process
    for tick, lab in zip(ax.get_yticklabels(), mat.index):
        tick.set_color(NS.ECO[NS.eco_group(lab)])
    ax.tick_params(length=0)
    for j, reg in enumerate(regs):
        if reg in ("DXAL", "XXAL"):
            ax.add_patch(plt.Rectangle((j - 0.5, -0.5), 1, len(mat.index), fill=False,
                         ec="#D55E00", lw=1.4, clip_on=False))
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("rel. mean|SHAP|", fontsize=6); cb.ax.tick_params(labelsize=5, length=2)
    ax.set_title(f"{'2005–2015' if period=='05_15' else '2015–2024'}", fontsize=7.5, loc="left")
    fig.legend(handles=NS.eco_legend_handles(), loc="upper center", ncol=2,
               fontsize=5.2, handlelength=1.1, bbox_to_anchor=(0.5, 1.02))
    NS.save(fig, str(OUTF / f"Figure_SHAP_augmented_{period}"))


def main(figs_only=False):
    if figs_only:
        allimp = pd.read_csv(OUTT / "shap_importance_all.csv")
        for period in ["05_15", "15_24"]:
            figure(allimp, period)
        print("done (figures only)")
        return
    H, W, transform, crs = grid()
    allimp = []
    for period in ["05_15", "15_24"]:
        a = run_period(period, H, W, transform, crs)
        if not a.empty:
            allimp.append(a)
    allimp = pd.concat(allimp, ignore_index=True)
    allimp.to_csv(OUTT / "shap_importance_all.csv", index=False, encoding="utf-8")
    print("\nwrote shap_importance_all.csv", allimp.shape)
    for period in ["05_15", "15_24"]:
        figure(allimp, period)
    print("done")


if __name__ == "__main__":
    import sys
    main(figs_only=("figs" in sys.argv))
