# Figure S3 - The 2024 RF AGB map against CTrees 2024 and CFATD 2023

(a-c) Cell-wise comparison of the 2024 RF AGB map with CTrees 2024, CFATD 2023 and their mean on a
common 1 km grid (dashed line 1:1, orange line OLS fit); (d) mean AGB (+/- 1 SD) of the three
products in the whole forest domain and in four forest zones. Units: Mg ha-1.

## Contents

```
FigureS3_external_benchmark/
├── FigureS3_external_benchmark.py     draws the figure from the 1 km grids
├── data/
│   ├── grids_1km/grid_{RF,CTREES,CFATD}.npy   1 km grids (2349 x 1782, EPSG:4326, NaN = no data)
│   ├── RF_2024_res1km.tif                      grid template (transform, CRS, shape)
│   └── shapefiles/                             polygons of the four forest zones
├── scripts_upstream/
│   ├── build_grids.py                 averages the three products onto the 1 km grid
│   └── download_ctrees_agb_ne.py      clips the CTrees product to the study area
└── output/FigureS3_external_benchmark.png, .pdf, .svg
```

## Run

```
python -X utf8 FigureS3_external_benchmark.py
```

Python 3 with numpy, rasterio, geopandas and matplotlib; font Arial.

## Method

- Products: RF 2024 (this study, 30 m), CTrees 2024 (100 m), CFATD 2023 (30 m); ensemble = cell-wise
  mean of CTrees and CFATD.
- Each product is area-averaged onto the 1 km grid (values with 0 < AGB < 400 Mg ha-1); a panel
  compares the cells that are valid in both products.
- Statistics per panel: n, Pearson r, R2 = r squared, RMSE, bias = reference - RF, OLS slope and
  intercept.
