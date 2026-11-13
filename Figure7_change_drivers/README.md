# Figure 7 - Drivers of the change in AGB density and forest fraction

## Run

From this folder (numpy, pandas, matplotlib; `requirements.txt`):

```
python -X utf8 code/figure7.py check    # validate the tables, write nothing
python -X utf8 code/figure7.py render   # write the plotting tables and the figure
```

## Files

| Path | Content |
|---|---|
| `code/figure7.py` | checks, normalization, figure |
| `code/task2f_joint_permutation_models.py`, `code/task2h_hybrid_structure_models.py`, `code/variable_config.py` | model fits from the 1 km rasters (folders set by the `AGB_NE_*` environment variables) |
| `code/upstream/` | 1 km covariates and climate export |
| `tables/fig7_hybrid_repeats.csv` | permutation results: 4 models x 7 factors x 50 repeats |
| `tables/fig7_hybrid_bootstrap_betas.csv` | direction of association |
| `tables/fig7_hybrid_model_r2.csv` | holdout R2 and sample sizes |
| `tables/fig7_hybrid_summary.csv` | model summary |
| `tables/fig7_hybrid_period_display.csv`, `tables/SourceData_Figure7.csv` | plotted values |
| `figures/Figure7.png`, `.pdf`, `.svg` | figure |

## Normalization

Within each outcome and period the seven factors sum to 100 %:

importance (%) = 100 x max(mean ΔR2, 0) / Σ max(mean ΔR2, 0)

Whiskers: 2.5th and 97.5th percentiles of the 50 permutations, scaled by the same denominator.

## Samples

- Density model: 1 km cells passing the k = 1 uncertainty screen in 2005-2015; no screen in 2015-2024.
- Area model: 1 km cells with initial forest fraction < 0.95.
