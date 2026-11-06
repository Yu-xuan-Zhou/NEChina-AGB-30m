# Earth Engine scripts

Code Editor scripts (JavaScript) that sampled the predictors at the field plots and exported the
predictor rasters, the forest masks and the map products. They use objects of the Code Editor
"Imports" panel: `table` = Northeast China boundary, `table2` = field-plot points, `image`,
`image2`, ... = maps uploaded as assets.

| Script | What it does |
|---|---|
| `landsat_5.js` | Landsat 5 (Collection 2, Level 2), May-October 2005: median composite with cloud and cloud-shadow mask, spectral indices; samples the plots and exports the predictor rasters |
| `landsat8.js` | Landsat 8, May-October 2015: median composite with cloud and cloud-shadow mask, spectral indices; samples the plots |
| `LANDSAT_LC09_C02_T1_L2.js` | Landsat 9, May-October 2024: median composite; exports NDVI, LSWI, NDWI, SR_B3 and SR_B4 at 30 m |
| `Palsar_2005.js` | PALSAR yearly mosaic 2007: HH, HV, their combinations and GLCM textures (3 x 3 window) sampled at the plots |
| `palsar_2015_points.js` | PALSAR-2 yearly mosaic 2015: the same variables sampled at the plots |
| `PALSAR.js` | PALSAR-2 yearly mosaic 2024: exports HH, HV and HV_savg at 30 m |
| `srtm.js` | SRTM elevation and slope sampled at the plots |
| `CATCD_treecover_export.js` | CATCD tree cover of one year (percent), exported for the forest mask |
| `RF_10_2024_CATCD.js` | forest mask of 2024: CATCD tree cover > 10 % |
| `MLR_2005.js`, `MLR_2015.js`, `Cubist_2015.js` | per-pixel mean and SD of the uploaded maps, masked with CATCD tree cover > 10 % |
| `RF_bootstrap_mean_sd_mask_template.js` | the same step for a list of asset ids, with the relative SD |
| `AGB_masked_export.js` | the final maps masked with CATCD tree cover > 10 % of their year, exported at 30 m |
