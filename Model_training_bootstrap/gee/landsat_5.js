// Landsat 5 Collection 1 Surface Reflectance, May-October 2005.
// RECONSTRUCTION, not the recovered historical production script: the previous C2 implementation
// did not match the archived 2005 predictor tables. This version restores the C1 product, band
// names, QA definitions and stored-value convention supported by those tables and Table S1.
// Scene selection, the exact historical QA rule, and index/compositing order still require
// verification against the original GEE script/export records. Do not claim pixelwise reproduction.
// Historical catalog: https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LT05_C01_T1_SR
// C1 is deprecated. A rerun requires an accessible archive of the original C1 scenes and QA;
// substituting C2 (or renaming its bands) does not reproduce the original predictors.
// Objects from the Code Editor Imports panel: table = Northeast China boundary, table2 = field plots.

var START = '2005-05-01';
var END   = '2005-11-01';          // exclusive -> May to October
var COLLECTION_ID = 'LANDSAT/LT05/C01/T1_SR';  // historical ID; use a verified C1 archive if unavailable
var OPTICAL_BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7'];
var PREDICTOR_BANDS = ['B2', 'B3', 'B4', 'B6', 'B7', 'EVI', 'MSAVI', 'NDMI', 'NDVI'];

// Keep C1 stored values for compatibility with the archived training tables:
// optical reflectance = stored value * 0.0001; B6 brightness temperature (K) = stored value * 0.1.
// No scaling is applied to model inputs here. B6 is brightness temperature, not C2 ST_B6.

// Collection 1 pixel_qa: bit 5 = cloud, bit 3 = cloud shadow (bit 4 is snow).
// This is a reconstruction of the stated cloud/shadow exclusion, not a verified original QA rule.
function maskClouds(image) {
  var qa = image.select('pixel_qa');
  var clear = qa.bitwiseAnd(1 << 5).eq(0).and(qa.bitwiseAnd(1 << 3).eq(0));
  var valid = image.select(OPTICAL_BANDS).mask().reduce(ee.Reducer.min());
  return image.updateMask(clear).updateMask(valid);
}

// Only the four indices used by the archived 2005 model tables are reconstructed.
// EVI/MSAVI deliberately retain the legacy stored-integer formulas documented in Table S1.
// They are NOT conventional reflectance-scale indices. Silently scaling these inputs would
// change predictor definitions; adopting standard indices requires re-extraction and refitting.
function addIndices(image) {
  var blue  = image.select('B1');
  var red   = image.select('B3');
  var nir   = image.select('B4');
  var swir1 = image.select('B5');
  var ndvi  = nir.subtract(red).divide(nir.add(red)).rename('NDVI');                       // (NIR - Red) / (NIR + Red)
  var evi   = image.expression('2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
                               {NIR: nir, RED: red, BLUE: blue}).rename('EVI');
  var msavi = image.expression('0.5 * (2 * NIR + 1 - sqrt((2 * NIR + 1) * (2 * NIR + 1) - 8 * (NIR - RED)))',
                               {NIR: nir, RED: red}).rename('MSAVI');
  var ndmi  = nir.subtract(swir1).divide(nir.add(swir1)).rename('NDMI');                   // (NIR - SWIR1) / (NIR + SWIR1)
  return image.addBands([ndvi, evi, msavi, ndmi]);
}

// Retain the previous script's per-scene-index -> median order as a reconstruction assumption.
// The archived point tables alone cannot establish the historical order.
var composite = ee.ImageCollection(COLLECTION_ID)
    .filterDate(START, END)
    .filterBounds(table)
    .map(maskClouds)
    .map(addIndices)
    .median()
    .select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'NDVI', 'EVI', 'MSAVI', 'NDMI']);
print('Reconstructed Landsat 5 C1 composite 2005 (stored values)', composite);

// 1) values at the field plots (one row per plot) -> training table
var pointsdata = composite.reduceRegions({collection: table2, reducer: ee.Reducer.mean(), scale: 30});
Export.table.toDrive({
  collection: pointsdata,
  folder: '2005_C1_reconstructed',
  description: 'Landsat5_C1_2005_reconstructed_predictors',
  fileFormat: 'CSV'
});

// 2) predictor rasters for mapping, one export per layer (the 2005 models use B2, B3, B4, B6, B7, EVI, MSAVI,
//    NDMI and NDVI; Landsat-only and Landsat+PALSAR sets are subsets of this list)
var exportLayer = function(name) {
  Export.image.toDrive({
    image: composite.select(name).clip(table),
    description: name + '_2005_C1_reconstructed',
    folder: '2005_landsat_C1_reconstructed',
    region: table,
    scale: 30,
    crs: 'EPSG:4326',
    maxPixels: 1e13
  });
};
PREDICTOR_BANDS.forEach(exportLayer);

Map.centerObject(table, 5);
Map.addLayer(composite, {bands: ['B3', 'B2', 'B1'], min: 0, max: 3000}, 'Landsat 5 C1 2005 (stored values)');
