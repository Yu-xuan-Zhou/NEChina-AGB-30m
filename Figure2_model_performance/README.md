# Figure 2 - Model performance on the validation data

Nine panels (rows: RF, Cubist, MLR; columns: Landsat+PALSAR, Landsat, PALSAR) of field AGB
density against predicted AGB density for 2005 (red) and 2015 (grey), with N, R2, RMSE and Bias
per year. Units: Mg ha-1.

## Contents

```
Figure2_model_performance/
├── train_RF.R, train_MLR.R, train_Cubist.R   model fits; write data/prediction/
├── Figure2_model_performance.R               draws the figure from data/prediction/
├── data/
│   ├── training_input/<table>/<combination>/<year>.csv    predictor tables read by the fits: AGB (Mg ha-1) and the predictors
│   └── prediction/<model>/<combination>/{2005,2015}.csv   actual, prediction (validation plots)
└── output/Figure2_model_performance.jpg
```

`<model>` is RF, Cubist or MLR; `<combination>` is Landsat+Palsar, Landsat or Palsar.

## Run

```
Rscript train_RF.R
Rscript train_MLR.R
Rscript train_Cubist.R
Rscript Figure2_model_performance.R
```

R 4.2.2 with randomForest, MASS, Cubist, caret, ggplot2 (>= 3.4), ggpubr and gridExtra; font Arial.

## Method

- Plots with 0 < AGB < 200 Mg ha-1; `set.seed(11)`, then repeated 70 % / 30 % splits
  (`caret::createDataPartition`); the model of the last repeat predicts its 30 % part. The
  predictor table and the number of repeats of each run are set in the `runs` table of the
  `train_*.R` scripts.
- RF: `randomForest` with the default settings; MLR: backward `stepAIC`; Cubist:
  `cubist(committees = 10)`.
- RMSE = sqrt(mean((actual - prediction)^2)); Bias = mean(actual - prediction); R2 from
  `ggpubr::stat_regline_equation`.
