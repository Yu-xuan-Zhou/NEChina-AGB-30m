"""
Deeper area-analysis covariates on the 1 km gating grid.

  afforest_frac_<year>.tif   30 m forest fraction (AGB>0) per 1 km cell, year in {2005,2015,2024}
  afforest_delta_05_15.tif   frac2015 - frac2005  (continuous afforestation INTENSITY target)
  afforest_delta_15_24.tif   frac2024 - frac2015
  dist_to_forest_2005.tif    distance (km) from each cell to nearest 2005 forest
  dist_to_forest_2015.tif    same for 2015 (period-start proximity for 15-24)

The 30 m RF mean masks share the Hansen grid (72632x55084, EPSG:4326); forest
fraction is accumulated by the same bin-count aggregation as task2a.
"""
from pathlib import Path
import numpy as np, rasterio
from rasterio.windows import Window
from scipy.ndimage import distance_transform_edt

RES = Path(r"I:\AGB_models\Res")
OUT = Path(r"E:\DATA\Python\AGB_NE\R3_revision\covariates_1km")
TEMPLATE = RES / "RF_2005_res1km.tif"
RF30 = {2005: r"I:\AGB_models\boostrapping\RF_2005_mean_mask.tif",
        2015: r"I:\AGB_models\boostrapping\RF_2015_mean_mask.tif",
        2024: r"I:\AGB_models\RF_2024.tif"}
STRIP = 1024
KM_PER_CELL = 0.927  # ~0.00833 deg at ~47 N


def template():
    with rasterio.open(TEMPLATE) as t:
        return t.transform, t.crs, t.width, t.height


def write1(name, arr, transform, crs):
    with rasterio.open(OUT / f"{name}.tif", "w", driver="GTiff", height=arr.shape[0],
                       width=arr.shape[1], count=1, dtype="float32", crs=crs,
                       transform=transform, nodata=-9999.0, compress="lzw") as d:
        d.write(arr.astype("float32"), 1)
    print("  wrote", name)


def forest_fraction(rf_path, transform, W1, H1):
    """Per 1 km cell: count(AGB>0) / count(in-domain finite 30 m pixels)."""
    ulx, uly, res1 = transform.c, transform.f, transform.a
    forest = np.zeros(H1 * W1, np.float64)
    total = np.zeros(H1 * W1, np.float64)
    ML = H1 * W1
    with rasterio.open(rf_path) as src:
        t30, res30, W30, H30 = src.transform, src.transform.a, src.width, src.height
        lon = t30.c + (np.arange(W30) + 0.5) * res30
        col1 = np.floor((lon - ulx) / res1).astype(np.int64)
        col_ok = (col1 >= 0) & (col1 < W1)
        for rs in range(0, H30, STRIP):
            R = min(STRIP, H30 - rs)
            lat = uly - (np.arange(rs, rs + R) + 0.5) * res30
            row1 = np.floor((uly - lat) / res1).astype(np.int64)
            row_ok = (row1 >= 0) & (row1 < H1)
            a = src.read(1, window=Window(0, rs, W30, R)).astype("float32")
            # denominator = ALL 30 m pixels geometrically in the cell (~961); RF non-forest
            # is stored as nodata, so a>0 isolates forest. fraction = forest / geometric.
            idx = row1[:, None] * W1 + col1[None, :]
            ok = row_ok[:, None] & col_ok[None, :]
            total += np.bincount(idx[ok], minlength=ML)
            forest += np.bincount(idx[ok & (a > 0)], minlength=ML)
            if (rs // STRIP) % 12 == 0:
                print(f"    {Path(rf_path).name} strip {rs}/{H30}")
    with np.errstate(invalid="ignore", divide="ignore"):
        frac = np.where(total > 0, forest / total, -9999.0)
    return frac.reshape(H1, W1)


def dist_to_forest(mask_path, transform, crs):
    with rasterio.open(mask_path) as m:
        mask = m.read(1); nd = m.nodata
    forest = (mask == 1)
    dist_cells = distance_transform_edt(~forest)          # cells to nearest forest
    dist_km = dist_cells * KM_PER_CELL
    dist_km = np.where(mask == nd, -9999.0, dist_km)       # nodata outside region
    return dist_km.astype("float32")


def main():
    transform, crs, W1, H1 = template()
    print("template", W1, "x", H1)
    fr = {}
    for yr, p in RF30.items():
        print(f"forest fraction {yr} ...")
        fr[yr] = forest_fraction(p, transform, W1, H1)
        write1(f"afforest_frac_{yr}", fr[yr], transform, crs)
    # deltas (only where both endpoints valid)
    for a, b, name in [(2005, 2015, "afforest_delta_05_15"), (2015, 2024, "afforest_delta_15_24")]:
        d = np.where((fr[a] != -9999) & (fr[b] != -9999), fr[b] - fr[a], -9999.0)
        write1(name, d, transform, crs)
    print("distance-to-forest ...")
    write1("dist_to_forest_2005", dist_to_forest(RES / "forest_mask_2005.tif", transform, crs), transform, crs)
    write1("dist_to_forest_2015", dist_to_forest(RES / "forest_mask_2015.tif", transform, crs), transform, crs)
    print("done")


if __name__ == "__main__":
    main()
