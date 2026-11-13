# Forest aboveground biomass of Northeast China at 30 m (2005, 2015, 2024)

Code and small data behind the figures and tables of

> Zhou Y., Feng L., Zhang R., Ouyang Z., Barnes M., Tang X., Du Z., Zhou X. **Integrating
> Multi-Source Data with Machine Learning to Estimate Forest Aboveground Biomass Dynamics in
> Northeast China.** *Journal of Plant Ecology* (manuscript JPE-2026-0380).

The six 30 m maps of the paper (random-forest AGB of 2005, 2015 and 2024 and the three change
maps) are archived on Zenodo: https://doi.org/10.5281/zenodo.23906949 (cloud-optimised GeoTIFF,
CC BY 4.0).


## Layout

One folder per figure or table, with the code, the small input data it reads, the output and a
`README.md` with the command to run it.

| Folder | Content | Tool |
|---|---|---|
| `Figure1_study_area/` | Figure 1 - study area, forest cover and field plots | field-plot table, exported map |
| `Figure2_model_performance/` | Figure 2 - validation scatter plots of the nine model x data combinations, with the model fits | R |
| `Figure3_variable_importance/` | Figure 3 - variable importance by AGB range | R, Python notebook |
| `Figure4_model_comparison/` | Figure 4 - comparison of the RF, Cubist and MLR estimates | Python |
| `Figure5_agb_maps/` | Figure 5 - AGB maps of 2005, 2015 and 2024 and change maps | exported map, Python |
| `Figure6_carbon_dynamics/` | Figure 6 - changes in AGB density, carbon storage and forest area | Python notebook |
| `Figure7_change_drivers/` | Figure 7 - drivers of the change in AGB density and forest fraction | Python |
| `FigureS1_training_performance/` | Figure S1 - training-data scatter plots | R |
| `FigureS2_model_maps/` | Figure S2 - maps of the RF, Cubist and MLR models for 2005 and 2015 | exported map |
| `FigureS3_external_benchmark/` | Figure S3 - the 2024 RF map against CTrees 2024 and CFATD 2023 | Python |
| `Table1_bootstrap_accuracy/` | Table 1 - accuracy of the nine combinations over 100 random splits | R |
| `Table2_product_comparison/` | Table 2 - density, forest area and carbon of this study's maps and other products | Python |
| `TableS1_variable_descriptions/` | Table S1 - predictor variables | CSV |
| `TablesS2_S4_shap_subregion_drivers/` | Tables S2-S4 - SHAP check and driver importance by subregion | Python |
| `Model_training_bootstrap/` | model workflow: supplied predictor tables, model fits, mapping, aggregation of the repeated maps, Earth Engine scripts | R, Earth Engine JavaScript |
| `data_release/` | conversion of the AGB maps to the files of the Zenodo record | Python |

## Running the code

Clone the repository (`git clone https://github.com/Yu-xuan-Zhou/NEChina-AGB-30m.git`) and run each
script from inside its folder with the command given in the folder's README.

- R scripts: `Rscript <script>.R` (R 4.2.2).
- Python scripts: `python -X utf8 <script>.py`; notebooks:
  `jupyter nbconvert --to notebook --execute <notebook>.ipynb`.
- `ENVIRONMENT.md` lists the software versions.

The figures are drawn from the data in their folders. Scripts that start from the 30 m rasters
read them from the paths set at the top of each script.

## Conventions

- AGB: aboveground biomass of living trees, dry mass, Mg ha-1.
- Pixel area on the WGS84 ellipsoid; valid pixel: value > 0 and finite; AGB density = area-weighted
  mean of the valid pixels; forest area = sum of the areas of the valid pixels; carbon stock =
  density x area x 0.5 (carbon fraction 0.50).
- Forest mask: China Annual Tree Cover Dataset (CATCD), tree cover > 10 % of the same year.
- Field plots: `Figure1_study_area/data/samples/field_plots.csv`; predictor tables of the models:
  `Model_training_bootstrap/data/predictor_tables/`.

## Licence and citation

Code: MIT License (`LICENSE`). Data on Zenodo: CC BY 4.0. Please cite the paper and the data
record (`CITATION.cff`).

Contact: Zhenggang Du, Northeast Forestry University, zgdu@nefu.edu.cn
