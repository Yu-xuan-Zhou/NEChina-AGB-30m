# Table S1 - Predictor variables

`TableS1_variable_descriptions.csv` lists the category, index, description and reference of
the 18 predictors (PALSAR backscatter and texture, Landsat spectral indices and bands, and
terrain). Predictor names and the selection of variables in each model are unchanged.

## Sensor-specific Landsat bands

Band numbers follow the native sensor definitions. Identical band numbers do not necessarily
denote equivalent spectral regions. The table distinguishes Landsat 5 TM (2005) and Landsat 8
OLI (2015). Landsat 9 OLI-2 (2024) uses the same band designations as OLI for the bands below.

| Variable | Landsat 5 TM (2005) | Landsat 8 OLI (2015) / Landsat 9 OLI-2 (2024) |
|---|---|---|
| B2 | Green, 0.52-0.60 micrometres | Blue, 0.45-0.51 micrometres |
| B3 | Red, 0.63-0.69 micrometres | Green, 0.53-0.59 micrometres |
| B4 | Near infrared, 0.76-0.90 micrometres | Red, 0.64-0.67 micrometres |
| B6 | Thermal infrared, 10.40-12.50 micrometres | SWIR1, 1.57-1.65 micrometres |
| B7 | SWIR2, 2.08-2.35 micrometres | SWIR2, 2.11-2.29 micrometres |

TM B6 is a thermal variable, not a reflectance band. Its native spatial resolution is 120 m;
the delivered band is resampled to 30 m. This band-description table does not imply that
every listed band was selected in every year or model. The packaged 2005 model tables use
unprefixed TM band names. In the 2015 tables, RF uses `SR_B3` and `SR_B4`, while Cubist
uses `SR_B5` (near infrared, 0.85-0.88 micrometres). The existing 18-row table is retained;
it is not the complete union of every selected predictor in all model combinations.

Sources (accessed 2026-11-10):

- [USGS Landsat 5](https://www.usgs.gov/Landsat-missions/landsat-5)
- [USGS band designations](https://www.usgs.gov/faqs/what-are-band-designations-landsat-satellites)


