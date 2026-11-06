# Figure 4 - Comparison of the RF, Cubist and MLR AGB estimates

Three panels drawn by one script: (a) latitude profile of the coefficient of variation of the AGB
maps, (b) violin plots of AGB density by year and method, with the field data, (c) stacked bars
of AGB density classes for the field data and the models. Units: Mg ha-1.

## Contents

```
Figure4_model_comparison/
├── Figure4_combine.py              draws the three panels
├── build_precomputed_data.py       builds data/precomputed_data.npz from the relative-SD rasters
├── data/
│   ├── precomputed_data.npz            panel (a): row means of the relative SD of the six maps
│   ├── field_plots_literature.xlsx     field plots: ID, Latitude, Longitude, AGB, Year, Reference
│   └── density_class/<model>_<year>_mask_10.csv   panel (c): class proportions of each map
├── cache/violin_samples.npz        panel (b): sample of 1e6 pixels of each AGB map
└── output/                         the figure (pdf, png) and the separate panels
```

## Run

```
python -X utf8 Figure4_combine.py
```

Python 3 with numpy, pandas, matplotlib, seaborn, rasterio and openpyxl; font Arial. The figure
is drawn from `data/` and `cache/`. `Figure4_combine.py --resample` and
`build_precomputed_data.py` read the 30 m rasters from the paths set at the top of the scripts.

## Method

- Panel (a): row mean of the relative SD (values <= 0 ignored), smoothed with a moving average.
- Panel (b): values outside 1.5 x IQR removed per year and method; field plots of 2005-2010 are
  shown as 2005 and those of 2011-2015 as 2015; dashed lines mark the group medians.
- Panel (c): proportion of each AGB density class per map and per field period.
