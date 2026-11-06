// CATCD tree cover of one year as a GeoTIFF.
//
// Exports the tree-cover band of the China Annual Tree Cover Dataset (CATCD) of YEAR (percent), bilinearly
// resampled and clipped to the study region, to Google Drive. 05_aggregate_bootstrap_maps.R
// (--mask <this file> --threshold 10) applies it as the forest mask (tree cover > 10 %).
// Object from the Code Editor Imports panel: table = Northeast China boundary.
// CATCD: Yaotong Cai, Sun Yat-sen University; asset projects/ee-caiyt33-catcd/assets/China_Annual_Tree_Cover_Dataset.

var YEAR = 2015;                    // 2005, 2015 or 2024

var CATCD = ee.ImageCollection('projects/ee-caiyt33-catcd/assets/China_Annual_Tree_Cover_Dataset');
var treeCover = CATCD.filterDate(YEAR + '-01-01', YEAR + '-12-31').first()
                     .select('TreeCover').resample('bilinear').clip(table);
print('CATCD image used', treeCover);

Map.centerObject(table, 4);
Map.addLayer(treeCover, {min: 0, max: 100, palette: ['ffffff', 'afce56', '5f9c00', '0e6a00', '003800']},
             'CATCD tree cover ' + YEAR + ' (%)');
Map.addLayer(treeCover.gt(10).selfMask(), {palette: ['000000']}, 'tree cover > 10 %', false);

Export.image.toDrive({
  image: treeCover,
  description: 'CATCD_treecover_' + YEAR,
  folder: 'CATCD_treecover_' + YEAR,
  region: table,
  scale: 30,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});
