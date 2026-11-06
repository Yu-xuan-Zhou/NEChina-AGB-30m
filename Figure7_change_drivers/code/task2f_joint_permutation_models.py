#!/usr/bin/env python3
"""
TASK 2f -- final Figure 7 grouped joint-permutation models.

Final Figure 7 uses two response models:
  * density: AGB density change (dAGB)
  * area: forest-fraction change

Environmental factors are estimated from exogenous-only Random Forest models.
All variables within a factor are permuted jointly on a validation split and the
drop in R2 is recorded. Starting-state constraints are fitted separately as the
R2 gain from adding baseline state variables to the exogenous-only model.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from scipy.stats import spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


RES = Path(os.environ.get("AGB_NE_RES_DIR", r"I:\AGB_models\Res"))
DF = RES / "df"
COV = Path(os.environ.get("AGB_NE_COV_DIR", r"E:\DATA\Python\AGB_NE\R3_revision\covariates_1km"))
GAT = Path(os.environ.get("AGB_NE_GATE_DIR", str(RES / "gating")))
OUT = Path(os.environ.get("AGB_NE_TABLE_DIR", r"E:\DATA\Python\AGB_NE\R3_revision\tables"))
REGION = Path(os.environ.get("AGB_NE_REGION_PATH", r"I:\Shp\SHP\dongbei.shp"))
TEMPLATE = RES / "RF_2005_res1km.tif"

SEED = 42
MAX_FIT = 120_000
N_TREES = 300
MIN_LEAF = 20
N_PERM = 50
N_BOOT = 500
TEST_SIZE = 0.30

PERIOD_LABEL = {"05_15": "2005-2015", "15_24": "2015-2024"}


@dataclass(frozen=True)
class Factor:
    name: str
    variables: tuple[str, ...]
    label: str
    kind: str = "environmental"


DENSITY_ENV_FACTORS = [
    Factor("Water availability", ("period_pdsi", "period_soil", "period_pr"), "Water availability"),
    Factor("Drought and heat stress", ("period_def", "period_vpd", "period_lst"), "Drought and heat stress"),
    Factor("Terrain", ("Elevation", "Slope"), "Terrain"),
]
DENSITY_START = Factor(
    "Starting-state constraint",
    ("initAGB",),
    "Initial AGB\nbaseline/recovery",
    kind="starting_state",
)

AREA_ENV_FACTORS = [
    Factor("Disturbance", ("hansen_loss_inperiod",), "Forest loss"),
    Factor("Water availability", ("period_pdsi", "period_soil", "period_pr"), "Water availability"),
    Factor("Drought and heat stress", ("period_def", "period_vpd", "period_lst"), "Drought and heat stress"),
    Factor("Terrain", ("Elevation", "Slope"), "Terrain"),
]
AREA_START = Factor(
    "Starting-state constraint",
    ("fracstart", "dist_to_forest"),
    "Initial forest fraction\n+ distance-to-forest",
    kind="starting_state",
)

PERIOD = {
    "05_15": {
        "density_target": DF / "RF_d05_15_res1km.tif",
        "init_agb": RES / "RF_2005_res1km.tif",
        "forest": RES / "forest_mask_2005.tif",
        "gated": True,
        "area_target": COV / "afforest_delta_05_15.tif",
        "fracstart": COV / "afforest_frac_2005.tif",
        "dist_to_forest": COV / "dist_to_forest_2005.tif",
        "hansen_loss": COV / "hansen_loss_frac_05_15.tif",
    },
    "15_24": {
        "density_target": DF / "RF_d15_24_res1km.tif",
        "init_agb": RES / "RF_2015_res1km.tif",
        "forest": RES / "forest_mask_2015.tif",
        "gated": False,
        "area_target": COV / "afforest_delta_15_24.tif",
        "fracstart": COV / "afforest_frac_2015.tif",
        "dist_to_forest": COV / "dist_to_forest_2015.tif",
        "hansen_loss": COV / "hansen_loss_frac_16_23.tif",
    },
}


def read1(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        arr = src.read(1).astype("float64")
        nodata = src.nodata
    if nodata is not None:
        arr = np.where(arr == nodata, np.nan, arr)
    arr = np.where(np.abs(arr) >= 1e30, np.nan, arr)
    return arr.ravel()


def period_climate(period: str) -> dict[str, np.ndarray]:
    return {
        name: read1(COV / f"{name}_{period}.tif")
        for name in ["period_pdsi", "period_def", "period_vpd", "period_soil", "period_pr", "period_lst"]
    }


def common_static() -> dict[str, np.ndarray]:
    return {
        "Elevation": read1(RES / "Elevation_res1km.tif"),
        "Slope": read1(RES / "Slope_res1km.tif"),
    }


def region_mask() -> np.ndarray:
    with rasterio.open(TEMPLATE) as tmpl:
        shape = (tmpl.height, tmpl.width)
        transform = tmpl.transform
        crs = tmpl.crs
    shp = gpd.read_file(REGION).to_crs(crs)
    return rasterize([(geom, 1) for geom in shp.geometry], out_shape=shape, transform=transform,
                     fill=0, dtype="uint8").ravel()


def sample_frame(df: pd.DataFrame, seed_offset: int) -> pd.DataFrame:
    if len(df) > MAX_FIT:
        return df.sample(MAX_FIT, random_state=SEED + seed_offset)
    return df


def build_density_frame(period: str, static: dict[str, np.ndarray]) -> pd.DataFrame:
    p = PERIOD[period]
    data = dict(static)
    data.update(period_climate(period))
    data["initAGB"] = read1(p["init_agb"])
    data["target"] = read1(p["density_target"])
    data["forest"] = read1(p["forest"])
    data["sig"] = read1(GAT / "sig_mask_k1.0_1km.tif") if p["gated"] else np.ones_like(data["target"])
    df = pd.DataFrame(data)
    env_features = [v for factor in DENSITY_ENV_FACTORS for v in factor.variables]
    full_features = env_features + list(DENSITY_START.variables)
    mask = (df["forest"] == 1) & (df["sig"] == 1)
    return sample_frame(df.loc[mask, full_features + ["target"]].dropna(), 10 if period == "05_15" else 20)


def build_area_frame(period: str, static: dict[str, np.ndarray], region: np.ndarray) -> pd.DataFrame:
    p = PERIOD[period]
    data = dict(static)
    data.update(period_climate(period))
    data["hansen_loss_inperiod"] = np.nan_to_num(read1(p["hansen_loss"]), nan=0.0)
    data["fracstart"] = read1(p["fracstart"])
    data["dist_to_forest"] = read1(p["dist_to_forest"])
    data["target"] = read1(p["area_target"])
    data["region"] = region
    df = pd.DataFrame(data)
    env_features = [v for factor in AREA_ENV_FACTORS for v in factor.variables]
    full_features = env_features + list(AREA_START.variables)
    mask = (df["region"] == 1) & (df["fracstart"] < 0.95)
    return sample_frame(df.loc[mask, full_features + ["target"]].dropna(), 30 if period == "05_15" else 40)


def fit_rf(X: np.ndarray, y: np.ndarray) -> RandomForestRegressor:
    model = RandomForestRegressor(
        n_estimators=N_TREES,
        min_samples_leaf=MIN_LEAF,
        n_jobs=-1,
        random_state=SEED,
        oob_score=False,
    )
    model.fit(X, y)
    return model


def bootstrap_group_betas(X: np.ndarray, y: np.ndarray, features: list[str], factors: list[Factor]) -> pd.DataFrame:
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    ys = (y - y.mean()) / y.std()
    n = len(ys)
    rng = np.random.default_rng(SEED + 901)
    beta_draws = []
    k = max(10, int(0.7 * n))
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, k)
        beta, *_ = np.linalg.lstsq(np.c_[np.ones(k), Xs[idx]], ys[idx], rcond=None)
        beta_draws.append(beta[1:])
    beta_draws = np.asarray(beta_draws)
    rows = []
    for factor in factors:
        cols = [features.index(v) for v in factor.variables]
        draws = beta_draws[:, cols].sum(axis=1)
        mean = float(draws.mean())
        lo = float(np.percentile(draws, 2.5))
        hi = float(np.percentile(draws, 97.5))
        if lo > 0:
            sign = "+"
        elif hi < 0:
            sign = "-"
        else:
            sign = "0"
        rows.append({
            "factor": factor.name,
            "factor_label": factor.label,
            "beta_mean": mean,
            "beta_lo": lo,
            "beta_hi": hi,
            "direction": sign,
            "direction_source": "bootstrap_group_beta",
        })
    return pd.DataFrame(rows)


def grouped_permutation(
    model: RandomForestRegressor,
    X: np.ndarray,
    y: np.ndarray,
    features: list[str],
    factors: list[Factor],
    outcome: str,
    period: str,
) -> pd.DataFrame:
    baseline = r2_score(y, model.predict(X))
    rng = np.random.default_rng(SEED + 1000 + (0 if period == "05_15" else 100) + (0 if outcome == "density" else 10))
    rows = []
    for factor in factors:
        cols = [features.index(v) for v in factor.variables]
        for rep in range(N_PERM):
            Xp = X.copy()
            perm = rng.permutation(len(Xp))
            Xp[:, cols] = Xp[perm][:, cols]
            permuted = r2_score(y, model.predict(Xp))
            rows.append({
                "outcome": outcome,
                "period_code": period,
                "period": PERIOD_LABEL[period],
                "factor": factor.name,
                "factor_label": factor.label,
                "factor_type": factor.kind,
                "variables": ";".join(factor.variables),
                "repeat": rep + 1,
                "baseline_r2": baseline,
                "permuted_r2": permuted,
                "delta_r2": baseline - permuted,
            })
    return pd.DataFrame(rows)


def run_one(outcome: str, period: str, frame: pd.DataFrame, factors: list[Factor], start_factor: Factor):
    env_features = [v for factor in factors for v in factor.variables]
    start_features = list(start_factor.variables)
    full_features = env_features + start_features
    train, test = train_test_split(frame, test_size=TEST_SIZE, random_state=SEED, shuffle=True)

    X_train = train[env_features].to_numpy()
    X_test = test[env_features].to_numpy()
    y_train = train["target"].to_numpy()
    y_test = test["target"].to_numpy()

    exo_model = fit_rf(X_train, y_train)
    exo_r2 = float(exo_model.score(X_test, y_test))
    perm = grouped_permutation(exo_model, X_test, y_test, env_features, factors, outcome, period)
    beta = bootstrap_group_betas(X_train, y_train, env_features, factors)
    beta["outcome"] = outcome
    beta["period_code"] = period
    beta["period"] = PERIOD_LABEL[period]

    Xf_train = train[full_features].to_numpy()
    Xf_test = test[full_features].to_numpy()
    full_model = fit_rf(Xf_train, y_train)
    full_r2 = float(full_model.score(Xf_test, y_test))
    start_delta = max(0.0, full_r2 - exo_r2)

    start_rows = pd.DataFrame([{
        "outcome": outcome,
        "period_code": period,
        "period": PERIOD_LABEL[period],
        "factor": start_factor.name,
        "factor_label": start_factor.label,
        "factor_type": start_factor.kind,
        "variables": ";".join(start_features),
        "delta_r2": start_delta,
        "exo_r2": exo_r2,
        "full_r2": full_r2,
        "n_train": len(train),
        "n_test": len(test),
    }])
    r2 = pd.DataFrame([{
        "outcome": outcome,
        "period_code": period,
        "period": PERIOD_LABEL[period],
        "n_total": len(frame),
        "n_train": len(train),
        "n_test": len(test),
        "exo_r2": exo_r2,
        "full_r2": full_r2,
        "starting_state_delta_r2": start_delta,
    }])
    print(f"{outcome} {period}: exo R2={exo_r2:.3f}, full R2={full_r2:.3f}, start gain={start_delta:.3f}")
    return perm, beta, start_rows, r2


def summarize(perm: pd.DataFrame, beta: pd.DataFrame, start: pd.DataFrame) -> pd.DataFrame:
    env = (
        perm.groupby(["outcome", "factor", "factor_label", "factor_type", "variables"], as_index=False)
        .agg(
            delta_r2_mean=("delta_r2", "mean"),
            delta_r2_lo=("delta_r2", lambda x: np.percentile(x, 2.5)),
            delta_r2_hi=("delta_r2", lambda x: np.percentile(x, 97.5)),
        )
    )
    beta_summary = (
        beta.groupby(["outcome", "factor", "factor_label"], as_index=False)
        .agg(
            beta_mean=("beta_mean", "mean"),
            beta_lo=("beta_lo", "min"),
            beta_hi=("beta_hi", "max"),
        )
    )
    beta_summary["direction"] = np.where(
        beta_summary["beta_lo"] > 0, "+", np.where(beta_summary["beta_hi"] < 0, "-", "0")
    )
    env = env.merge(beta_summary, on=["outcome", "factor", "factor_label"], how="left")
    env["direction_source"] = "bootstrap_group_beta"

    start_summary = (
        start.groupby(["outcome", "factor", "factor_label", "factor_type", "variables"], as_index=False)
        .agg(
            delta_r2_mean=("delta_r2", "mean"),
            delta_r2_lo=("delta_r2", "min"),
            delta_r2_hi=("delta_r2", "max"),
        )
    )
    start_summary["beta_mean"] = np.nan
    start_summary["beta_lo"] = np.nan
    start_summary["beta_hi"] = np.nan
    start_summary["direction"] = "state"
    start_summary["direction_source"] = "full_minus_exogenous_r2"

    out = pd.concat([start_summary, env], ignore_index=True)
    order = {
        ("density", "Starting-state constraint"): 1,
        ("density", "Water availability"): 2,
        ("density", "Drought and heat stress"): 3,
        ("density", "Terrain"): 4,
        ("area", "Starting-state constraint"): 1,
        ("area", "Disturbance"): 2,
        ("area", "Water availability"): 3,
        ("area", "Drought and heat stress"): 4,
        ("area", "Terrain"): 5,
    }
    out["plot_order"] = [order.get((r.outcome, r.factor), 99) for r in out.itertuples()]
    return out.sort_values(["outcome", "plot_order"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    static = common_static()
    region = region_mask()

    frames = {
        ("density", "05_15"): build_density_frame("05_15", static),
        ("density", "15_24"): build_density_frame("15_24", static),
        ("area", "05_15"): build_area_frame("05_15", static, region),
        ("area", "15_24"): build_area_frame("15_24", static, region),
    }

    perm_parts = []
    beta_parts = []
    start_parts = []
    r2_parts = []
    for period in ["05_15", "15_24"]:
        perm, beta, start, r2 = run_one("density", period, frames[("density", period)],
                                        DENSITY_ENV_FACTORS, DENSITY_START)
        perm_parts.append(perm); beta_parts.append(beta); start_parts.append(start); r2_parts.append(r2)
        perm, beta, start, r2 = run_one("area", period, frames[("area", period)],
                                        AREA_ENV_FACTORS, AREA_START)
        perm_parts.append(perm); beta_parts.append(beta); start_parts.append(start); r2_parts.append(r2)

    perm = pd.concat(perm_parts, ignore_index=True)
    beta = pd.concat(beta_parts, ignore_index=True)
    start = pd.concat(start_parts, ignore_index=True)
    r2 = pd.concat(r2_parts, ignore_index=True)
    summary = summarize(perm, beta, start)

    perm.to_csv(OUT / "fig7_jointperm_repeats.csv", index=False, encoding="utf-8")
    beta.to_csv(OUT / "fig7_jointperm_bootstrap_group_betas.csv", index=False, encoding="utf-8")
    start.to_csv(OUT / "fig7_jointperm_starting_state_period.csv", index=False, encoding="utf-8")
    r2.to_csv(OUT / "fig7_jointperm_model_r2.csv", index=False, encoding="utf-8")
    summary.to_csv(OUT / "fig7_jointperm_summary.csv", index=False, encoding="utf-8")
    print("wrote fig7_jointperm_* tables")


if __name__ == "__main__":
    main()
