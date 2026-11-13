"""Normalize retained Figure 7 model results and render the corrected figure."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "tables"
MODEL_KEYS = ["outcome", "period_code"]
STRUCTURE_FACTOR = "Forest structure / starting state"
FACTOR_ORDER = {
    STRUCTURE_FACTOR: 1, "Precipitation": 2, "Soil moisture": 3,
    "Water deficit": 4, "VPD": 5, "LST": 6, "Terrain": 7,
}
PERIOD_ORDER = {"05_15": 0, "15_24": 1}


def normalize_importance(repeats, beta):
    """Scale means and permutation ranges by a fixed denominator per model."""
    data = repeats.groupby(
        MODEL_KEYS + ["period", "factor", "factor_label", "factor_type", "variables"],
        as_index=False,
    ).agg(
        delta_r2_mean=("delta_r2", "mean"),
        delta_r2_lo=("delta_r2", lambda x: np.percentile(x, 2.5)),
        delta_r2_hi=("delta_r2", lambda x: np.percentile(x, 97.5)),
    )
    join_keys = MODEL_KEYS + ["period", "factor", "factor_label"]
    data = data.merge(
        beta[join_keys + ["beta_mean", "beta_lo", "beta_hi", "direction", "direction_source"]],
        on=join_keys, how="left", validate="one_to_one",
    )
    data["plot_order"] = data.factor.map(FACTOR_ORDER)
    data["period_order"] = data.period_code.map(PERIOD_ORDER)
    data.loc[data.variables.eq("dLST"), "factor_label"] = "\u0394LST"
    data["period_denominator_delta_r2"] = np.nan
    data["relative_importance_pct"] = np.nan
    data["relative_importance_lo_pct"] = np.nan
    data["relative_importance_hi_pct"] = np.nan
    for model, idx in data.groupby(MODEL_KEYS).groups.items():
        positive = data.loc[idx, "delta_r2_mean"].clip(lower=0)
        denominator = float(positive.sum())
        if not np.isfinite(denominator) or denominator <= 0:
            raise ValueError(f"No finite positive mean importance for {model}")
        data.loc[idx, "period_denominator_delta_r2"] = denominator
        data.loc[idx, "relative_importance_pct"] = 100.0 * positive / denominator
        for bound in ["lo", "hi"]:
            data.loc[idx, f"relative_importance_{bound}_pct"] = (
                100.0 * data.loc[idx, f"delta_r2_{bound}"].clip(lower=0) / denominator
            )
    return data.sort_values(["outcome", "plot_order", "period_order"])


def load_tables(write_output=False):
    """Validate original model outputs and calculate the normalized display."""
    repeats = pd.read_csv(TABLE_DIR / "fig7_hybrid_repeats.csv")
    beta = pd.read_csv(TABLE_DIR / "fig7_hybrid_bootstrap_betas.csv")
    r2 = pd.read_csv(TABLE_DIR / "fig7_hybrid_model_r2.csv")
    keys = MODEL_KEYS + ["factor"]
    assert len(repeats) == 1400, "Expected 4 models x 7 factors x 50 repeats"
    assert not repeats.duplicated(keys + ["repeat"]).any()
    assert repeats.groupby(keys).size().eq(50).all()
    assert len(beta) == 28 and not beta.duplicated(keys).any()
    assert len(r2) == 4 and not r2.duplicated(MODEL_KEYS).any()
    assert set(zip(r2.outcome, r2.period_code)) == {
        (outcome, period) for outcome in ["density", "area"] for period in PERIOD_ORDER
    }
    assert repeats.groupby(MODEL_KEYS).factor.agg(set).apply(lambda x: x == set(FACTOR_ORDER)).all()
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
    data = normalize_importance(repeats, beta)
    assert len(data) == 28
    np.testing.assert_allclose(data.groupby(MODEL_KEYS).relative_importance_pct.sum(), 100)
    assert np.isfinite(data.relative_importance_pct).all()
    assert (data.relative_importance_pct >= 0).all()
    assert data.direction.isin(["+", "-", "0"]).all()
    if write_output:
        data.to_csv(TABLE_DIR / "fig7_hybrid_period_display.csv", index=False)
    data["display_role"] = np.where(
        data.factor.eq(STRUCTURE_FACTOR), "starting_state", "climate_or_terrain"
    )
    data["display_direction"] = np.where(
        data.display_role.eq("starting_state"), "neutral",
        data.direction.map({"+": "positive association", "-": "negative association", "0": "uncertain direction"}),
    )
    if write_output:
        data.to_csv(TABLE_DIR / "SourceData_Figure7.csv", index=False)
    return data, r2


def render(data, r2):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

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
    parser.add_argument(
        "action", choices=["check", "render"], nargs="?", default="render",
        help="check the retained CSVs without writing, or normalize and render (default)",
    )
    args = parser.parse_args()
    data, r2 = load_tables(write_output=args.action == "render")
    if args.action == "check":
        print("PASS: 1400 permutations, 28 factor-period rows, 4 models; each model sums to 100%.")
        return
    render(data, r2)
    report = {
        "action": "render", "python": sys.version,
        "packages": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "matplotlib"]},
        "table_checks": "PASS: 1400 permutations, 28 factor-period rows, 4 models",
        "normalization": "seven positive mean Delta R2 values within each outcome-period sum to 100; original model outputs retained",
        "refit_in_this_invocation": False,
    }
    (ROOT / "logs").mkdir(exist_ok=True)
    (ROOT / "logs" / "run_render.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
