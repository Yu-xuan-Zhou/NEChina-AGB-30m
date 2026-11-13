"""Figure 4 - Methodological and temporal comparison of estimated AGB (RF / Cubist / MLR).

Builds the three panels in ONE matplotlib figure:

  (a) latitude profile of the coefficient of variation      <- precomputed_data.npz
  (b) violin plot of AGB density by year and method,
      including field data                                   <- uniform whole-region raster samples + final model samples
  (c) stacked bars of AGB density classes, field vs models   <- full-raster class CSVs + final model samples

Panel (b) starts with deterministic uniform samples without replacement from all
valid positive pixels of the current root rasters. Each model-year group is then
filtered inclusively to Q1 - 1.5*IQR through Q3 + 1.5*IQR for this panel only.
Field observations are not filtered. Raw samples and panel (c) remain unchanged.
Panel (c) uses full-raster counts, not the violin samples. Both use seven
right-closed classes: (0,20], (20,40], ..., (100,130], >130.

Run from this folder:
    python -X utf8 Figure4_combine.py            # uses cache/violin_samples.npz if present
    python -X utf8 Figure4_combine.py --resample # see the shared scan instructions

Outputs: output/Figure4_model_comparison_current_rasters_IQR_2026-11-10.pdf / .png / .svg
Units: AGB density in Mg ha-1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
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
from scipy.stats import gaussian_kde

HERE = Path(__file__).resolve().parent

# ----------------------------------------------------------------------------- inputs
PRECOMPUTED_NPZ = HERE / "data" / "precomputed_data.npz"   # panel (a); see build_precomputed_data.py
FIELD_CSV = HERE.parent / "Figure1_study_area" / "data" / "samples" / "final_model_samples.csv"

# Panel (b) rasters
VIOLIN_RASTERS = {
    "RF_2005":     r"I:\AGB_models\RF_2005.tif",
    "MLR_2005":    r"I:\AGB_models\MLR_2005.tif",
    "Cubist_2005": r"I:\AGB_models\Cubist_2005.tif",
    "RF_2015":     r"I:\AGB_models\RF_2015.tif",
    "MLR_2015":    r"I:\AGB_models\MLR_2015.tif",
    "Cubist_2015": r"I:\AGB_models\Cubist_2015.tif",
}
CACHE_NPZ = HERE / "cache" / "violin_samples.npz"
SCAN_PROVENANCE = HERE / "cache" / "current_raster_distribution_provenance.json"
SCAN_METHOD_VERSION = "whole-grid-positive-right-closed-uniform-ranks-v1"
METHOD_ORDER = ["Field Data", "RF", "MLR", "Cubist"]
# The original four Set2 colours are retained.
METHOD_COLORS = dict(zip(METHOD_ORDER, ["#66c2a5", "#fc8d62", "#8da0cb", "#e78ac3"]))
VIOLIN_DENSITY_CACHE = {}

# Panel (c) density-class proportions per model (columns: bin, proportion)
MODEL_CLASS_CSVS = [
    str(HERE / "data" / "density_class" / "RF_2005_mask_10.csv"),
    str(HERE / "data" / "density_class" / "RF_2015_mask_10.csv"),
    str(HERE / "data" / "density_class" / "MLR_2005_mask_10.csv"),
    str(HERE / "data" / "density_class" / "MLR_2015_mask_10.csv"),
    str(HERE / "data" / "density_class" / "Cubist_2005_mask_10.csv"),
    str(HERE / "data" / "density_class" / "Cubist_2015_mask_10.csv"),
]

OUTPUT_VERSION = "current_rasters_IQR_2026-11-10"
OUT_STEM = HERE / "output" / f"Figure4_model_comparison_{OUTPUT_VERSION}"

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
def load_scan_provenance() -> dict:
    if not SCAN_PROVENANCE.exists():
        raise FileNotFoundError(f"Missing current-raster provenance: {SCAN_PROVENANCE}. "
                                "Run Figure4_combine.py --resample before drawing; legacy caches are not accepted.")
    record = json.loads(SCAN_PROVENANCE.read_text(encoding="utf-8"))
    if record.get("method_version") != SCAN_METHOD_VERSION or record.get("outlier_filter") is not None:
        raise ValueError("The scan provenance does not describe the current whole-grid uniform unfiltered samples.")
    if set(record.get("products", {})) != set(VIOLIN_RASTERS):
        raise ValueError("Current-raster provenance must describe all six model/year products.")
    for name, product in record["products"].items():
        if (product.get("method_version") != SCAN_METHOD_VERSION
                or product.get("right_closed") is not True
                or product.get("sample", {}).get("n") != 1_000_000
                or product.get("sample", {}).get("outlier_filter") is not None):
            raise ValueError(f"Invalid current scan metadata for {name}")
    return record


def load_violin_samples(resample: bool) -> pd.DataFrame:
    scanner = HERE.parent / "shared" / "recompute_current_agb_distributions.py"
    if resample:
        if not scanner.exists():
            raise FileNotFoundError(f"Shared raster scan is not available: {scanner}. "
                                    "Run it with --workers 2 --publish-figure4 before drawing.")
        subprocess.run([sys.executable, str(scanner), "--workers", "2", "--publish-figure4"], check=True)
    if not CACHE_NPZ.exists():
        raise FileNotFoundError(f"Missing {CACHE_NPZ}. Run {scanner} --workers 2 --publish-figure4.")
    provenance = load_scan_provenance()
    with np.load(CACHE_NPZ) as z:
        if set(z.files) != set(VIOLIN_RASTERS):
            raise ValueError(f"Expected six named model-year arrays; found {z.files}")
        frames = []
        for k in VIOLIN_RASTERS:
            v = z[k]
            if v.ndim != 1 or v.size != 1_000_000 or not np.all(np.isfinite(v) & (v > 0)):
                raise ValueError(f"Invalid positive finite sample array: {k}")
            expected = provenance["products"][k]["sample"]
            if (float(v.min()) != expected["min"] or float(v.max()) != expected["max"]
                    or not np.array_equal(np.quantile(v, [.25, .5, .75]), np.asarray(expected["quantiles"])[[2, 3, 4]])):
                raise ValueError(f"{k}: cache values do not match the published whole-grid sample statistics.")
            method, year = k.split("_", 1)
            frames.append(pd.DataFrame({
                "Method": pd.Categorical.from_codes(
                    np.full(v.size, METHOD_ORDER.index(method), dtype=np.int8), categories=METHOD_ORDER),
                "Year": pd.Categorical.from_codes(
                    np.full(v.size, ["2005", "2015"].index(year), dtype=np.int8), categories=["2005", "2015"]),
                "raster_values": v,
            }))
    print(f"panel (b): loaded whole-region samples from {CACHE_NPZ.name}")
    return pd.concat(frames, ignore_index=True)


def load_field_for_violin() -> pd.DataFrame:
    """All final modelling samples, grouped by their assigned model year."""
    raw = pd.read_csv(FIELD_CSV)
    year = pd.to_numeric(raw["Model_year"], errors="raise").astype(int)
    agb = pd.to_numeric(raw["AGB"], errors="raise").astype(float)
    if year.value_counts().to_dict() != {2005: 164, 2015: 957}:
        raise ValueError("Canonical field sample counts must be 164 (2005) and 957 (2015).")
    if not np.all(np.isfinite(agb) & (agb > 0)):
        raise ValueError("Canonical field samples contain invalid AGB values.")
    return pd.DataFrame({
        "Method": pd.Categorical.from_codes(np.zeros(len(raw), dtype=np.int8), categories=METHOD_ORDER),
        "Year": pd.Categorical(year.astype(str), categories=["2005", "2015"]),
        "raster_values": agb,
    })


def violin_statistics(values: np.ndarray) -> tuple[dict, dict]:
    """Gaussian KDE of the supplied plotting sample, with robust bandwidth.

    h = 0.9 * min(SD, IQR / 1.349) * n**(-1/5). Model samples have already
    undergone their group-specific 1.5*IQR display filter; field samples have
    not been filtered. This function performs no additional exclusion.
    """
    v = np.asarray(values, dtype=float)
    minimum, q1, median, q3, maximum = np.quantile(v, [0, .25, .5, .75, 1])
    sd = float(np.std(v, ddof=1)) if v.size > 1 else 0.0
    if maximum == minimum:
        coords = np.array([minimum - .001, maximum + .001])
        density = np.ones(2)
        bandwidth = 0.0
    else:
        robust_sd = min(sd, (q3-q1)/1.349) if q3 > q1 else sd
        bandwidth = .9 * robust_sd * v.size**(-.2)
        coords = np.linspace(minimum, maximum, 512)
        density = gaussian_kde(v, bw_method=bandwidth/sd)(coords)
    stats = {"coords": coords, "vals": density, "mean": float(np.mean(v)),
             "median": median, "min": minimum, "max": maximum}
    summary = {"n": int(v.size), "min": minimum, "q1": q1, "median": median,
               "q3": q3, "max": maximum, "mean": stats["mean"], "sd": sd,
               "density_bandwidth": bandwidth}
    for threshold in [200, 500, 1000]:
        summary[f"n_above_{threshold}"] = int(np.count_nonzero(v > threshold))
        summary[f"pct_above_{threshold}"] = 100.0 * summary[f"n_above_{threshold}"] / v.size
    return stats, summary


def cached_violin_statistics(values: np.ndarray, year: str, method: str, filtering: dict) -> tuple[dict, dict]:
    """Reuse a density only when all input values and the method are identical."""
    contiguous = np.ascontiguousarray(values)
    signature = json.dumps({
        "values_sha256": hashlib.sha256(contiguous.view(np.uint8)).hexdigest(),
        "dtype": str(contiguous.dtype), "n": int(contiguous.size),
        "method": "model-year-IQR-display-gaussian-kde-robust-silverman-0.9-IQR1.349-n^-0.2-v2",
        "filter": filtering,
        "grid": "512 linear coordinates spanning the retained sample min/max",
        "y_axis": "linear",
    }, sort_keys=True)
    cache_key = (year, method, signature)
    if cache_key in VIOLIN_DENSITY_CACHE:
        return VIOLIN_DENSITY_CACHE[cache_key]
    cached = HERE / "cache" / f"density_grid_IQR_{year}_{method.replace(' ', '_')}.npz"
    if cached.exists():
        with np.load(cached, allow_pickle=False) as z:
            if str(z["signature"].item()) == signature:
                summary = json.loads(str(z["summary"].item()))
                stats = {"coords": z["coords"], "vals": z["vals"],
                         **{k: summary[k] for k in ["mean", "median", "min", "max"]}}
                VIOLIN_DENSITY_CACHE[cache_key] = (stats, summary)
                print(f"panel (b): verified density cache {year} {method}", flush=True)
                return stats, summary
    print(f"panel (b): plotting-sample density {year} {method}", flush=True)
    stats, summary = violin_statistics(values)
    np.savez_compressed(cached, coords=stats["coords"], vals=stats["vals"],
                        signature=np.array(signature), summary=np.array(json.dumps(summary)))
    VIOLIN_DENSITY_CACHE[cache_key] = (stats, summary)
    return stats, summary


def draw_panel_b(ax, resample: bool):
    df = pd.concat([load_violin_samples(resample), load_field_for_violin()], ignore_index=True)
    summaries = []
    for base, year in enumerate(["2005", "2015"]):
        for j, method in enumerate(METHOD_ORDER):
            values = df.loc[(df["Year"] == year) & (df["Method"] == method), "raster_values"].to_numpy()
            n_before = int(values.size)
            input_q1, input_q3 = np.quantile(values, [.25, .75])
            apply_filter = method != "Field Data"
            lower = float(input_q1 - 1.5*(input_q3-input_q1)) if apply_filter else None
            upper = float(input_q3 + 1.5*(input_q3-input_q1)) if apply_filter else None
            if apply_filter:
                values = values[(values >= lower) & (values <= upper)]
            filtering = {
                "filter_applied": apply_filter,
                "filter_rule": "inclusive model-year 1.5*IQR" if apply_filter else "none; all final field observations",
                "iqr_multiplier": 1.5 if apply_filter else None,
                "n_before": n_before, "n_after": int(values.size),
                "n_removed": n_before-int(values.size),
                "percent_removed": 100.0*(n_before-int(values.size))/n_before,
                "input_q1": float(input_q1), "input_q3": float(input_q3),
                "lower_bound": lower, "upper_bound": upper,
            }
            stats, summary = cached_violin_statistics(values, year, method, filtering)
            x_center = base + (j - 1.5) * .2
            violin = ax.violin([stats], positions=[x_center], widths=.18,
                               showmeans=False, showmedians=False, showextrema=False)
            for body in violin["bodies"]:
                body.set_facecolor(METHOD_COLORS[method])
                body.set_edgecolor("#404040")
                body.set_alpha(1)
                body.set_linewidth(.8)
            ax.vlines(x_center, summary["min"], summary["max"], color=METHOD_COLORS[method], linewidth=.45)
            for key in ["q1", "median", "q3"]:
                ax.hlines(summary[key], x_center - .055, x_center + .055, color="#444444",
                          linewidth=.7, linestyles="solid" if key == "median" else "dashed")
            ax.hlines(summary["median"], -.5, x_center, color=METHOD_COLORS[method],
                      linestyles="dashed", linewidth=.8)
            summaries.append({"Year": year, "Method": method, **summary, **filtering})
    summary_df = pd.DataFrame(summaries)
    ax.set_xlabel("Year")
    ax.set_ylabel(f"AGB Density ({UNIT})")
    ax.set_xticks([0, 1], ["2005", "2015"])
    ax.set_xlim(-0.5, 1.5)
    upper = max(320.0, np.ceil(summary_df["max"].max()/20)*20)
    ax.set_yscale("linear")
    ax.set_ylim(0, upper)
    ax.set_yticks(np.arange(0, upper+1, 50))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    handles = [Patch(facecolor=METHOD_COLORS[m], edgecolor="#404040", label=m) for m in METHOD_ORDER]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, 1.08),
              frameon=False, ncol=4, fontsize=8, handlelength=1.0,
              columnspacing=.7, handletextpad=.35, borderaxespad=0)
    return summary_df


# ============================================================================= panel (c)
CLASS_BREAKS = [0, 20, 40, 60, 80, 100, 130, np.inf]
BIN_ORDER = ["> 130", "(100, 130]", "(80, 100]", "(60, 80]", "(40, 60]", "(20, 40]", "(0, 20]"]
COLOR_MAPPING = {"> 130": "#006837", "(100, 130]": "#1A9850", "(80, 100]": "#66BD63", "(60, 80]": "#D9EF8B",
                 "(40, 60]": "#FEE08B", "(20, 40]": "#F46D43", "(0, 20]": "#D73027"}


def load_model_classes() -> pd.DataFrame:
    """Density-class proportions of the six model maps (data/density_class/*.csv)."""
    import re
    provenance = load_scan_provenance()
    rows = {}
    for fp in MODEL_CLASS_CSVS:
        p = Path(fp)
        method, year = p.stem.split("_")[:2]
        df = pd.read_csv(p)
        canonical = {re.sub(r"\s+", "", b): b for b in BIN_ORDER}
        canonical["≤20"] = "(0, 20]"  # Shared scanner already enforces AGB > 0.
        df["bin"] = df["bin"].map(lambda s: canonical.get(re.sub(r"\s+", "", str(s)), str(s)))
        if set(df["bin"]) != set(BIN_ORDER) or len(df) != len(BIN_ORDER):
            raise ValueError(f"{p}: expected seven current right-closed classes; regenerate via the shared scanner.")
        prop = pd.to_numeric(df["proportion"], errors="coerce")
        if not np.all(np.isfinite(prop) & (prop >= 0) & (prop <= 1)) or not np.isclose(prop.sum(), 1, atol=1e-8):
            raise ValueError(f"{p}: class proportions must be fractions summing to one.")
        if "pixel_count" not in df:
            raise ValueError(f"{p}: current full-raster pixel counts are required; legacy proportions are not accepted.")
        population = provenance["products"][f"{method}_{year}"]
        counts = pd.to_numeric(df["pixel_count"], errors="raise").to_numpy()
        if (not np.array_equal(counts, np.asarray(population["class_counts"]))
                or counts.sum() != population["n_valid"]
                or not np.allclose(prop, counts / counts.sum(), rtol=1e-12, atol=1e-15)):
            raise ValueError(f"{p}: full-raster class counts/proportions disagree with scan provenance.")
        prop = prop * 100.0
        s = pd.Series(prop.values, index=df["bin"])
        rows[f"{year}-{method.replace('Cusbit', 'Cubist')}"] = {b: float(s.get(b, 0.0)) for b in BIN_ORDER}
    return pd.DataFrame.from_dict(rows, orient="index").reindex(columns=BIN_ORDER, fill_value=0.0)


def load_field_classes() -> pd.DataFrame:
    """All canonical field samples, using the same positive right-closed classes."""
    df = load_field_for_violin()
    agb = df["raster_values"]
    cat = pd.cut(agb, bins=CLASS_BREAKS, labels=list(reversed(BIN_ORDER)),
                 right=True, include_lowest=False)
    d = pd.DataFrame({"Year": df["Year"], "AGB_Category": cat})
    if d["AGB_Category"].isna().any():
        raise ValueError("A field sample was omitted by the shared class definition.")
    counts = d.groupby(["Year", "AGB_Category"], observed=True).size().unstack(fill_value=0).reindex(columns=BIN_ORDER, fill_value=0)
    return counts.div(counts.sum(axis=1), axis=0) * 100.0


def draw_panel_c(ax):
    obs_pct, model_pct = load_field_classes(), load_model_classes()
    labels = ["Field-2005", "Field-2015", "", "RF-2005", "RF-2015", "", "MLR-2005", "MLR-2015", "", "Cubist-2005", "Cubist-2015"]
    model_keys = ["2005-RF", "2015-RF", "", "2005-MLR", "2015-MLR", "", "2005-Cubist", "2015-Cubist"]
    n = len(labels)
    data = {b: np.zeros(n) for b in BIN_ORDER}
    for j, period in enumerate(["2005", "2015"]):
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
    parser.add_argument("--resample", action="store_true",
                        help="run the shared full-raster scan and publish the uniform samples/classes before drawing")
    args = parser.parse_args()

    fig = plt.figure(figsize=(FIG_WIDTH_MM / 25.4, FIG_HEIGHT_MM / 25.4))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.0, 1.15], height_ratios=[1.0, 0.95],
                          left=0.085, right=0.82, top=0.96, bottom=0.09, wspace=1.0, hspace=0.32)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, :])

    draw_panel_a(ax_a)
    summary = draw_panel_b(ax_b, args.resample)
    obs_pct, model_pct = draw_panel_c(ax_c)
    panel_label(ax_a, "(a)")
    panel_label(ax_b, "(b)")
    panel_label(ax_c, "(c)", dx=-0.045)

    OUT_STEM.parent.mkdir(exist_ok=True)
    for extension in ["pdf", "png", "svg"]:
        fig.savefig(f"{OUT_STEM}.{extension}", dpi=600, bbox_inches="tight")
    plt.close(fig)

    # Separate b export. The existing current-raster standalone c is unchanged.
    for stem, width_mm, height_mm, draw in [
        ("panel_b_violin", 90, 78, lambda ax: draw_panel_b(ax, False)),
    ]:
        single, ax = plt.subplots(figsize=(width_mm / 25.4, height_mm / 25.4))
        draw(ax)
        panel_label(ax, "(b)" if stem.startswith("panel_b") else "(c)", dx=-.12 if stem.startswith("panel_b") else -.045)
        for extension in ["pdf", "png", "svg"]:
            single.savefig(OUT_STEM.parent / f"{stem}_{OUTPUT_VERSION}.{extension}", dpi=600, bbox_inches="tight")
        plt.close(single)

    summary.to_csv(OUT_STEM.parent / f"panel_b_summary_{OUTPUT_VERSION}.csv", index=False)
    files = [Path(__file__), CACHE_NPZ, SCAN_PROVENANCE, FIELD_CSV, PRECOMPUTED_NPZ, *map(Path, MODEL_CLASS_CSVS)]
    provenance = {
        "panel_b": "Start with one million uniformly selected whole-region valid positive pixels per model/year; retain values inclusively between each raw group Q1-1.5*IQR and Q3+1.5*IQR for panel b only. Recompute all plotting quantiles from the retained values. Raw cache remains unfiltered.",
        "panel_b_density": "Gaussian KDE using every retained plotting value; bandwidth 0.9*min(SD,IQR/1.349)*n^(-1/5). 512 linear coordinates bounded by observed retained min/max.",
        "panel_b_y_axis": "Linear 0-320 Mg ha-1, displaying the complete retained model range and every field value.",
        "field": "All final model samples grouped by Model_year: 164 for 2005; 957 for 2015. No IQR filtering is applied to field observations.",
        "panel_c": "Full-raster positive valid pixel counts with seven right-closed classes, not violin sample estimates or area-weighted proportions.",
        "panel_a": "Existing precomputed data and drawing routine retained unchanged.",
        "shared_scan_summary": str(HERE.parent / "shared" / "current_agb_distributions" / "summary.json"),
        "input_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
    }
    (OUT_STEM.parent / f"plotting_provenance_{OUTPUT_VERSION}.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"saved {OUT_STEM}.pdf / .png / .svg and separate panel b; existing standalone c retained")
    print("\npanel (b) medians (Mg ha-1):\n" + summary.pivot(index="Method", columns="Year", values="median").round(2).to_string())
    print("\npanel (c) field classes (%):\n" + obs_pct.round(1).to_string())


if __name__ == "__main__":
    main()
