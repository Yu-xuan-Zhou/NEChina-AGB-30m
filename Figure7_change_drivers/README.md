# Figure 7 - Drivers of the change in AGB density and forest fraction

Relative grouped permutation importance of seven factors in random-forest models of (a) the change
in AGB density and (b) the change in forest fraction, for 2005-2015 and 2015-2024, on a 1 km grid.

## Contents

```
Figure7_change_drivers/
├── code/
│   ├── figure7.py                           entry point: render, check, fit
│   ├── task2h_hybrid_structure_models.py    the density and area models
│   ├── task2f_joint_permutation_models.py   raster reading, random forest, permutation and bootstrap helpers
│   ├── task5d_figure7_hybrid.py             builds the plotting table
│   ├── variable_config.py                   predictor lists
│   └── upstream/                            scripts that built the 1 km covariates and exported the climate layers
├── tables/
│   ├── SourceData_Figure7.csv               bar values, intervals and directions drawn in the figure
│   └── fig7_hybrid_*.csv                    model outputs: permutation repeats, bootstrap coefficients, R2
├── figures/Figure7.pdf, .png, .svg
├── paths.json                               locations of the 1 km rasters read by `fit` and `check`
└── requirements.txt
```

## Run

```
python -X utf8 code/figure7.py render
```

draws the figure from `tables/` (numpy, pandas, matplotlib). `python -X utf8 code/figure7.py fit`
refits the four models from the 1 km rasters listed in `paths.json` and rewrites the tables and
the figure; `check` inspects those rasters.

## Method

- One random forest per response (change in AGB density, change in forest fraction) and period:
  300 trees, minimum leaf size 20, 70 % / 30 % split of the sampled 1 km cells.
- Importance: the predictors of a factor are permuted together in the test data and the decrease
  in R2 is averaged over 50 permutations; the 14 bars of a panel (seven factors, two periods) sum
  to 100 %.
- Colour: sign of the standardized coefficient of a multiple linear regression over 500 bootstrap
  resamples (blue positive, red negative, light grey when the interval includes zero); the
  starting-state factor is dark grey.

| Factor | Predictors |
|---|---|
| Forest structure / starting state | density models: initial AGB, tree cover 2000; area models: initial forest fraction, distance to forest, tree cover 2000 |
| Precipitation | May-October precipitation (TerraClimate) |
| Soil moisture | May-October soil moisture (TerraClimate) |
| Water deficit | May-October climatic water deficit (TerraClimate) |
| VPD | May-October vapour-pressure deficit (TerraClimate) |
| Delta LST | change in land-surface temperature (MODIS) |
| Terrain | elevation, slope |
