"""Check that the Figure S4 label correction preserves the original plot geometry."""
from pathlib import Path
import ast
import csv
import hashlib
import json
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
matplotlib.set_loglevel("error")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
OLD = ROOT / "_backup_before_label_update_2026-11-10/make_fig1_workflow.py"
NEW = ROOT / "make_figureS4_workflow.py"
CHANGES = {
    "Global Forest Cover\nChange dataset (GFCC)": "China Annual Tree Cover\nDataset (CATCD)",
    "ERA5-Land": "TerraClimate",
    "Data preprocessing and validation (1,000 iterations)":
        "Data preprocessing and validation (100 repeated training-validation splits)",
}


def inspect_plot(path):
    # Execute the plotting instructions without writing files or printing exports.
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tree.body = [
        node for node in tree.body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and ((isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "savefig")
                     or (isinstance(node.value.func, ast.Name) and node.value.func.id == "print")))
    ]
    env = {"__file__": str(path), "__name__": "__label_verification__"}
    exec(compile(tree, str(path), "exec"), env)
    return env["fig"], env["ax"]


old_fig, old_ax = inspect_plot(OLD)
new_fig, new_ax = inspect_plot(NEW)
assert len(old_ax.texts) == len(new_ax.texts)
assert len(old_ax.patches) == len(new_ax.patches)
assert len(old_ax.lines) == len(new_ax.lines)
assert np.array_equal(old_fig.get_size_inches(), new_fig.get_size_inches())
assert old_ax.get_xlim() == new_ax.get_xlim() and old_ax.get_ylim() == new_ax.get_ylim()

labels = []
for i, (a, b) in enumerate(zip(old_ax.texts, new_ax.texts), 1):
    assert b.get_text() == CHANGES.get(a.get_text(), a.get_text())
    assert a.get_position() == b.get_position()
    assert a.get_fontproperties() == b.get_fontproperties()
    assert a.get_color() == b.get_color()
    assert a.get_ha() == b.get_ha() and a.get_va() == b.get_va()
    labels.append({"label_number": i, "before": a.get_text(), "after": b.get_text(),
                   "changed": a.get_text() != b.get_text()})
assert sum(x["changed"] for x in labels) == 3
for a, b in zip(old_ax.patches, new_ax.patches):
    assert type(a) is type(b)
    assert np.array_equal(a.get_path().vertices, b.get_path().vertices)
    assert np.array_equal(a.get_path().codes, b.get_path().codes)
    assert np.array_equal(a.get_transform().get_matrix(), b.get_transform().get_matrix())
    assert a.get_facecolor() == b.get_facecolor() and a.get_edgecolor() == b.get_edgecolor()
    assert a.get_linewidth() == b.get_linewidth() and a.get_linestyle() == b.get_linestyle()
for a, b in zip(old_ax.lines, new_ax.lines):
    assert np.array_equal(a.get_xydata(), b.get_xydata())
    assert a.get_color() == b.get_color() and a.get_linewidth() == b.get_linewidth()

# Confirm each changed label fits the original rounded rectangle.
new_fig.canvas.draw()
renderer = new_fig.canvas.get_renderer()
for label in new_ax.texts:
    if label.get_text() not in CHANGES.values():
        continue
    cx, cy = new_ax.transData.transform(label.get_position())
    containers = [p.get_window_extent(renderer) for p in new_ax.patches
                  if p.get_window_extent(renderer).contains(cx, cy)]
    rect = min(containers, key=lambda b: b.width * b.height)
    text = label.get_window_extent(renderer)
    assert text.x0 >= rect.x0 and text.x1 <= rect.x1
    assert text.y0 >= rect.y0 and text.y1 <= rect.y1

backup = OLD.parent
for line in (backup / "SHA256SUMS.txt").read_text().splitlines():
    expected, name = line.split("  ", 1)
    assert hashlib.sha256((backup / name).read_bytes()).hexdigest() == expected

svg = ET.parse(ROOT / "output/FigureS4_workflow_labels_corrected.svg").getroot()
svg_text = " ".join("".join(node.itertext()) for node in svg.iter()
                    if node.tag.endswith("}text"))
assert "TerraClimate" in svg_text and "CATCD" in svg_text
assert "100 repeated training-validation splits" in svg_text
assert "GFCC" not in svg_text and "ERA5" not in svg_text and "1,000" not in svg_text

with (ROOT / "output/label_comparison.csv").open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=labels[0].keys())
    writer.writeheader()
    writer.writerows(labels)
result = {"status": "PASS", "labels_compared": len(labels), "labels_changed": 3,
          "patches_unchanged": len(old_ax.patches), "line_objects_unchanged": len(old_ax.lines),
          "all_text_positions_and_styles_unchanged": True,
          "changed_labels_fit_original_boxes": True, "backup_hashes_verified": True,
          "editable_svg_text_verified": True,
          "png_pixels": list(Image.open(ROOT / "output/FigureS4_workflow_labels_corrected.png").size),
          "unchanged_driver_branches": True}
(ROOT / "output/verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
plt.close("all")
print(json.dumps(result))
