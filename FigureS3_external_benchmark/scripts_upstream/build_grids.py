"""Budgeted, resumable aggregation of native AGB products -> common 1km grid.
Each call processes strips until BUDGET seconds, saving state every strip.
Re-run until 'ALL DONE'. Order: light products first."""
import os, sys, time, json, numpy as np, rasterio, warnings
os.environ.setdefault("GDAL_NUM_THREADS","ALL_CPUS")
os.environ.setdefault("GDAL_CACHEMAX","1024")
from rasterio.vrt import WarpedVRT
from rasterio.enums import Resampling
from rasterio.windows import Window
warnings.filterwarnings("ignore")

AGB  = "/sessions/wonderful-sleepy-bohr/mnt/AGB_models"
NE   = "/sessions/wonderful-sleepy-bohr/mnt/AGB_NE"
WORK = "/sessions/wonderful-sleepy-bohr/mnt/outputs/extval"
REF1K= NE + "/input_data_organized/figure7_inputs/agb_res_1km/RF_2024_res1km.tif"
VMIN, VMAX = 0.0, 400.0
STRIP  = int(os.environ.get("STRIP", 120))
BUDGET = float(os.environ.get("BUDGET", 38))

PRODUCTS = [
    ("CTREES", AGB + "/external/2024/ctrees_agb_100m_dongbei_2024.tif",        1.0),
    ("RF",     AGB + "/RF_2024.tif",                                           1.0),
    ("CFATD",  AGB + "/external/2024/CFATD_AGBD_2023_Northeast_China_30m.tif", 1.0),
    ("LIU",    AGB + "/external/2024/AGB_2024_LIU.tif",                         1.0),
]

def log(m):
    line=f"{time.strftime('%H:%M:%S')} {m}"; print(line,flush=True)
    open(WORK+"/build.log","a").write(line+"\n")

with rasterio.open(REF1K) as g:
    GT,CRS,W,H = g.transform,g.crs,g.width,g.height

t0=time.time()
for name,path,scale in PRODUCTS:
    out=f"{WORK}/grid_{name}.npy"
    if os.path.exists(out): continue
    part=f"{WORK}/grid_{name}.state.npz"
    arr=None; nxt=0
    if os.path.exists(part):
        try:
            d=np.load(part); arr=d["arr"].copy(); nxt=int(d["next"])
        except Exception:
            arr=None; nxt=0
    if arr is None:
        arr=np.full((H,W),np.nan,np.float32); nxt=0
    with rasterio.open(path) as src, WarpedVRT(src,crs=CRS,transform=GT,width=W,height=H,
                                               resampling=Resampling.average) as vrt:
        for r0 in range(nxt,H,STRIP):
            h=min(STRIP,H-r0)
            a=vrt.read(1,window=Window(0,r0,W,h)).astype("float32")*scale
            a[~np.isfinite(a)|(a<=VMIN)|(a>=VMAX)]=np.nan
            arr[r0:r0+h]=a
            np.savez(part,arr=arr,next=r0+h)
            if time.time()-t0>BUDGET:
                log(f"{name}: paused rows {r0+h}/{H}  ({time.time()-t0:.0f}s)")
                sys.exit(0)
    np.save(out,arr)
    try:
        if os.path.exists(part): os.remove(part)
    except Exception: pass
    v=arr[np.isfinite(arr)]
    log(f"{name}: DONE valid={v.size:,} mean={v.mean():.2f}  ({time.time()-t0:.0f}s)")
    if time.time()-t0>BUDGET: sys.exit(0)
log("ALL DONE")
