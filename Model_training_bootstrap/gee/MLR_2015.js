// Per-pixel mean and SD of the MLR 2015 maps uploaded as Earth Engine assets (Imports panel: image,
// image2, ...), masked with the forest mask and exported as MLR_2015_mean_mask / MLR_2015_sd_mask
// (30 m, EPSG:4326). Forest mask: China Annual Tree Cover Dataset (CATCD) of the same year, bilinearly
// resampled to the 30 m grid, tree cover > 10 %.

var YEAR = 2015;
var THRESHOLD = 10;   // percent tree cover

var CATCD = ee.ImageCollection('projects/ee-caiyt33-catcd/assets/China_Annual_Tree_Cover_Dataset');
var treeCanopyCover = CATCD.filterDate(YEAR + '-01-01', YEAR + '-12-31').first()
                           .select('TreeCover').resample('bilinear').clip(table);

var maps = ee.ImageCollection([
  image,image2,image3,image4,image5,image6,image7,image8,image9,image10,
  image11,image12,image13,image14,image15,image16,image17,image18,image19,
  image21,image22,image23,image24,image25,image26,image27,image28,
  ]);

var sd = maps.reduce(ee.Reducer.stdDev());
var mean = maps.reduce(ee.Reducer.mean());
print('number of bootstrap maps', maps.size());
print(sd);

var treeCanopyCoverVis = {
  min: 0.0,
  max: 10.0,
  palette: ['ffffff', 'afce56', '5f9c00', '0e6a00', '003800'],
};
var mask = function(image, my_type){
  var mask = treeCanopyCover.gt(my_type);
  var masked_image = image.updateMask(mask);
  return masked_image;
};
var sd_mask = mask(sd, THRESHOLD);
var mean_mask = mask(mean, THRESHOLD);
Map.centerObject(table, 3);
Map.addLayer(sd_mask, treeCanopyCoverVis, 'SD of the bootstrap maps (forest)');
Export.image.toDrive({
        image: sd_mask,
        description: 'MLR_2015_sd_mask',
        folder : 'MLR_2015_sd_mask',
        region: table,
        scale: 30,
        crs: "EPSG:4326",
        maxPixels: 1e13
      });

Export.image.toDrive({
        image: mean_mask,
        description: 'MLR_2015_mean_mask',
        folder : 'MLR_2015_mean_mask',
        region: table,
        scale: 30,
        crs: "EPSG:4326",
        maxPixels: 1e13
      });
