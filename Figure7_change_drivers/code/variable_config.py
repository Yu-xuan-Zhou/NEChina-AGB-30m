#!/usr/bin/env python3
"""
variable_config.py -- feature sets of the Figure 7 models and of the SHAP analysis.

  * Figure 7 uses seven factor groups: forest structure / starting state, five climate
    variables and terrain.
  * SHAP = the density-driver set of Figure 7 + the four model-internal variables
    (dNDVI, dNDWI, dHH, dHV), which are inputs of the AGB maps.
  * LST  = dLST, the change in growing-season land-surface temperature (MODIS).

`task2h_hybrid_structure_models.py` (Figure 7) and `shap/task7_shap_augmented.py` import from
here and assert their feature lists against the constants below.
"""
from __future__ import annotations

# --- canonical tokens -------------------------------------------------------
LST_VAR = "dLST"                                  # change in LST (MODIS thermal)
STRUCTURE_DENSITY = ["initAGB", "treecover2000"]
STRUCTURE_AREA = ["fracstart", "dist_to_forest", "treecover2000"]
CLIMATE = ["period_pr", "period_soil", "period_def", "period_vpd", LST_VAR]
TERRAIN = ["Elevation", "Slope"]

# four Landsat/PALSAR deltas that were inputs to the AGB maps -> circular
RS_INTERNAL = ["dNDVI", "dNDWI", "dHH", "dHV"]

# --- flat feature lists (ORDER MATCHES the grouped factor order) ------------
DENSITY_FEATURES = STRUCTURE_DENSITY + CLIMATE + TERRAIN
AREA_FEATURES = STRUCTURE_AREA + CLIMATE + TERRAIN

# SHAP is fit on the density target (RF_d{period}); its exogenous set therefore
# equals the Figure 7 density-driver set, and the full SHAP feature set adds the
# four model-internal deltas.
SHAP_EXO = list(DENSITY_FEATURES)
SHAP_FEATS = SHAP_EXO + RS_INTERNAL

# --- group membership (for colouring / exogenous-share accounting) ----------
GROUP = {
    "initAGB": "Forest structure / starting state",
    "treecover2000": "Forest structure / starting state",
    "fracstart": "Forest structure / starting state",
    "dist_to_forest": "Forest structure / starting state",
    "period_pr": "Climate & water",
    "period_soil": "Climate & water",
    "period_def": "Climate & water",
    "period_vpd": "Climate & water",
    "dLST": "Climate & water",
    "Elevation": "Topography & setting",
    "Slope": "Topography & setting",
    "dNDVI": "Observed RS (model-internal)",
    "dNDWI": "Observed RS (model-internal)",
    "dHH": "Observed RS (model-internal)",
    "dHV": "Observed RS (model-internal)",
}

# --- pretty labels ----------------------------------------------------------
PRETTY = {
    "initAGB": "Initial AGB",
    "treecover2000": "Tree cover 2000",
    "fracstart": "Initial forest fraction",
    "dist_to_forest": "Distance to forest",
    "period_pr": "Precipitation",
    "period_soil": "Soil moisture",
    "period_def": "Water deficit",
    "period_vpd": "VPD",
    "dLST": "ΔLST (surface temp.)",
    "Elevation": "Elevation",
    "Slope": "Slope",
    "dNDVI": "ΔNDVI",
    "dNDWI": "ΔNDWI",
    "dHH": "ΔHH",
    "dHV": "ΔHV",
}


def dlst_raster(DF, period):
    """Path to the ΔLST raster for a period, e.g. DF/'LST_d05_15_res1km.tif'."""
    return DF / f"LST_d{period}_res1km.tif"


def assert_matches(features, expected, label):
    """Loud guard: fail fast if a model's feature list drifts from the agreement."""
    if list(features) != list(expected):
        raise AssertionError(
            f"[variable_config] {label} feature list disagrees with the canonical set.\n"
            f"  expected: {list(expected)}\n  got:      {list(features)}"
        )
