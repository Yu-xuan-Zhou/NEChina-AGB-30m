// Landsat 9 (Collection 2, Level 2), May-October 2024: median composite with cloud and cloud-shadow mask;
// exports NDVI, LSWI, NDWI, SR_B3 and SR_B4 at 30 m.
function applyScaleFactors(image) {
  var opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2);
  var thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0);
  return image.addBands(opticalBands, null, true)
              .addBands(thermalBands, null, true);
}

function maskL9Clouds(image) {
  var qa = image.select('QA_PIXEL');

  var cloudMask = qa.bitwiseAnd(1 << 3).eq(0) //
                   .and(qa.bitwiseAnd(1 << 4).eq(0));
  return image.updateMask(cloudMask);
}
var dataset = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .filterDate('2024-05-01', '2024-11-01')
    .map(applyScaleFactors)
    .map(maskL9Clouds)  // apply the cloud mask
    .filterBounds(table)
    .median()
    .clip(table)

var ndvi = dataset.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI');
var lswi = dataset.normalizedDifference(['SR_B5', 'SR_B6']).rename('LSWI');
var ndwi = dataset.normalizedDifference(['SR_B3', 'SR_B5']).rename('NDWI');


var result = dataset.addBands(ndvi)
                    .addBands(lswi)
                    .addBands(ndwi)
var visualization = {
  bands: ['SR_B4', 'SR_B3', 'SR_B2'],
  min: 0.0,
  max: 0.3,
};

Map.centerObject(table, 8);

Map.addLayer(dataset, visualization, 'True Color (432)');
Export.image.toDrive({
  image: result.select('NDVI'),
  description: 'NDVI',
  folder: 'GEE_exports', // Drive folder of the export (change as needed)
  region: table.geometry(),  // table = the study-area geometry (imported asset)
  scale: 30,  // export resolution (Landsat: 30 m)
  crs: 'EPSG:4326',
  maxPixels: 1e13  // allow a large export region
});
Export.image.toDrive({
  image: result.select('LSWI'),
  description: 'LSWI',
  folder: 'GEE_exports', // Drive folder of the export (change as needed)
  region: table.geometry(),  // table = the study-area geometry (imported asset)
  scale: 30,  // export resolution (Landsat: 30 m)
  crs: 'EPSG:4326',
  maxPixels: 1e13  // allow a large export region
});
Export.image.toDrive({
  image: result.select('NDWI'),
  description: 'NDWI',
  folder: 'GEE_exports', // Drive folder of the export (change as needed)
  region: table.geometry(),  // table = the study-area geometry (imported asset)
  scale: 30,  // export resolution (Landsat: 30 m)
  crs: 'EPSG:4326',
  maxPixels: 1e13  // allow a large export region
});
Export.image.toDrive({
  image: result.select('SR_B3'),
  description: 'SR_B3',
  folder: 'GEE_exports', // Drive folder of the export (change as needed)
  region: table.geometry(),  // table = the study-area geometry (imported asset)
  scale: 30,  // export resolution (Landsat: 30 m)
  crs: 'EPSG:4326',
  maxPixels: 1e13  // allow a large export region
});
Export.image.toDrive({
  image: result.select('SR_B4'),
  description: 'SR_B4',
  folder: 'GEE_exports', // Drive folder of the export (change as needed)
  region: table.geometry(),  // table = the study-area geometry (imported asset)
  scale: 30,  // export resolution (Landsat: 30 m)
  crs: 'EPSG:4326',
  maxPixels: 1e13  // allow a large export region
});
