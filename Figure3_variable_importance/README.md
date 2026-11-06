# Figure 3 - Variable importance across AGB ranges

Two stacked-bar panels, (a) 2005 and (b) 2015: for each AGB range (0-200, 0-50, 50-100, 100-150,
150-200 Mg ha-1) the random-forest importance of every predictor as a share (%) of the total
importance within that range.

## Contents

```
Figure3_variable_importance/
├── Figure3_variable_importance.ipynb   draws the figure from data/RF_importance_<year>.csv
├── RF_importance_by_range.R            importance shares per year and AGB range
├── data/
│   ├── RF_importance_2005.csv, RF_importance_2015.csv   tables drawn in the figure (index, important, Range)
│   ├── per_range_raw/RF_<year>_<range>.csv              importance shares of all predictors per year and AGB range
│   └── training_input/Landsat+Palsar_{2005,2015}.csv    input of the R script: AGB (Mg ha-1) and the RF predictors
└── output/
    ├── Figure3_variable_importance.pdf, .png
    └── importance_by_range/RF_<year>_<range>.csv        written by the R script
```

## Run

```
jupyter nbconvert --to notebook --execute Figure3_variable_importance.ipynb
Rscript RF_importance_by_range.R
```

Python 3 with pandas, matplotlib and seaborn; R 4.2.2 with randomForest and caret.

## Method

- R script: plots of the AGB range, `set.seed(11)`, 100 random 70 % / 30 % splits, random forest on
  the 70 % part; permutation importance (`caret::varImp`) of the last model, positive values
  expressed as shares (%) of their sum.
- Tables drawn in the figure: the shares of `data/per_range_raw/`; in the 2005 table
  `Optical_Bands`, `HH_Texture` and `HV_Texture` are the sums of the Landsat bands, the HH texture
  predictors and the HV texture predictors.
