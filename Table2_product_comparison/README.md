# Table 2 - AGB density, forest area and carbon of this study's maps and other products

## Contents

```
Table2_product_comparison/
├── Table2_product_comparison.py          builds the table from the raster statistics
├── data/model_comparison_rawstats.csv    per raster: valid pixels, sum, range, pixel area
└── output/
    ├── model_comparison_table_all_products.csv   all products
    └── Table2_manuscript.csv                     the rows of Table 2
```

## Run

```
python -X utf8 Table2_product_comparison.py
```

Python 3 with numpy, pandas and rasterio. The table is built from
`data/model_comparison_rawstats.csv`; with `FORCE_RESCAN = True` the script reads the rasters
again from the paths set at the top of the script.

## Calculation

- Valid pixel: value > 0, finite and not NoData; pixel area from the resolution of each raster
  (0.09 ha on the 30 m grid).
- Density = mean of the valid pixels (Mg ha-1); forest area = valid pixels x pixel area.
- Carbon = density x area (ha) x 0.5 x 1e-9 (Pg C); carbon fraction 0.50.
- The values of Zhao (2005) and Xu (2015) are entered in the `LITERATURE` list of the script.
