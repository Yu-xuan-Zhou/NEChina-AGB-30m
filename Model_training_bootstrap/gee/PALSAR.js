// PALSAR-2 yearly mosaic 2024 (SAR_EPOCH): HH, HV and GLCM textures (3 x 3 window); exports the HH, HV and
// HV_savg rasters at 30 m.

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



var dataset = ee.ImageCollection('JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH')
                  .filter(ee.Filter.date('2024-01-01', '2024-12-31'))
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
var pointsData1 = glcm.reduceRegions(table,ee.Reducer.mean(),30)
// for(var i = 1;i<=35;i++){
// var n = glcm.select(i);
// print(n);
// var pointsData1 = n.reduceRegions(buffer,ee.Reducer.mean(),30);
// var
// Map.centerObject(table, 4);

// }
var pointsData = sarHh.reduceRegions(table,ee.Reducer.mean(),30)
Export.image.toDrive({

        image: glcm.select('HV_savg').clip(table),

        description: 'HV_savg',

        folder : 'HV_savg',

        region: table,

        scale: 30,

        crs: "EPSG:4326",

        maxPixels: 1e13

      });
Export.image.toDrive({

        image: sarHh1.select('HH').clip(table),

        description: 'HH',

        folder : 'HH',

        region: table,

        scale: 30,

        crs: "EPSG:4326",

        maxPixels: 1e13

      });
Export.image.toDrive({

        image: sarHh1.select('HV').clip(table),

        description: 'HV',

        folder : 'HV',

        region: table,

        scale: 30,

        crs: "EPSG:4326",

        maxPixels: 1e13

      });
