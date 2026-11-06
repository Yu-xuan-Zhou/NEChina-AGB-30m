# Figure 1 - Study area, forest cover and field plots

Map of Northeast China with the forest-cover classes (tree cover of the 30 m China Annual Tree
Cover Dataset, CATCD, for 2005: <= 10, 10-30, 30-50, 50-70, > 70 %) and the field plots, coloured
by period (2005-2010 red, 2011-2015 black). The map was composed and exported in QGIS.

## Contents

```
Figure1_study_area/
├── data/samples/field_plots.csv   the 1,415 field plots drawn on the map
└── output/Figure1_study_area.pdf, .png
```

## Columns of `field_plots.csv`

- `Period`: 2005-2010 (165 plots) or 2011-2015 (1,250 plots)
- `ID`: plot number within the period
- `Latitude`, `Longitude`: decimal degrees, WGS 84
- `AGB`: aboveground biomass density, Mg ha-1
