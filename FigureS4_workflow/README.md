# Figure S4 — local workflow-label correction

This package reproduces the workflow embedded in
`manuscript_ZhouYX_1110.docx` (`word/media/image11.jpeg`), using the matching
native plotting source `R3_revision/scripts/make_fig1_workflow.py`.
The separate root-level `Figure1_workflow_revised.svg` is a different,
simplified diagram and was not used or changed.

Only three displayed labels were updated on 2026-11-10:

| Previous label | Corrected label |
| --- | --- |
| Global Forest Cover Change dataset (GFCC) | China Annual Tree Cover Dataset (CATCD) |
| ERA5-Land | TerraClimate |
| Data preprocessing and validation (1,000 iterations) | Data preprocessing and validation (100 repeated training-validation splits) |

Evidence: `../Model_training_bootstrap/README.md` specifies the CATCD mask
(tree cover > 10%); `../../gee_code/03_export_period_climate_burned.js:32`
uses `IDAHO_EPSCOR/TERRACLIMATE`; and
`../Table1_bootstrap_accuracy/Table1_bootstrap_accuracy.R:20` sets 100
repeats, with repeated train-validation partitioning inside the fitting loop.

The three-stage layout, all boxes and arrows, exogenous/model-internal
branches, uncertainty-gated/ungated wording, grouped permutation analysis,
standardized coefficients, SHAP branch, and conclusions are unchanged.
This is a label correction only, not a validation or revision of those
downstream analyses. Figure 7 and its data/code are untouched. This package itself does not edit a DOCX. The label-corrected workflow is
included in the complete release; the driver-analysis branches remain unchanged.

## Files

- `make_figureS4_workflow.py`: copied native source with the three labels
  changed and SVG/PDF/PNG output enabled.
- `output/FigureS4_workflow_labels_corrected.svg`: editable text and vector
  shapes; suitable as the editable source.
- `output/FigureS4_workflow_labels_corrected.pdf`: vector PDF.
- `output/FigureS4_workflow_labels_corrected.png`: 600-dpi PNG, 4440 × 6850 px.
- `_backup_before_label_update_2026-11-10/`: original plotting source and
  extracted manuscript JPEG, with verified SHA-256 checksums.
- `verify_labels.py`, `output/label_comparison.csv`, and
  `output/verification.json`: label and geometry comparison with the old source.

## Reproduce

```powershell
python make_figureS4_workflow.py
python verify_labels.py
```

Requires Python, matplotlib, NumPy, and Pillow. Arial is available on the
Windows machine used for export. A missing optional Liberation Sans fallback
produced matplotlib font warnings but did not prevent Arial rendering.

## Verification

The exported PNG was visually checked. All three new labels fit within their
original boxes. Automated verification passed: 45 text labels compared,
exactly 3 changed; all 78 shapes/arrows and 3 line objects unchanged;
text positions, font styles, layout, and colors unchanged. SVG contains
editable text, and both backup checksums match.
