"""Tables S2, S3 and S4 - SHAP circularity check and per-subregion driver importance.

Rebuilds the three-sheet workbook output/Tables_S2_S3_S4.xlsx from the
computed CSVs in data/ (SHAP importances from scripts_upstream/shap/task7_shap_augmented.py,
subregion importances and R2 from scripts_upstream/task2i_subregion_drivers.py).
Run from this folder: python -X utf8 build_tables_S2_S4.py   (needs pandas, numpy, openpyxl)
"""
# === CONFIG ===
import pandas as pd, numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from pathlib import Path
HERE = Path(__file__).resolve().parent
TABLES = str(HERE / "data")
XLSX_OUT = str(HERE / "output" / "Tables_S2_S3_S4.xlsx")
FONT = "Times New Roman"
HDR_SZ, BODY_SZ, TITLE_SZ, CAP_SZ = 11, 11, 11, 10
reglab={"NE":"NE China (all)","DXAL":"Daxing'an Mts.","XXAL":"Xiaoxing'an Mts.","CBS":"Changbai Mts.","SJP":"Sanjiang Plain","PERMA":"Permafrost zone"}
regorder=["NE","DXAL","XXAL","CBS","SJP","PERMA"]
perlab={"05_15":"2005–2015","15_24":"2015–2024"}
facorder=["Forest structure / starting state","Precipitation","Soil moisture","Water deficit","VPD","LST","Terrain"]
facshort=["Structure","Precip.","Soil moisture","Water deficit","VPD","LST","Terrain"]

# === build the workbook (three-line style) from the computed CSVs ===
med=Side(style="medium"); thin=Side(style="thin")
headb=Border(top=med,bottom=thin); botb=Border(bottom=med)
hF=Font(name=FONT,size=HDR_SZ,bold=True); cF=Font(name=FONT,size=BODY_SZ); cFb=Font(name=FONT,size=BODY_SZ,bold=True)
tF=Font(name=FONT,size=TITLE_SZ,bold=True); capF=Font(name=FONT,size=CAP_SZ,italic=True)
ctr=Alignment(horizontal="center",vertical="center",wrap_text=True); lft=Alignment(horizontal="left",vertical="center",wrap_text=True)
wb=Workbook()

# ---- Table S2 ----
sh=pd.read_csv(f"{TABLES}/shap/shap_importance_all.csv")
ws=wb.active; ws.title="Table S2"
ws["A1"]="Table S2. SHAP-based circularity check for the driver analysis."; ws["A1"].font=tF
hdr=["Subregion","Period","Exogenous share (%)","Model-internal share (%)","Dominant model-internal driver","Leading exogenous driver"]
hr=3
for j,h in enumerate(hdr,1):
    c=ws.cell(hr,j,h); c.font=hF; c.alignment=lft if j==1 else ctr; c.border=headb
r=hr+1
for reg in regorder:
    rs=r
    for per in ["05_15","15_24"]:
        d=sh[(sh.region==reg)&(sh.period==per)]; tot=d.mean_abs_shap.sum()
        exo=d[d.group=="EXOGENOUS"]; intl=d[d.group!="EXOGENOUS"]
        ti=intl.sort_values("mean_abs_shap",ascending=False).iloc[0]; te=exo.sort_values("mean_abs_shap",ascending=False).iloc[0]
        es=100*exo.mean_abs_shap.sum()/tot
        vals=[reglab[reg],perlab[per],round(es,1),round(100-es,1),
              f"{ti.driver_label} ({100*ti.mean_abs_shap/tot:.0f}%)",f"{te.driver_label} ({100*te.mean_abs_shap/tot:.0f}%)"]
        for j,v in enumerate(vals,1):
            c=ws.cell(r,j,v); c.font=cFb if j==4 else cF; c.alignment=lft if j in(1,5,6) else ctr
        r+=1
    ws.merge_cells(start_row=rs,start_column=1,end_row=rs+1,end_column=1); ws.cell(rs,1).alignment=lft
for j in range(1,7): ws.cell(r-1,j).border=botb
for w,col in zip([16,12,15,17,26,24],"ABCDEF"): ws.column_dimensions[col].width=w

# ---- S3 / S4 ----
lg=pd.read_csv(f"{TABLES}/subregion_fig7_importance_long.csv"); r2=pd.read_csv(f"{TABLES}/subregion_fig7_model_r2.csv")
def build(outcome,title,sheet):
    ws=wb.create_sheet(sheet); ws["A1"]=title; ws["A1"].font=tF
    hdr=["Subregion","Period"]+facshort+["R2"]; hr=3
    for j,h in enumerate(hdr,1):
        c=ws.cell(hr,j,h); c.font=hF; c.alignment=lft if j==1 else ctr; c.border=headb
    r=hr+1
    for reg in regorder:
        rs=r
        for per in ["05_15","15_24"]:
            d=lg[(lg.outcome==outcome)&(lg.region==reg)&(lg.period==per)]
            vals=[round(float(d[d.factor==f].rel_importance_pct.iloc[0]),1) for f in facorder]; mx=max(vals)
            rr=r2[(r2.outcome==outcome)&(r2.region==reg)&(r2.period==per)].r2.iloc[0]
            ws.cell(r,1,reglab[reg]).font=cF; ws.cell(r,1).alignment=lft
            ws.cell(r,2,perlab[per]).font=cF; ws.cell(r,2).alignment=ctr
            for j,v in enumerate(vals,3):
                c=ws.cell(r,j,v); c.font=cFb if abs(v-mx)<1e-9 else cF; c.alignment=ctr; c.number_format="0.0"
            c=ws.cell(r,10,round(float(rr),2)); c.font=cF; c.alignment=ctr; c.number_format="0.00"
            r+=1
        ws.merge_cells(start_row=rs,start_column=1,end_row=rs+1,end_column=1); ws.cell(rs,1).alignment=lft
    for j in range(1,11): ws.cell(r-1,j).border=botb
    ws.column_dimensions["A"].width=16; ws.column_dimensions["B"].width=12
    for col in "CDEFGHI": ws.column_dimensions[col].width=11
    ws.column_dimensions["J"].width=7
build("density","Table S3. Density model — subregional driver decomposition of Figure 7.","Table S3 (density)")
build("area","Table S4. Area model — subregional driver decomposition of Figure 7.","Table S4 (area)")
wb.save(XLSX_OUT); print("saved", XLSX_OUT)
# preview in-notebook
print(pd.read_csv(f"{TABLES}/subregion_fig7_importance_long.csv").head())