// PALSAR yearly mosaic 2007: HH, HV, their combinations and GLCM textures (3 x 3 window) sampled at the
// field plots; exports the tables ALOS_Bands and ALOS_Texture.

function HHVV_sum(image) {
                    var sum = image.expression('HH + HV',
                    {
                      'HH' : image.select('HH'),
                      'HV' : image.select('HV'),
                    }).float();
                    return image.addBands(sum.rename('HHVV_sum'));
}
function HHVV_sub(image) {
                    var sub = image.expression('HH - HV',
                    {
                      'HH' : image.select('HH'),
                      'HV' : image.select('HV'),
                    }).float();
                    return image.addBands(sub.rename('HHVV_sub'));
}
function HHVV_ND(image){
                         var nd = image.normalizedDifference(["HH","HV"]).rename('HHVV_ND')
                         return image.addBands(nd.rename('HHVV_ND'))
                       }



var dataset = ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/SAR')
                  .filter(ee.Filter.date('2007-01-01', '2007-12-31'))
                  .filterBounds(table2)
                  .map(HHVV_sum)
                  .map(HHVV_sub)
                  .map(HHVV_ND);
print(dataset);
var sarHh = dataset.mean();
var sarHh = sarHh;
var sarHh1 = sarHh.select('HH','HV')
var image = sarHh1.toInt();
var glcm = image.glcmTexture({size: 1})
print(glcm);
var longlat=ee.Image.pixelLonLat();
var pointsData1 = glcm.addBands(longlat).reduceRegions(table,ee.Reducer.mean(),30)
var pointsData = sarHh.addBands(longlat).reduceRegions(table,ee.Reducer.mean(),30)
Export.table.toDrive({
  collection:pointsData,
  folder: '2007',
  description:'ALOS_Bands',
  fileFormat:'CSV'
})
Export.table.toDrive({
  collection:pointsData1,
  folder: '2007',
  description:'ALOS_Texture',
  fileFormat:'CSV'
})
