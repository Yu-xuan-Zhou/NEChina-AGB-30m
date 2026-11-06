r"""
Download a Northeast China clip from the public CTrees global AGB 100 m COGs.

This avoids downloading the ~35 GiB global GeoTIFF. It reads only the window
covering the local dongbei shapefile, masks pixels outside the polygon, and
writes a cropped GeoTIFF plus a small CSV summary.

Interpreter:
    C:\ProgramData\anaconda3\python.exe

Example:
    set PYTHONIOENCODING=utf-8
    "C:/ProgramData/anaconda3/python.exe" download_ctrees_agb_ne.py

Optional:
    "C:/ProgramData/anaconda3/python.exe" download_ctrees_agb_ne.py --years 2024 2025 --include-uncertainty
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask
from rasterio.windows import Window, transform as window_transform


ROOT = Path(r"E:\DATA\Python\AGB_NE")
DEFAULT_SHP = ROOT / "input_data_organized" / "figure7_inputs" / "shapefiles" / "dongbei" / "dongbei.shp"
DEFAULT_OUT = ROOT / "external_validation" / "ctrees_agb_ne"

BASE_URL = "https://ctrees-agb-100m-global.s3.us-west-2.amazonaws.com"
OBJECT_TEMPLATE = (
    "cogs/global_agb_100m_landsat0024_all_{year}_densenet_l1_"
    "agb_mosaic_100m_base_cd_ts{suffix}.tif"
)

PRODUCTS = {
    "agb": {
        "suffix": "",
        "label": "agb",
        "description": "CTrees above-ground biomass",
        "units": "Mg ha-1",
    },
    "sem": {
        "suffix": "_uncertainty_sem",
        "label": "agb_uncertainty_sem",
        "description": "CTrees above-ground biomass uncertainty SEM",
        "units": "Mg ha-1",
    },
}

SOURCE_NODATA = -9999
OUTPUT_NODATA = -9999.0
AGB_SCALE_FACTOR = 10.0
STRIP_ROWS = 512


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--years", nargs="+", type=int, default=[2024], help="Years to clip, e.g. 2024 2025.")
    p.add_argument("--shp", type=Path, default=DEFAULT_SHP, help="Study-region shapefile.")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT, help="Output directory.")
    p.add_argument("--include-uncertainty", action="store_true", help="Also clip CTrees uncertainty SEM COGs.")
    p.add_argument("--strip-rows", type=int, default=STRIP_ROWS, help="Rows per streaming read/write strip.")
    p.add_argument("--force", action="store_true", help="Overwrite existing output GeoTIFFs.")
    return p.parse_args()


def product_url(year: int, product: str) -> str:
    cfg = PRODUCTS[product]
    key = OBJECT_TEMPLATE.format(year=year, suffix=cfg["suffix"])
    return f"{BASE_URL}/{key}"


def clamp_window(src: rasterio.DatasetReader, bounds: tuple[float, float, float, float]) -> Window:
    raw = src.window(*bounds)
    col0 = max(0, math.floor(raw.col_off))
    row0 = max(0, math.floor(raw.row_off))
    col1 = min(src.width, math.ceil(raw.col_off + raw.width))
    row1 = min(src.height, math.ceil(raw.row_off + raw.height))
    if col1 <= col0 or row1 <= row0:
        raise ValueError(f"Shapefile bounds do not overlap raster bounds: {bounds}")
    return Window(col0, row0, col1 - col0, row1 - row0)


def read_region(shp: Path, dst_crs) -> tuple[object, tuple[float, float, float, float], int]:
    if not shp.exists():
        raise FileNotFoundError(f"Study-region shapefile not found: {shp}")
    gdf = gpd.read_file(shp, engine="pyogrio")
    if gdf.empty:
        raise ValueError(f"Shapefile has no features: {shp}")
    if dst_crs is not None:
        gdf = gdf.to_crs(dst_crs)
    geom = gdf.union_all()
    return geom, tuple(float(x) for x in geom.bounds), len(gdf)


def valid_values(arr: np.ndarray, inside: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite_inside = inside & np.isfinite(arr) & (arr != OUTPUT_NODATA)
    all_vals = arr[finite_inside]
    positive_vals = arr[finite_inside & (arr > 0)]
    return all_vals, positive_vals


def update_stats(stats: dict[str, float], arr: np.ndarray, inside: np.ndarray) -> None:
    all_vals, positive_vals = valid_values(arr, inside)
    stats["inside_pixels"] += int(all_vals.size)
    stats["positive_pixels"] += int(positive_vals.size)
    if all_vals.size:
        stats["sum_all"] += float(all_vals.sum(dtype="float64"))
        stats["min_all"] = min(stats["min_all"], float(all_vals.min()))
        stats["max_all"] = max(stats["max_all"], float(all_vals.max()))
    if positive_vals.size:
        stats["sum_positive"] += float(positive_vals.sum(dtype="float64"))
        stats["min_positive"] = min(stats["min_positive"], float(positive_vals.min()))
        stats["max_positive"] = max(stats["max_positive"], float(positive_vals.max()))


def init_stats(year: int, product: str, url: str, out_path: Path) -> dict[str, float | int | str]:
    return {
        "year": year,
        "product": product,
        "units": PRODUCTS[product]["units"],
        "source_raw_scale_factor": AGB_SCALE_FACTOR,
        "source_url": url,
        "output_tif": str(out_path),
        "inside_pixels": 0,
        "positive_pixels": 0,
        "sum_all": 0.0,
        "sum_positive": 0.0,
        "min_all": float("inf"),
        "max_all": float("-inf"),
        "min_positive": float("inf"),
        "max_positive": float("-inf"),
    }


def finalize_stats(stats: dict[str, float | int | str]) -> dict[str, float | int | str]:
    inside = int(stats["inside_pixels"])
    positive = int(stats["positive_pixels"])
    stats["mean_all_pixels"] = float(stats["sum_all"] / inside) if inside else np.nan
    stats["mean_positive_pixels"] = float(stats["sum_positive"] / positive) if positive else np.nan
    stats["positive_fraction"] = float(positive / inside) if inside else np.nan
    for key in ("sum_all", "sum_positive"):
        stats.pop(key, None)
    for key in ("min_all", "max_all", "min_positive", "max_positive"):
        if not np.isfinite(stats[key]):
            stats[key] = np.nan
    return stats


def output_name(year: int, product: str) -> str:
    label = PRODUCTS[product]["label"]
    return f"ctrees_{label}_100m_dongbei_{year}.tif"


def clip_one(year: int, product: str, shp: Path, out_dir: Path, strip_rows: int, force: bool) -> dict:
    url = product_url(year, product)
    out_path = out_dir / output_name(year, product)
    if out_path.exists() and not force:
        print(f"[skip] exists: {out_path}")
        return {
            "year": year,
            "product": product,
            "source_url": url,
            "output_tif": str(out_path),
            "status": "exists",
        }

    print(f"[open] {url}")
    env_opts = {
        "AWS_NO_SIGN_REQUEST": "YES",
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF",
        "GDAL_HTTP_MULTIRANGE": "YES",
        "VSI_CACHE": "TRUE",
        "VSI_CACHE_SIZE": "268435456",
    }

    with rasterio.Env(**env_opts):
        with rasterio.open(url) as src:
            geom, bounds, feature_count = read_region(shp, src.crs)
            win = clamp_window(src, bounds)
            win = Window(int(win.col_off), int(win.row_off), int(win.width), int(win.height))
            out_transform = window_transform(win, src.transform)

            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                height=int(win.height),
                width=int(win.width),
                transform=out_transform,
                dtype="float32",
                nodata=OUTPUT_NODATA,
                compress="DEFLATE",
                predictor=3,
                tiled=True,
                blockxsize=512,
                blockysize=512,
                BIGTIFF="IF_SAFER",
            )
            out_path.parent.mkdir(parents=True, exist_ok=True)
            stats = init_stats(year, product, url, out_path)

            print(
                f"[clip] year={year} product={product} features={feature_count} "
                f"window={int(win.width)}x{int(win.height)} -> {out_path}"
            )
            with rasterio.open(out_path, "w", **profile) as dst:
                dst.set_band_description(1, PRODUCTS[product]["description"])
                dst.update_tags(
                    source="CTrees global AGB 100m public COG",
                    source_url=url,
                    source_year=str(year),
                    region_shapefile=str(shp),
                    region="Northeast China / dongbei",
                    outside_region_nodata=str(OUTPUT_NODATA),
                    units=PRODUCTS[product]["units"],
                    source_raw_dtype=str(src.dtypes[0]),
                    source_raw_scale_factor=str(AGB_SCALE_FACTOR),
                    transform_applied=f"raw_value / {AGB_SCALE_FACTOR}",
                )
                for local_r0 in range(0, int(win.height), strip_rows):
                    h = min(strip_rows, int(win.height) - local_r0)
                    src_win = Window(int(win.col_off), int(win.row_off) + local_r0, int(win.width), h)
                    dst_win = Window(0, local_r0, int(win.width), h)
                    raw = src.read(1, window=src_win)
                    arr = raw.astype("float32")
                    source_valid = raw != SOURCE_NODATA
                    arr[source_valid] = arr[source_valid] / AGB_SCALE_FACTOR
                    arr[~source_valid] = OUTPUT_NODATA
                    inside = geometry_mask(
                        [geom.__geo_interface__],
                        out_shape=(h, int(win.width)),
                        transform=window_transform(src_win, src.transform),
                        invert=True,
                    )
                    update_stats(stats, arr, inside)
                    out = arr.copy()
                    out[~inside] = OUTPUT_NODATA
                    dst.write(out, 1, window=dst_win)

                    done = local_r0 + h
                    if done == int(win.height) or local_r0 == 0 or done % (strip_rows * 20) == 0:
                        print(f"  rows {done:,}/{int(win.height):,}", flush=True)

    stats = finalize_stats(stats)
    stats["status"] = "written"
    return stats


def products_to_run(include_uncertainty: bool) -> list[str]:
    products = ["agb"]
    if include_uncertainty:
        products.append("sem")
    return products


def main() -> int:
    args = parse_args()
    rows = []
    for year in args.years:
        if year < 2000 or year > 2025:
            raise ValueError("CTrees public COG years currently span 2000-2025.")
        for product in products_to_run(args.include_uncertainty):
            rows.append(clip_one(year, product, args.shp, args.out_dir, args.strip_rows, args.force))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / "ctrees_agb_ne_clip_summary.csv"
    df = pd.DataFrame(rows)
    df.to_csv(summary_path, index=False)
    print(f"[done] summary: {summary_path}")
    if not df.empty:
        cols = [c for c in ("year", "product", "status", "inside_pixels", "positive_pixels",
                            "mean_all_pixels", "mean_positive_pixels", "positive_fraction",
                            "output_tif") if c in df.columns]
        print(df[cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
