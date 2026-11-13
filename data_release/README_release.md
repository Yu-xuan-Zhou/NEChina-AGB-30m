# Forest aboveground biomass of Northeast China at 30 m (2005, 2015, 2024) and its change

Data accompanying the paper **Integrating Multi-Source Data with Machine Learning to Estimate
Forest Aboveground Biomass Dynamics in Northeast China** (*Journal of Plant Ecology*,
manuscript JPE-2026-0380).

Authors: Yuxuan Zhou (1, 3), Lianjun Feng (1), Rong Zhang (2), Zutao Ouyang (2), Mallory
Barnes (3), Xuli Tang (4), Zhenggang Du (1, corresponding), Xuhui Zhou (1, corresponding).

1. Institute of Carbon Neutrality, Key Laboratory of Sustainable Forest Ecosystem
   Management-Ministry of Education, School of Ecology, Northeast Forestry University, Harbin
   150040, China
2. College of Forestry, Wildlife and Environment, Auburn University, Auburn, AL, USA
3. O'Neill School of Public and Environmental Affairs, Indiana University, Bloomington, IN, USA
4. Key Laboratory of Vegetation Restoration and Management of Degraded Ecosystems, South China
   Botanical Garden, Chinese Academy of Sciences, Guangzhou, China

Contact: Zhenggang Du, Northeast Asia Ecosystem Carbon Sink Research Center (NACC), Key
Laboratory of Sustainable Forest Ecosystem Management-Ministry of Education, School of
Forestry, Northeast Forestry University, Harbin 150040, China; zgdu@nefu.edu.cn

This record holds the three random-forest (RF) AGB maps of the paper and the three change
maps drawn in Figure 5.

## Files

<!-- FILE TABLE -->
| File | Size (GB) | Valid pixels | Pixel arithmetic mean (Mg ha-1) | Min | Max | Check | sha256 (first 12) |
|---|---|---|---|---|---|---|---|
| `NEChina_AGB_30m_RF_2005.tif` | 1.51 | 687,710,895 | 83.63 | 10.2 | 160.2 | passed | fd768f3aba6c |
| `NEChina_AGB_30m_RF_2015.tif` | 2.07 | 913,915,190 | 79.44 | 11.2 | 174.0 | passed | ca7e161738f7 |
| `NEChina_AGB_30m_RF_2024.tif` | 2.20 | 960,589,141 | 78.11 | 11.3 | 173.5 | passed | 6c707d391236 |
| `NEChina_AGBchange_30m_2005_2015.tif` | 2.14 | 919,979,172 | 16.40 | -155.9 | 172.1 | passed | 4617f0ab1285 |
| `NEChina_AGBchange_30m_2005_2024.tif` | 2.27 | 969,335,841 | 18.07 | -157.5 | 171.6 | passed | b61435f4de9e |
| `NEChina_AGBchange_30m_2015_2024.tif` | 2.34 | 989,505,121 | 2.45 | -172.2 | 170.7 | passed | f552205440b5 |
<!-- /FILE TABLE -->

Full checksums: `sha256sums.txt` and `md5sums.txt`. Each `.tif` has a `.json` with the
statistics of the Float32 source and of the released file, the comparison results and the
encoding. The means in this file table and the per-file JSON reports are unweighted pixel
arithmetic means used to check the encoding. They are distinct from the area-weighted
regional means reported below.

| File | Content |
|---|---|
| `NEChina_AGB_30m_RF_2005.tif` | AGB 2005; RF model, Landsat 5 TM (2005) + ALOS PALSAR (2007 mosaic) predictors |
| `NEChina_AGB_30m_RF_2015.tif` | AGB 2015; RF model, Landsat 8 OLI + ALOS-2 PALSAR-2 predictors |
| `NEChina_AGB_30m_RF_2024.tif` | AGB 2024; the 2015 RF model applied to Landsat 9 OLI + PALSAR-2 predictors of 2024 |
| `NEChina_AGBchange_30m_2005_2015.tif` | AGB 2015 minus AGB 2005 (Figure 5 d) |
| `NEChina_AGBchange_30m_2015_2024.tif` | AGB 2024 minus AGB 2015 (Figure 5 e) |
| `NEChina_AGBchange_30m_2005_2024.tif` | AGB 2024 minus AGB 2005 (Figure 5 f) |

## Grid and format

- 72,632 columns x 55,084 rows, EPSG:4326 (WGS 84), pixel 0.000269494585 degrees (nominal
  30 m resolution); upper-left corner 115.5218184 E, 53.5636658 N;
  extent 115.52-135.10 E, 38.72-53.56 N. All six files share this grid exactly.
  Actual pixel area varies with latitude and is calculated on the WGS 84 ellipsoid.
- Int16; **stored value = 10 x AGB in Mg ha-1** (scale factor 0.1 is written in the band
  metadata; GDAL tools, QGIS, R `terra` and ArcGIS apply it; in `rasterio` / numpy multiply
  by 0.1 yourself). Precision 0.1 Mg ha-1; the largest difference to the Float32 originals is
  0.05 Mg ha-1 and the pixel arithmetic means agree to better than 1e-5 Mg ha-1.
- NoData = -32768: outside the forest mask (and, in the AGB maps, source pixels <= 0).
- Cloud-optimised GeoTIFF: DEFLATE (level 9, predictor 2), 512 x 512 tiles, overviews
  (average resampling, factors 2-256). The files can be read in place over HTTP with
  `/vsicurl/` or opened in QGIS without downloading when the host supports range requests.
- Tags in each file: TITLE, YEAR, UNITS, SCALE_FACTOR, NODATA_VALUE, VALUE_RULE, FOREST_MASK,
  MODEL, SOURCE_FILE, CRS, CREATED, REFERENCE.
  Existing TIFFs contain a descriptive CRS tag stating "about 30 m, 0.09 ha". This is a
  legacy nominal-resolution description, not the actual area of each geographic-grid
  pixel; do not use 0.09 ha for regional area or stock calculations. The raster CRS,
  transform and pixel values are unchanged.

## Definitions

- **AGB**: aboveground biomass of living trees, dry mass, Mg ha-1 (oven-dry tonnes per hectare).
- **Forest mask**: China Annual Tree Cover Dataset (CATCD; Cai et al. 2024) tree cover > 10 %
  of the same year. After applying this mask, forest area is operationally defined as
  the summed WGS 84 ellipsoidal area of valid, finite pixels with AGB > 0. Pixels outside
  the mask, NoData and AGB <= 0 are excluded. The resulting forest areas are 41.54 Mha in
  2005, 55.75 Mha in 2015 and 58.68 Mha in 2024 (Table 2 of the paper).
- **Change maps**: AGB of the later year minus AGB of the earlier year, over the union of the
  forest pixels of both years, as drawn in Figure 5 d-f; positive = gain. A pixel that is
  forest in only one of the two years enters with AGB = 0 for the year in which it is not
  forest, so new forest shows its full later-year AGB as a gain and cleared forest its full
  earlier-year AGB as a loss.
- **Regional statistics of the paper** (Table 2, Figure 6): calculated from the Float32
  RF source maps using the same mask and AGB > 0 rule. For valid pixel i with AGB density
  B_i (Mg ha-1) and WGS 84 ellipsoidal area a_i (ha), forest area = sum(a_i), area-weighted
  mean AGB density = sum(B_i x a_i) / sum(a_i), and AGB carbon stock =
  sum(B_i x a_i) x 0.50 / 1e9 (Pg C; carbon fraction 0.50). Pixel areas are calculated
  between the latitude boundaries of each raster row. The values for Northeast China are:

| Year | Area-weighted mean AGB density (Mg ha-1) | Forest area (Mha) | AGB carbon stock (Pg C) |
|---|---|---|---|
| 2005 | 84.24 | 41.54 | 1.75 |
| 2015 | 79.57 | 55.75 | 2.22 |
| 2024 | 78.44 | 58.68 | 2.30 |

## Method summary

Field plots compiled from the literature (two periods, 2005-2010 and 2011-2015) were matched
with growing-season Landsat composites, PALSAR / PALSAR-2 mosaics and SRTM terrain; nine model /
data combinations (RF, Cubist, MLR x Landsat, PALSAR, both) were compared over 100 random
training / validation splits; the RF model on Landsat + PALSAR was used for the maps. The code
of every figure and of the model workflow, including the scripts that built and checked the
files of this record, is in the GitHub repository
https://github.com/Yu-xuan-Zhou/NEChina-AGB-30m (MIT License).

## Processing

The maps were exported from Google Earth Engine as Float32 GeoTIFF (masked with CATCD) and
converted with `build_release_maps.py`: values multiplied by 10 and rounded to Int16, NaN (and,
for the AGB maps, values <= 0) set to NoData, written as cloud-optimised GeoTIFF with
`gdal_translate` (GDAL 3.6.2).

## Licence and citation

Licence: Creative Commons Attribution 4.0 International (CC BY 4.0).
Please cite the paper and this record: Zenodo, https://doi.org/10.5281/zenodo.23906949
(version 1.0.0).
