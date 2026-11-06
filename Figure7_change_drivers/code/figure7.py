"""Figure 7 submission entry point: check, render, or explicitly refit."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def configure(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    for key, env_name in {
        "res_dir": "AGB_NE_RES_DIR",
        "covariates_dir": "AGB_NE_COV_DIR",
        "gating_dir": "AGB_NE_GATE_DIR",
        "region_path": "AGB_NE_REGION_PATH",
    }.items():
        os.environ[env_name] = config[key]
    os.environ["AGB_NE_TABLE_DIR"] = str(ROOT / "tables")


def load_tables():
    import numpy as np
    import pandas as pd
    import task5d_figure7_hybrid as plot

    plot.TABLE_DIR = ROOT / "tables"
    plot.REPEATS = plot.TABLE_DIR / "fig7_hybrid_repeats.csv"
    plot.BETAS = plot.TABLE_DIR / "fig7_hybrid_bootstrap_betas.csv"
    plot.R2 = plot.TABLE_DIR / "fig7_hybrid_model_r2.csv"
    plot.DISPLAY_TABLE = plot.TABLE_DIR / "fig7_hybrid_period_display.csv"
    repeats = pd.read_csv(plot.REPEATS)
    beta = pd.read_csv(plot.BETAS)
    r2 = pd.read_csv(plot.R2)
    keys = ["outcome", "period_code", "factor"]
    assert len(repeats) == 1400, "Expected 4 models x 7 factors x 50 repeats"
    assert not repeats.duplicated(keys + ["repeat"]).any()
    assert repeats.groupby(keys).size().eq(50).all()
    assert len(beta) == 28 and not beta.duplicated(keys).any()
    assert len(r2) == 4 and not r2.duplicated(["outcome", "period_code"]).any()
    assert set(repeats.loc[repeats.factor.eq("LST"), "variables"]) == {"dLST"}
    np.testing.assert_allclose(
        repeats.delta_r2, repeats.baseline_r2 - repeats.permuted_r2, atol=1e-12
    )
    expected_sign = np.where(beta.beta_lo > 0, "+", np.where(beta.beta_hi < 0, "-", "0"))
    assert (expected_sign == beta.direction).all()
    for row in r2.itertuples():
        sub = repeats[(repeats.outcome == row.outcome) & (repeats.period_code == row.period_code)]
        np.testing.assert_allclose(sub.baseline_r2, row.hybrid_r2, atol=1e-12)
        assert row.n_train + row.n_test == row.n_total
    data, r2 = plot.build_display_table()
    assert len(data) == 28
    np.testing.assert_allclose(data.groupby("outcome").relative_importance_pct.sum(), 100)
    assert np.isfinite(data.relative_importance_pct).all()
    assert (data.relative_importance_pct >= 0).all()
    data["display_role"] = np.where(
        data.factor.eq(plot.STRUCTURE_FACTOR), "starting_state", "climate_or_terrain"
    )
    data["display_direction"] = np.where(
        data.display_role.eq("starting_state"), "neutral",
        data.direction.map({"+": "positive association", "-": "negative association", "0": "uncertain direction"}),
    )
    data.to_csv(ROOT / "tables" / "SourceData_Figure7.csv", index=False)
    return data, r2


def check_inputs():
    import numpy as np
    import rasterio
    import task2f_joint_permutation_models as base
    import task2h_hybrid_structure_models as model
    import variable_config as vc

    vc.assert_matches(model.feature_list(model.DENSITY_FACTORS), vc.DENSITY_FEATURES, "density")
    vc.assert_matches(model.feature_list(model.AREA_FACTORS), vc.AREA_FEATURES, "area")
    paths = {
        base.TEMPLATE: "template / initial AGB 2005",
        base.RES / "Elevation_res1km.tif": "terrain",
        base.RES / "Slope_res1km.tif": "terrain",
        base.GAT / "sig_mask_k1.0_1km.tif": "2005-2015 selection gate",
        base.COV / "hansen_treecover2000.tif": "baseline tree cover",
    }
    for period, spec in base.PERIOD.items():
        for field in ["density_target", "init_agb", "forest", "area_target", "fracstart", "dist_to_forest"]:
            paths[spec[field]] = field
        paths[vc.dlst_raster(base.DF, period)] = "temperature change predictor"
        for var in ["pr", "soil", "def", "vpd", "pdsi", "lst"]:
            paths[base.COV / f"period_{var}_{period}.tif"] = (
                "loaded by shared helper; excluded from fit" if var in {"pdsi", "lst"} else "climate predictor"
            )
    records = []
    with rasterio.open(base.TEMPLATE) as template:
        for path, role in paths.items():
            record = {"path": str(path), "role": role, "exists": path.is_file()}
            if record["exists"]:
                with rasterio.open(path) as src:
                    record.update(
                        shape=[src.height, src.width], crs=str(src.crs),
                        transform=list(src.transform)[:6], nodata=src.nodata,
                        grid_matches_template=(
                            src.shape == template.shape and src.crs == template.crs
                            and np.allclose(tuple(src.transform), tuple(template.transform), rtol=0, atol=1e-10)
                        ),
                    )
            records.append(record)
    for suffix in [".shp", ".shx", ".dbf", ".prj"]:
        path = base.REGION.with_suffix(suffix)
        records.append({"path": str(path), "role": "region boundary", "exists": path.is_file()})
    (ROOT / "logs" / "input_inventory.json").write_text(
        json.dumps(records, indent=2, allow_nan=False), encoding="utf-8"
    )
    assert all(r["exists"] for r in records), "Missing input: inspect logs/input_inventory.json"
    assert all(r.get("grid_matches_template", True) for r in records), "Raster grid mismatch"
    return len(records)


def render(data, r2):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    import numpy as np

    colors = {"neutral": "#7d7d7d", "+": "#2f6fd0", "-": "#d24b3e", "0": "#bfbfbf"}
    plt.rcParams.update({
        "font.family": "Arial", "font.size": 10, "pdf.fonttype": 42,
        "ps.fonttype": 42, "svg.fonttype": "none",
    })
    fig, axes = plt.subplots(2, 1, figsize=(8.8, 10.4))
    xmax = max(30, int(np.ceil(data.relative_importance_hi_pct.max() / 5) * 5))
    for ax, outcome, letter in zip(axes, ["density", "area"], ["a", "b"]):
        sub = data[data.outcome.eq(outcome)].sort_values(["plot_order", "period_order"])
        factors = sub.factor.drop_duplicates().tolist()
        for center, factor in zip(np.arange(len(factors))[::-1], factors):
            for period, label, offset in [("05_15", "05-15", 0.19), ("15_24", "15-24", -0.19)]:
                row = sub[(sub.factor == factor) & (sub.period_code == period)].iloc[0]
                color = colors["neutral"] if row.display_role == "starting_state" else colors[row.direction]
                value = row.relative_importance_pct
                ax.barh(center + offset, value, height=0.34, color=color,
                        edgecolor="white", linewidth=0.6, zorder=3)
                ax.errorbar(value, center + offset,
                            xerr=[[max(value - row.relative_importance_lo_pct, 0)],
                                  [max(row.relative_importance_hi_pct - value, 0)]],
                            fmt="none", color="#333333", elinewidth=0.8, capsize=2, zorder=4)
                ax.text(-0.4, center + offset, label, ha="right", va="center", fontsize=10, color="#555555")
        labels = sub.drop_duplicates("factor").factor_label.tolist()
        ax.set_yticks(np.arange(len(factors))[::-1], labels, fontsize=12)
        ax.tick_params(axis="y", pad=38, length=0)
        ax.set_xlim(0, xmax)
        ax.set_xticks(np.arange(0, xmax + 1, 5))
        ax.set_ylim(-0.6, len(factors) + 0.05)
        ax.set_xlabel("Relative permutation importance (%)", fontsize=12)
        metrics = r2[r2.outcome.eq(outcome)].set_index("period_code").hybrid_r2
        ax.text(1, 0.99,
                f"Holdout $R^2$: 05-15 = {metrics['05_15']:.2f}; 15-24 = {metrics['15_24']:.2f}",
                transform=ax.transAxes, ha="right", va="top", fontsize=10, color="#666666")
        # Panel letters: same point size as the axis labels (12 pt, bold), the
        # convention shared with Figures 4 and 6.
        ax.text(-0.30, 1.02, f"({letter})", transform=ax.transAxes, fontsize=12, fontweight="bold")
        ax.grid(axis="x", color="#dddddd", linewidth=0.6)
        ax.set_axisbelow(True)
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
    handles = [
        Patch(facecolor=colors["neutral"], label="forest structure / starting state"),
        Patch(facecolor=colors["+"], label="positive association"),
        Patch(facecolor=colors["-"], label="negative association"),
        Patch(facecolor=colors["0"], label="uncertain direction"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=10, bbox_to_anchor=(0.5, 0.005))
    fig.subplots_adjust(left=0.34, right=0.97, top=0.95, bottom=0.11, hspace=0.32)
    target = ROOT / "figures"
    target.mkdir(exist_ok=True)
    for ext in ["png", "pdf", "svg"]:
        fig.savefig(target / f"Figure7.{ext}", dpi=400, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["check", "render", "fit"], nargs="?", default="render")
    parser.add_argument("--config", type=Path, default=ROOT / "paths.json")
    args = parser.parse_args()
    configure(args.config)
    for directory in ["tables", "figures", "logs"]:
        (ROOT / directory).mkdir(exist_ok=True)
    if args.action == "fit":
        check_inputs()
        import task2h_hybrid_structure_models as model
        model.main()
    data, r2 = load_tables()
    if args.action == "check":
        count = check_inputs()
        print(f"Input check passed: {count} files; raster headers match the template.")
    else:
        render(data, r2)
    versions = {}
    for package in ["numpy", "pandas", "matplotlib", "scipy", "scikit-learn", "rasterio", "geopandas"]:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed (not needed for this action)"
    report = {
        "action": args.action, "python": sys.version, "packages": versions,
        "table_checks": "PASS: 1400 permutations, 28 factor-period rows, 4 models",
        "normalization": "all 14 bars across both periods within each outcome sum to 100",
        "refit_in_this_invocation": args.action == "fit",
    }
    (ROOT / "logs" / f"run_{args.action}.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
