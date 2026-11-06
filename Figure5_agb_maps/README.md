# Figure 5 - AGB maps of 2005, 2015 and 2024 and AGB change

Six map panels: the 30 m random-forest AGB maps of (a) 2005, (b) 2015 and (c) 2024 and the changes
(d) 2005-2015, (e) 2015-2024 and (f) 2005-2024, each with an inset bar chart of class proportions.
The maps were composed and exported in QGIS.

## Contents

```
Figure5_agb_maps/
├── compute_class_proportions.py    class proportions of the six maps
├── tables/class_proportions.json   pixel counts and percentages per class
├── data/insets/*_range_bar.png     the six inset bar charts
└── output/Figure5_agb_maps.pdf, .png
```

## Run

```
python -X utf8 compute_class_proportions.py
```

Python 3 with numpy and rasterio. The script reads the six 30 m maps (Float32, Mg ha-1) from the
paths set at the top of the script and writes `tables/class_proportions.json`. The maps are
archived at https://doi.org/10.5281/zenodo.23906949 (Int16, scale factor 0.1).

## Classes

- AGB: <= 20, 20-40, 40-60, 60-80, 80-100, 100-120, 120-130, > 130 Mg ha-1.
- Change: <= -80 to > 80 Mg ha-1 in steps of 20.
- Valid pixel: finite and, for the AGB maps, > 0.
