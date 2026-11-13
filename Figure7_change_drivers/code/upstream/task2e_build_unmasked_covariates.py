"""
Resample the UN-MASKED 500 m driver stacks to the 1 km gating grid.

Annual baseline stacks provide full-grid initial conditions on non-forest land:
  climfull_pdsi_<Y>, climfull_def_<Y>, climfull_vpd_<Y>, climfull_soil_<Y>, climfull_pr_<Y>
  burnedfull_<Y>, lstfull_<Y>, ndvifull_<Y>, laifull_<Y>, landcover_<Y>

Period stacks provide temporally matched forcing for the driver models:
  period_pdsi_<P>, period_def_<P>, period_vpd_<P>, period_soil_<P>, period_pr_<P>
  period_lst_<P>, period_burnfreq_<P>, period_burnany_<P>, period_burncount_<P>
where P is 05_15 or 15_24.
"""
from pathlib import Path
import numpy as np, rasterio
from rasterio.warp import reproject, Resampling

RES = Path(r"I:\AGB_models\Res")
OUT = Path(r"E:\DATA\Python\AGB_NE\R3_revision\covariates_1km")
TEMPLATE = RES / "RF_2005_res1km.tif"
SRC = {2005: RES / "dongbei_stack_500m_unmasked_2005.tif",
       2015: RES / "dongbei_stack_500m_unmasked_2015.tif",
       2024: RES / "dongbei_stack_500m_unmasked_2024.tif"}

PERIOD_SRC = {
    "05_15": RES / "dongbei_period_climate_burned_05_15_driver_period.tif",
    "15_24": RES / "dongbei_period_climate_burned_15_24_driver_period.tif",
}

# band index (1-based) in the unmasked stack -> (out-name, resampling)
BANDS = {
    10: ("climfull_pdsi", Resampling.average), 11: ("climfull_def", Resampling.average),
    13: ("climfull_vpd", Resampling.average), 12: ("climfull_soil", Resampling.average),
    9:  ("climfull_pr", Resampling.average),
    7:  ("burnedfull", Resampling.average), 8: ("lstfull", Resampling.average),
    3:  ("ndvifull", Resampling.average), 5: ("laifull", Resampling.average),
    14: ("landcover", Resampling.mode),
}

PERIOD_BANDS = {
    1: ("period_pr", Resampling.average),
    2: ("period_pdsi", Resampling.average),
    3: ("period_def", Resampling.average),
    4: ("period_soil", Resampling.average),
    5: ("period_vpd", Resampling.average),
    6: ("period_lst", Resampling.average),
    7: ("period_burnfreq", Resampling.average),
    8: ("period_burnany", Resampling.average),
    9: ("period_burncount", Resampling.average),
}


def main():
    with rasterio.open(TEMPLATE) as t:
        transform, crs, W, H = t.transform, t.crs, t.width, t.height
    for yr, src_path in SRC.items():
        print(f"resampling {yr} ...")
        with rasterio.open(src_path) as src:
            for bi, (name, rs) in BANDS.items():
                dst = np.full((H, W), np.nan, np.float32)
                reproject(source=rasterio.band(src, bi), destination=dst,
                          src_transform=src.transform, src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, resampling=rs)
                dst = np.where(np.isfinite(dst), dst, -9999.0).astype("float32")
                outname = f"{name}_{yr}"
                with rasterio.open(OUT / f"{outname}.tif", "w", driver="GTiff", height=H,
                                   width=W, count=1, dtype="float32", crs=crs,
                                   transform=transform, nodata=-9999.0, compress="lzw") as d:
                    d.write(dst, 1)
                print("  wrote", outname)
    for period, src_path in PERIOD_SRC.items():
        print(f"resampling period {period} ...")
        with rasterio.open(src_path) as src:
            for bi, (name, rs) in PERIOD_BANDS.items():
                dst = np.full((H, W), np.nan, np.float32)
                reproject(source=rasterio.band(src, bi), destination=dst,
                          src_transform=src.transform, src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, resampling=rs)
                dst = np.where(np.isfinite(dst), dst, -9999.0).astype("float32")
                outname = f"{name}_{period}"
                with rasterio.open(OUT / f"{outname}.tif", "w", driver="GTiff", height=H,
                                   width=W, count=1, dtype="float32", crs=crs,
                                   transform=transform, nodata=-9999.0, compress="lzw") as d:
                    d.write(dst, 1)
                print("  wrote", outname)
    print("done")


if __name__ == "__main__":
    main()
