"""
TASK 2a -- Build the new 1 km exogenous covariates on the gating template grid
(2349 x 1782, EPSG:4326, res 0.008333). Writes single-band GeoTIFFs to
R3_revision/covariates_1km/.

  Hansen (30 m -> 1 km, block-streamed):
    hansen_loss_frac_all   loss 2001-2023 / forest baseline (treecover2000>=30)
    hansen_loss_frac_pre05 loss 2001-2004 / forest baseline   (prior disturbance)
    hansen_loss_frac_05_15 loss 2005-2015 / forest baseline   (in-period disturbance)
    hansen_mean_lossyear   mean calendar loss year among lost px (recency = age proxy)
    hansen_treecover2000   mean % tree cover 2000
  2005 MODIS stack (500 m -> 1 km, resampled):
    clim_pdsi, clim_def, clim_vpd, clim_soil, clim_pr, burned_frac_2005, forest_type
  Polygon:
    permafrost_flag        1 inside 2000frozen, else 0
"""
from pathlib import Path
import numpy as np, rasterio, geopandas as gpd
from rasterio.windows import Window
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize
from osgeo import gdal

TEMPLATE = r"I:\AGB_models\Res\RF_2005_res1km.tif"
HANSEN_VRT = r"E:\DATA\Python\AGB_NE\R3_revision\scripts\hansen_mosaic.vrt"
MODIS2005 = r"I:\env\MODIS_annual_500m\dongbei_MODIS_annual_500m_2005.tif"
FROZEN = r"I:\Shp\SHP\2000frozen\2000frozen.shp"
OUT = Path(r"E:\DATA\Python\AGB_NE\R3_revision\covariates_1km")
OUT.mkdir(parents=True, exist_ok=True)
TC_THRESH = 30
STRIP = 1024


def template():
    with rasterio.open(TEMPLATE) as t:
        return t.transform, t.crs, t.width, t.height, t.bounds


def write_1km(name, arr, transform, crs, nodata=-9999.0):
    arr = arr.astype("float32")
    with rasterio.open(OUT / f"{name}.tif", "w", driver="GTiff", height=arr.shape[0],
                       width=arr.shape[1], count=1, dtype="float32", crs=crs,
                       transform=transform, nodata=nodata, compress="lzw") as d:
        d.write(arr, 1)
    print("  wrote", name)


def hansen_to_1km(transform, crs, W1, H1):
    ulx, uly = transform.c, transform.f
    res1 = transform.a
    forest = np.zeros(H1 * W1, np.float64)
    loss_all = np.zeros(H1 * W1, np.float64)
    loss_pre = np.zeros(H1 * W1, np.float64)
    loss_in = np.zeros(H1 * W1, np.float64)
    ly_sum = np.zeros(H1 * W1, np.float64)
    tc_sum = np.zeros(H1 * W1, np.float64)
    tot = np.zeros(H1 * W1, np.float64)
    with rasterio.open(HANSEN_VRT) as src:
        t30 = src.transform; res30 = t30.a; W30 = src.width; H30 = src.height
        lon = t30.c + (np.arange(W30) + 0.5) * res30
        col1 = np.floor((lon - ulx) / res1).astype(np.int64)
        col_ok = (col1 >= 0) & (col1 < W1)
        for rs in range(0, H30, STRIP):
            R = min(STRIP, H30 - rs)
            lat = uly - (np.arange(rs, rs + R) + 0.5) * res30
            row1 = np.floor((uly - lat) / res1).astype(np.int64)
            row_ok = (row1 >= 0) & (row1 < H1)
            win = Window(0, rs, W30, R)
            ly = src.read(1, window=win)
            tc = src.read(2, window=win)
            forest_px = tc >= TC_THRESH
            # flat 1km index per 30m pixel
            idx = row1[:, None] * W1 + col1[None, :]
            ok = row_ok[:, None] & col_ok[None, :]
            f = forest_px & ok
            fi = idx[f]
            ML = H1 * W1
            forest += np.bincount(fi, minlength=ML)
            tc_sum += np.bincount(fi, weights=tc[f].astype(np.float64), minlength=ML)
            lyf = ly[f]
            lost = lyf >= 1
            loss_all += np.bincount(fi[lost], minlength=ML)
            ly_sum += np.bincount(fi[lost], weights=lyf[lost].astype(np.float64), minlength=ML)
            loss_pre += np.bincount(fi[(lyf >= 1) & (lyf <= 4)], minlength=ML)
            loss_in += np.bincount(fi[(lyf >= 5) & (lyf <= 15)], minlength=ML)
            tot += np.bincount(idx[ok], minlength=ML)
            if (rs // STRIP) % 10 == 0:
                print(f"    hansen strip {rs}/{H30}")
    with np.errstate(divide="ignore", invalid="ignore"):
        frac_all = np.where(forest > 0, loss_all / forest, -9999.0)
        frac_pre = np.where(forest > 0, loss_pre / forest, -9999.0)
        frac_in = np.where(forest > 0, loss_in / forest, -9999.0)
        mean_ly = np.where(loss_all > 0, ly_sum / loss_all + 2000.0, -9999.0)
        tc_mean = np.where(tot > 0, tc_sum / np.maximum(tot, 1), -9999.0)
    sh = (H1, W1)
    write_1km("hansen_loss_frac_all", frac_all.reshape(sh), transform, crs)
    write_1km("hansen_loss_frac_pre05", frac_pre.reshape(sh), transform, crs)
    write_1km("hansen_loss_frac_05_15", frac_in.reshape(sh), transform, crs)
    write_1km("hansen_mean_lossyear", mean_ly.reshape(sh), transform, crs)
    write_1km("hansen_treecover2000", tc_mean.reshape(sh), transform, crs)


def modis2005_to_1km(transform, crs, W1, H1):
    bands = {"clim_pdsi": (10, Resampling.average), "clim_def": (11, Resampling.average),
             "clim_soil": (12, Resampling.average), "clim_vpd": (13, Resampling.average),
             "clim_pr": (9, Resampling.average), "burned_frac_2005": (7, Resampling.average),
             "forest_type": (14, Resampling.mode)}
    with rasterio.open(MODIS2005) as src:
        for name, (bi, rs) in bands.items():
            dst = np.full((H1, W1), np.nan, np.float32)
            reproject(source=rasterio.band(src, bi), destination=dst,
                      src_transform=src.transform, src_crs=src.crs,
                      dst_transform=transform, dst_crs=crs, resampling=rs)
            dst = np.where(np.isfinite(dst), dst, -9999.0)
            write_1km(name, dst, transform, crs)


def permafrost_to_1km(transform, crs, W1, H1):
    g = gpd.read_file(FROZEN).to_crs(crs)
    arr = rasterize([(geom, 1) for geom in g.geometry], out_shape=(H1, W1),
                    transform=transform, fill=0, dtype="float32")
    write_1km("permafrost_flag", arr, transform, crs)


def main():
    transform, crs, W1, H1, bounds = template()
    print("template", W1, "x", H1, "res", round(transform.a, 6))
    print("Hansen 30m -> 1km ...")
    hansen_to_1km(transform, crs, W1, H1)
    print("MODIS-2005 500m -> 1km ...")
    modis2005_to_1km(transform, crs, W1, H1)
    print("permafrost flag ...")
    permafrost_to_1km(transform, crs, W1, H1)
    print("done")


if __name__ == "__main__":
    main()
