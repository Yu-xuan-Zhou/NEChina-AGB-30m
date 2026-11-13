# Panel (a) input: rebuild data/precomputed_data.npz (row mean, values <= 0 -> NaN, moving average window 6);
# the five *_rela_sd_mask.tif rasters are in percent and are divided by 100.
import rasterio, numpy as np, time, sys
from pathlib import Path
from rasterio.windows import Window
out_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent / "data" / "precomputed_data.npz")
R = "I:/AGB_models/boostrapping/"
files = [  # label, raster, scale
 ("MLR_2015",    R+"VCF_variation/MLR_2015_rela_sd_mask.tif", 1/100),
 ("MLR_2005",    R+"VCF_variation/MLR_2005_rela_sd_mask.tif", 1/100),
 ("Cubist_2015", R+"VCF_variation/Cubist_2015_rela_sd_mask.tif", 1/100),
 ("Cubist_2005", R+"VCF_variation/Cubist_2005_rela_sd_mask.tif", 1/100),
 ("RF_2015",     R+"RF_2015_rela_sd_mask.tif", 1/100),
 ("RF_2005",     R+"VCF_variation/RF_2005_sd_rela.tif", 1.0),
]
window_size = 6
def moving_average_filter(x, w):
    return np.convolve(x, np.ones(w) / w, mode="same")
all_data = {}
for lab, p, k in files:
    t0 = time.time()
    with rasterio.open(p) as s:
        means = np.empty(s.height, dtype=np.float32); nd = s.nodata
        for row in range(s.height):
            data = s.read(1, window=Window(0, row, s.width, 1)).astype(np.float32).squeeze()
            if nd is not None: data[data <= 0] = np.nan
            data[~np.isfinite(data)] = np.nan
            means[row] = np.nanmean(data) * k if np.isfinite(data).any() else np.nan
        lat = np.linspace(53.56, 38.71, s.height)
    all_data[lab] = {"mean_data": moving_average_filter(means, window_size), "lat": lat, "source": p, "scale": k}
    print(f"{lab}: rows={s.height} nan_rows={int(np.isnan(means).sum())} p50={np.nanpercentile(means,50):.4f} ({time.time()-t0:.0f}s)", flush=True)
np.savez_compressed(out_path, all_data=all_data)
print("saved", out_path)
