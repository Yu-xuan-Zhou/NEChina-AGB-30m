// PALSAR-2 yearly mosaic 2015: HH, HV, their combinations and GLCM textures (3 x 3 window) sampled at the
// field plots (table2).

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
                  .filter(ee.Filter.date('2015-01-01', '2016-01-01'))
                  .filterBounds(table)
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
var pointsData1 = glcm.reduceRegions(table2,ee.Reducer.mean(),30)
// for(var i = 1;i<=35;i++){
// var n = glcm.select(i);
// print(n);
// var pointsData1 = n.reduceRegions(buffer,ee.Reducer.mean(),30);
// var
// Map.centerObject(table, 4);

// }
var pointsData = sarHh.reduceRegions(table2,ee.Reducer.mean(),30)
Export.table.toDrive({
  collection:pointsData,
  folder: '2015',
  description:'ALOS_Bands_1204',
  fileFormat:'CSV'
})
Export.table.toDrive({
  collection:pointsData1,
  folder: '2015',
  description:'ALOS_Texture_1204',
  fileFormat:'CSV'
})
