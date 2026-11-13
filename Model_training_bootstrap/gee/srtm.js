// SRTM (USGS/SRTMGL1_003): slope (degrees) and elevation (m) sampled at the field plots (table).

var elevation = ee.Image('USGS/SRTMGL1_003').select('elevation');

var slope = ee.Terrain.slope(elevation);
var DEM = slope.addBands(elevation);
var pointsData = DEM.reduceRegions(table, ee.Reducer.mean(), 30);
Export.table.toDrive({
  collection: pointsData,
  folder: '2010',
  description: 'DEM',
  fileFormat: 'CSV'
});
