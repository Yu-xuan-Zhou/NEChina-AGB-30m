# Earth Engine scripts

Code Editor scripts (JavaScript) for sampling the predictors at the field plots and exporting the
predictor rasters, the forest masks and the map products. The 2005 Landsat script is a documented
reconstruction, not a recovered historical production script (see below). They use objects of the Code Editor
"Imports" panel: `table` = Northeast China boundary, `table2` = field-plot points, `image`,
`image2`, ... = maps uploaded as assets.

| Script | What it does |
|---|---|
| `landsat_5.js` | Landsat 5 Collection 1 Surface Reflectance, May-October 2005: reconstructed C1 workflow retaining the archived predictors' stored-value scale; historical scene/QA/compositing details remain to be verified |
| `landsat8.js` | Landsat 8 Collection 2 Level-2, May-October 2015: scaled reflectance, per-scene indices, then median; samples the plots |
| `LANDSAT_LC09_C02_T1_L2.js` | Landsat 9 Collection 2 Level-2, May-October 2024: scaled reflectance, median, then indices; exports NDVI, LSWI, NDWI, SR_B3 and SR_B4 at 30 m |
| `Palsar_2005.js` | PALSAR yearly mosaic 2007: HH, HV, their combinations and GLCM textures (3 x 3 window) sampled at the plots |
| `palsar_2015_points.js` | PALSAR-2 yearly mosaic 2015: the same variables sampled at the plots |
| `PALSAR.js` | PALSAR-2 yearly mosaic 2024: exports HH, HV and HV_savg at 30 m |
| `srtm.js` | SRTM elevation and slope sampled at the plots |
| `CATCD_treecover_export.js` | CATCD tree cover of one year (percent), exported for the forest mask |
| `RF_10_2024_CATCD.js` | forest mask of 2024: CATCD tree cover > 10 % |
| `MLR_2005.js`, `MLR_2015.js`, `Cubist_2015.js` | per-pixel mean and SD of the uploaded maps, masked with CATCD tree cover > 10 % |
| `RF_bootstrap_mean_sd_mask_template.js` | the same step for a list of asset ids, with the relative SD |
| `AGB_masked_export.js` | the final maps masked with CATCD tree cover > 10 % of their year, exported at 30 m |

## 2005 Landsat provenance and scale

The study used Collection 1 for 2005 and Collection 2 for 2015/2024. The previous
`landsat_5.js` selected `LANDSAT/LT05/C02/T1_L2`; its C2 scaling and band names did not
match the archived 2005 predictor tables. The corrected script is explicitly a
**reconstruction** based on the confirmed collection, the archived table schema and
the legacy EVI/MSAVI convention documented in manuscript Table S1. No original C1
production script or scene export log was recovered from this repository.

| Item | Reconstructed 2005 convention |
|---|---|
| Historical collection | `LANDSAT/LT05/C01/T1_SR` (Collection 1 Surface Reflectance) |
| Optical bands | `B1`–`B5`, `B7`; retain stored values, with physical reflectance = stored value × 0.0001 |
| Thermal band | `B6`; retain stored values, with brightness temperature in K = stored value × 0.1; this is not C2 surface temperature `ST_B6` |
| QA | `pixel_qa`, cloud bit 5 and cloud-shadow bit 3; the exact original QA rule still needs confirmation |
| Model indices | NDVI, NDMI, EVI and MSAVI; EVI/MSAVI retain the nonstandard stored-integer formulas documented in Table S1 |
| Compositing | May–October, indices per scene followed by median; retained from the previous script, not independently established as the original order |
| Output names | Include `C1_reconstructed`; these outputs are not replacements for the archived production predictors until validated |

The RF 2005 Landsat+PALSAR table has 164 rows, `B2` = 331–1098,
`B4` = 1554–3581.5 and `B6` = 2857.5–2981. These ranges support the stored-value
convention. They do not uniquely establish which scenes, masks, spatial reducers or
compositing order produced each value. Compare against the original scene manifest,
plot geometries, predictor exports and table rows before claiming full reproduction.

The official C1 catalog is deprecated. Running this historical collection ID is not
guaranteed; an accessible, verified archive must preserve the original C1 bands,
stored values, timestamps and QA. C2 bands cannot be made equivalent by renaming
them or applying the C1 scale factor. No GEE scene retrieval or raster exports were
executed as part of this correction.

Keeping the legacy EVI/MSAVI convention preserves the stated predictor definition;
it does not make these standard reflectance-scale indices. Standardizing them would
require re-extraction, refitting and reassessment of the maps. The 2015/2024 scripts
also currently differ in index/compositing order, as listed above; verify the actual
production pipelines before interpreting this reconstruction as a temporal consistency check.

Sources: [C1 Landsat 5 catalog and band/QA definitions](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LT05_C01_T1_SR),
[C1-to-C2 migration guide](https://developers.google.com/earth-engine/landsat_c1_to_c2).
