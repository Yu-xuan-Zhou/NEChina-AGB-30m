# Figure 6 - Changes in AGB density, carbon storage and forest area

Four panels for five regions (Northeast China, Permafrost, Changbai Mt., Daxing'anling,
Xiaoxing'anling) and two periods (2005-2015, 2015-2024): (a) change in AGB density (Mg ha-1),
(b) change in carbon storage (Pg C), (c) change in forest area (Mha), (d) decomposition of the
carbon change of Northeast China into an area-driven and a density-driven part (Pg C).

## Contents

```
Figure6_carbon_dynamics/
├── Figure6_carbon_dynamics.ipynb       draws the figure from the three CSV files
├── build_fig6_tables.py                builds the CSV files from the RF AGB maps
├── figure6_yearly_raster_stats.csv     region x year: pixels, area, density, carbon stock
├── figure6_raster_summary.csv          region x period: changes in density, stock and area
├── figure6_decomposition_summary.csv   Northeast China: area-driven, density-driven, interaction, total
└── output/Figure6_carbon_dynamics.pdf, .png
```

## Run

```
jupyter nbconvert --to notebook --execute Figure6_carbon_dynamics.ipynb
```

Python 3 with numpy, pandas, matplotlib and rasterio; font Arial. `python build_fig6_tables.py`
rebuilds the CSV files from the 30 m RF maps (paths at the top of the script).

## Calculation

- Pixel area 0.09 ha; valid pixel: value > 0 and finite.
- AGB density = mean of the valid pixels (Mg ha-1); forest area = valid pixels x 0.09 ha.
- Carbon stock = area (ha) x density x 0.5 x 1e-9 (Pg C); carbon fraction 0.50.
- Decomposition of a period t0 -> t1: area-driven = density(t0) x change in area; density-driven =
  area(t0) x change in density; interaction = change in area x change in density.
