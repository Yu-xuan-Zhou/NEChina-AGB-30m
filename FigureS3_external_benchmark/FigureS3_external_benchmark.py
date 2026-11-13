"""Figure S3 - External benchmark comparison of the 2024 RF AGB map against independent products.

(a-c) cell-wise density scatter of the 2024 RF AGB map against CTrees 2024, CFATD 2023 and
their ensemble on a common 1 km grid (dashed 1:1, orange OLS fit); (d) mean AGB (+/- 1 SD)
by product across the whole forest domain and four forest zones.

Reads the cached 1 km grids in data/grids_1km
(built from the native rasters by scripts_upstream/build_grids.py), so it runs in seconds.

Run from this folder:
    python -X utf8 FigureS3_external_benchmark.py
Outputs: output/FigureS3_external_benchmark.{png,pdf,svg}
Units: Mg ha-1.
"""
# ---------------- CONFIG ----------------
from pathlib import Path
HERE  = Path(__file__).resolve().parent
GRID  = HERE / "data" / "grids_1km"
SHPD  = HERE / "data" / "shapefiles"
REF1K = HERE / "data" / "RF_2024_res1km.tif"          # 1 km grid template (transform / CRS / shape)
OUT   = HERE / "output"
PLIM  = (0, 200); OLS = "#D55E00"
COL   = {"RF":"#222222","CTREES":"#009E73","CFATD":"#D55E00"}
FS    = 10          # base font size (Arial 10 pt, as in Figures 4 and 6)
FIG_WIDTH_MM, FIG_HEIGHT_MM = 180, 129   # 180 mm canvas, 14:10 aspect
# Arial 10 pt, 600 dpi; panel letters = axis-label size (10 pt, bold); y labels on two lines.
# scatter panels: grid key, short label (axis), native resolution (shown in title)
SCAT  = [("CTREES","CTrees 2024","100 m"),
         ("CFATD","CFATD 2023","30 m"),
         ("ENSEMBLE","Ensemble","1 km")]
BARPRODS = [("CTREES","CTrees 2024"),("RF","RF 2024"),("CFATD","CFATD 2023")]   # order: CTrees, RF, CFATD
REGIONS = [("Northeast China", None),      # whole forest domain
           ("Daxing'anling",  "daxing"),
           ("Xiaoxing'anling", "xiaoxing"),
           ("Changbai",        "changbai"),
           ("Permafrost",      "2000frozen")]

import numpy as np, rasterio, geopandas as gpd, warnings, time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rasterio.features import rasterize
warnings.filterwarnings("ignore")
plt.rcParams.update({"font.size":FS,"axes.titlesize":FS,"axes.labelsize":FS,
    "xtick.labelsize":FS,"ytick.labelsize":FS,"legend.fontsize":FS-1,
    "axes.linewidth":0.8,"xtick.major.width":0.8,"ytick.major.width":0.8,
    "savefig.dpi":600,"pdf.fonttype":42,"font.family":"Arial"})
t0=time.time()
with rasterio.open(REF1K) as g: GT,CRS,W,H = g.transform,g.crs,g.width,g.height
RF=np.load(GRID/"grid_RF.npy"); CT=np.load(GRID/"grid_CTREES.npy"); CF=np.load(GRID/"grid_CFATD.npy")
ENS=np.nanmean(np.dstack([CT,CF]),axis=2)
ARR={"RF":RF,"CTREES":CT,"CFATD":CF,"ENSEMBLE":ENS}
def rmask(name):
    gdf=gpd.read_file(SHPD/name/(name+".shp")).to_crs(CRS)
    return rasterize([(g_,1) for g_ in gdf.geometry],out_shape=(H,W),transform=GT,fill=0,dtype="uint8").astype(bool)
RMASK=[(lbl, np.isfinite(RF) if shp is None else rmask(shp)) for lbl,shp in REGIONS]
def stats(x,y):
    m=np.isfinite(x)&np.isfinite(y); x,y=x[m],y[m]; mx,my=x.mean(),y.mean()
    vx=x.var(); cov=((x-mx)*(y-my)).mean(); r=cov/np.sqrt(vx*y.var()); sl=cov/vx; ic=my-sl*mx; d=y-x
    return dict(n=x.size,r=r,r2=r*r,RMSE=float(np.sqrt((d*d).mean())),bias=float(d.mean()),slope=sl,intc=ic)
print(f"ready in {time.time()-t0:.2f}s")

t0=time.time()
fig=plt.figure(figsize=(FIG_WIDTH_MM/25.4,FIG_HEIGHT_MM/25.4),layout="constrained")
fig.get_layout_engine().set(w_pad=0.02,h_pad=0.02,wspace=0.08,hspace=0.08)
gs=fig.add_gridspec(2,3,height_ratios=[1.0,0.82])
for i,(key,label,res) in enumerate(SCAT):
    ax=fig.add_subplot(gs[0,i]); x,y=RF,ARR[key]; m=np.isfinite(x)&np.isfinite(y); s=stats(x,y)
    ax.hexbin(x[m],y[m],gridsize=70,bins="log",cmap="viridis",extent=(*PLIM,*PLIM),mincnt=1,linewidths=0)
    lim=list(PLIM); ax.plot(lim,lim,"k--",lw=0.8,label="1:1"); xs=np.array(lim)
    ax.plot(xs,s["slope"]*xs+s["intc"],color=OLS,lw=1.0,label="OLS")
    ax.set_xlim(lim); ax.set_ylim(lim); ax.set_aspect("equal")
    ax.set_xlabel("RF 2024 AGB (Mg ha$^{-1}$)")
    ax.set_ylabel(f"{label} AGB" + chr(10) + "(Mg ha$^{-1}$)")   # two lines: fits the 1.6 in panels
    ax.text(0.05,0.95,f"{res} vs RF 30 m\nn={s['n']:,}\nr={s['r']:.2f}  R$^2$={s['r2']:.2f}\nRMSE={s['RMSE']:.1f}\nbias={s['bias']:+.1f}",
            transform=ax.transAxes,va="top",ha="left",fontsize=FS-3,linespacing=1.15,
            bbox=dict(boxstyle="round,pad=0.25",fc="white",ec="0.6",lw=0.5,alpha=0.85))
    ax.legend(loc="lower right",frameon=False)
    ax.text(-0.27,1.06,f"({'abc'[i]})",transform=ax.transAxes,fontsize=FS,fontweight="bold")
axb=fig.add_subplot(gs[1,:]); xpos=np.arange(len(RMASK)); wbar=0.26
for i,(pk,label) in enumerate(BARPRODS):
    arr=ARR[pk]
    means=[float(arr[m&np.isfinite(arr)].mean()) for _,m in RMASK]
    sds  =[float(arr[m&np.isfinite(arr)].std())  for _,m in RMASK]
    axb.bar(xpos+(i-1)*wbar,means,wbar,yerr=sds,capsize=3,error_kw=dict(lw=0.6),label=label,color=COL[pk])
axb.set_xticks(xpos); axb.set_xticklabels([r[0] for r in RMASK],rotation=8,ha="center",fontsize=FS-1)
axb.set_ylabel("mean AGB (Mg ha$^{-1}$)")
axb.set_ylim(0,215)   # headroom so the legend clears the tallest error bar
axb.legend(frameon=False,ncol=3,loc="upper right")
axb.text(-0.055,1.05,"(d)",transform=axb.transAxes,fontsize=FS,fontweight="bold")
OUT.mkdir(exist_ok=True)
for ext in ("png","pdf","svg"): fig.savefig(OUT/f"FigureS3_external_benchmark.{ext}",bbox_inches="tight",dpi=600)
print(f"combined figure built+saved in {time.time()-t0:.2f}s")
