# Table 2 - AGB density, forest area and carbon of this study's maps and other products

## Contents

```
Table2_product_comparison/
├── Table2_product_comparison.py          builds the table from the raster statistics
├── data/model_comparison_rawstats.csv    per raster: valid pixels, sum, range, area
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

- Valid pixel: value > 0, finite and not NoData; pixel area on the WGS84 ellipsoid for geographic
  rasters, native cell size for projected rasters.
- Density = area-weighted mean of the valid pixels (Mg ha-1); forest area = sum of the areas of
  the valid pixels.
- Raster carbon = density x area (ha) x 0.5 x 1e-9 (Pg C); carbon fraction 0.50.
- Literature entries retain the source's carbon accounting. Zhao (2005) is entered in `LITERATURE`.
- The script also synchronizes the Xu row of the existing manuscript CSV; other manuscript rows are preserved.

## Xu et al. (2018) source and scope

Xu, L., Yu, G., He, N., Wang, Q., Gao, Y., Wen, D., Li, S., Niu, S., and Ge, J.
(2018). Carbon storage in China's terrestrial ecosystems: A synthesis.
Scientific Reports 8, 2806. https://doi.org/10.1038/s41598-018-20764-9


Source supplement: https://media.springernature.com/full/springer-static/esm/art%3A10.1038%2Fs41598-018-20764-9/MediaObjects/41598_2018_20764_MOESM1_ESM.doc

