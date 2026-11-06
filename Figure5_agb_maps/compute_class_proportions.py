"""Class proportions behind the Figure 5 inset histograms, recomputed from the 30 m RF rasters.

Valid pixel: finite and (for AGB maps) > 0; change maps may be negative. Writes a JSON
(default tables/class_proportions.json) with counts and percentages per class.
Run: python -X utf8 compute_class_proportions.py [out.json]   (reads the six 30 m maps, about 15 min)
"""
import numpy as np, rasterio, json, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
AGB_BINS = [-np.inf, 20, 40, 60, 80, 100, 120, 130, np.inf]
AGB_LABELS = ["<20","20-40","40-60","60-80","80-100","100-120","120-130",">130"]
CHG_BINS = [-np.inf,-80,-60,-40,-20,0,20,40,60,80,np.inf]
CHG_LABELS = ["<=-80","-80--60","-60--40","-40--20","-20-0","0-20","20-40","40-60","60-80",">80"]
TASKS = {
 "RF_2005": (r"I:\AGB_models\RF_2005.tif", "agb"),
 "RF_2015": (r"I:\AGB_models\RF_2015.tif", "agb"),
 "RF_2024": (r"I:\AGB_models\RF_2024.tif", "agb"),
 "Change_05-15": (r"I:\AGB_models\Change_05-15.tif", "chg"),
 "Change_15-24": (r"I:\AGB_models\Change_15-24.tif", "chg"),
 "Change_05-24": (r"I:\AGB_models\Change_05-24.tif", "chg"),
}
def run(name, path, kind):
    t0=time.time(); bins = AGB_BINS if kind=="agb" else CHG_BINS
    counts=np.zeros(len(bins)-1, dtype=np.int64); n=0; s=0.0
    with rasterio.open(path) as src:
        meta=dict(nodata=src.nodata, dtype=str(src.dtypes[0]), w=src.width, h=src.height)
        for _,win in src.block_windows(1):
            b=src.read(1, window=win, masked=True)
            d=b.data.astype("float64"); ok=(~b.mask)&np.isfinite(d)
            if kind=="agb": ok &= d>0
            if ok.any():
                v=d[ok]; counts+=np.histogram(v,bins=bins)[0]; n+=v.size; s+=v.sum()
    return name, dict(meta=meta, n_valid=int(n), mean=s/n if n else None,
                      labels=(AGB_LABELS if kind=="agb" else CHG_LABELS),
                      counts=counts.tolist(), pct=(100*counts/counts.sum()).round(3).tolist(), sec=round(time.time()-t0,1))
out={}
with ThreadPoolExecutor(max_workers=3) as pool:
    fut={pool.submit(run,k,p,kd):k for k,(p,kd) in TASKS.items()}
    for f in as_completed(fut):
        k,r=f.result(); out[k]=r; print(k, "done", r["sec"],"s  n=",r["n_valid"], "mean=",r["mean"], flush=True)
        json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "tables/class_proportions.json", "w"), indent=1)
print("ALL DONE")
