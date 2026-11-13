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

R 4.2.2 with randomForest, Cubist, MASS, caret, dplyr, tidyr and ggplot2; about 10 minutes.

## Method

- For each of the 18 tables the plots are sorted by AGB; `set.seed(11)`, then 100 repeats of
  `createDataPartition(AGB, p = 0.7)`: the model is fitted on the 70 % part and evaluated on the 30 % part.
- RF: `randomForest` with the default settings; MLR: backward `stepAIC`; Cubist:
  `cubist(committees = 10)`.
- R2 = 1 - SSres / SStot; Bias = mean(prediction) - mean(observation).
