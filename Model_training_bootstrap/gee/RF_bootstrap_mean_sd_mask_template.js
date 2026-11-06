// Per-pixel mean, SD and relative SD of uploaded maps with the CATCD forest mask.
//
// The maps are given as a list of asset ids: set MODEL, YEAR and ASSETS before running. Forest mask: China
// Annual Tree Cover Dataset (CATCD) of the same year, bilinearly resampled to the 30 m grid, tree cover > 10 %.
// Object from the Code Editor Imports panel: table = Northeast China boundary.

var MODEL     = 'RF';
var YEAR      = 2005;
var THRESHOLD = 10;                 // percent tree cover
var ASSETS = [                      // one uploaded bootstrap map per entry, e.g. maps <MODEL>_<YEAR>_<k>.tif
  // 'projects/ee-zhouheiheiheihei/assets/RF_2005_1',
  // 'projects/ee-zhouheiheiheihei/assets/RF_2005_2',
  // ...
];

var CATCD = ee.ImageCollection('projects/ee-caiyt33-catcd/assets/China_Annual_Tree_Cover_Dataset');
var treeCanopyCover = CATCD.filterDate(YEAR + '-01-01', YEAR + '-12-31').first()
                           .select('TreeCover').resample('bilinear').clip(table);

var maps = ee.ImageCollection(ASSETS.map(function(id) { return ee.Image(id); }));
print('number of bootstrap maps', maps.size());

var sd   = maps.reduce(ee.Reducer.stdDev());
var mean = maps.reduce(ee.Reducer.mean());
var relativeSd = sd.divide(mean).multiply(100);      // percent, as in the *_rela_sd_mask products

var forest = treeCanopyCover.gt(THRESHOLD);
var sd_mask   = sd.updateMask(forest);
var mean_mask = mean.updateMask(forest);
var rela_mask = relativeSd.updateMask(forest);

var prefix = MODEL + '_' + YEAR;
var exportTask = function(image, suffix) {
  Export.image.toDrive({
    image: image,
    description: prefix + '_' + suffix,
    folder: prefix + '_' + suffix,
    region: table,
    scale: 30,
    crs: 'EPSG:4326',
    maxPixels: 1e13
  });
};
exportTask(sd_mask,   'sd_mask');
exportTask(mean_mask, 'mean_mask');
exportTask(rela_mask, 'rela_sd_mask');

Map.centerObject(table, 3);
Map.addLayer(mean_mask, {min: 0, max: 200, palette: ['ffffcc', 'c2e699', '78c679', '31a354', '006837']},
             prefix + ' bootstrap mean (forest)');
