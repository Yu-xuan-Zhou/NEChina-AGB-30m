// ============================================================
// Northeast China -- unmasked period climate and burned summaries
//
// Purpose:
//   Fills the main temporal gap left by single-year baseline stacks:
//   period-level climate-water variables and burned disturbance.
//
// Default periods are "after-baseline" years:
//   05_15: 2006-2015
//   15_24: 2016-2024
//
// This avoids reusing the baseline year as both an initial condition and
// an in-period forcing. Edit PERIODS if you prefer inclusive 2005-2015
// and 2015-2024 summaries.
//
// GS_END_EXCLUSIVE_M is kept at 11 to match existing stack exports
// (May-Oct). If you want May-Nov, rerun all related exports with 12.
// ============================================================

// ---------- config ----------
var region = table;
var EXPORT_FOLDER = 'dongbei_period_climate_burned_500m_unmasked';
var GS_START_M = 5;
var GS_END_EXCLUSIVE_M = 11;

var PERIODS = [
  {label: '05_15_driver_period', startYear: 2006, endYear: 2015},
  {label: '15_24_driver_period', startYear: 2016, endYear: 2024}
];

// ---------- collections ----------
var terra = ee.ImageCollection('IDAHO_EPSCOR/TERRACLIMATE');
var mcd64 = ee.ImageCollection('MODIS/061/MCD64A1');
var mod11 = ee.ImageCollection('MODIS/061/MOD11A2');

function annualClimateBurn(year) {
  year = ee.Number(year);
  var start = ee.Date.fromYMD(year, 1, 1);
  var end = start.advance(1, 'year');
  var gsStart = ee.Date.fromYMD(year, GS_START_M, 1);
  var gsEnd = ee.Date.fromYMD(year, GS_END_EXCLUSIVE_M, 1);

  var tc = terra.filterDate(gsStart, gsEnd);
  var prSum = tc.select('pr').sum()
      .resample('bilinear').rename('pr_sum').toFloat();
  var pdsiMean = tc.select('pdsi').mean().multiply(0.01)
      .resample('bilinear').rename('pdsi_mean').toFloat();
  var defSum = tc.select('def').sum().multiply(0.1)
      .resample('bilinear').rename('def_sum').toFloat();
  var soilMean = tc.select('soil').mean().multiply(0.1)
      .resample('bilinear').rename('soil_mean').toFloat();
  var vpdMean = tc.select('vpd').mean().multiply(0.01)
      .resample('bilinear').rename('vpd_mean').toFloat();

  var lstMean = mod11.filterDate(gsStart, gsEnd).select('LST_Day_1km').mean()
      .multiply(0.02).subtract(273.15)
      .resample('bilinear').rename('LST_mean_C').toFloat();

  var burnedAnyYear = mcd64.filterDate(start, end).select('BurnDate').max()
      .gte(1).unmask(0).rename('Burned_any_year').toFloat();

  return prSum
      .addBands(pdsiMean)
      .addBands(defSum)
      .addBands(soilMean)
      .addBands(vpdMean)
      .addBands(lstMean)
      .addBands(burnedAnyYear)
      .set({year: year, 'system:time_start': start.millis()})
      .clip(region);
}

function periodImage(period) {
  var years = ee.List.sequence(period.startYear, period.endYear);
  var annuals = ee.ImageCollection.fromImages(years.map(annualClimateBurn));

  var climateMean = annuals.select([
      'pr_sum', 'pdsi_mean', 'def_sum', 'soil_mean', 'vpd_mean', 'LST_mean_C'
    ]).mean().rename([
      'pr_sum_period_mean',
      'pdsi_period_mean',
      'def_sum_period_mean',
      'soil_period_mean',
      'vpd_period_mean',
      'LST_period_mean_C'
    ]);

  var burnedFreq = annuals.select('Burned_any_year').mean()
      .rename('Burned_frequency');
  var burnedAny = annuals.select('Burned_any_year').max()
      .rename('Burned_any');
  var burnedCount = annuals.select('Burned_any_year').sum()
      .rename('Burned_count');

  return climateMean
      .addBands(burnedFreq)
      .addBands(burnedAny)
      .addBands(burnedCount)
      .toFloat()
      .clip(region)
      .set({
        label: period.label,
        startYear: period.startYear,
        endYear: period.endYear,
        yearCount: period.endYear - period.startYear + 1
      });
}

// ---------- sanity ----------
var preview = periodImage(PERIODS[0]);
print('Period summary bands:', preview.bandNames());
Map.centerObject(region, 5);
Map.addLayer(preview.select('pdsi_period_mean'),
  {min:-4, max:4, palette:['red','white','blue']}, 'period PDSI mean');
Map.addLayer(preview.select('Burned_frequency'),
  {min:0, max:1, palette:['white','orange','red']}, 'burned frequency');

// ---------- exports ----------
PERIODS.forEach(function(period) {
  Export.image.toDrive({
    image: periodImage(period),
    description: 'dongbei_period_climate_burned_' + period.label,
    folder: EXPORT_FOLDER,
    fileNamePrefix: 'dongbei_period_climate_burned_' + period.label,
    region: region,
    scale: 500,
    crs: 'EPSG:4326',
    maxPixels: 1e13,
    fileFormat: 'GeoTIFF',
    formatOptions: { cloudOptimized: true }
  });
});
