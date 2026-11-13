// Landsat 8 (Collection 2, Level 2), May-October 2015: median composite with the QA_PIXEL cloud (bit 3) and
// cloud-shadow (bit 4) mask; spectral indices with the OLI bands (SR_B2 blue, SR_B3 green, SR_B4 red,
// SR_B5 NIR, SR_B6 SWIR1, SR_B7 SWIR2); samples the predictors at the field plots.
// Objects from the Code Editor Imports panel: table = Northeast China boundary, table2 = field plots.

function maskL8sr(image) {
  var cloudBitMask       = (1 << 3);   // Collection 2 QA_PIXEL bit 3: cloud
  var cloudShadowBitMask = (1 << 4);   // Collection 2 QA_PIXEL bit 4: cloud shadow
  var qa = image.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(cloudBitMask).eq(0)
               .and(qa.bitwiseAnd(cloudShadowBitMask).eq(0));
  return image.updateMask(mask);
}

function NDVI(image){
  var ndvi = image.normalizedDifference(['SR_B5','SR_B4']).rename('NDVI');          // (NIR - Red) / (NIR + Red)
  return image.addBands(ndvi);
}
function NDWI(image) {
  return image.addBands(image.normalizedDifference(['SR_B3', 'SR_B5']).rename('NDWI'));   // (Green - NIR) / (Green + NIR)
}
function EVI(image){
  var evi = image.expression('2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
    'NIR' : image.select('SR_B5'),
    'RED' : image.select('SR_B4'),
    'BLUE': image.select('SR_B2')
  }).float();
  return image.addBands(evi.rename('EVI'));
}
function MSAVI(image){
  var msavi = image.expression('0.5*(2*NIR+1-sqrt((2*NIR+1)*(2*NIR+1)-8*(NIR-RED)))', {
    'NIR' : image.select('SR_B5'),
    'RED' : image.select('SR_B4'),
  }).float();
  return image.addBands(msavi.rename('MSAVI'));
}
function LSWI(image){
  return image.addBands(image.normalizedDifference(['SR_B5', 'SR_B6']).rename('LSWI'));   // (NIR - SWIR1) / (NIR + SWIR1)
}
function DVI(image){
  return image.addBands(image.select('SR_B5').subtract(image.select('SR_B4')).rename('DVI'));
}
function SAVI(image){
  return image.addBands(image.select('SR_B5').subtract(image.select('SR_B4'))
    .divide(image.select('SR_B5').add(image.select('SR_B4')).add(0.5)).multiply(1.5).rename('SAVI'));   // L = 0.5
}
function SR(image){
  return image.addBands(image.select('SR_B5').divide(image.select('SR_B4')).rename('SR'));
}

var landsat = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                 .filterDate("2015-05-01", "2015-11-01")        // end date exclusive: May to October
                 .filterBounds(table)
                 .map(maskL8sr)
                 .select('SR_B1','SR_B2','SR_B3','SR_B4','SR_B5','SR_B6','SR_B7')
                 .map(function(image){
                   var image = image.multiply(2.75e-05).add(-0.2);   // Collection 2 scale factors
                   return image;
                 })
                 .map(NDVI)
                 .map(EVI)
                 .map(LSWI)
                 .map(NDWI)
                 .map(DVI)
                 .map(SAVI)
                 .map(MSAVI)
                 .median();

var longlat = ee.Image.pixelLonLat();
var pointsData = landsat.addBands(longlat).reduceRegions(table2, ee.Reducer.mean(), 30);   // mean per plot
Export.table.toDrive({
  collection: pointsData,
  folder: '2015',
  description: 'edit_20211021_05',
  fileFormat: 'CSV'
});
Map.centerObject(table, 5);
