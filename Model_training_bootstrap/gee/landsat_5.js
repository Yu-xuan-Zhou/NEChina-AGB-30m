// Landsat 5 (Collection 2, Level 2), May-October 2005: median composite with the QA_PIXEL cloud (bit 3) and
// cloud-shadow (bit 4) mask; spectral indices of Table S1 with the TM bands (SR_B1 blue, SR_B2 green,
// SR_B3 red, SR_B4 NIR, SR_B5 SWIR1, SR_B7 SWIR2); samples the predictors at the field plots and exports
// the predictor rasters.
// Objects from the Code Editor Imports panel: table = Northeast China boundary, table2 = field plots.

var START = '2005-05-01';
var END   = '2005-11-01';          // exclusive -> May to October

function applyScaleFactors(image) {
  var optical = image.select('SR_B.').multiply(0.0000275).add(-0.2);
  var thermal = image.select('ST_B6').multiply(0.00341802).add(149.0);
  return image.addBands(optical, null, true).addBands(thermal, null, true);
}

// Collection 2 QA_PIXEL: bit 3 = cloud, bit 4 = cloud shadow
function maskClouds(image) {
  var qa = image.select('QA_PIXEL');
  var clear = qa.bitwiseAnd(1 << 3).eq(0).and(qa.bitwiseAnd(1 << 4).eq(0));
  var valid = image.select('SR_B.').mask().reduce(ee.Reducer.min());   // drop edge pixels missing in any band
  return image.updateMask(clear).updateMask(valid);
}

// Landsat 5 TM: SR_B1 blue, SR_B2 green, SR_B3 red, SR_B4 NIR, SR_B5 SWIR1, SR_B7 SWIR2 (Table S1 formulas)
function addIndices(image) {
  var blue  = image.select('SR_B1');
  var green = image.select('SR_B2');
  var red   = image.select('SR_B3');
  var nir   = image.select('SR_B4');
  var swir1 = image.select('SR_B5');
  var ndvi  = nir.subtract(red).divide(nir.add(red)).rename('NDVI');                       // (NIR - Red) / (NIR + Red)
  var evi   = image.expression('2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))',
                               {NIR: nir, RED: red, BLUE: blue}).rename('EVI');
  var savi  = nir.subtract(red).divide(nir.add(red).add(0.5)).multiply(1.5).rename('SAVI');  // L = 0.5
  var msavi = image.expression('0.5 * (2 * NIR + 1 - sqrt((2 * NIR + 1) * (2 * NIR + 1) - 8 * (NIR - RED)))',
                               {NIR: nir, RED: red}).rename('MSAVI');
  var ndwi  = green.subtract(nir).divide(green.add(nir)).rename('NDWI');                   // (Green - NIR) / (Green + NIR)
  var lswi  = nir.subtract(swir1).divide(nir.add(swir1)).rename('LSWI');                   // (NIR - SWIR1) / (NIR + SWIR1)
  var ndmi  = lswi.rename('NDMI');                                                         // same formula in Table S1
  return image.addBands([ndvi, evi, savi, msavi, ndwi, lswi, ndmi]);
}

var composite = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .filterDate(START, END)
    .filterBounds(table)
    .map(applyScaleFactors)
    .map(maskClouds)
    .map(addIndices)
    .median()
    .select(['SR_B1', 'SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B7', 'ST_B6',
             'NDVI', 'EVI', 'SAVI', 'MSAVI', 'NDWI', 'LSWI', 'NDMI']);
print('Landsat 5 composite 2005', composite);

// 1) values at the field plots (one row per plot) -> training table
var pointsdata = composite.reduceRegions({collection: table2, reducer: ee.Reducer.mean(), scale: 30});
Export.table.toDrive({
  collection: pointsdata,
  folder: '2005',
  description: 'LC_05_0809_11',
  fileFormat: 'CSV'
});

// 2) predictor rasters for mapping, one export per layer (the 2005 models use B2, B3, B4, B6, B7, EVI, MSAVI,
//    NDMI and NDVI; Landsat-only and Landsat+PALSAR sets are subsets of this list)
var exportLayer = function(name) {
  Export.image.toDrive({
    image: composite.select(name).clip(table),
    description: name + '_2005',
    folder: '2005_landsat',
    region: table,
    scale: 30,
    crs: 'EPSG:4326',
    maxPixels: 1e13
  });
};
['SR_B2', 'SR_B3', 'SR_B4', 'ST_B6', 'SR_B7', 'EVI', 'MSAVI', 'NDMI', 'NDVI'].forEach(exportLayer);

Map.centerObject(table, 5);
Map.addLayer(composite, {bands: ['SR_B3', 'SR_B2', 'SR_B1'], min: 0, max: 0.3}, 'Landsat 5 2005 (true colour)');
