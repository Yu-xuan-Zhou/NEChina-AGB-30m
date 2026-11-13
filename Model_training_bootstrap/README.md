# Model workflow: model fits, accuracy and mapping

The modelling steps upstream of the figures: the 70 % / 30 % model fits behind
Figure 2 and Figure S1, the accuracy table (Table 1), the application of a model to the predictor
rasters, the aggregation of the repeated maps, and the Earth Engine scripts that sampled and
exported the predictors. AGB in Mg ha-1.

## Contents

```
Model_training_bootstrap/
├── 02_fit_models_70_30.R            fits the 18 model x data x year combinations
├── 03_bootstrap_accuracy_table1.R   runs ../Table1_bootstrap_accuracy and copies its table
├── 04_map_and_bootstrap_maps.R      applies the model of split k to a raster stack
├── 05_aggregate_bootstrap_maps.R    per-pixel mean, SD and relative SD of the repeated maps, forest mask
├── data/
│   ├── predictor_tables/<model>/<combination>/{2005,2015}.csv   AGB and the predictors of each model
│   └── variable_selection/candidates_2015.csv    historical candidate table; not required by steps 02–05
├── gee/                             Earth Engine scripts (see gee/README.md)
└── output/
    ├── validation/<model>/<combination>/<year>.csv   30 % part: actual, prediction (Figure 2)
    ├── training/<model>/<combination>/<year>.csv     70 % part: actual, prediction (Figure S1)
    ├── fit_summary.csv                               N, R2, RMSE and Bias per file
    ├── table1_bootstrap_comparison_table.csv         table written by 03
    └── variable_selection/                           historical exploratory outputs; not required by steps 02–05
```

## Run

From this folder, R 4.2.2:

```
Rscript 02_fit_models_70_30.R
Rscript 03_bootstrap_accuracy_table1.R
Rscript 04_map_and_bootstrap_maps.R --model RF --year 2015 --table data/predictor_tables/RF/Landsat+Palsar/2015.csv \
        --rasters <folder with one GeoTIFF per predictor> --out <folder> --first 1 --last 100
Rscript 05_aggregate_bootstrap_maps.R --maps <folder of maps> --model RF --year 2015 --out <folder> \
        --mask <CATCD tree cover of the year> --threshold 10
```

Packages: randomForest, caret, Cubist, MASS, rpart, correlation, car, raster.

## Steps

- **02** Plots sorted by AGB; `set.seed(11)`, then one
  `caret::createDataPartition(AGB, p = 0.7)`; the model is fitted on the 70 % part and predicts
  both parts. RF: `randomForest` with the default settings; MLR: backward `stepAIC`; Cubist:
  `cubist(committees = 10)`.
- **03** Runs the Table 1 script of `../Table1_bootstrap_accuracy` and copies its table.
- **04** All plots are retained and sorted by AGB, as in **02**; there is no AGB upper cutoff.
  The model of split k predicts the raster stack and writes `<model>_<year>_<k>.tif`;
  k = 1..100 gives the repeated maps. Use the default MLR fit without `--formula` when matching
  **02**; `--formula` is an optional fixed-variable fit for historical workflows.
- **05** Per-pixel mean, SD and relative SD (100 x SD / mean) of the repeated maps, masked with the
  CATCD tree cover of the same year > 10 %.

