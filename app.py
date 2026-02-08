"""
Ecommerce Profit Dashboard v5.5
Multi-Country · Dropi + Facebook + TikTok
Fixes: Flete Dev logic, Transit scope, Logistics pie charts, P&L with logistics %, Utility charts, Manual ads improvements, Product mapping bug
"""
import streamlit as st, pandas as pd, io
try:
    import plotly.express as px; import plotly.graph_objects as go
except ImportError:
    import subprocess,sys; subprocess.check_call([sys.executable,"-m","pip","install","plotly"])
    import plotly.express as px; import plotly.graph_objects as go
import requests,json,os,re
from datetime import datetime,timedelta
from collections import defaultdict

st.set_page_config(page_title="Profit Dashboard",page_icon="📊",layout="wide",initial_sidebar_state="expanded")

PAISES={"Colombia":{"flag":"🇨🇴","moneda":"COP","sym":"$"},"Ecuador":{"flag":"🇪🇨","moneda":"USD","sym":"$"},"Guatemala":{"flag":"🇬🇹","moneda":"GTQ","sym":"Q"}}
SETTINGS_FILE="dashboard_settings.json";MAPPING_FILE="product_mappings.json";CAMP_MAPPING_FILE="campaign_mappings.json";MANUAL_ADS_FILE="manual_ads.json"
C=dict(profit="#10B981",loss="#EF4444",warn="#F59E0B",blue="#3B82F6",purple="#8B5CF6",orange="#F97316",cyan="#06B6D4",muted="#64748B",text="#E2E8F0",sub="#94A3B8",grid="#1E293B",bg="#0B0F19")
STATUS_ENT=["ENTREGADO"];STATUS_CAN=["CANCELADO","RECHAZADO"]
STATUS_DEV=["DEVOLUCION","DEVOLUCIÓN","EN DEVOLUCION","EN DEVOLUCIÓN"]
STATUS_NOV=["NOVEDAD","CON NOVEDAD"]
STATUS_TRA_EXPLICIT=["EN TRANSITO","EN TRÁNSITO","EN ESPERA DE RUTA DOMESTICA","DESPACHADA","DESPACHADO","ENVIADO","EN REPARTO","EN RUTA","EN BODEGA TRANSPORTADORA","EN BODEGA DESTINO","GUIA IMPRESA","EN ALISTAMIENTO","EN CAMINO","ESPERANDO RUTA","PENDIENTE","EN ESPERA"]
COUNTRY_ALIASES={"CO":"Colombia","COL":"Colombia","COLOMBIA":"Colombia","EC":"Ecuador","ECU":"Ecuador","ECUADOR":"Ecuador","GT":"Guatemala","GUA":"Guatemala","GUATEMALA":"Guatemala"}

def mss(s,pats): return any(p in s.upper().strip() for p in pats)

# FIX: "in transit" = everything NOT entregado, NOT cancelado/rechazado, NOT devolucion
def is_transit(s):
    su=s.upper().strip()
    return not mss(su,STATUS_ENT) and not mss(su,STATUS_CAN) and not mss(su,STATUS_DEV)

def pl(**kw):
    b=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Inter,system-ui,sans-serif",color=C["text"],size=12),xaxis=dict(gridcolor=C["grid"],zerolinecolor=C["grid"]),yaxis=dict(gridcolor=C["grid"],zerolinecolor=C["grid"]),margin=dict(l=40,r=20,t=50,b=40),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=11,color=C["sub"])))
    b.update(kw);return b

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#0B0F19!important;color:#E2E8F0!important;font-family:'Inter',system-ui,sans-serif!important}
header[data-testid="stHeader"]{background:#0B0F19!important}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0F1420,#080C14)!important;border-right:1px solid #1E293B!important}
section[data-testid="stSidebar"] *{color:#E2E8F0!important}
section[data-testid="stSidebar"] .stSelectbox>div>div,section[data-testid="stSidebar"] .stTextInput>div>div>input,section[data-testid="stSidebar"] .stNumberInput>div>div>input,section[data-testid="stSidebar"] .stMultiSelect>div>div{background:#1E293B!important;border-color:#334155!important;color:#E2E8F0!important;border-radius:.5rem!important}
section[data-testid="stSidebar"] .stFileUploader>div{background:#111827!important;border:1px dashed #334155!important;border-radius:.75rem!important}
.stTabs [data-baseweb="tab-list"]{background:#111827!important;border-radius:.75rem!important;padding:4px!important;gap:4px!important;border:1px solid #1E293B!important}
.stTabs [data-baseweb="tab"]{border-radius:.5rem!important;color:#64748B!important;font-weight:500!important;padding:8px 16px!important}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:#10B981!important;color:#0B0F19!important;font-weight:600!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none!important}
div[data-testid="stMetric"]{display:none!important}
[data-testid="stExpander"]{border:1px solid #1E293B!important;border-radius:.75rem!important;background:#111827!important}
.stButton>button{background:linear-gradient(135deg,#10B981,#059669)!important;color:#0B0F19!important;border:none!important;border-radius:.5rem!important;font-weight:600!important}
hr{border-color:#1E293B!important}
[data-testid="stDateInput"]>div>div>input{background:#1E293B!important;border-color:#334155!important;color:#E2E8F0!important;border-radius:.5rem!important}
.kcard{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.3rem 1.5rem;position:relative;overflow:hidden}
.kcard:hover{border-color:rgba(16,185,129,0.4)}.kcard.green{border-color:rgba(16,185,129,0.3)}.kcard.red{border-color:rgba(239,68,68,0.3)}.kcard.blue{border-color:rgba(59,130,246,0.3)}.kcard.purple{border-color:rgba(139,92,246,0.3)}
.kcard .icon{position:absolute;top:1.2rem;right:1.2rem;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1rem;opacity:.7}
.kcard .icon.g{background:rgba(16,185,129,0.15);color:#10B981}.kcard .icon.r{background:rgba(239,68,68,0.15);color:#EF4444}.kcard .icon.b{background:rgba(59,130,246,0.15);color:#3B82F6}.kcard .icon.w{background:rgba(148,163,184,0.15);color:#94A3B8}.kcard .icon.p{background:rgba(139,92,246,0.15);color:#8B5CF6}
.kcard .lbl{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#64748B;margin-bottom:.35rem}
.kcard .val{font-family:'JetBrains Mono',monospace;font-weight:700;margin-bottom:.15rem}
.kcard .val.xl{font-size:2rem}.kcard .val.lg{font-size:1.6rem}.kcard .val.md{font-size:1.3rem}
.kcard .val.green{color:#10B981}.kcard .val.red{color:#EF4444}.kcard .val.white{color:#F1F5F9}.kcard .val.blue{color:#3B82F6}.kcard .val.purple{color:#8B5CF6}
.kcard .sub{font-size:.78rem;color:#64748B}.kcard .pct{font-size:.72rem;color:#94A3B8;font-family:'JetBrains Mono',monospace;margin-top:2px}
.row2{display:grid;gap:1rem;margin-bottom:1rem}.r2{grid-template-columns:1fr 1fr}.r3{grid-template-columns:1fr 1fr 1fr}.r4{grid-template-columns:1fr 1fr 1fr 1fr}
.section-hdr{font-size:1.05rem;font-weight:700;color:#E2E8F0;border-left:3px solid #10B981;padding-left:12px;margin:1.5rem 0 1rem}
.cas-row{display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #111827}
.cas-lbl{width:170px;font-size:.82rem;color:#94A3B8;flex-shrink:0}.cas-bar-wrap{flex:1;height:26px;position:relative;margin:0 16px}
.cas-bar{height:100%;border-radius:4px;min-width:4px}.cas-amt{width:140px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:600;font-size:.88rem;flex-shrink:0}
.cas-pct{width:60px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#64748B;flex-shrink:0}
.otbl{width:100%;border-collapse:separate;border-spacing:0;font-size:.82rem}
.otbl th{padding:10px 12px;text-align:left;font-size:.65rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;background:#111827;border-bottom:1px solid #1E293B}
.otbl td{padding:10px 12px;border-bottom:1px solid rgba(15,20,32,0.8);color:#E2E8F0;white-space:nowrap}.otbl tr:hover td{background:#131A2B}
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:9999px;font-size:.72rem;font-weight:600}
.p-ent{background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3)}.p-can{background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3)}.p-tra{background:rgba(245,158,11,0.15);color:#F59E0B;border:1px solid rgba(245,158,11,0.3)}.p-dev{background:rgba(249,115,22,0.15);color:#F97316;border:1px solid rgba(249,115,22,0.3)}.p-nov{background:rgba(139,92,246,0.15);color:#8B5CF6;border:1px solid rgba(139,92,246,0.3)}.p-pen{background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)}
.lgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:1rem;margin:1rem 0}
.litem{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1rem;text-align:center}
.litem h3{font-size:1.3rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin:.3rem 0}.litem p{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;margin:0}
.badge{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:.75rem;font-weight:600;font-family:'JetBrains Mono',monospace}
</style>""",unsafe_allow_html=True)

# ═══ HELPERS ═══
def lj(p):
    if os.path.exists(p):
        try:
            with open(p) as f: return json.load(f)
        except: pass
    return {}
def sj(p,d):
    try:
        with open(p,"w") as f: json.dump(d,f,ensure_ascii=False)
    except: pass
def load_cfg(): return lj(SETTINGS_FILE)
def save_cfg(k,v): s=load_cfg();s[k]=v;sj(SETTINGS_FILE,s)

@st.cache_data(ttl=3600,show_spinner=False)
def get_trm():
    rates={"COP_USD":4200,"COP_GTQ":540}
    try:
        r=requests.get("https://open.er-api.com/v6/latest/USD",timeout=10)
        if r.ok: d=r.json();rates["COP_USD"]=d["rates"].get("COP",4200);rates["COP_GTQ"]=rates["COP_USD"]/d["rates"].get("GTQ",7.75)
    except: pass
    return rates
def cop_to(v,t,trm):
    if t=="COP": return v
    return v/trm.get("COP_USD",4200) if t=="USD" else v/trm.get("COP_GTQ",540)
def to_cop(v,s,trm):
    if s=="COP": return v
    return v*trm.get("COP_USD",4200) if s=="USD" else v*trm.get("COP_GTQ",540)

@st.cache_data(show_spinner=False)
def cargar(data_bytes,name):
    buf=io.BytesIO(data_bytes)
    if name.lower().endswith((".xlsx",".xls")): df=pd.read_excel(buf,dtype=str,engine="openpyxl")
    else:
        for enc in ("utf-8","latin-1","cp1252"):
            try: buf.seek(0);df=pd.read_csv(buf,dtype=str,encoding=enc,sep=None,engine="python");break
            except: continue
        else: buf.seek(0);df=pd.read_csv(buf,dtype=str,encoding="latin-1",on_bad_lines="skip")
    df.columns=df.columns.str.strip().str.upper()
    alias={"TOTAL DE LA ORDEN":["TOTAL DE LA ORDEN","TOTAL_DE_LA_ORDEN"],"PRECIO PROVEEDOR":["PRECIO PROVEEDOR","PRECIO_PROVEEDOR"],"PRECIO FLETE":["PRECIO FLETE","PRECIO_FLETE"],"COSTO DEVOLUCION FLETE":["COSTO DEVOLUCION FLETE","COSTO_DEVOLUCION_FLETE"],"GANANCIA":["GANANCIA","PROFIT"],"CANTIDAD":["CANTIDAD","QTY"],"ESTATUS":["ESTATUS","STATUS","ESTADO"],"PRODUCTO":["PRODUCTO","PRODUCT"],"FECHA":["FECHA","DATE"],"CIUDAD DESTINO":["CIUDAD DESTINO","CIUDAD"]}
    for canon,vs in alias.items():
        for v in vs:
            if v in df.columns and canon not in df.columns: df.rename(columns={v:canon},inplace=True);break
    for col in ["TOTAL DE LA ORDEN","PRECIO PROVEEDOR","PRECIO PROVEEDOR X CANTIDAD","PRECIO FLETE","COSTO DEVOLUCION FLETE","GANANCIA","CANTIDAD","COMISION"]:
        if col in df.columns: df[col]=df[col].astype(str).str.replace(r"[^\d.\-]","",regex=True).replace("","0");df[col]=pd.to_numeric(df[col],errors="coerce").fillna(0)
    if "FECHA" in df.columns: df["FECHA"]=pd.to_datetime(df["FECHA"],dayfirst=True,errors="coerce")
    if "ESTATUS" in df.columns: df["ESTATUS"]=df["ESTATUS"].astype(str).str.strip().str.upper()
    return df

def filtrar(df,ini,fin):
    if "FECHA" not in df.columns: return df
    return df[(df["FECHA"]>=pd.Timestamp(ini))&(df["FECHA"]<=pd.Timestamp(fin)+pd.Timedelta(days=1)-pd.Timedelta(seconds=1))].copy()

def detect_country(df):
    co={"BOGOTA","BOGOTÁ","MEDELLIN","MEDELLÍN","CALI","BARRANQUILLA","CARTAGENA","BUCARAMANGA","PEREIRA","CUCUTA","MANIZALES","IBAGUE","PASTO","SANTA MARTA","VILLAVICENCIO","NEIVA","DOSQUEBRADAS","ARMENIA","POPAYAN","SINCELEJO","VALLEDUPAR","TUNJA","MONTERIA"}
    ec={"QUITO","GUAYAQUIL","CUENCA","AMBATO","PORTOVIEJO","MACHALA","DURÁN","LOJA","MANTA","SANTO DOMINGO","RIOBAMBA"}
    gt={"GUATEMALA","MIXCO","VILLA NUEVA","QUETZALTENANGO","ESCUINTLA","CHINAUTLA","HUEHUETENANGO","COBAN","ANTIGUA"}
    if "CIUDAD DESTINO" in df.columns:
        c=set(df["CIUDAD DESTINO"].dropna().str.upper().str.strip().unique())
        sc={"Colombia":len(c&co),"Ecuador":len(c&ec),"Guatemala":len(c&gt)};b=max(sc,key=sc.get)
        if sc[b]>0: return b
    return None

def extraer_base(n):
    n=re.sub(r'\s*-\s*',' ',str(n).strip().upper())
    w=[x for x in n.split() if not re.match(r'^\d+$',x) and x not in ("X","DE","EL","LA","EN","CON","PARA","POR")]
    return " ".join(w[:2]) if w else n

def apply_groups(df,gm):
    rv={}
    for gn,ors in gm.items():
        for o in ors: rv[o.upper().strip()]=gn
    df["GRUPO_PRODUCTO"]=df["PRODUCTO"].str.upper().str.strip().map(rv).fillna(df["PRODUCTO"]);return df

def fmt(v,pn="Colombia"): return f"{PAISES.get(pn,PAISES['Colombia'])['sym']} {v:,.0f}".replace(",",".")
def fmt_cop(v): return f"$ {v:,.0f}".replace(",",".")
def pof(p,w): return f"{(p/w*100):.1f}%" if w else "0%"
def parse_camp_country(n):
    parts=[x.strip().upper() for x in str(n).split("-")]
    return COUNTRY_ALIASES.get(parts[0],None) if parts else None
def to_excel(df):
    buf=io.BytesIO();df.to_excel(buf,index=False,engine="openpyxl");return buf.getvalue()

# FIX #1: Flete devolucion — COSTO DEVOLUCION FLETE first, fallback PRECIO FLETE
def calc_flete_dev(row):
    cdf=row.get("COSTO DEVOLUCION FLETE",0) or 0
    pf=row.get("PRECIO FLETE",0) or 0
    return cdf if cdf > 0 else pf

def get_F(df):
    return {c:c in df.columns for c in ["ID","ESTATUS","TOTAL DE LA ORDEN","PRODUCTO","CANTIDAD","GANANCIA","PRECIO FLETE","PRECIO PROVEEDOR","COSTO DEVOLUCION FLETE","CIUDAD DESTINO","FECHA","GRUPO_PRODUCTO","PRECIO PROVEEDOR X CANTIDAD"]}

def count_statuses(df,F):
    """Count unique IDs per status category."""
    ne=nc=nv=nt=0
    if F.get("ESTATUS") and F.get("ID"):
        sid=df.drop_duplicates("ID")
        for _,r in sid.iterrows():
            s=str(r["ESTATUS"])
            if mss(s,STATUS_ENT): ne+=1
            elif mss(s,STATUS_CAN): nc+=1
            elif mss(s,STATUS_DEV): nv+=1
            else: nt+=1
    return ne,nc,nv,nt

def calc_kpis(df,F,gfb,gtt):
    no=df["ID"].nunique() if F.get("ID") else len(df)
    fb=df["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    dnc=df[~df["ESTATUS"].apply(lambda s:mss(s,STATUS_CAN))] if F.get("ESTATUS") else df
    fn=dnc["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    nd=dnc["ID"].nunique() if F.get("ID") else len(dnc)
    aov=fb/no if no>0 else 0;ga=gfb+gtt;roas=fn/ga if ga>0 else 0
    ne,nc,nv,nt=count_statuses(df,F)
    nnc=no-nc;pcan=(nc/no*100) if no>0 else 0;pent=(ne/nnc*100) if nnc>0 else 0
    # Financials
    de=df[df["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
    ir=de["TOTAL DE LA ORDEN"].sum() if not de.empty else 0
    cpr=de["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns) else ((de["PRECIO PROVEEDOR"]*de["CANTIDAD"]).sum() if not de.empty and F.get("PRECIO PROVEEDOR") and F.get("CANTIDAD") else 0)
    fle=de["PRECIO FLETE"].sum() if (not de.empty and F.get("PRECIO FLETE")) else 0
    # FIX #1: Flete devolucion
    dd=df[df["ESTATUS"].apply(lambda s:mss(s,STATUS_DEV))] if F.get("ESTATUS") else pd.DataFrame()
    fld=0
    if not dd.empty:
        if F.get("COSTO DEVOLUCION FLETE"): fld=dd.apply(calc_flete_dev,axis=1).sum()
        elif F.get("PRECIO FLETE"): fld=dd["PRECIO FLETE"].sum()
    # FIX #3: Fletes transito = ALL except entregado, cancelado, devolucion
    dt=df[df["ESTATUS"].apply(lambda s:is_transit(s))] if F.get("ESTATUS") else pd.DataFrame()
    flt=dt["PRECIO FLETE"].sum() if (not dt.empty and F.get("PRECIO FLETE")) else 0
    ur=ir-cpr-ga-fle-fld-flt
    return dict(n_ord=no,fact_bruto=fb,fact_neto=fn,n_desp=nd,aov=aov,g_fb=gfb,g_tt=gtt,g_ads=ga,roas=roas,n_ent=ne,n_can=nc,n_tra=nt,n_dev=nv,n_nov=0,n_otr=0,n_nc=nnc,pct_can=pcan,pct_ent=pent,tasa_ent=pent,ing_real=ir,cpr=cpr,fl_ent=fle,fl_dev=fld,fl_tra=flt,u_real=ur)

# FIX #5: P&L per product with logistics columns
def product_pnl(df,gc,F,lgxp):
    rows=[]
    for prod in df[gc].dropna().unique():
        dp=df[df[gc]==prod];nids=dp["ID"].nunique() if F.get("ID") else len(dp)
        ne,nc,nv,nt=count_statuses(dp,F);nnc=nids-nc
        de=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
        ir=de["TOTAL DE LA ORDEN"].sum() if not de.empty else 0
        cp=de["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns) else 0
        fe=de["PRECIO FLETE"].sum() if (not de.empty and F.get("PRECIO FLETE")) else 0
        dd=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_DEV))] if F.get("ESTATUS") else pd.DataFrame()
        fd=0
        if not dd.empty:
            if F.get("COSTO DEVOLUCION FLETE"): fd=dd.apply(calc_flete_dev,axis=1).sum()
            elif F.get("PRECIO FLETE"): fd=dd["PRECIO FLETE"].sum()
        dtr=dp[dp["ESTATUS"].apply(lambda s:is_transit(s))] if F.get("ESTATUS") else pd.DataFrame()
        ft=dtr["PRECIO FLETE"].sum() if (not dtr.empty and F.get("PRECIO FLETE")) else 0
        ap=lgxp.get(prod.upper(),0);ut=ir-cp-fe-fd-ft-ap
        rows.append(dict(Producto=prod,Ord=nids,Ent=ne,Can=nc,Dev=nv,Tra=nt,
            pEnt=f"{(ne/nnc*100):.0f}%" if nnc else "-",pCan=f"{(nc/nids*100):.0f}%" if nids else "-",
            pDev=f"{(nv/nnc*100):.0f}%" if nnc else "-",pTra=f"{(nt/nnc*100):.0f}%" if nnc else "-",
            Ingreso=ir,Costo=cp,FlEnt=fe,FlDev=fd,FlTra=ft,Ads=ap,Utilidad=ut))
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def calc_projection(df,gc,F,pe_dict,rb,lgxp):
    rows=[]
    for prod in df[gc].dropna().unique():
        dp=df[df[gc]==prod]
        if dp.empty: continue
        n_can=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_CAN))]["ID"].nunique() if F.get("ESTATUS") and F.get("ID") else 0
        n_ord=dp["ID"].nunique() if F.get("ID") else len(dp);n_nc=n_ord-n_can
        de=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
        n_ent_real=de["ID"].nunique() if (not de.empty and F.get("ID")) else 0
        ir_real=de["TOTAL DE LA ORDEN"].sum() if not de.empty else 0
        cp_real=de["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns) else 0
        fl_real=de["PRECIO FLETE"].sum() if (not de.empty and F.get("PRECIO FLETE")) else 0
        aov=ir_real/n_ent_real if n_ent_real else 0;cpoe=cp_real/n_ent_real if n_ent_real else 0;floe=fl_real/n_ent_real if n_ent_real else 0
        dnd=dp[~dp["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT)|mss(s,STATUS_CAN))] if F.get("ESTATUS") else pd.DataFrame()
        fl_nd_avg=dnd["PRECIO FLETE"].mean() if (not dnd.empty and F.get("PRECIO FLETE")) else floe
        pe=pe_dict.get(prod,80);proj_ent=n_nc*pe/100;proj_nent=n_nc-proj_ent
        ip=proj_ent*aov;cp_=proj_ent*cpoe;fl_ent=proj_ent*floe
        fl_rest=proj_nent*fl_nd_avg*rb if proj_nent>0 else 0
        ap=lgxp.get(prod.upper(),0);ut=ip-cp_-fl_ent-fl_rest-ap
        rows.append({"Producto":prod,"Órdenes":int(n_nc),"% Ent":int(pe),"Ingreso":round(ip),"Costo":round(cp_),"FlEnt":round(fl_ent),"FlResto":round(fl_rest),"Ads":round(ap),"Utilidad":round(ut)})
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def status_pill(s):
    s=s.upper()
    if "ENTREGADO" in s: return '<span class="pill p-ent">✅ Ent</span>'
    if "CANCELADO" in s or "RECHAZADO" in s: return '<span class="pill p-can">⊘ Can</span>'
    if "DEVOLUCION" in s or "DEVOLUCIÓN" in s: return '<span class="pill p-dev">↩ Dev</span>'
    if mss(s,STATUS_NOV): return '<span class="pill p-nov">⚠ Nov</span>'
    return '<span class="pill p-tra">🚚 Trá</span>'

def render_logistics(label,k,C_):
    no=k["n_ord"];nc=k["n_can"];ne=k["n_ent"];nt=k["n_tra"];nv=k["n_dev"];nnc=no-nc
    def p(n): return f"{(n/nnc*100):.0f}%" if nnc else "0%"
    return f"""<p class="section-hdr">{label} — {no:,}</p>
    <div class="lgrid"><div class="litem" style="border-color:rgba(239,68,68,0.3)"><p>❌ CAN/RECH</p><h3 style="color:{C_['loss']}">{nc:,}</h3><span class="badge" style="background:rgba(239,68,68,0.15);color:#EF4444">{(nc/no*100):.0f}% total</span></div></div>
    <div class="lgrid"><div class="litem" style="border-color:rgba(16,185,129,0.3)"><p>✅ ENTREGADO</p><h3 style="color:{C_['profit']}">{ne:,}</h3><span class="badge" style="background:rgba(16,185,129,0.15);color:#10B981">{p(ne)}</span></div><div class="litem" style="border-color:rgba(59,130,246,0.3)"><p>🚚 TRÁNSITO+</p><h3 style="color:{C_['blue']}">{nt:,}</h3><span class="badge" style="background:rgba(59,130,246,0.15);color:#3B82F6">{p(nt)}</span></div><div class="litem" style="border-color:rgba(245,158,11,0.3)"><p>↩ DEVOLUCIÓN</p><h3 style="color:{C_['warn']}">{nv:,}</h3><span class="badge" style="background:rgba(245,158,11,0.15);color:#F59E0B">{p(nv)}</span></div></div>"""

def dl_log(df,F,label,pats,key):
    if not F.get("ESTATUS"): return
    filt=df[df["ESTATUS"].apply(lambda s:mss(s,pats))]
    if not filt.empty: st.download_button(f"📥 {label} ({len(filt)})",to_excel(filt),file_name=f"{label.lower().replace(' ','_')}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key=key)

# Facebook/TikTok APIs
def fb_spend(tok,cid,i,f):
    if not tok or not cid: return 0.0
    cid=cid.strip()
    if not cid.startswith("act_"): cid=f"act_{cid}"
    try:
        r=requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"spend","level":"account"},timeout=30);d=r.json()
        if "data" in d and d["data"]: return float(d["data"][0].get("spend",0))
    except: pass
    return 0.0
def fb_camps_api(tok,cid,i,f):
    if not tok or not cid: return pd.DataFrame(columns=["campaign_name","spend"])
    cid=cid.strip()
    if not cid.startswith("act_"): cid=f"act_{cid}"
    try:
        r=requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"campaign_name,spend","level":"campaign","limit":500},timeout=30);d=r.json()
        if "data" in d: return pd.DataFrame([{"campaign_name":x.get("campaign_name",""),"spend":float(x.get("spend",0))} for x in d["data"]])
    except: pass
    return pd.DataFrame(columns=["campaign_name","spend"])
def fb_accts(tok):
    if not tok: return []
    try:
        r=requests.get("https://graph.facebook.com/v21.0/me/adaccounts",params={"access_token":tok,"fields":"name,account_id,currency","limit":50},timeout=15);d=r.json()
        if "data" in d: return [{"id":a.get("account_id",""),"name":a.get("name",""),"cur":a.get("currency","")} for a in d["data"]]
    except: pass
    return []
def tt_spend(tok,aid,i,f):
    if not tok or not aid: return 0.0
    try:
        r=requests.post("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",headers={"Access-Token":tok,"Content-Type":"application/json"},json={"advertiser_id":aid,"report_type":"BASIC","data_level":"AUCTION_ADVERTISER","dimensions":["advertiser_id"],"metrics":["spend"],"start_date":i,"end_date":f},timeout=30);d=r.json()
        if d.get("code")==0 and d.get("data",{}).get("list"): return float(d["data"]["list"][0]["metrics"].get("spend",0))
    except: pass
    return 0.0

def ai_map_testeo(camps_info,products_by_country,key):
    if not key: return {}
    prompt=f"""Empareja campañas Facebook con productos Dropi.
Formato: [PAÍS] - [PRODUCTO/TESTEO] - [FECHA]
CO/COL=Colombia, EC/ECU=Ecuador, GT/GUA=Guatemala
Si campaña tiene "TESTEO" -> asignar a "TESTEO CO"/"TESTEO EC"/"TESTEO GT"
Emparejar por PAÍS + similitud texto producto

Campañas: {json.dumps(camps_info,ensure_ascii=False)}
Productos: {json.dumps(products_by_country,ensure_ascii=False)}

Responde SOLO JSON: {{"campaña":"producto"}}"""
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":3000},timeout=45)
        txt=r.json()["choices"][0]["message"]["content"].strip();txt=re.sub(r'^```json\s*','',txt);txt=re.sub(r'```$','',txt)
        return json.loads(txt)
    except Exception as e: st.error(f"IA: {e}");return {}

# ═══ TRM ═══
trm=get_trm();trm_usd=trm.get("COP_USD",4200);trm_gtq=trm.get("COP_GTQ",540)

# ═══ SIDEBAR ═══
cfg=load_cfg()
with st.sidebar:
    st.markdown("### 📊 Dashboard v5.5")
    st.divider()
    usar_api=st.checkbox("Usar APIs",value=True)
    fb_token="";fb_cids=[];tt_token="";tt_aids=[]
    if usar_api:
        fb_token=st.text_input("Token FB",type="password",value=cfg.get("fb_token",""),key="fbt")
        if fb_token: save_cfg("fb_token",fb_token)
        accts=fb_accts(fb_token)
        if accts:
            opts={f"{a['name']} ({a['id']})":a["id"] for a in accts};ok=list(opts.keys())
            if st.checkbox("✅ Todas",key="sel_all"): fb_cids=[opts[k] for k in ok]
            else: fb_cids=[opts[l] for l in st.multiselect("Cuentas",ok,key="fb_ms")]
        else:
            v=st.text_input("IDs FB",value=cfg.get("fb_cids",""))
            if v: save_cfg("fb_cids",v);fb_cids=[x.strip() for x in v.split(",") if x.strip()]
        tt_token=st.text_input("Token TT",type="password",value=cfg.get("tt_token",""),key="ttt")
        tt_inp=st.text_input("IDs TT",value=cfg.get("tt_aids",""))
        if tt_token: save_cfg("tt_token",tt_token)
        if tt_inp: save_cfg("tt_aids",tt_inp);tt_aids=[x.strip() for x in tt_inp.split(",") if x.strip()]
        st.caption(f"TRM: 1 USD={trm_usd:,.0f} COP")
    ads_manual_sb={}
    if not usar_api:
        for pn in PAISES: ads_manual_sb[pn]=st.number_input(f"Ads {pn} ({PAISES[pn]['moneda']})",min_value=0.0,value=0.0,step=1000.0,key=f"gm_{pn}")
    st.divider()
    oai_key=st.text_input("🤖 OpenAI",type="password",value=cfg.get("oai_key",""),key="oai")
    if oai_key: save_cfg("oai_key",oai_key)

# ═══ INIT ═══
for pn in PAISES:
    for k in (f"_b_{pn}",f"_n_{pn}"):
        if k not in st.session_state: st.session_state[k]=None

# ═══ TITLE + QUICK DATES ═══
st.markdown('<p style="text-align:center;font-size:1.8rem;font-weight:800;color:#F1F5F9;margin-bottom:.5rem">📊 Ecommerce Profit Dashboard</p>',unsafe_allow_html=True)
hoy=datetime.today().date()
presets={"Hoy":(hoy,hoy),"Ayer":(hoy-timedelta(days=1),hoy-timedelta(days=1)),"Últimos 7 días":(hoy-timedelta(days=7),hoy),"Últimos 30 días":(hoy-timedelta(days=30),hoy),"Este mes":(hoy.replace(day=1),hoy),"Mes anterior":((hoy.replace(day=1)-timedelta(days=1)).replace(day=1),hoy.replace(day=1)-timedelta(days=1))}
pc1,pc2,pc3,pc4=st.columns([2,1,1,2])
with pc1: preset=st.selectbox("📅 Rango",list(presets.keys())+["Personalizado"],index=3,key="preset")
if preset=="Personalizado":
    with pc2: f_ini=st.date_input("Desde",value=hoy-timedelta(days=30),key="d_ini")
    with pc3: f_fin=st.date_input("Hasta",value=hoy,key="d_fin")
else: f_ini,f_fin=presets[preset]
with pc4: st.markdown(f'<div style="padding-top:1.6rem"><span style="color:{C["sub"]};font-size:.8rem">TRM: <b style="color:{C["text"]}">1 USD={trm_usd:,.0f} COP</b></span></div>',unsafe_allow_html=True)

any_data=any(st.session_state.get(f"_b_{pn}") for pn in PAISES)
if not any_data:
    st.divider()
    files=st.file_uploader("📁 Sube archivos",type=["csv","xlsx","xls"],accept_multiple_files=True,key="up_multi")
    if files:
        for f in files:
            td=cargar(f.getvalue(),f.name);det=detect_country(td)
            if det: st.session_state[f"_b_{det}"]=f.getvalue();st.session_state[f"_n_{det}"]=f.name;st.success(f"✅ {PAISES[det]['flag']} {det}")
            else: st.warning(f"⚠ {f.name}")
        if any(st.session_state.get(f"_b_{pn}") for pn in PAISES): st.rerun()
    for pn,pi in PAISES.items():
        f=st.file_uploader(f"{pi['flag']} {pn}",type=["csv","xlsx","xls"],key=f"up_m_{pn}")
        if f: st.session_state[f"_b_{pn}"]=f.getvalue();st.session_state[f"_n_{pn}"]=f.name;st.rerun()
    st.stop()

with st.sidebar:
    st.divider();st.markdown("##### 📁 Archivos")
    for pn,pi in PAISES.items():
        if st.session_state.get(f"_b_{pn}"):
            c1,c2=st.columns([3,1])
            with c1: st.caption(f"✅ {pi['flag']} {st.session_state[f'_n_{pn}']}")
            with c2:
                if st.button("🗑",key=f"del_{pn}"): st.session_state[f"_b_{pn}"]=None;st.session_state[f"_n_{pn}"]=None;st.rerun()
        f=st.file_uploader(f"{pi['flag']} {pn}",type=["csv","xlsx","xls"],key=f"up_sb_{pn}",label_visibility="collapsed")
        if f: st.session_state[f"_b_{pn}"]=f.getvalue();st.session_state[f"_n_{pn}"]=f.name;st.rerun()

# ═══ LOAD DATA ═══
si,sf=f_ini.strftime("%Y-%m-%d"),f_fin.strftime("%Y-%m-%d")
CD={};PM=lj(MAPPING_FILE);gxp={};gxp_local={}
all_camps=pd.DataFrame(columns=["campaign_name","spend"])
if usar_api:
    for c in fb_cids: all_camps=pd.concat([all_camps,fb_camps_api(fb_token,c,si,sf)])
if not all_camps.empty: all_camps=all_camps[all_camps["spend"]>0].copy()
camp_spend={c:all_camps[all_camps["campaign_name"]==c]["spend"].sum() for c in all_camps["campaign_name"].unique()} if not all_camps.empty else {}
if usar_api: gfb_cop=sum(fb_spend(fb_token,c,si,sf) for c in fb_cids);gtt_cop=sum(tt_spend(tt_token,a,si,sf) for a in tt_aids)
else: gfb_cop=sum(to_cop(ads_manual_sb.get(pn,0),PAISES[pn]["moneda"],trm) for pn in PAISES);gtt_cop=0
crl={};tr_=0
for pn in PAISES:
    if not st.session_state.get(f"_b_{pn}"): continue
    df_t=filtrar(cargar(st.session_state[f"_b_{pn}"],st.session_state[f"_n_{pn}"]),f_ini,f_fin)
    if not df_t.empty: crl[pn]=len(df_t);tr_+=len(df_t)
for pn in PAISES:
    if not st.session_state.get(f"_b_{pn}"): continue
    df_f=filtrar(cargar(st.session_state[f"_b_{pn}"],st.session_state[f"_n_{pn}"]),f_ini,f_fin)
    if df_f.empty: continue
    mon=PAISES[pn]["moneda"]
    if "PRODUCTO" in df_f.columns:
        sv=PM.get(pn,{});cp=sorted(df_f["PRODUCTO"].dropna().unique())
        if sv:
            cps=set(p.upper().strip() for p in cp);vsv={gn:[o for o in ors if o.upper().strip() in cps] for gn,ors in sv.items()};vsv={k:v for k,v in vsv.items() if v}
            df_f=apply_groups(df_f,vsv if vsv else {extraer_base(p):[p] for p in cp})
        else: ag={extraer_base(p):[p] for p in cp};df_f=apply_groups(df_f,ag);PM[pn]=ag;sj(MAPPING_FILE,PM)
    F=get_F(df_f)
    if usar_api:
        r_=crl.get(pn,0)/max(tr_,1);gfl=cop_to(gfb_cop*r_,mon,trm);gtl=cop_to(gtt_cop*r_,mon,trm);gfc=gfb_cop*r_;gtc=gtt_cop*r_
    else: gfl=ads_manual_sb.get(pn,0);gtl=0;gfc=to_cop(gfl,mon,trm);gtc=0
    kpis=calc_kpis(df_f,F,gfl,gtl);kpis["g_fb_cop"]=gfc;kpis["g_tt_cop"]=gtc;kpis["g_ads_cop"]=gfc+gtc
    CD[pn]={"df":df_f,"kpis":kpis,"F":F}
if not CD: st.warning("Sin datos.");st.stop()

# Product grouping - FIX #8: Bug DeltaGenerator
with st.expander("📦 Productos",expanded=False):
    for pn,cd in CD.items():
        if "PRODUCTO" not in cd["df"].columns: continue
        st.write(f"**{PAISES[pn]['flag']} {pn}**")  # FIX: usar st.write en lugar de st.markdown
        cp=sorted(cd["df"]["PRODUCTO"].dropna().unique());sv=PM.get(pn,{})
        cps=set(p.upper().strip() for p in cp);rows=[]
        for gn,ms_ in sv.items():
            for m in ms_:
                if m.upper().strip() in cps: rows.append({"Original":m,"Grupo":gn})
        if not rows:
            for p in cp: rows.append({"Original":p,"Grupo":extraer_base(p)})
        epg=st.data_editor(pd.DataFrame(rows),use_container_width=True,hide_index=True,key=f"pg_{pn}",num_rows="dynamic")
        if st.button(f"💾 {pn}",key=f"sp_{pn}"):
            ng=defaultdict(list)
            for _,r in epg.iterrows():
                o=str(r.get("Original","")).strip();g=str(r.get("Grupo","")).strip()
                if o and g: ng[g].append(o)
            PM[pn]=dict(ng);sj(MAPPING_FILE,PM);st.rerun()

# Campaign mapping
cm_saved=lj(CAMP_MAPPING_FILE)
if not all_camps.empty:
    cn=sorted(all_camps["campaign_name"].unique().tolist())
    with st.expander("🔗 Campañas → Productos",expanded=False):
        pbc={};all_prods=[]
        for pn2,cd2 in CD.items():
            gc2="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in cd2["df"].columns else ("PRODUCTO" if cd2["F"].get("PRODUCTO") else None)
            if gc2:
                pp=sorted(cd2["df"][gc2].dropna().unique().tolist());pbc[pn2]=pp
                for p in pp: all_prods.append((pn2,p))
        for pn2 in CD:
            tk=f"TESTEO {pn2.upper()[:2]}";pbc.setdefault(pn2,[])
            if tk not in pbc[pn2]: pbc[pn2].append(tk);all_prods.append((pn2,tk))
        if "cd" not in st.session_state: st.session_state["cd"]=dict(cm_saved)
        a1,a2=st.columns([1,3])
        with a1:
            if st.button("🪄 IA",key="ai"):
                if oai_key:
                    asgn=set()
                    for v in st.session_state["cd"].values(): asgn.update(v)
                    ci=[{"name":c,"spend":camp_spend.get(c,0),"country":parse_camp_country(c) or "?"} for c in cn if c not in asgn]
                    with st.spinner("IA..."):
                        res=ai_map_testeo(ci,pbc,oai_key)
                    if res:
                        for camp,prod in res.items():
                            st.session_state["cd"].setdefault(prod,[])
                            if camp not in st.session_state["cd"][prod]: st.session_state["cd"][prod].append(camp)
                        st.rerun()
        with a2:
            ta=sum(len(v) for v in st.session_state["cd"].values())
            st.caption(f"{len(cn)} camps · {ta} asignadas · {len(cn)-ta} sin")
        search=st.text_input("🔍",key="cs",placeholder="Filtrar...")
        for pn2,prod in all_prods:
            curr=st.session_state["cd"].get(prod,[])
            other=set()
            for k2,v2 in st.session_state["cd"].items():
                if k2!=prod: other.update(v2)
            avail=[c for c in cn if c not in other]
            if search: avail=[c for c in avail if search.upper() in c.upper()]
            opts=[f"{c} (${camp_spend.get(c,0):,.0f})" for c in avail]
            omap={f"{c} (${camp_spend.get(c,0):,.0f})":c for c in avail}
            defs=[f"{c} (${camp_spend.get(c,0):,.0f})" for c in curr if c in avail]
            sel=st.multiselect(f"{PAISES[pn2]['flag']} {prod}",opts,default=defs,key=f"cm_{pn2}_{prod}")
            st.session_state["cd"][prod]=[omap[s] for s in sel if s in omap]
        st.divider()
        asgn2=set()
        for v in st.session_state["cd"].values(): asgn2.update(v)
        un=[c for c in cn if c not in asgn2]
        if un:
            st.markdown(f"⚠️ **{len(un)} sin asignar:**")
            for c in un[:20]:
                st.caption(f"• {c} — ${camp_spend.get(c,0):,.0f}")
        if st.button("💾 Guardar",key="sc",type="primary"):
            cm_saved=dict(st.session_state["cd"]);sj(CAMP_MAPPING_FILE,cm_saved);st.success("✅");st.rerun()

    for prod,camps in cm_saved.items():
        tc=sum(camp_spend.get(c,0) for c in camps)
        if tc>0: gxp[prod.upper()]=tc
    for pn2 in CD:
        gxp_local[pn2]={};gc2="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in CD[pn2]["df"].columns else ("PRODUCTO" if CD[pn2]["F"].get("PRODUCTO") else None)
        if gc2:
            for prod in CD[pn2]["df"][gc2].dropna().unique():
                cv=gxp.get(prod.upper(),0)
                if cv>0: gxp_local[pn2][prod.upper()]=cop_to(cv,PAISES[pn2]["moneda"],trm)

# FIX #6: Manual ads per product per day - IMPROVED
manual_ads=lj(MANUAL_ADS_FILE)
with st.expander("📢 Publicidad Manual (por Producto/Día)",expanded=False):
    st.markdown("**Agrega gasto diario por producto** (TikTok manual, Google, etc)")
    
    # Selector de país
    ma_pn=st.selectbox("País",list(CD.keys()),format_func=lambda x:f"{PAISES[x]['flag']} {x}",key="ma_pn")
    gc_ma="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in CD[ma_pn]["df"].columns else ("PRODUCTO" if CD[ma_pn]["F"].get("PRODUCTO") else None)
    
    if gc_ma:
        prods_ma=[""] + sorted(CD[ma_pn]["df"][gc_ma].dropna().unique().tolist())
        
        # Cargar datos guardados
        saved_rows=manual_ads.get(ma_pn,[])
        
        # Preparar DataFrame
        if not saved_rows:
            saved_rows=[{"Producto":"","Fecha":hoy.strftime("%Y-%m-%d"),"Monto":0.0}]
        
        df_ma=pd.DataFrame(saved_rows)
        for c in ["Producto","Fecha","Monto"]:
            if c not in df_ma.columns:
                if c == "Producto": df_ma[c]=""
                elif c == "Fecha": df_ma[c]=hoy.strftime("%Y-%m-%d")
                else: df_ma[c]=0.0
        
        # Editor mejorado
        edited=st.data_editor(
            df_ma,
            column_config={
                "Producto":st.column_config.SelectboxColumn(
                    "Producto",
                    options=prods_ma,
                    required=True
                ),
                "Fecha":st.column_config.DateColumn(
                    "Fecha",
                    format="YYYY-MM-DD",
                    required=True
                ),
                "Monto":st.column_config.NumberColumn(
                    f"Monto ({PAISES[ma_pn]['moneda']})",
                    min_value=0,
                    step=100,
                    format="%.2f",
                    required=True
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="ma_ed"
        )
        
        col1, col2, col3 = st.columns([2,1,1])
        with col1:
            if st.button("💾 Guardar Ads Manual",key="ma_save",type="primary"):
                # Limpiar filas vacías
                clean_rows = []
                for _, row in edited.iterrows():
                    prod = str(row.get("Producto","")).strip()
                    fecha = row.get("Fecha","")
                    monto = float(row.get("Monto",0) or 0)
                    
                    if prod and fecha and monto > 0:
                        # Convertir fecha a string si es necesario
                        if isinstance(fecha, pd.Timestamp):
                            fecha = fecha.strftime("%Y-%m-%d")
                        clean_rows.append({
                            "Producto": prod,
                            "Fecha": str(fecha),
                            "Monto": monto
                        })
                
                manual_ads[ma_pn] = clean_rows
                sj(MANUAL_ADS_FILE, manual_ads)
                st.success(f"✅ Guardados {len(clean_rows)} registros")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Limpiar Todo",key="ma_clear"):
                manual_ads[ma_pn] = []
                sj(MANUAL_ADS_FILE, manual_ads)
                st.success("✅ Limpiado")
                st.rerun()
        
        # Mostrar resumen
        if saved_rows and len([r for r in saved_rows if r.get("Monto",0) > 0]) > 0:
            st.divider()
            st.caption("**📊 Resumen Actual:**")
            total_manual = sum(float(r.get("Monto",0) or 0) for r in saved_rows)
            prod_totals = {}
            for r in saved_rows:
                prod = r.get("Producto","")
                monto = float(r.get("Monto",0) or 0)
                if prod and monto > 0:
                    prod_totals[prod] = prod_totals.get(prod, 0) + monto
            
            st.metric(f"Total {PAISES[ma_pn]['moneda']}", f"{total_manual:,.2f}")
            if prod_totals:
                for prod, total in sorted(prod_totals.items(), key=lambda x: -x[1]):
                    st.caption(f"• {prod}: {PAISES[ma_pn]['sym']}{total:,.2f}")

# Apply manual ads to gxp_local - filtrando por fecha
for pn_m, rows_m in manual_ads.items():
    if pn_m not in CD: continue
    for row_m in rows_m:
        pr_m = str(row_m.get("Producto","")).upper().strip()
        mt = float(row_m.get("Monto",0) or 0)
        fecha_m = row_m.get("Fecha","")
        
        # Convertir fecha_m a datetime para comparar
        try:
            if isinstance(fecha_m, str):
                fecha_dt = pd.to_datetime(fecha_m).date()
            elif isinstance(fecha_m, pd.Timestamp):
                fecha_dt = fecha_m.date()
            else:
                continue
            
            # Solo agregar si la fecha está en el rango seleccionado
            if f_ini <= fecha_dt <= f_fin and pr_m and mt > 0:
                gxp_local.setdefault(pn_m, {})
                gxp_local[pn_m][pr_m] = gxp_local[pn_m].get(pr_m, 0) + mt
                cop_v = to_cop(mt, PAISES[pn_m]["moneda"], trm)
                gxp[pr_m] = gxp.get(pr_m, 0) + cop_v
        except:
            continue

# ═══ TABS ═══
def gcol(cd): return "GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in cd["df"].columns else ("PRODUCTO" if cd["F"].get("PRODUCTO") else None)
tn=["🏠 Dashboard","📊 Proyección Global"]
for pn in CD: tn.append(f"{PAISES[pn]['flag']} {pn}")
tn.append("📢 Publicidad");tabs=st.tabs(tn)

# ═══ DASHBOARD ═══
with tabs[0]:
    to=sum(cd["kpis"]["n_ord"] for cd in CD.values());tf=sum(to_cop(cd["kpis"]["fact_neto"],PAISES[p]["moneda"],trm) for p,cd in CD.items())
    ta=sum(cd["kpis"].get("g_ads_cop",0) for cd in CD.values());tu=sum(to_cop(cd["kpis"]["u_real"],PAISES[p]["moneda"],trm) for p,cd in CD.items());tr2=tf/ta if ta>0 else 0
    st.markdown(f'<p class="section-hdr">Total (COP)</p><div class="row2 r4"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{to:,}</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO</div><div class="val lg green">{fmt_cop(tf)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val lg red">{fmt_cop(ta)}</div></div><div class="kcard {"green" if tu>=0 else "red"}"><div class="icon {"g" if tu>=0 else "r"}">💰</div><div class="lbl">UTILIDAD</div><div class="val lg {"green" if tu>=0 else "red"}">{fmt_cop(tu)}</div><div class="sub">ROAS:{tr2:.2f}x</div></div></div>',unsafe_allow_html=True)
    
    # FIX #4: Chart with Facturación + Órdenes + Utilidad Real + Utilidad Proyectada
    ad=[]
    for pn,cd in CD.items():
        df_=cd["df"];mon_=PAISES[pn]["moneda"]
        if "FECHA" not in df_.columns: continue
        for dt_date,g in df_.groupby(df_["FECHA"].dt.date):
            fac=to_cop(g["TOTAL DE LA ORDEN"].sum(),mon_,trm)
            ords=g["ID"].nunique()
            de=g[g["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT))]
            u_r=de["TOTAL DE LA ORDEN"].sum()-de.get("PRECIO PROVEEDOR X CANTIDAD",pd.Series([0])).sum()-de["PRECIO FLETE"].sum() if not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns else 0
            ad.append({"Fecha":dt_date,"Fac":fac,"Ords":ords,"U_Real":to_cop(u_r,mon_,trm)})
    
    if ad:
        dg=pd.DataFrame(ad).groupby("Fecha").sum().reset_index()
        fig=go.Figure()
        fig.add_trace(go.Bar(x=dg["Fecha"],y=dg["Ords"],name="Órdenes",marker_color=C["blue"],opacity=.5,yaxis="y2"))
        fig.add_trace(go.Scatter(x=dg["Fecha"],y=dg["Fac"],name="Facturación",line=dict(color=C["profit"],width=2.5),fill="tozeroy",fillcolor="rgba(16,185,129,0.08)"))
        fig.add_trace(go.Scatter(x=dg["Fecha"],y=dg["U_Real"],name="Utilidad Real",line=dict(color=C["purple"],width=2,dash="dot")))
        # TODO: Agregar Utilidad Proyectada requiere cálculo más complejo por día
        fig.update_layout(**pl(title="FACTURACIÓN + ÓRDENES + UTILIDAD (COP)",yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)")))
        st.plotly_chart(fig,use_container_width=True,key="gf")
    
    st.divider()
    for pn,cd in CD.items():
        k=cd["kpis"];pi=PAISES[pn];uc="green" if k["u_real"]>=0 else "red"
        cn_=f'<span style="font-size:.65rem;color:#475569">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if pi["moneda"]!="COP" else ""
        st.markdown(f'<div class="row2 r4"><div class="kcard"><div class="icon w">📦</div><div class="lbl">{pi["flag"]} {pn.upper()}</div><div class="val lg white">{k["n_ord"]:,}</div><div class="sub">{k["n_ent"]} ent·{k["tasa_ent"]:.0f}%</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO</div><div class="val lg green">{fmt(k["fact_neto"],pn)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val md red">{fmt(k["g_ads"],pn)}</div>{cn_}</div><div class="kcard {uc}"><div class="icon {"g" if k["u_real"]>=0 else "r"}">💰</div><div class="lbl">UTILIDAD</div><div class="val lg {uc}">{fmt(k["u_real"],pn)}</div></div></div>',unsafe_allow_html=True)
    st.divider()
    gk={f:sum(cd["kpis"][f] for cd in CD.values()) for f in ["n_ord","n_ent","n_can","n_tra","n_dev"]}
    gk["n_nc"]=gk["n_ord"]-gk["n_can"]
    st.markdown(render_logistics("Global",gk,C),unsafe_allow_html=True)
    for pn,cd in CD.items():
        st.markdown(render_logistics(f"{PAISES[pn]['flag']} {pn}",cd["kpis"],C),unsafe_allow_html=True)
        dc1,dc2,dc3,dc4=st.columns(4)
        with dc1: dl_log(cd["df"],cd["F"],"Entregados",STATUS_ENT,f"de_{pn}")
        with dc2: dl_log(cd["df"],cd["F"],"Cancelados",STATUS_CAN,f"dc_{pn}")
        with dc3: dl_log(cd["df"],cd["F"],"Tránsito",STATUS_TRA_EXPLICIT,f"dt_{pn}")
        with dc4: dl_log(cd["df"],cd["F"],"Devolución",STATUS_DEV,f"dd_{pn}")

# ═══ PROYECCIÓN GLOBAL ═══
with tabs[1]:
    st.markdown('<p class="section-hdr">Proyección Global (COP)</p>',unsafe_allow_html=True)
    g_pe={};g_rb={}
    cc=st.columns(len(CD))
    for i,(pn,cd) in enumerate(CD.items()):
        with cc[i]:
            g_pe[pn]=st.slider(f"%Ent {PAISES[pn]['flag']}",50,100,80,key=f"gpe_{pn}")
            g_rb[pn]=st.number_input(f"Colchón {PAISES[pn]['flag']}",value=1.4,min_value=1.0,max_value=3.0,step=0.05,key=f"grb_{pn}")
    all_proj=[];proj_det={}
    for pn,cd in CD.items():
        gc_=gcol(cd)
        if not gc_: continue
        lgxp=gxp_local.get(pn,{});pe_d={p:g_pe[pn] for p in cd["df"][gc_].dropna().unique()}
        dfp=calc_projection(cd["df"],gc_,cd["F"],pe_d,g_rb[pn],lgxp)
        if not dfp.empty:
            dfp["País"]=f"{PAISES[pn]['flag']} {pn}";dfp["pn"]=pn
            dfp["I_COP"]=dfp["Ingreso"].apply(lambda v:to_cop(v,PAISES[pn]["moneda"],trm))
            dfp["U_COP"]=dfp["Utilidad"].apply(lambda v:to_cop(v,PAISES[pn]["moneda"],trm))
            all_proj.append(dfp);proj_det[pn]=dfp
    if all_proj:
        dfgp=pd.concat(all_proj);ti=dfgp["I_COP"].sum();tu2=dfgp["U_COP"].sum();to2=dfgp["Órdenes"].sum()
        st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{to2:,}</div></div><div class="kcard green"><div class="icon g">📊</div><div class="lbl">INGRESO</div><div class="val lg green">{fmt_cop(ti)}</div></div><div class="kcard {"green" if tu2>=0 else "red"}"><div class="icon {"g" if tu2>=0 else "r"}">📈</div><div class="lbl">UTILIDAD</div><div class="val lg {"green" if tu2>=0 else "red"}">{fmt_cop(tu2)}</div></div></div>',unsafe_allow_html=True)
        st.divider()
        sp=st.selectbox("País",list(proj_det.keys()),format_func=lambda x:f"{PAISES[x]['flag']} {x}",key="gpp")
        if sp in proj_det:
            dpd=proj_det[sp].sort_values("Utilidad",ascending=False)
            h="<tr>"+"".join(f"<th>{c}</th>" for c in ["Producto","Órd","%","Ingreso","Costo","FlEnt","FlResto","Ads","Utilidad"])+"</tr>";rb=""
            for _,r in dpd.iterrows():
                utc=C["profit"] if r["Utilidad"]>=0 else C["loss"]
                rb+=f'<tr><td>{r["Producto"]}</td><td>{int(r["Órdenes"])}</td><td>{int(r["% Ent"])}%</td><td class="mono">{fmt(r["Ingreso"],sp)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Costo"],sp)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["FlEnt"],sp)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["FlResto"],sp)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Ads"],sp)}</td><td class="mono" style="color:{utc}">{fmt(r["Utilidad"],sp)}</td></tr>'
            st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead>{h}</thead><tbody>{rb}</tbody></table></div>',unsafe_allow_html=True)

# ═══ COUNTRY TABS ═══
for idx,(pn,cd) in enumerate(CD.items()):
    with tabs[idx+2]:
        k=cd["kpis"];df_f=cd["df"];F=cd["F"];pi=PAISES[pn];gc_=gcol(cd);mon=PAISES[pn]["moneda"]
        prods=sorted(df_f[gc_].dropna().unique()) if gc_ else [];lgxp=gxp_local.get(pn,{})
        ct1,ct2,ct3,ct4=st.tabs(["🌡 Termómetro","📊 Proyecciones","💰 Operación","📋 Órdenes"])
        
        with ct1:
            at=f'<span style="font-size:.65rem;color:#475569">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if mon!="COP" else ""
            rc="green" if k["roas"]>=2 else ("red" if k["roas"]<1 else "white");tc="green" if k["tasa_ent"]>=60 else ("red" if k["tasa_ent"]<40 else "white")
            st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">💰</div><div class="lbl">BRUTO</div><div class="val lg white">{fmt(k["fact_bruto"],pn)}</div><div class="sub">{k["n_ord"]:,} órdenes</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">NETO</div><div class="val lg green">{fmt(k["fact_neto"],pn)}</div></div><div class="kcard"><div class="icon w">🛒</div><div class="lbl">AOV</div><div class="val lg white">{fmt(k["aov"],pn)}</div></div></div><div class="row2 r3"><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val lg red">{fmt(k["g_ads"],pn)}</div>{at}</div><div class="kcard"><div class="icon g">⚡</div><div class="lbl">ROAS</div><div class="val lg {rc}">{k["roas"]:.2f}x</div></div><div class="kcard"><div class="icon g">✅</div><div class="lbl">ENTREGA</div><div class="val lg {tc}">{k["tasa_ent"]:.0f}%</div></div></div>',unsafe_allow_html=True)
            
            if gc_ and F.get("FECHA"):
                pf=st.selectbox("Producto",["Todos"]+prods,key=f"pf_{pn}")
                dch=df_f if pf=="Todos" else df_f[df_f[gc_]==pf]
                dy=dch.groupby(dch["FECHA"].dt.date).agg(fac=("TOTAL DE LA ORDEN","sum"),ords=("ID","nunique")).reset_index();dy.columns=["Fecha","Fac","Ords"]
                g1,g2=st.columns(2)
                with g1:
                    fig=go.Figure();fig.add_trace(go.Bar(x=dy["Fecha"],y=dy["Ords"],name="Órdenes",marker_color=C["blue"],opacity=.5,yaxis="y2"));fig.add_trace(go.Scatter(x=dy["Fecha"],y=dy["Fac"],name="Facturación",line=dict(color=C["profit"],width=2),fill="tozeroy",fillcolor="rgba(16,185,129,0.1)"))
                    fig.update_layout(**pl(title="FAC+ÓRD",yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)")));st.plotly_chart(fig,use_container_width=True,key=f"fc_{pn}")
                with g2:
                    if F.get("ESTATUS"):
                        edf=dch["ESTATUS"].value_counts().reset_index();edf.columns=["E","N"]
                        cm_={s:(C["profit"] if "ENTREGADO" in s else C["loss"] if mss(s,STATUS_CAN) else C["warn"] if mss(s,STATUS_DEV) else C["blue"]) for s in edf["E"]}
                        f3=px.pie(edf,names="E",values="N",hole=.55,color="E",color_discrete_map=cm_);f3.update_layout(**pl(showlegend=True,title="ESTADOS"));f3.update_traces(textinfo="percent");st.plotly_chart(f3,use_container_width=True,key=f"pi_{pn}")
            
            st.markdown(render_logistics(f"{pi['flag']} {pn}",k,C),unsafe_allow_html=True)
            dc1,dc2,dc3,dc4=st.columns(4)
            with dc1: dl_log(df_f,F,"Entregados",STATUS_ENT,f"de2_{pn}")
            with dc2: dl_log(df_f,F,"Cancelados",STATUS_CAN,f"dc2_{pn}")
            with dc3: dl_log(df_f,F,"Tránsito",STATUS_TRA_EXPLICIT,f"dt2_{pn}")
            with dc4: dl_log(df_f,F,"Devolución",STATUS_DEV,f"dd2_{pn}")
            
            # FIX #7: Product summary — %Can over total, %E/%T/%D over non-cancelled
            if gc_:
                st.markdown('<p class="section-hdr">Resumen por Producto</p>',unsafe_allow_html=True)
                sb=st.selectbox("Ordenar",["Facturado","Pedidos","Ads","Entregados"],key=f"sb_{pn}");pr=[]
                for prod in prods:
                    dp=df_f[df_f[gc_]==prod]
                    if dp.empty: continue
                    np_=dp["ID"].nunique() if F.get("ID") else len(dp)
                    ne_,nc_,nv_,nt_=count_statuses(dp,F)
                    de_=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
                    fp_=de_["TOTAL DE LA ORDEN"].sum() if not de_.empty else 0;nnc_=np_-nc_;ap_=lgxp.get(prod.upper(),0)
                    pr.append({"Producto":prod,"Pedidos":np_,"Facturado":fp_,"Ent":ne_,"Can":nc_,"Tra":nt_,"Dev":nv_,"Ads":ap_,
                        "%E":f"{(ne_/nnc_*100):.0f}%" if nnc_ else "-","%C":f"{(nc_/np_*100):.0f}%" if np_ else "-",
                        "%T":f"{(nt_/nnc_*100):.0f}%" if nnc_ else "-","%D":f"{(nv_/nnc_*100):.0f}%" if nnc_ else "-"})
                if pr:
                    dfpr=pd.DataFrame(pr);sc_={"Facturado":"Facturado","Pedidos":"Pedidos","Ads":"Ads","Entregados":"Ent"}[sb];dfpr=dfpr.sort_values(sc_,ascending=False)
                    h="<tr>"+"".join(f"<th>{c}</th>" for c in ["Producto","Ped","Fact Ent","Ent","%E","Can","%C*","Trá","%T","Dev","%D","Ads"])+"</tr>";rb=""
                    for _,r in dfpr.iterrows():
                        rb+=f'<tr><td>{r["Producto"]}</td><td>{r["Pedidos"]}</td><td class="mono">{fmt(r["Facturado"],pn)}</td><td style="color:{C["profit"]}">{r["Ent"]}</td><td style="color:{C["profit"]}">{r["%E"]}</td><td style="color:{C["loss"]}">{r["Can"]}</td><td style="color:{C["loss"]}">{r["%C"]}</td><td style="color:{C["blue"]}">{r["Tra"]}</td><td style="color:{C["blue"]}">{r["%T"]}</td><td style="color:{C["warn"]}">{r["Dev"]}</td><td style="color:{C["warn"]}">{r["%D"]}</td><td class="mono" style="color:{C["loss"]}">{fmt(r["Ads"],pn)}</td></tr>'
                    st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead>{h}</thead><tbody>{rb}</tbody></table></div><p style="font-size:.7rem;color:{C["sub"]}">*%Can sobre total · %E/%T/%D sobre no-cancelados</p>',unsafe_allow_html=True)
        
        # Projections
        with ct2:
            if not gc_: st.warning("Sin productos.")
            else:
                s1,s2=st.columns(2)
                with s1: dg_=st.slider("% Entrega",50,100,80,key=f"dg_{pn}")
                with s2: rb_=st.number_input("Colchón",value=1.4,min_value=1.0,max_value=3.0,step=0.05,key=f"rb_{pn}")
                pek=f"pe_{pn}"
                if pek not in st.session_state: st.session_state[pek]={}
                pdg=st.session_state.get(f"pdg_{pn}",80)
                for p in prods:
                    if p not in st.session_state[pek]: st.session_state[pek][p]=float(dg_)
                    elif st.session_state[pek][p]==pdg: st.session_state[pek][p]=float(dg_)
                st.session_state[f"pdg_{pn}"]=dg_
                pf2=st.selectbox("Filtrar",["Todos"]+prods,key=f"pfp_{pn}");sb2=st.selectbox("Ordenar",["Utilidad","Ingreso","Órdenes"],key=f"sbp_{pn}")
                pe_d={p:st.session_state[pek].get(p,float(dg_)) for p in prods}
                src=df_f if pf2=="Todos" else df_f[df_f[gc_]==pf2]
                if pf2!="Todos": pe_d={pf2:pe_d.get(pf2,float(dg_))}
                dfp=calc_projection(src,gc_,F,pe_d,rb_,lgxp)
                if not dfp.empty:
                    sc__=sb2;dfp=dfp.sort_values(sc__,ascending=False)
                    ti=dfp["Ingreso"].sum();tu3=dfp["Utilidad"].sum()
                    st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{dfp["Órdenes"].sum():,}</div></div><div class="kcard green"><div class="icon g">📊</div><div class="lbl">INGRESO</div><div class="val lg green">{fmt(ti,pn)}</div></div><div class="kcard {"green" if tu3>=0 else "red"}"><div class="icon {"g" if tu3>=0 else "r"}">📈</div><div class="lbl">UTILIDAD</div><div class="val lg {"green" if tu3>=0 else "red"}">{fmt(tu3,pn)}</div></div></div>',unsafe_allow_html=True)
                    mx_p=max(dfp["Ingreso"].max(),1);bh=""
                    for _,r in dfp.iterrows():
                        ipp=min(r["Ingreso"]/mx_p*100,100);utp=min(max(r["Utilidad"],0)/mx_p*100,100);utc=C["profit"] if r["Utilidad"]>=0 else C["loss"]
                        bh+=f'<div style="margin-bottom:1.2rem"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="color:{C["text"]};font-weight:600">{r["Producto"]}</span><span style="color:{C["sub"]};font-size:.78rem">{int(r["Órdenes"])}·{int(r["% Ent"])}%</span></div><div style="display:flex;gap:8px;align-items:center"><div style="flex:1;background:#111827;border-radius:4px;height:22px;position:relative;overflow:hidden"><div style="width:{ipp:.0f}%;height:100%;background:rgba(16,185,129,0.2)"></div><div style="position:absolute;top:0;left:0;width:{utp:.0f}%;height:100%;background:{C["profit"]};opacity:.7"></div></div><span style="font-family:JetBrains Mono;font-size:.82rem;color:{utc};width:130px;text-align:right;font-weight:600">{fmt(r["Utilidad"],pn)}</span></div><div style="display:flex;gap:12px;margin-top:3px;font-size:.7rem;color:{C["sub"]}"><span>Ing:{fmt(r["Ingreso"],pn)}</span><span>Cst:-{fmt(r["Costo"],pn)}</span><span>FlE:-{fmt(r["FlEnt"],pn)}</span><span>FlR:-{fmt(r["FlResto"],pn)}</span><span>Ads:-{fmt(r["Ads"],pn)}</span></div></div>'
                    st.markdown(f'<div class="kcard" style="padding:1.5rem">{bh}</div>',unsafe_allow_html=True)
                    with st.expander("📝 Editar %"):
                        ed=st.data_editor(dfp[["Producto","% Ent"]],column_config={"% Ent":st.column_config.NumberColumn("%",min_value=0,max_value=100,step=1,format="%d")},use_container_width=True,hide_index=True,key=f"pt_{pn}")
                        if ed is not None:
                            for _,r in ed.iterrows(): st.session_state[pek][r["Producto"]]=r["% Ent"]
        
        # FIX #2: Operación con pie logístico
        with ct3:
            ir=k["ing_real"];cpr=k["cpr"];fe=k["fl_ent"];ga=k["g_ads"];fd=k["fl_dev"];ft_=k["fl_tra"];ur=k["u_real"];mg=(ur/ir*100) if ir>0 else 0;uc="green" if ur>=0 else "red"
            at2=f'<span style="font-size:.65rem;color:#475569">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if mon!="COP" else ""
            st.markdown(f'<div class="kcard {uc}" style="padding:2rem;margin-bottom:1.5rem"><div class="icon {"g" if ur>=0 else "r"}" style="width:48px;height:48px;font-size:1.3rem">💰</div><div class="lbl">UTILIDAD REAL</div><div class="val xl {uc}">{fmt(ur,pn)}</div><div class="pct">Margen:{mg:.1f}%</div></div><div class="row2 r3"><div class="kcard green"><div class="icon g">✅</div><div class="lbl">INGRESO</div><div class="val md green">{fmt(ir,pn)}</div></div><div class="kcard red"><div class="icon r">📦</div><div class="lbl">COSTO</div><div class="val md red">-{fmt(cpr,pn)}</div><div class="pct">{pof(cpr,ir)}</div></div><div class="kcard red"><div class="icon r">🚚</div><div class="lbl">FL ENT</div><div class="val md red">-{fmt(fe,pn)}</div><div class="pct">{pof(fe,ir)}</div></div></div><div class="row2 r3"><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val md red">-{fmt(ga,pn)}</div>{at2}<div class="pct">{pof(ga,ir)}</div></div><div class="kcard red"><div class="icon r">⚠️</div><div class="lbl">FL DEV</div><div class="val md red">-{fmt(fd,pn)}</div><div class="pct">{pof(fd,ir)}</div></div><div class="kcard"><div class="icon b">🚚</div><div class="lbl">FL TRÁ</div><div class="val md white">-{fmt(ft_,pn)}</div><div class="pct">{pof(ft_,ir)}</div></div></div>',unsafe_allow_html=True)
            
            # FIX #2: Pie charts - Agregando segundo pie logístico
            op1,op2=st.columns(2)
            with op1:
                ldat=[("Entregado",k["n_ent"],C["profit"]),("Can/Rech",k["n_can"],C["loss"]),("Devolución",k["n_dev"],C["warn"]),("Tránsito+",k["n_tra"],C["blue"])]
                ldf=pd.DataFrame([{"E":l,"N":n} for l,n,_ in ldat if n>0])
                if not ldf.empty:
                    fp=px.pie(ldf,names="E",values="N",hole=.55,color="E",color_discrete_map={l:c for l,_,c in ldat})
                    fp.update_layout(**pl(title="LOGÍSTICA",showlegend=True));fp.update_traces(textinfo="percent+value")
                    st.plotly_chart(fp,use_container_width=True,key=f"lp_{pn}")
            with op2:
                cdat=[("Ingreso",ir,C["profit"]),("Costo",cpr,C["loss"]),("Fl Ent",fe,C["warn"]),("Fl Dev",fd,C["orange"]),("Fl Trá",ft_,C["blue"]),("Ads",ga,C["purple"])]
                cdf=pd.DataFrame([{"Concepto":l,"Monto":n} for l,n,_ in cdat if n>0])
                if not cdf.empty:
                    fp2=px.pie(cdf,names="Concepto",values="Monto",hole=.55,color="Concepto",color_discrete_map={l:c for l,_,c in cdat})
                    fp2.update_layout(**pl(title="COSTOS",showlegend=True));fp2.update_traces(textinfo="percent")
                    st.plotly_chart(fp2,use_container_width=True,key=f"cp_{pn}")
            
            # Cascade
            cpf=st.selectbox("Cascada",["Todos"]+prods,key=f"cpf_{pn}") if gc_ else "Todos"
            c_ir,c_cpr,c_fe,c_ga,c_fd,c_ft=ir,cpr,fe,ga,fd,ft_
            if cpf!="Todos" and gc_:
                dp=df_f[df_f[gc_]==cpf]
                de=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_ENT))]
                c_ir=de["TOTAL DE LA ORDEN"].sum() if not de.empty else 0
                c_cpr=de["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns) else 0
                c_fe=de["PRECIO FLETE"].sum() if not de.empty else 0;c_ga=lgxp.get(cpf.upper(),0)
                dd=dp[dp["ESTATUS"].apply(lambda s:mss(s,STATUS_DEV))]
                if not dd.empty:
                    if F.get("COSTO DEVOLUCION FLETE"): c_fd=dd.apply(calc_flete_dev,axis=1).sum()
                    else: c_fd=dd["PRECIO FLETE"].sum()
                else: c_fd=0
                dtr=dp[dp["ESTATUS"].apply(lambda s:is_transit(s))];c_ft=dtr["PRECIO FLETE"].sum() if not dtr.empty else 0
            c_ur=c_ir-c_cpr-c_fe-c_ga-c_fd-c_ft
            items=[("Ingreso",c_ir,True),("Costo",c_cpr,False),("Fl Ent",c_fe,False),("Ads",c_ga,False),("Fl Dev",c_fd,False),("Fl Trá",c_ft,False)]
            mx_c=max(c_ir,1);ch=""
            for lb,vl,pos in items:
                bp=min(vl/mx_c*100,100);bc=C["profit"] if pos else C["loss"];sg="" if pos else "-"
                ch+=f'<div class="cas-row"><div class="cas-lbl">{lb}</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{bp:.0f}%;background:{bc}"></div></div><div class="cas-amt" style="color:{bc}">{sg}{fmt(vl,pn)}</div><div class="cas-pct">{pof(vl,c_ir)}</div></div>'
            up=min(abs(c_ur)/mx_c*100,100);ucol=C["profit"] if c_ur>=0 else C["loss"]
            st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem">{ch}<div style="border-top:2px solid #1E293B;margin:8px 0"></div><div class="cas-row" style="border-bottom:none"><div class="cas-lbl" style="font-weight:700;color:#F1F5F9">UTILIDAD</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{up:.0f}%;background:{ucol}"></div></div><div class="cas-amt" style="color:{ucol}">{"" if c_ur>=0 else "-"}{fmt(abs(c_ur),pn)}</div><div class="cas-pct" style="color:{ucol}">{pof(abs(c_ur),c_ir)}</div></div></div>',unsafe_allow_html=True)
            
            # FIX #5: P&L with logistics
            if gc_:
                st.markdown('<p class="section-hdr">P&L por Producto</p>',unsafe_allow_html=True)
                dpnl=product_pnl(df_f,gc_,F,lgxp)
                if not dpnl.empty:
                    dpnl=dpnl.sort_values("Ingreso",ascending=False)
                    h2="<tr>"+"".join(f"<th>{c}</th>" for c in ["Producto","Órd","Ent","%E","Can","%C*","Dev","%D","Trá","%T","Ingreso","Costo","FlE","FlD","FlT","Ads","Util","Mg"])+"</tr>";rb2=""
                    for _,r in dpnl.iterrows():
                        utc=C["profit"] if r["Utilidad"]>=0 else C["loss"];mg2=pof(r["Utilidad"],r["Ingreso"])
                        rb2+=f'<tr><td>{r["Producto"]}</td><td>{r["Ord"]}</td><td style="color:{C["profit"]}">{r["Ent"]}</td><td style="color:{C["profit"]}">{r["pEnt"]}</td><td style="color:{C["loss"]}">{r["Can"]}</td><td style="color:{C["loss"]}">{r["pCan"]}</td><td style="color:{C["warn"]}">{r["Dev"]}</td><td style="color:{C["warn"]}">{r["pDev"]}</td><td style="color:{C["blue"]}">{r["Tra"]}</td><td style="color:{C["blue"]}">{r["pTra"]}</td><td class="mono">{fmt(r["Ingreso"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Costo"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["FlEnt"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["FlDev"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["FlTra"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Ads"],pn)}</td><td class="mono" style="color:{utc}">{fmt(r["Utilidad"],pn)}</td><td style="color:{utc}">{mg2}</td></tr>'
                    st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead>{h2}</thead><tbody>{rb2}</tbody></table></div><p style="font-size:.7rem;color:{C["sub"]}">*%Can sobre total · %E/%D/%T sobre no-cancelados</p>',unsafe_allow_html=True)
        
        with ct4:
            cols=[c for c in ["ID","FECHA","PRODUCTO","CANTIDAD","TOTAL DE LA ORDEN","PRECIO FLETE","COSTO DEVOLUCION FLETE","CIUDAD DESTINO","ESTATUS"] if c in df_f.columns]
            if cols:
                dfo=df_f[cols].copy()
                if "FECHA" in dfo.columns: dfo=dfo.sort_values("FECHA",ascending=False)
                nr=len(dfo);hm={"ID":"ID","FECHA":"FECHA","PRODUCTO":"PROD","CANTIDAD":"Q","TOTAL DE LA ORDEN":"TOTAL","PRECIO FLETE":"FLETE","COSTO DEVOLUCION FLETE":"FL DEV","CIUDAD DESTINO":"CIUDAD","ESTATUS":"ESTADO"}
                hd="".join(f"<th>{hm.get(c,c)}</th>" for c in cols);ps=50;opk=f"op_{pn}"
                if opk not in st.session_state: st.session_state[opk]=0
                tp=max(1,(nr-1)//ps+1);s=st.session_state[opk]*ps;e=min(s+ps,nr);rh=""
                for _,row in dfo.iloc[s:e].iterrows():
                    td=""
                    for c in cols:
                        v=row[c]
                        if c=="FECHA": td+=f'<td>{v.strftime("%d %b") if pd.notna(v) else "-"}</td>'
                        elif c in ("TOTAL DE LA ORDEN","PRECIO FLETE","COSTO DEVOLUCION FLETE"): td+=f'<td class="mono">{fmt(v,pn)}</td>'
                        elif c=="ESTATUS": td+=f'<td>{status_pill(str(v))}</td>'
                        else: td+=f'<td>{v if pd.notna(v) else "-"}</td>'
                    rh+=f"<tr>{td}</tr>"
                st.markdown(f'<p class="section-hdr">Órdenes — {df_f["ID"].nunique():,} ({nr} líneas)</p><div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead><tr>{hd}</tr></thead><tbody>{rh}</tbody></table></div>',unsafe_allow_html=True)
                c1,c2,c3=st.columns([1,2,1])
                with c1:
                    if st.button("←",disabled=st.session_state[opk]==0,key=f"pv_{pn}"): st.session_state[opk]-=1;st.rerun()
                with c2: st.markdown(f'<p style="text-align:center;color:#64748B">{st.session_state[opk]+1}/{tp}</p>',unsafe_allow_html=True)
                with c3:
                    if st.button("→",disabled=st.session_state[opk]>=tp-1,key=f"nx_{pn}"): st.session_state[opk]+=1;st.rerun()
                st.download_button("📥 Todas",to_excel(df_f),file_name=f"ordenes_{pn.lower()}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key=f"da_{pn}")

# ═══ PUBLICIDAD ═══
with tabs[-1]:
    tfc=sum(cd["kpis"].get("g_fb_cop",0) for cd in CD.values());ttc=sum(cd["kpis"].get("g_tt_cop",0) for cd in CD.values());tac=tfc+ttc
    tmc=sum(to_cop(float(r.get("Monto",0) or 0),PAISES[p]["moneda"],trm) for p,rows in manual_ads.items() if p in PAISES for r in rows)
    tac+=tmc
    tp_=sum(cd["kpis"]["n_ord"] for cd in CD.values());te_=sum(cd["kpis"]["n_ent"] for cd in CD.values());cpo=tac/tp_ if tp_>0 else 0;cpe=tac/te_ if te_>0 else 0
    st.markdown(f'<p class="section-hdr">Publicidad</p><div class="row2 r4"><div class="kcard purple"><div class="icon p">📢</div><div class="lbl">TOTAL</div><div class="val lg purple">{fmt_cop(tac)}</div></div><div class="kcard blue"><div class="icon b">📘</div><div class="lbl">FB</div><div class="val lg blue">{fmt_cop(tfc)}</div></div><div class="kcard"><div class="icon w">🎵</div><div class="lbl">TT</div><div class="val lg white">{fmt_cop(ttc)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">CPA</div><div class="val lg red">{fmt_cop(cpo)}</div><div class="sub">Ent:{fmt_cop(cpe)}</div></div></div>',unsafe_allow_html=True)
    if tmc>0: st.markdown(f'<div class="kcard"><div class="lbl">MANUAL</div><div class="val md purple">{fmt_cop(tmc)}</div></div>',unsafe_allow_html=True)
    if gxp:
        pa=pd.DataFrame([{"Producto":k,"COP":v} for k,v in sorted(gxp.items(),key=lambda x:-x[1])]);fp_=px.bar(pa,x="Producto",y="COP",color_discrete_sequence=[C["purple"]]);fp_.update_layout(**pl(title="GASTO (COP)"));st.plotly_chart(fp_,use_container_width=True,key="ap")

st.divider()
st.markdown(f'<div style="text-align:center;color:#475569;font-size:.75rem">v5.5 · {sum(1 for p in PAISES if st.session_state.get(f"_b_{p}"))} países · {f_ini.strftime("%d/%m")}–{f_fin.strftime("%d/%m/%Y")}</div>',unsafe_allow_html=True)
