"""Figure 4 - Methodological and temporal comparison of estimated AGB (RF / Cubist / MLR).

Builds the three panels in ONE matplotlib figure:

  (a) latitude profile of the coefficient of variation      <- precomputed_data.npz
  (b) violin plot of AGB density by year and method,
      including field data                                   <- 6 AGB rasters + field-data workbook
  (c) stacked bars of AGB density classes, field vs models   <- 6 density-class CSVs + field-data workbook

Raster samples for panel (b) are cached in
cache/violin_samples.npz so the figure can be redrawn without re-reading the rasters.

Run from this folder:
    python -X utf8 Figure4_combine.py            # uses cache/violin_samples.npz if present
    python -X utf8 Figure4_combine.py --resample # re-read the rasters

Outputs: output/Figure4_model_comparison.pdf / .png
Units: AGB density in Mg ha-1.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib import patheffects as pe
from matplotlib.patches import Patch
import seaborn as sns

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------- inputs
PRECOMPUTED_NPZ = HERE / "data" / "precomputed_data.npz"   # panel (a); see build_precomputed_data.py
FIELD_XLSX = HERE / "data" / "field_plots_literature.xlsx"   # field plots (ID, Latitude, Longitude, AGB, Year, Reference)
FIELD_SHEET = "Combined Data"

# Panel (b) rasters
VIOLIN_RASTERS = {
    "RF_2005":     r"I:\AGB_models\RF_2005.tif",
    "MLR_2005":    r"I:\AGB_models\MLR_2005.tif",
    "Cubist_2005": r"I:\AGB_models\Cubist_2005.tif",
    "RF_2015":     r"I:\AGB_models\MLR_2015.tif",
    "MLR_2015":    r"I:\AGB_models\RF_2015.tif",
    "Cubist_2015": r"I:\AGB_models\Cubist_2015.tif",
}
MAX_SAMPLES = 1_000_000
CACHE_NPZ = HERE / "cache" / "violin_samples.npz"

# Panel (c) density-class proportions per model (columns: bin, proportion)
MODEL_CLASS_CSVS = [
    str(HERE / "data" / "density_class" / "RF_2005_mask_10.csv"),
    str(HERE / "data" / "density_class" / "RF_2015_mask_10.csv"),
    str(HERE / "data" / "density_class" / "MLR_2005_mask_10.csv"),
    str(HERE / "data" / "density_class" / "MLR_2015_mask_10.csv"),
    str(HERE / "data" / "density_class" / "Cubist_2005_mask_10.csv"),
    str(HERE / "data" / "density_class" / "Cubist_2015_mask_10.csv"),
]

OUT_STEM = HERE / "output" / "Figure4_model_comparison"

# ----------------------------------------------------------------------------- style
# Canvas and typography follow Figure 6 (180 mm wide, Arial 10 pt, 0.8 pt axes).
FIG_WIDTH_MM, FIG_HEIGHT_MM = 180, 141          # 14:11 aspect ratio
plt.rcParams.update({
    "font.family": "Arial", "font.size": 10, "axes.labelsize": 10, "axes.titlesize": 10,
    "xtick.labelsize": 10, "ytick.labelsize": 10, "legend.fontsize": 9,
    "legend.title_fontsize": 10, "axes.linewidth": 0.8, "xtick.major.width": 0.8,
    "ytick.major.width": 0.8, "lines.linewidth": 1.0, "axes.unicode_minus": False,
    "pdf.fonttype": 42,
})
UNIT = "Mg ha$^{-1}$"


def panel_label(ax, text, dx=-0.12):
    # Panel letters use the same point size as the axis labels (bold), the
    # convention shared with Figures 6 and 7.
    ax.text(dx, 1.02, text, transform=ax.transAxes,
            fontsize=plt.rcParams["axes.labelsize"], fontweight="bold",
            va="bottom", ha="left")


# ============================================================================= panel (a)
def draw_panel_a(ax):
    """Latitude profile of CV; plotting logic from ab.ipynb (June-2025 cell)."""
    all_data = np.load(PRECOMPUTED_NPZ, allow_pickle=True)["all_data"].item()
    labels = ["MLR_2015", "MLR_2005", "Cubist_2015", "Cubist_2005", "RF_2015", "RF_2005"]
    palette = cm.get_cmap("tab10", len(labels))
    colors = {lab: palette(i) for i, lab in enumerate(labels)}
    smooth_w, step = 201, 300                        # 200 -> 201 (odd), as in the notebook
    kernel = np.ones(smooth_w) / smooth_w
    lw_main, lw_shadow, shadow_alpha, light_ratio = 1.0, 4.0, 0.10, 0.75
    for lab in labels:
        if lab not in all_data:
            continue
        x = np.convolve(all_data[lab]["mean_data"], kernel, mode="same")[::step]
        y = np.asarray(all_data[lab]["lat"])[::step]
        base = colors[lab]
        light = tuple(1 - (1 - c) * light_ratio for c in base[:3]) + (1.0,)
        ax.plot(x, y, lw=lw_shadow, color=light, alpha=shadow_alpha, zorder=1)
        ax.plot(x, y, lw=lw_main, color=base, alpha=0.95, label=lab, zorder=2,
                path_effects=[pe.withStroke(linewidth=lw_shadow, foreground=light, alpha=shadow_alpha)])
    ax.set_xlim(0, 1)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_ylim(38, 54)
    ax.set_yticks(np.arange(38, 55, 2))
    ax.set_xlabel("Coefficient of Variation")
    ax.set_ylabel("Latitude (°N)")
    leg = ax.legend(frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5), handlelength=1.2,
                    borderaxespad=0.2, labelspacing=0.4)
    for line in leg.get_lines():
        line.set_path_effects([])


# ============================================================================= panel (b)
def sample_raster(path: str, max_samples: int) -> np.ndarray:
    """Valid pixels (> 0, finite) collected block by block
    until max_samples is reached; the last block is subsampled at random."""
    import rasterio
    samples, total = [], 0
    with rasterio.open(path) as src:
        for _, window in src.block_windows(1):
            data = src.read(1, window=window)
            filtered = data[np.isfinite(data) & (data > 0)]
            if filtered.size == 0:
                continue
            if total + filtered.size > max_samples:
                allowed = max_samples - total
                if allowed > 0:
                    idx = np.random.choice(filtered.size, allowed, replace=False)
                    samples.append(filtered[idx])
                break
            samples.append(filtered)
            total += filtered.size
    return np.concatenate(samples) if samples else np.array([], dtype="float32")


def load_violin_samples(resample: bool) -> pd.DataFrame:
    if CACHE_NPZ.exists() and not resample:
        z = np.load(CACHE_NPZ)
        frames = [pd.DataFrame({"Label": k, "raster_values": z[k]}) for k in z.files]
        print(f"panel (b): loaded cached samples from {CACHE_NPZ.name}")
    else:
        np.random.seed(0)                            # makes the last-block subsample repeatable
        frames, cache = [], {}
        for label, path in VIOLIN_RASTERS.items():
            print(f"panel (b): sampling {label} <- {path}", flush=True)
            v = sample_raster(path, MAX_SAMPLES)
            cache[label] = v
            frames.append(pd.DataFrame({"Label": label, "raster_values": v}))
        CACHE_NPZ.parent.mkdir(exist_ok=True)
        np.savez_compressed(CACHE_NPZ, **cache)
        print(f"panel (b): cached samples -> {CACHE_NPZ}")
    df = pd.concat(frames, ignore_index=True)
    df[["Method", "Year"]] = df["Label"].str.split("_", expand=True)
    return df.drop(columns=["Label"])


def load_field_for_violin() -> pd.DataFrame:
    """Field plots 2005-2010 -> '2005', 2011-2015 -> '2015'."""
    raw = pd.read_excel(FIELD_XLSX, sheet_name=FIELD_SHEET)
    d = raw[["AGB", "Year"]].apply(pd.to_numeric, errors="coerce").dropna()
    d = d[d["AGB"] > 0]
    year = d["Year"].astype(int)
    group = np.select([(year >= 2005) & (year <= 2010), (year >= 2011) & (year <= 2015)],
                      ["2005", "2015"], default=None)
    d = d.assign(Year=group).dropna(subset=["Year"])
    return pd.DataFrame({"Method": "Field Data", "Year": d["Year"].astype(str),
                         "raster_values": d["AGB"].astype(float)})


def remove_outliers(s: pd.Series) -> pd.Series:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    return s[(s >= q1 - 1.5 * iqr) & (s <= q3 + 1.5 * iqr)]


def draw_panel_b(ax, resample: bool):
    df = pd.concat([load_violin_samples(resample), load_field_for_violin()], ignore_index=True)
    df["Year"] = pd.Categorical(df["Year"], categories=["2005", "2015"], ordered=True)
    df["raster_values"] = df.groupby(["Year", "Method"], observed=True)["raster_values"].transform(remove_outliers)
    df = df.dropna(subset=["raster_values"])

    method_order = ["Field Data", "RF", "MLR", "Cubist"]
    palette = sns.color_palette("Set2", n_colors=len(method_order))
    color_dict = dict(zip(method_order, palette))
    major, minor = (int(v) for v in sns.__version__.split(".")[:2])
    bw_kw = {"bw_method": 0.2} if (major, minor) >= (0, 13) else {"bw": 0.2}
    sns.violinplot(x="Year", y="raster_values", hue="Method", data=df, hue_order=method_order,
                   inner="quartile", palette=palette, linewidth=0.8, ax=ax, **bw_kw)
    ax.set_xlabel("Year")
    ax.set_ylabel(f"AGB Density ({UNIT})")
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-20, df["raster_values"].max() * 1.5)      # headroom for the legend at 180 mm
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(title="Method", loc="upper right", frameon=True, ncol=2, fontsize=8, title_fontsize=9,
              handlelength=1.2, columnspacing=0.8, labelspacing=0.3, borderpad=0.4)
    # dashed median lines from the left axis to each violin centre (as in the notebook)
    n = len(method_order)
    spacing = 0.8 / n
    med = df.groupby(["Year", "Method"], observed=True)["raster_values"].median().reset_index()
    for _, row in med.iterrows():
        base = {"2005": 0, "2015": 1}[str(row["Year"])]
        x_center = base + (method_order.index(row["Method"]) - (n - 1) / 2) * spacing
        ax.hlines(row["raster_values"], -0.5, x_center, color=color_dict[row["Method"]],
                  linestyles="dashed", linewidth=0.8)
    return med


# ============================================================================= panel (c)
BIN_ORDER = ["> 130", "120-130", "80-100", "60-80", "40-60", "20-40", "≤ 20"]
COLOR_MAPPING = {"> 130": "#006837", "120-130": "#1A9850", "80-100": "#66BD63", "60-80": "#D9EF8B",
                 "40-60": "#FEE08B", "20-40": "#F46D43", "≤ 20": "#D73027"}
BIN_ALIASES = {"<= 20": "≤ 20", "<=20": "≤ 20", "< 20": "≤ 20", "<20": "≤ 20", "≤20": "≤ 20",
               "120 - 130": "120-130", "80 - 100": "80-100", "60 - 80": "60-80", "40 - 60": "40-60",
               "20 - 40": "20-40", ">130": "> 130"}


def load_model_classes() -> pd.DataFrame:
    """Density-class proportions of the six model maps (data/density_class/*.csv)."""
    import re
    rows = {}
    for fp in MODEL_CLASS_CSVS:
        p = Path(fp)
        method, year = p.stem.split("_")[:2]
        df = pd.read_csv(p)
        df["bin"] = df["bin"].map(lambda s: BIN_ALIASES.get(re.sub(r"\s+", " ", str(s).strip()), re.sub(r"\s+", " ", str(s).strip())))
        prop = pd.to_numeric(df["proportion"], errors="coerce")
        prop = prop * 100.0 if float(prop.max()) <= 1.0 else prop
        s = pd.Series(prop.values, index=df["bin"])
        rows[f"{year}-{method.replace('Cusbit', 'Cubist')}"] = {b: float(s.get(b, 0.0)) for b in BIN_ORDER}
    return pd.DataFrame.from_dict(rows, orient="index").reindex(columns=BIN_ORDER, fill_value=0.0)


def load_field_classes() -> pd.DataFrame:
    """Field plots: periods 2005-2010 and 2011-2015 (>= 2011), AGB classes."""
    df = pd.read_excel(FIELD_XLSX)
    year = pd.to_numeric(df["Year"], errors="coerce")
    agb = pd.to_numeric(df["AGB"], errors="coerce")
    period = np.select([year.between(2005, 2010, inclusive="both"), year >= 2011],
                       ["2005-2010", "2011-2015"], default="Before 2005")
    cat = np.select([agb > 130, (agb >= 120) & (agb <= 130), (agb >= 80) & (agb < 120),
                     (agb >= 60) & (agb < 80), (agb >= 40) & (agb < 60), (agb >= 20) & (agb < 40), agb < 20],
                    BIN_ORDER, default=None)
    d = pd.DataFrame({"Period": period, "AGB_Category": cat})
    d = d[(d["Period"] != "Before 2005") & d["AGB_Category"].notna()]
    counts = d.groupby(["Period", "AGB_Category"]).size().unstack(fill_value=0).reindex(columns=BIN_ORDER, fill_value=0)
    return counts.div(counts.sum(axis=1), axis=0) * 100.0


def draw_panel_c(ax):
    obs_pct, model_pct = load_field_classes(), load_model_classes()
    labels = ["Field-2005", "Field-2015", "", "RF-2005", "RF-2015", "", "MLR-2005", "MLR-2015", "", "Cubist-2005", "Cubist-2015"]
    model_keys = ["2005-RF", "2015-RF", "", "2005-MLR", "2015-MLR", "", "2005-Cubist", "2015-Cubist"]
    n = len(labels)
    data = {b: np.zeros(n) for b in BIN_ORDER}
    for j, period in enumerate(["2005-2010", "2011-2015"]):
        for b in BIN_ORDER:
            data[b][j] = float(obs_pct.loc[period, b]) if period in obs_pct.index else 0.0
    for i, key in enumerate(model_keys):
        if key:
            for b in BIN_ORDER:
                data[b][3 + i] = float(model_pct.loc[key, b]) if key in model_pct.index else 0.0
    x, bottoms = np.arange(n), np.zeros(n)
    for b in BIN_ORDER:
        ax.bar(x, data[b], 0.7, bottom=bottoms, color=COLOR_MAPPING[b], edgecolor="black", linewidth=0.5)
        bottoms += data[b]
    ax.set_ylabel("Proportion (%)")
    ax.set_xlabel("Year-Method")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="center", fontsize=8)   # rotated labels at 8 pt, as in Figure 6
    ax.set_ylim(0, 105)
    for xv in (2.5, 5.5, 8.5):
        ax.axvline(xv, color="gray", linestyle="--", linewidth=0.6, alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles = [Patch(facecolor=COLOR_MAPPING[b], edgecolor="black", linewidth=0.5, label=b) for b in BIN_ORDER]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=True,
              title=f"AGB ({UNIT})", edgecolor="black", fancybox=False)
    return obs_pct, model_pct


# ============================================================================= assembly
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resample", action="store_true", help="re-read the rasters for panel (b)")
    args = parser.parse_args()

    fig = plt.figure(figsize=(FIG_WIDTH_MM / 25.4, FIG_HEIGHT_MM / 25.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.15], height_ratios=[1.0, 0.95],
                          left=0.085, right=0.82, top=0.96, bottom=0.09, wspace=1.0, hspace=0.32)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    draw_panel_a(ax_a)
    med = draw_panel_b(ax_b, args.resample)
    obs_pct, model_pct = draw_panel_c(ax_c)
    panel_label(ax_a, "(a)")
    panel_label(ax_b, "(b)")
    panel_label(ax_c, "(c)", dx=-0.045)

    OUT_STEM.parent.mkdir(exist_ok=True)
    fig.savefig(f"{OUT_STEM}.pdf", bbox_inches="tight")
    fig.savefig(f"{OUT_STEM}.png", dpi=600, bbox_inches="tight")
    print(f"saved {OUT_STEM}.pdf / .png")
    print("\npanel (b) medians (Mg ha-1):\n" + med.pivot(index="Method", columns="Year", values="raster_values").round(2).to_string())
    print("\npanel (c) field classes (%):\n" + obs_pct.round(1).to_string())


if __name__ == "__main__":
    main()
