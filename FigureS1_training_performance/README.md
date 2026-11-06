# Figure S1 - Model performance on the training data

Training-data counterpart of Figure 2: nine panels (rows: RF, Cubist, MLR; columns: Landsat+PALSAR,
Landsat, PALSAR) of field AGB density against predicted AGB density for the training plots of 2005
(red) and 2015 (grey), with N, R2, RMSE and Bias per year. Units: Mg ha-1.

## Contents

```
FigureS1_training_performance/
├── FigureS1_training_performance.R                       draws the figure
├── data/training/<model>/<combination>/{2005,2015}.csv   actual, prediction (training plots)
└── output/FigureS1_training_performance.jpg
```

## Run

```
Rscript FigureS1_training_performance.R
```

R 4.2.2 with ggplot2 (>= 3.4), ggpubr and gridExtra; font Arial. The data files are written by
`../Model_training_bootstrap/02_fit_models_70_30.R`.
