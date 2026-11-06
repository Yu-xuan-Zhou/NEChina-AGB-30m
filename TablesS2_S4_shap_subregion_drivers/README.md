# Tables S2, S3 and S4 - SHAP check and driver importance by subregion

- Table S2: share of the mean |SHAP| held by the exogenous and by the model-internal predictors,
  per subregion and period.
- Table S3 (AGB density) and Table S4 (forest fraction): relative grouped permutation importance (%)
  of the seven factors of Figure 7 in models fitted per subregion, with the holdout R2.

## Contents

```
TablesS2_S4_shap_subregion_drivers/
├── build_tables_S2_S4.py                    builds output/Tables_S2_S3_S4.xlsx from data/
├── data/
│   ├── shap/shap_importance_all.csv         region x period x predictor: mean |SHAP|, group
│   ├── shap/shap_importance_<region>_<period>.csv
│   ├── subregion_fig7_importance_long.csv   region x response x period x factor: relative importance (%)
│   ├── subregion_fig7_model_r2.csv          holdout R2 and n per model
│   └── subregion_fig7_{density,area}_wide_{05_15,15_24}.csv
├── scripts_upstream/                        scripts that computed the files in data/
│   ├── shap/task7_shap_augmented.py         SHAP analysis (random forest, shap.TreeExplainer)
│   ├── task2i_subregion_drivers.py          subregion models
│   └── task2h_hybrid_structure_models.py, task2f_joint_permutation_models.py, variable_config.py
└── output/
    ├── Tables_S2_S3_S4.xlsx                 three sheets
    └── Table_S2_SHAP_circularity.docx, Table_S3_S4_subregion_drivers.docx
```

## Run

```
python -X utf8 build_tables_S2_S4.py
```

Python 3 with pandas, numpy and openpyxl. The scripts in `scripts_upstream/` read the 1 km rasters
from the paths set inside the scripts.

Subregions: NE (all of Northeast China), DXAL (Daxing'an Mts.), XXAL (Xiaoxing'an Mts.), CBS
(Changbai Mts.), SJP (Sanjiang Plain), PERMA (permafrost zone). Periods: 2005-2015 and 2015-2024.
