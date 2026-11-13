# Figure 4 — current rasters, IQR-filtered violin display


## Statistical definitions

- Panel a: original latitude-profile data and plotting function retained.
- Panel b: start with a uniform random sample without replacement of one
  million valid positive pixels per model-year map. Each of the six model-year
  groups is filtered inclusively to Q1−1.5×IQR through Q3+1.5×IQR, using
  quartiles of its original sample. Filtering is for panel b visualization only.
- All plotting quartiles and medians are recomputed after filtering. The axis
  is linear; complete retained model ranges are shown. Gaussian KDE uses all
  retained values with robust Silverman bandwidth.
- Field data are the complete final 164/957 records from
  `../Figure1_study_area/data/samples/final_model_samples.csv`, without IQR filtering.
- Panel c: exact full-raster pixel-count proportions from valid, finite AGB>0
  within each existing mask, with no IQR filter and no area weighting. Classes
  are (0,20], (20,40], (40,60], (60,80], (80,100], (100,130], >130.
- Raw one-million-pixel samples, source TIFFs, masks and panel c statistics
  are not modified by the panel b display filter.

## Reproduction

`python -X utf8 Figure4_combine.py`



