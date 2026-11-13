#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Figure S4 | Overall workflow (three stages), local label correction 2026-11-10.

Copied from R3_revision/scripts/make_fig1_workflow.py, which matches the
manuscript embedded workflow. Only GFCC/CATCD, ERA5-Land/TerraClimate and
1,000 iterations/100 repeated training-validation splits labels are updated.
All analytical branches, arrows and conclusions are retained.

Stages 1-2 reproduce the original data / mapping workflow. Stage 3 is the
revised driver-attribution part: an exogenous-only random forest analysed with
grouped joint permutation (-> Figure 7), run in parallel with an augmented
random forest analysed with SHAP, which serves only as a circularity check.

Style follows the author's original diagram: dashed navy stage frames, rounded
solid boxes, hollow block arrows, terse one-line box labels (details go in the
caption).  Output: editable-text vector PDF + 600 dpi PNG.
"""
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch

OUT = Path(__file__).resolve().parent / "output" / "FigureS4_workflow_labels_corrected"
OUT.parent.mkdir(parents=True, exist_ok=True)

mpl.rcParams.update({
    "font.family": ["Arial", "Liberation Sans", "DejaVu Sans"],
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
    "savefig.bbox": "tight",
})

NAVY, EDGE, ARR = "#1F3864", "#1F4E79", "#2E75B6"
STAGE = {1: ("#FDF6DA", "#FBF0C4"),
         2: ("#DCEFF6", "#C5E6F0"),
         3: ("#EAF4E1", "#DCEDCC")}
GREY_BOX = "#E4E4E4"          # model-internal (circular) predictors
WHITE = "#FFFFFF"             # key outputs
ORANGE = "#C55A11"

# ---- metrics (units; figure width = 100 units) -----------------------------
H1 = 5.2          # standard box height (one or two lines)
H2 = 7.4          # taller box (three lines)
GAPV = 2.4        # arrow band between rows
APAD = 1.4        # dashed sub-group padding
SPAD = 2.2        # stage frame padding
FS = 8.2          # box font size
FSA = 7.4         # annotation font size

W = 100.0
fig = plt.figure(figsize=(7.2, 7.2))
ax = fig.add_axes([0, 0, 1, 1])
ax.axis("off")


# ------------------------------------------------------------------ helpers
def rbox(x, y, w, h, s, fill, fs=FS, ec=EDGE, lw=0.8, color=NAVY, z=3):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=fill, ec=ec, lw=lw, zorder=z))
    ax.text(x + w / 2, y + h / 2, s, ha="center", va="center", fontsize=fs,
            fontweight="bold", color=color, zorder=z + 1, linespacing=1.22)


def frame(x, y, w, h, fill="none", z=1.5, lw=1.1, ec=NAVY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.4",
                                fc=fill, ec=ec, lw=lw, ls=(0, (4, 2.6)), zorder=z))


def block_arrow(cx, ytop, h=2.2, w=3.6, color=ARR):
    hw, sw = w / 2, w / 4
    pts = [(cx - sw, ytop), (cx + sw, ytop), (cx + sw, ytop + h * 0.5),
           (cx + hw, ytop + h * 0.5), (cx, ytop + h),
           (cx - hw, ytop + h * 0.5), (cx - sw, ytop + h * 0.5)]
    ax.add_patch(Polygon(pts, closed=True, fc="white", ec=color, lw=0.9, zorder=4))


def thin_arrow(x1, y1, x2, y2, color="#111111", lw=0.8, ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=6,
                                 lw=lw, color=color, ls=ls, shrinkA=0, shrinkB=0, zorder=4))


def row(xs, ws, labels, ytop, h, fill, fs=FS, **kw):
    for x, w, s in zip(xs, ws, labels):
        rbox(x, ytop, w, h, s, fill, fs=fs, **kw)
    return ytop + h


def cols(x0, total, n, gap=2.2):
    w = (total - (n - 1) * gap) / n
    return [x0 + i * (w + gap) for i in range(n)], [w] * n


# ==================================================================== layout
X0, X1 = 1.5, 98.5
IX0, IX1 = X0 + SPAD, X1 - SPAD
IW = IX1 - IX0
CX = (X0 + X1) / 2

y = 1.5

# ------------------------------------------------------------------ STAGE 1
s1 = y
f1, b1 = STAGE[1]
xs, ws = cols(IX0, IW, 4)
yy = s1 + SPAD
r1 = yy
row(xs, ws, ["Literature search", "Landsat (5/8/9)", "ALOS PALSAR-1/2", "MODIS LST"], r1, H1, b1)

r2 = r1 + H1 + GAPV
rbox(xs[0], r2, ws[0], 7.2, "China Annual Tree Cover\nDataset (CATCD)", b1)
row(xs[1:], ws[1:], ["Spectral\nreflectance data", "Multi-polarization\ndata", "TerraClimate"],
    r2, H1, b1)

r3 = r2 + H1 + GAPV
row(xs[1:], ws[1:], ["Vegetation indices", "Texture indices", "SRTM"], r3, H1, b1)

r4 = r3 + H1 + GAPV
row(xs, ws, ["Field dataset", "Optical dataset", "Radar dataset", "Environmental dataset"],
    r4, H1, b1)

for i in range(4):
    c = xs[i] + ws[i] / 2
    thin_arrow(c, r1 + H1, c, r2 - 0.3)
for i in (1, 2, 3):
    c = xs[i] + ws[i] / 2
    thin_arrow(c, r2 + H1, c, r3 - 0.3)
    thin_arrow(c, r3 + H1, c, r4 - 0.3)
thin_arrow(xs[0] + ws[0] / 2, r2 + 7.2, xs[0] + ws[0] / 2, r4 - 0.3)
for i in range(3):
    ax.plot([xs[i] + ws[i], xs[i + 1]], [r4 + H1 / 2] * 2, color="#111111", lw=0.8, zorder=2)

s1b = r4 + H1 + SPAD
frame(X0, s1, X1 - X0, s1b - s1, f1, z=0)
block_arrow(CX, s1b + 0.7, h=2.8, w=5.4)
y = s1b + 4.2

# ------------------------------------------------------------------ STAGE 2
s2 = y
f2, b2 = STAGE[2]
yy = s2 + SPAD
half = (IW - 2.6) / 2

gh = 2 * APAD + H1
frame(IX0, yy, half, gh)
frame(IX0 + half + 2.6, yy, half, gh)
hxs, hws = cols(IX0 + APAD, half - 2 * APAD, 3, gap=1.8)
row(hxs, hws, ["Cubist", "MLR", "RF"], yy + APAD, H1, b2)
x2 = IX0 + half + 2.6
hxs2, hws2 = cols(x2 + APAD, half - 2 * APAD, 3, gap=1.8)
row(hxs2, hws2, ["Optical\ndataset", "Radar\ndataset", "Topographic\ndataset"],
    yy + APAD, H1, b2)
yy += gh
block_arrow(IX0 + half * 0.28, yy + 0.3, w=3.4)
block_arrow(x2 + half * 0.28, yy + 0.3, w=3.4)
yy += GAPV + 0.4

gh = 2 * APAD + H1
frame(IX0, yy, IW, gh)
txs, tws = cols(IX0 + APAD, IW - 2 * APAD, 3)
row(txs, tws, ["Feature importance-\nbased selection", "Machine-learning\nmodel selection",
               "Multi-source remote\nsensing data selection"], yy + APAD, H1, b2)
yy += gh
block_arrow(CX, yy + 0.3)
yy += GAPV + 0.4

rbox(IX0, yy, IW, H1, "Data preprocessing and validation (100 repeated training-validation splits)", b2)
yy += H1
block_arrow(CX, yy + 0.3)
yy += GAPV + 0.4

rbox(IX0, yy, IW, H1,
     "High-resolution spatial distribution of aboveground biomass in Northeast China", b2)
yy += H1
hxs3, hws3 = cols(IX0, IW, 2)
block_arrow(hxs3[0] + hws3[0] / 2, yy + 0.3)
block_arrow(hxs3[1] + hws3[1] / 2, yy + 0.3)
yy += GAPV + 0.4

row(hxs3, hws3, ["Uncertainty map",
                 "Validation using independent remote sensing\nand forest inventory data"],
    yy, H1, b2)
yy += H1

s2b = yy + SPAD
frame(X0, s2, X1 - X0, s2b - s2, f2, z=0)
block_arrow(CX, s2b + 0.7, h=2.8, w=5.4)
y = s2b + 4.2

# ------------------------------------------------------------------ STAGE 3
s3 = y
f3, b3 = STAGE[3]
yy = s3 + SPAD

rbox(IX0, yy, IW, H1, "Best-performing machine-learning model", b3)
yy += H1
block_arrow(CX, yy + 0.3)
yy += GAPV + 0.4

gh = 2 * APAD + H1
frame(IX0, yy, IW, gh)
axs, aws = cols(IX0 + APAD, IW - 2 * APAD, 3)
row(axs, aws, ["AGB map (2005)", "AGB map (2015)", "AGB map (2024)"], yy + APAD, H1, b3)
yy += gh
block_arrow(CX, yy + 0.3)
yy += GAPV + 0.4

rbox(IX0, yy, IW, H1,
     "Regional AGB change map  ·  2005–2015 (uncertainty-gated) and 2015–2024 (ungated)", b3)
yy += H1
block_arrow(CX, yy + 0.3)
yy += GAPV + 0.4

# --- predictor pool: exogenous vs model-internal
gh = 2 * APAD + H2 + 1.6
frame(IX0, yy, IW, gh)
pxs, pws = cols(IX0 + APAD, IW - 2 * APAD, 4)
ax.text(pxs[0] + (3 * pws[0] + 2 * 2.2) / 2, yy + 1.1, "exogenous predictors",
        ha="center", va="center", fontsize=FSA, style="italic", color=NAVY, zorder=6)
ax.text(pxs[3] + pws[3] / 2, yy + 1.1, "model-internal (circular)",
        ha="center", va="center", fontsize=FSA, style="italic", color="#5A5A5A", zorder=6)
for i, (s, fc, col) in enumerate([
        ("Forest structure /\nstarting state", b3, NAVY),
        ("Climate and water\n(precipitation, soil\nmoisture, VPD, ΔLST)", b3, NAVY),
        ("Terrain\n(elevation, slope)", b3, NAVY),
        ("Model-internal predictors\n(ΔNDVI, ΔNDWI,\nΔHH, ΔHV)",
         GREY_BOX, "#333333")]):
    rbox(pxs[i], yy + APAD + 1.8, pws[i], H2, s, fc, fs=7.6, color=col,
         ec=EDGE if fc == b3 else "#7A7A7A")
yy += gh

LXS, LWS = cols(IX0, IW, 2)
LX, RX, BW = LXS[0], LXS[1], LWS[0]
block_arrow(LX + BW / 2, yy + 0.3)
block_arrow(RX + BW / 2, yy + 0.3)
ax.text(LX + BW / 2 + 3.0, yy + 1.5, "exogenous only", ha="left", va="center",
        fontsize=FSA, color=NAVY, zorder=6)
ax.text(RX + BW / 2 + 3.0, yy + 1.5, "+ model-internal predictors", ha="left", va="center",
        fontsize=FSA, color="#5A5A5A", zorder=6)
yy += GAPV + 2.0

# --- each branch: RF model + its analysis merged into one box
H3 = 8.0
gh = 2 * APAD + H3
frame(LX - APAD, yy - APAD, BW + 2 * APAD, gh)
frame(RX - APAD, yy - APAD, BW + 2 * APAD, gh)
row([LX, RX], [BW, BW],
    ["Random forest regression\n→ grouped joint permutation (ΔR²)\n+ standardized coefficients",
     "Random forest regression\n→ SHapley Additive exPlanations (SHAP)\nby predictor group"],
    yy, H3, b3, fs=FS)
yy += H3
block_arrow(LX + BW / 2, yy + 0.3 + APAD)
block_arrow(RX + BW / 2, yy + 0.3 + APAD)
yy += GAPV + 0.4 + APAD

rbox(LX, yy, BW, H1, "Driver importance and direction", WHITE, fs=FS, lw=1.3)
rbox(RX, yy, BW, H1, "Circularity of model-internal\npredictors", WHITE,
     fs=FS, ec="#7A7A7A", color="#333333")
thin_arrow(RX - 0.3, yy + H1 / 2, LX + BW + 0.3, yy + H1 / 2, color=ORANGE, lw=1.0,
           ls=(0, (2.2, 1.8)))
yy += H1

s3b = yy + SPAD
frame(X0, s3, X1 - X0, s3b - s3, f3, z=0)

# ------------------------------------------------------------------ finalize
H = s3b + 1.5
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
fig.set_size_inches(7.2, 7.2 * H / W)

fig.savefig(f"{OUT}.svg", bbox_inches="tight")
fig.savefig(f"{OUT}.pdf", bbox_inches="tight")
fig.savefig(f"{OUT}.png", dpi=600, bbox_inches="tight")
print("wrote", OUT.name + ".svg/.pdf/.png  | H =", round(H, 1), " aspect =", round(H / W, 2))
