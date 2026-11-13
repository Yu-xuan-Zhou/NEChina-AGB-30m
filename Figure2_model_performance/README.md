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
│   ├── training_input/<model>/<combination>/<year>.csv    predictor tables read by the fits: AGB (Mg ha-1) and the predictors
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

R 4.2.2 with randomForest, MASS, Cubist, caret, ggplot2 (>= 3.4) and gridExtra; font Arial.

## Method

- Plots sorted by AGB; `set.seed(11)`, then one 70 % / 30 % split
  (`caret::createDataPartition`); the model predicts its 30 % part.
- RF: `randomForest` with the default settings; MLR: backward `stepAIC`; Cubist:
  `cubist(committees = 10)`.
- RMSE = sqrt(mean((actual - prediction)^2)); Bias = mean(prediction - actual);
  R2 = 1 - SSres / SStot.
