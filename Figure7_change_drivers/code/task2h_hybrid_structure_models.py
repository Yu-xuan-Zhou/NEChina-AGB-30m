#!/usr/bin/env python3
"""
TASK 2h -- final hybrid Figure 7 models.

This workflow follows the "hybrid" design:
  * keep a forest-structure / starting-state group as a baseline/recovery
    constraint rather than an environmental feedback,
  * expand key climate-water variables,
  * keep terrain as a grouped factor.

PDSI is omitted from this candidate to reduce overlap with precipitation,
soil moisture, deficit, VPD and LST. Disturbance is omitted so density and
area panels use the same factor set.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

import task2f_joint_permutation_models as base
import variable_config as vc


OUT = base.OUT


@dataclass(frozen=True)
class HybridSpec:
    outcome: str
    factors: list[base.Factor]


DENSITY_FACTORS = [
    base.Factor("Forest structure / starting state", ("initAGB", "treecover2000"), "Forest structure\n/ starting state"),
    base.Factor("Precipitation", ("period_pr",), "Precipitation"),
    base.Factor("Soil moisture", ("period_soil",), "Soil moisture"),
    base.Factor("Water deficit", ("period_def",), "Water deficit"),
    base.Factor("VPD", ("period_vpd",), "VPD"),
    base.Factor("LST", (vc.LST_VAR,), "LST"),   # vc.LST_VAR = "dLST" (change in LST)
    base.Factor("Terrain", ("Elevation", "Slope"), "Terrain"),
]

AREA_FACTORS = [
    base.Factor(
        "Forest structure / starting state",
        ("fracstart", "dist_to_forest", "treecover2000"),
        "Forest structure\n/ starting state",
    ),
    base.Factor("Precipitation", ("period_pr",), "Precipitation"),
    base.Factor("Soil moisture", ("period_soil",), "Soil moisture"),
    base.Factor("Water deficit", ("period_def",), "Water deficit"),
    base.Factor("VPD", ("period_vpd",), "VPD"),
    base.Factor("LST", (vc.LST_VAR,), "LST"),   # vc.LST_VAR = "dLST" (change in LST)
    base.Factor("Terrain", ("Elevation", "Slope"), "Terrain"),
]

FACTOR_ORDER = {
    ("density", "Forest structure / starting state"): 1,
    ("density", "Precipitation"): 2,
    ("density", "Soil moisture"): 3,
    ("density", "Water deficit"): 4,
    ("density", "VPD"): 5,
    ("density", "LST"): 6,
    ("density", "Terrain"): 7,
    ("area", "Forest structure / starting state"): 1,
    ("area", "Precipitation"): 2,
    ("area", "Soil moisture"): 3,
    ("area", "Water deficit"): 4,
    ("area", "VPD"): 5,
    ("area", "LST"): 6,
    ("area", "Terrain"): 7,
}


def feature_list(factors: list[base.Factor]) -> list[str]:
    return [v for factor in factors for v in factor.variables]


def build_density_frame(period: str, static: dict[str, np.ndarray]) -> pd.DataFrame:
    p = base.PERIOD[period]
    data = dict(static)
    data.update(base.period_climate(period))
    data["dLST"] = base.read1(vc.dlst_raster(base.DF, period))   # ΔLST replaces period_lst
    data["treecover2000"] = base.read1(base.COV / "hansen_treecover2000.tif")
    data["initAGB"] = base.read1(p["init_agb"])
    data["target"] = base.read1(p["density_target"])
    data["forest"] = base.read1(p["forest"])
    data["sig"] = base.read1(base.GAT / "sig_mask_k1.0_1km.tif") if p["gated"] else np.ones_like(data["target"])
    df = pd.DataFrame(data)
    features = feature_list(DENSITY_FACTORS)
    vc.assert_matches(features, vc.DENSITY_FEATURES, "Figure7 density")
    mask = (df["forest"] == 1) & (df["sig"] == 1)
    return base.sample_frame(df.loc[mask, features + ["target"]].dropna(), 110 if period == "05_15" else 120)


def build_area_frame(period: str, static: dict[str, np.ndarray], region: np.ndarray) -> pd.DataFrame:
    p = base.PERIOD[period]
    data = dict(static)
    data.update(base.period_climate(period))
    data["dLST"] = base.read1(vc.dlst_raster(base.DF, period))   # ΔLST replaces period_lst
    data["treecover2000"] = base.read1(base.COV / "hansen_treecover2000.tif")
    data["fracstart"] = base.read1(p["fracstart"])
    data["dist_to_forest"] = base.read1(p["dist_to_forest"])
    data["target"] = base.read1(p["area_target"])
    data["region"] = region
    df = pd.DataFrame(data)
    features = feature_list(AREA_FACTORS)
    vc.assert_matches(features, vc.AREA_FEATURES, "Figure7 area")
    mask = (df["region"] == 1) & (df["fracstart"] < 0.95)
    return base.sample_frame(df.loc[mask, features + ["target"]].dropna(), 130 if period == "05_15" else 140)


def run_one(outcome: str, period: str, frame: pd.DataFrame, factors: list[base.Factor]):
    features = feature_list(factors)
    structure_vars = list(factors[0].variables)
    climate_terrain_features = [f for f in features if f not in structure_vars]

    train, test = train_test_split(frame, test_size=base.TEST_SIZE, random_state=base.SEED, shuffle=True)
    y_train = train["target"].to_numpy()
    y_test = test["target"].to_numpy()

    model = base.fit_rf(train[features].to_numpy(), y_train)
    model_r2 = float(model.score(test[features].to_numpy(), y_test))
    perm = base.grouped_permutation(model, test[features].to_numpy(), y_test, features, factors, outcome, period)
    beta = base.bootstrap_group_betas(train[features].to_numpy(), y_train, features, factors)
    beta["outcome"] = outcome
    beta["period_code"] = period
    beta["period"] = base.PERIOD_LABEL[period]

    climate_terrain_model = base.fit_rf(train[climate_terrain_features].to_numpy(), y_train)
    climate_terrain_r2 = float(climate_terrain_model.score(test[climate_terrain_features].to_numpy(), y_test))
    structure_diagnostic_delta_r2 = max(0.0, model_r2 - climate_terrain_r2)

    r2 = pd.DataFrame([{
        "outcome": outcome,
        "period_code": period,
        "period": base.PERIOD_LABEL[period],
        "n_total": len(frame),
        "n_train": len(train),
        "n_test": len(test),
        "hybrid_r2": model_r2,
        "climate_terrain_r2": climate_terrain_r2,
        "structure_diagnostic_delta_r2": structure_diagnostic_delta_r2,
        "structure_variables": ";".join(structure_vars),
    }])
    print(
        f"{outcome} {period}: hybrid R2={model_r2:.3f}, "
        f"climate+terrain-only R2={climate_terrain_r2:.3f}, "
        f"structure diagnostic delta R2={structure_diagnostic_delta_r2:.3f}"
    )
    return perm, beta, r2


def summarize(perm: pd.DataFrame, beta: pd.DataFrame) -> pd.DataFrame:
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
    out = env.merge(beta_summary, on=["outcome", "factor", "factor_label"], how="left")
    out["direction_source"] = "bootstrap_group_beta"
    out["plot_order"] = [FACTOR_ORDER.get((r.outcome, r.factor), 99) for r in out.itertuples()]
    return out.sort_values(["outcome", "plot_order"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    static = base.common_static()
    region = base.region_mask()

    frames = {
        ("density", "05_15"): build_density_frame("05_15", static),
        ("density", "15_24"): build_density_frame("15_24", static),
        ("area", "05_15"): build_area_frame("05_15", static, region),
        ("area", "15_24"): build_area_frame("15_24", static, region),
    }

    perm_parts = []
    beta_parts = []
    r2_parts = []
    for period in ["05_15", "15_24"]:
        perm, beta, r2 = run_one("density", period, frames[("density", period)], DENSITY_FACTORS)
        perm_parts.append(perm)
        beta_parts.append(beta)
        r2_parts.append(r2)

        perm, beta, r2 = run_one("area", period, frames[("area", period)], AREA_FACTORS)
        perm_parts.append(perm)
        beta_parts.append(beta)
        r2_parts.append(r2)

    perm = pd.concat(perm_parts, ignore_index=True)
    beta = pd.concat(beta_parts, ignore_index=True)
    r2 = pd.concat(r2_parts, ignore_index=True)
    summary = summarize(perm, beta)

    perm.to_csv(OUT / "fig7_hybrid_repeats.csv", index=False)
    beta.to_csv(OUT / "fig7_hybrid_bootstrap_betas.csv", index=False)
    r2.to_csv(OUT / "fig7_hybrid_model_r2.csv", index=False)
    summary.to_csv(OUT / "fig7_hybrid_summary.csv", index=False)
    print("wrote fig7_hybrid_* tables")


if __name__ == "__main__":
    main()
