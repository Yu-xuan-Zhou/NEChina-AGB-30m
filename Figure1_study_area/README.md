# Figure 1 - Study area, forest cover and final model samples

The map uses the **1,121 samples in the final model input tables**: 164 for the
2005 calibration epoch and 957 for the 2015 calibration epoch. It retains the
original CATCD 2005 forest-cover background, map layout and period colours
(2005-2010 red; 2011-2015 black). 

## Contents

- `data/samples/field_plots.csv`: the exact 1,121 plotting records.
- `data/samples/final_model_samples.csv`: supplementary sample data with original
  plot ID, coordinates, AGB, model epoch, source row and model-input row.
- `output/Figure1_study_area.png` and `.pdf`: regenerated figure.

## Columns

`Period` is the historical figure's sampling-period group label, retained for
plotting; `Model_year` explicitly identifies the calibration epoch. The archived
coordinate tables do not establish an individual field measurement year for
every record. `ID` retains the source plot ID within an epoch. `Latitude` and
`Longitude` are the supplied decimal-degree WGS 84 coordinates; `AGB` is in
Mg ha-1. `RF_input_row` is the one-based RF Landsat+Palsar predictor-table row.
`Source_row` is the one-based data row in the archived coordinate CSV, excluding
the header. Source matching is described in `Match_basis`.


