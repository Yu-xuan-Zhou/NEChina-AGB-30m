#!/usr/bin/env python3
"""
TASK 5d -- final hybrid Figure 7 display.

Design:
  * Forest structure / starting-state group is plotted as a neutral baseline
    constraint, not as an environmental feedback.
  * Climate-water is expanded to precipitation, soil moisture, deficit, VPD and LST.
  * Terrain is kept as one grouped factor.

Bar length = period-specific grouped permutation importance normalized within
each panel to sum to 100%.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "tables"
FIG_DIR = ROOT / "figures"

REPEATS = TABLE_DIR / "fig7_hybrid_repeats.csv"
BETAS = TABLE_DIR / "fig7_hybrid_bootstrap_betas.csv"
R2 = TABLE_DIR / "fig7_hybrid_model_r2.csv"
DISPLAY_TABLE = TABLE_DIR / "fig7_hybrid_period_display.csv"

COLORS = {
    "+": "#3F7FD6",
    "-": "#D84A4A",
    "0": "#B8B8B8",
    "structure": "#8D8D86",
}

PANEL_TITLE = {
    "density": "Density model - target: $\\Delta$AGB",
    "area": "Area model - target: forest-fraction change",
}

STRUCTURE_FACTOR = "Forest structure / starting state"
PERIOD_SHORT = {"05_15": "05-15", "15_24": "15-24"}
PERIOD_ORDER = {"05_15": 0, "15_24": 1}
FACTOR_ORDER = {
    "Forest structure / starting state": 1,
    "Precipitation": 2,
    "Soil moisture": 3,
    "Water deficit": 4,
    "VPD": 5,
    "LST": 6,
    "Terrain": 7,
}


def apply_style() -> None:
    mpl.rcParams.update({
        "font.family": "Arial",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 7.5,
        "axes.linewidth": 0.55,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "svg.fonttype": "none",
        "xtick.major.size": 2.5,
        "xtick.major.width": 0.55,
        "ytick.major.size": 0,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def require_inputs() -> None:
    missing = [p for p in [REPEATS, BETAS, R2] if not p.exists()]
    if missing:
        names = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(f"Missing hybrid Figure 7 inputs: {names}. Run task2h_hybrid_structure_models.py.")


def nice_limit(values: pd.Series) -> float:
    mx = float(np.nanmax(values.to_numpy(dtype=float)))
    return max(10.0, float(np.ceil((mx + 1.0) / 5.0) * 5.0))


def build_display_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    require_inputs()
    repeats = pd.read_csv(REPEATS)
    betas = pd.read_csv(BETAS)
    r2 = pd.read_csv(R2)

    data = (
        repeats.groupby(
            ["outcome", "period_code", "period", "factor", "factor_label", "factor_type", "variables"],
            as_index=False,
        )
        .agg(
            delta_r2_mean=("delta_r2", "mean"),
            delta_r2_lo=("delta_r2", lambda x: np.percentile(x, 2.5)),
            delta_r2_hi=("delta_r2", lambda x: np.percentile(x, 97.5)),
        )
    )
    data = data.merge(
        betas[
            [
                "outcome",
                "period_code",
                "period",
                "factor",
                "factor_label",
                "beta_mean",
                "beta_lo",
                "beta_hi",
                "direction",
                "direction_source",
            ]
        ],
        on=["outcome", "period_code", "period", "factor", "factor_label"],
        how="left",
    )
    data["plot_order"] = [FACTOR_ORDER.get(r.factor, 99) for r in data.itertuples()]
    data["period_order"] = [PERIOD_ORDER.get(r.period_code, 99) for r in data.itertuples()]
    data.loc[data["variables"].eq("dLST"), "factor_label"] = "\u0394LST"
    data["panel_denominator_delta_r2"] = np.nan
    data["relative_importance_pct"] = np.nan
    data["relative_importance_lo_pct"] = np.nan
    data["relative_importance_hi_pct"] = np.nan
    for outcome, idx in data.groupby("outcome").groups.items():
        denom = float(data.loc[idx, "delta_r2_mean"].sum())
        if denom <= 0:
            continue
        data.loc[idx, "panel_denominator_delta_r2"] = denom
        data.loc[idx, "relative_importance_pct"] = 100.0 * data.loc[idx, "delta_r2_mean"] / denom
        data.loc[idx, "relative_importance_lo_pct"] = 100.0 * data.loc[idx, "delta_r2_lo"] / denom
        data.loc[idx, "relative_importance_hi_pct"] = 100.0 * data.loc[idx, "delta_r2_hi"] / denom
    data = data.sort_values(["outcome", "plot_order", "period_order"])
    data.to_csv(DISPLAY_TABLE, index=False, encoding="utf-8")
    return data, r2


def panel_layout(sub: pd.DataFrame) -> tuple[dict[tuple[str, str], float], list[float], list[str], float]:
    y_for: dict[tuple[str, str], float] = {}
    tick_pos: list[float] = []
    tick_labels: list[str] = []
    y = 0.0
    for _, group in sub.groupby("plot_order", sort=True):
        group = group.sort_values("period_order")
        ys = []
        for _, row in group.iterrows():
            yy = y
            y_for[(row["factor"], row["period_code"])] = yy
            ys.append(yy)
            y -= 0.34
        tick_pos.append(float(np.mean(ys)))
        tick_labels.append(group.iloc[0]["factor_label"])
        y -= 0.32
    return y_for, tick_pos, tick_labels, y


def r2_annotation(r2: pd.DataFrame, outcome: str) -> str:
    sub = r2[r2["outcome"] == outcome].sort_values("period_code")
    parts = [f"{PERIOD_SHORT[row['period_code']]} $R^2$={row['hybrid_r2']:.2f}" for _, row in sub.iterrows()]
    return "Model " + "; ".join(parts)


def draw_panel(ax, data: pd.DataFrame, r2: pd.DataFrame, outcome: str, letter: str, xlim: float) -> None:
    sub = data[data["outcome"] == outcome].sort_values(["plot_order", "period_order"]).reset_index(drop=True)
    y_for, tick_pos, tick_labels, ymin = panel_layout(sub)

    for _, row in sub.iterrows():
        yy = y_for[(row["factor"], row["period_code"])]
        mean = float(row["relative_importance_pct"])
        lo = float(row["relative_importance_lo_pct"])
        hi = float(row["relative_importance_hi_pct"])
        color = COLORS["structure"] if row["factor"] == STRUCTURE_FACTOR else COLORS[row["direction"]]
        ax.barh(yy, mean, height=0.24, color=color, edgecolor=color, linewidth=0.45, zorder=3)
        ax.errorbar(
            mean,
            yy,
            xerr=np.array([[max(0, mean - lo)], [max(0, hi - mean)]]),
            fmt="none",
            ecolor="0.30",
            elinewidth=0.55,
            capsize=1.8,
            capthick=0.55,
            zorder=4,
        )
        ax.text(
            -0.018 * xlim,
            yy,
            PERIOD_SHORT.get(row["period_code"], row["period_code"]),
            ha="right",
            va="center",
            fontsize=5.8,
            color="0.35",
            clip_on=False,
        )

    ax.set_yticks(tick_pos)
    ax.set_yticklabels(tick_labels, fontsize=7.0)
    ax.set_ylim(ymin + 0.18, 1.05)
    ax.set_xlim(0, xlim)
    ax.set_xlabel("Relative permutation importance (%)", fontsize=7.0)
    ax.grid(axis="x", color="0.88", lw=0.4, zorder=0)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("0.4")
    ax.tick_params(axis="x", labelsize=6.7)
    ax.tick_params(axis="y", pad=23)
    ax.set_title(PANEL_TITLE[outcome], loc="left", fontsize=8.4, fontweight="bold", pad=8)
    ax.text(
        0.985,
        0.985,
        r2_annotation(r2, outcome),
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=6.3,
        color="0.35",
        linespacing=1.2,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.88, "pad": 1.5},
    )
    ax.text(-0.17, 1.12, letter, transform=ax.transAxes,
            fontsize=11, fontweight="bold", va="top", ha="right")


def main() -> None:
    apply_style()
    data, r2 = build_display_table()
    xlim = nice_limit(data["relative_importance_hi_pct"])

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.95), sharex=True)
    draw_panel(axes[0], data, r2, "density", "a", xlim)
    draw_panel(axes[1], data, r2, "area", "b", xlim)

    handles = [
        Patch(facecolor=COLORS["structure"], label="forest structure / starting state"),
        Patch(facecolor=COLORS["+"], label="positive association"),
        Patch(facecolor=COLORS["-"], label="negative association"),
        Patch(facecolor=COLORS["0"], label="uncertain direction"),
    ]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.13, 0.005),
               ncol=4, frameon=False, fontsize=6.5, handlelength=1.1, columnspacing=1.25)
    fig.text(
        0.13,
        0.050,
        "Bars: relative grouped permutation importance. Colours: coefficient sign for climate/terrain; "
        "grey = forest-structure / starting-state constraint.",
        fontsize=6.7,
        color="0.25",
    )
    fig.subplots_adjust(left=0.35, right=0.97, top=0.93, bottom=0.12, hspace=0.42)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for stem in [
        FIG_DIR / "Figure7_hybrid_structure_climate_terrain",
        FIG_DIR / "Figure7_ABC_nature",
    ]:
        for ext in ["png", "pdf", "svg"]:
            fig.savefig(f"{stem}.{ext}", dpi=400, bbox_inches="tight", facecolor="white")
        print("wrote", str(stem) + ".png/.pdf/.svg")
    plt.close(fig)


if __name__ == "__main__":
    main()
