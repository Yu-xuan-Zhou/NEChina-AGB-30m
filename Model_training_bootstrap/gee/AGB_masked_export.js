// Export of the final AGB maps with the forest mask.
//
// Every final map (Earth Engine asset) is clipped to the tree-cover mask of the China Annual Tree Cover
// Dataset (CATCD) of its own year (tree cover resampled bilinearly to the 30 m grid, forest = tree cover
// > 10 %) and exported at 30 m in EPSG:4326, one task per map.
// Object from the Code Editor Imports panel: table = Northeast China boundary.

var PROJECT   = 'projects/ee-yuxuanzhoumlr/assets/';   // Cloud project that holds the final maps
var THRESHOLD = 10;                                    // percent tree cover
var MAPS = [
  {name: 'RF_2005',     year: 2005},
  {name: 'RF_2015',     year: 2015},
  {name: 'RF_2024',     year: 2024},
  {name: 'MLR_2005',    year: 2005},
  {name: 'MLR_2015',    year: 2015},
  {name: 'cubist_2005', year: 2005},
  {name: 'cubist_2015', year: 2015}
];

var CATCD = ee.ImageCollection('projects/ee-caiyt33-catcd/assets/China_Annual_Tree_Cover_Dataset');

function forestMask(year) {
  var treeCover = CATCD.filterDate(year + '-01-01', year + '-12-31').first()
                       .select('TreeCover').resample('bilinear');
  return treeCover.gt(THRESHOLD);
}

MAPS.forEach(function(m) {
  var agb = ee.Image(PROJECT + m.name);
  var masked = agb.updateMask(forestMask(m.year)).clip(table);
  Export.image.toDrive({
    image: masked,
    description: m.name + '_masked',
    folder: 'AGB_masked',
    region: table,
    scale: 30,
    crs: 'EPSG:4326',
    maxPixels: 1e13
  });
});

Map.centerObject(table, 4);
Map.addLayer(ee.Image(PROJECT + 'RF_2015').updateMask(forestMask(2015)).clip(table),
             {min: 0, max: 200, palette: ['ffffcc', 'c2e699', '78c679', '31a354', '006837']},
             'RF_2015 masked with CATCD 2015 > 10 %');
