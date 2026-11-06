# Table 1 - Accuracy of the nine model x data combinations

R2, RMSE and Bias (mean +/- SD over 100 repeats) and the minimum, maximum and mean of the
predictions for the RF, MLR and Cubist models on Landsat+PALSAR, Landsat and PALSAR predictors,
for 2005 and 2015. Units: Mg ha-1.

## Contents

```
Table1_bootstrap_accuracy/
├── Table1_bootstrap_accuracy.R
├── data/filtered_variables/<model>/<combination>/{2005,2015}.csv   AGB (Mg ha-1) and the predictors of each model
└── output/
    ├── bootstrap_comparison_table.csv   Table 1
    ├── all_bootstrap_results.csv        every repeat
    ├── bootstrap_summary_stats.csv, bootstrap_detailed_summary.csv
    └── r2_distribution.png, rmse_distribution.png, bias_distribution.png
```

## Run

```
Rscript Table1_bootstrap_accuracy.R
```

R 4.2.2 with randomForest, Cubist, caret, dplyr, tidyr and ggplot2; about 5 minutes.

## Method

- `set.seed(123)`; for each of the 18 tables 100 repeats of `createDataPartition(AGB, p = 0.8)`:
  the model is fitted on the 80 % part and evaluated on the 20 % part.
- RF: `randomForest(AGB ~ ., importance = TRUE)`; MLR: `lm(AGB ~ .)`; Cubist: `cubist()` with the
  default settings.
- R2 = 1 - SSres / SStot; Bias = mean(prediction) - mean(observation).
