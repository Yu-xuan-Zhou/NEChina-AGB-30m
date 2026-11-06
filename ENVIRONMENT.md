# Software used for the figures and tables

All packages were run on Windows 11. The versions are those installed on that machine; nothing
in the code pins them.

## R 4.2.2

- Figures 2, S1 and Table 1, the model fits of `Model_training_bootstrap/`: ggplot2 (>= 3.4),
  ggpubr, gridExtra, grid, randomForest 4.7-1.1, caret 6.0-93, Cubist 0.4.1, MASS 7.3-58.1, dplyr, tidyr,
  rpart 4.1.19, correlation 0.8.3, car 3.1-1, raster 3.6-14 (mapping scripts; `snow` for
  `--cores` > 1).
- The ggplot2 scripts open a scratch PNG device before arranging the panels so that they run
  non-interactively with `Rscript` and use the Arial font.

## Python 3 (Anaconda distribution)

- numpy, pandas, matplotlib, seaborn, scipy, scikit-learn, rasterio 1.4.3 (GDAL 3.6.2),
  geopandas, openpyxl, shap (Tables S2-S4), nbconvert 7.16 for the notebooks.
- Run scripts with `python -X utf8 <script>.py`; run notebooks with
  `jupyter nbconvert --to notebook --execute <notebook>.ipynb`.
- `data_release/` additionally uses the GDAL command-line tools (`gdal_translate`,
  `gdaladdo`; COG driver) and `requests` for the Zenodo upload; `markdown` renders the README
  into the Zenodo description.

## QGIS 3.x

- Figures 1, 5 and S2 were composed in QGIS.

## Google Earth Engine

- `Model_training_bootstrap/gee/` holds the Code Editor scripts (JavaScript) that sampled the
  predictors at the plots and exported the predictor rasters and forest masks.

## Fonts

- Arial, 10 pt on 180 mm canvases for the Python / R figures (Figure 7: 12 pt on an 8.8 in canvas).
