"""
Ecommerce Profit Dashboard v6.0 Ultimate
Premium UI (v5.2 visuals) + Robust Logic (v5.5 functionality)
Multi-File Landing · Cyclic Mapping · Auto-Testeo Grouping · Advanced HTML Tables
"""
import streamlit as st
import pandas as pd
import requests, json, os, re, io
from datetime import datetime, timedelta
from collections import defaultdict

# -----------------------------------------------------------------------------
# ⚙️ CONFIGURATION & SETUP
# -----------------------------------------------------------------------------
st.set_page_config(page_title="T-PILOT v6", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

try: import plotly.express as px; import plotly.graph_objects as go
except ImportError: import subprocess, sys; subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"]); import plotly.express as px; import plotly.graph_objects as go

PAISES = {
    "Colombia":  {"flag": "🇨🇴", "moneda": "COP", "sym": "$", "iso": "CO"},
    "Ecuador":   {"flag": "🇪🇨", "moneda": "USD", "sym": "$", "iso": "EC"},
    "Guatemala": {"flag": "🇬🇹", "moneda": "GTQ", "sym": "Q", "iso": "GT"},
}
SETTINGS_FILE = "dashboard_settings.json"
MAPPING_FILE = "product_mappings.json"
CAMPAIGN_MAP_FILE = "campaign_mappings.json"

# Colors Palette
C = dict(profit="#10B981", loss="#EF4444", warn="#F59E0B", blue="#3B82F6", purple="#8B5CF6", orange="#F97316", cyan="#06B6D4", muted="#64748B", text="#E2E8F0", sub="#94A3B8", grid="#1E293B", bg="#0B0F19")
STATUS_ENT=["ENTREGADO"]; STATUS_CAN=["CANCELADO"]; STATUS_DEV=["DEVOLUCION","DEVOLUCIÓN"]; STATUS_NOV=["NOVEDAD"]
STATUS_TRA=["TRANSITO","TRÁNSITO","EN RUTA","EN CAMINO","DESPACHADO","ENVIADO","PROCESADO","REPARTO"]

# -----------------------------------------------------------------------------
# 🎨 PREMIUM CSS STYLES (The "Pretty" Version)
# -----------------------------------------------------------------------------
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
.stApp { background:#0B0F19; color:#E2E8F0; font-family:'Inter',sans-serif; }
/* Sidebar & Inputs */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0F1420, #080C14) !important; border-right: 1px solid #1E293B; }
div[data-testid="stSelectbox"] > div > div, div[data-testid="stTextInput"] > div > div, div[data-testid="stNumberInput"] > div > div, .stDateInput > div > div > input { background-color: #1E293B !important; color: white !important; border: 1px solid #334155 !important; border-radius: 8px; }
/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: #111827; border-radius: 12px; padding: 4px; border: 1px solid #1E293B; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; color: #64748B; font-weight: 600; }
.stTabs [data-baseweb="tab"][aria-selected="true"] { background: #10B981; color: #0B0F19; }
/* Cards */
.kcard { background: linear-gradient(180deg, #131A2B, #0F1420); border: 1px solid #1E293B; border-radius: 16px; padding: 1.5rem; position: relative; transition: all 0.2s; overflow: hidden; }
.kcard:hover { border-color: rgba(16,185,129,0.4); } .kcard.green { border-color: rgba(16,185,129,0.3); } .kcard.red { border-color: rgba(239,68,68,0.3); }
.kcard .icon { position: absolute; top: 1.2rem; right: 1.2rem; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; opacity: 0.8; }
.icon.g { background: rgba(16,185,129,0.15); color: #10B981; } .icon.r { background: rgba(239,68,68,0.15); color: #EF4444; } .icon.b { background: rgba(59,130,246,0.15); color: #3B82F6; } .icon.w { background: rgba(148,163,184,0.15); color: #94A3B8; }
.kcard .lbl { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #64748B; margin-bottom: 0.5rem; }
.kcard .val { font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 1.8rem; }
.val.green { color: #10B981; } .val.red { color: #EF4444; } .val.white { color: #F1F5F9; }
.kcard .sub { font-size: 0.85rem; color: #94A3B8; margin-top: 4px; display: flex; gap: 8px; align-items: center; }
/* Tables & Pills */
.otbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.85rem; }
.otbl th { text-align: left; padding: 12px 16px; color: #64748B; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; background: #111827; border-bottom: 1px solid #1E293B; }
.otbl td { padding: 14px 16px; border-bottom: 1px solid rgba(15,20,32,0.8); color: #E2E8F0; vertical-align: middle; }
.otbl tr:hover td { background: #131A2B; } .mono { font-family: 'JetBrains Mono', monospace; }
.pill { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.p-ent { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.3); }
.p-can { background: rgba(239,68,68,0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.3); }
.p-tra { background: rgba(59,130,246,0.15); color: #3B82F6; border: 1px solid rgba(59,130,246,0.3); }
.p-dev { background: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.3); }
.p-pen { background: rgba(100,116,139,0.15); color: #94A3B8; border: 1px solid rgba(100,116,139,0.3); }
/* Thermometer & Grids */
.thermo { background: #111827; border: 1px solid #1E293B; border-radius: 16px; padding: 1.5rem; margin: 1rem 0; }
.thermo .bar { height: 14px; border-radius: 7px; background: linear-gradient(90deg, #EF4444 0%, #F59E0B 50%, #10B981 100%); position: relative; margin: 12px 0; }
.thermo .mk { position: absolute; top: -5px; width: 4px; height: 24px; background: #FFF; border-radius: 2px; box-shadow: 0 0 10px rgba(255,255,255,0.5); }
.row3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin-bottom: 1rem; }
.row4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 1rem; }
.section-hdr { font-size: 1.1rem; font-weight: 700; color: #E2E8F0; margin: 2rem 0 1rem; display: flex; align-items: center; gap: 8px; }
.section-hdr::before { content: ""; display: block; width: 4px; height: 18px; background: #10B981; border-radius: 2px; }
/* Cascade */
.cas-row { display: flex; align-items: center; padding: 12px 0; border-bottom: 1px solid rgba(30,41,59,0.5); }
.cas-lbl { width: 180px; font-size: 0.85rem; color: #94A3B8; display: flex; align-items: center; gap: 8px; }
.cas-bar-wrap { flex: 1; height: 28px; background: rgba(15,20,32,0.5); border-radius: 6px; overflow: hidden; margin: 0 16px; }
.cas-amt { width: 150px; text-align: right; font-family: 'JetBrains Mono'; font-weight: 600; }
.cas-pct { width: 70px; text-align: right; font-size: 0.75rem; color: #64748B; font-family: 'JetBrains Mono'; }
</style>""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 🛠️ HELPERS & LOGIC
# -----------------------------------------------------------------------------
def load_json(p): return json.load(open(p)) if os.path.exists(p) else {}
def save_json(p, d): json.dump(d, open(p, "w"), indent=2)
def load_cfg(): return load_json(SETTINGS_FILE)
def save_cfg(k, v): s=load_cfg(); s[k]=v; save_json(SETTINGS_FILE, s)
def load_mappings(): return load_json(MAPPING_FILE)
def save_mappings(d): save_json(MAPPING_FILE, d)

@st.cache_data(ttl=3600)
def get_trm():
    r={"COP_USD":4200,"COP_GTQ":540}
    try:
        req=requests.get("https://open.er-api.com/v6/latest/COP", timeout=5)
        if req.ok: d=req.json()["rates"]; r["COP_USD"]=1/d["USD"]; r["COP_GTQ"]=1/d["GTQ"]
    except: pass
    return r
trm=get_trm()
def convert_cop_to(v,t): return v/trm["COP_USD"] if t=="USD" else (v/trm["COP_GTQ"] if t=="GTQ" else v)
def fmt(v,p="Colombia"): return f"{PAISES.get(p,PAISES['Colombia'])['sym']} {v:,.0f}".replace(",",".")
def pof(p,w): return f"{(p/w*100):.1f}%" if w else "0%"
def pl(**kw):
    b=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(color=C["text"],family="Inter"),margin=dict(l=20,r=20,t=40,b=20),xaxis=dict(gridcolor=C["grid"]),yaxis=dict(gridcolor=C["grid"]))
    b.update(kw); return b
def ms(s,pats): return any(p in str(s).upper() for p in pats)
def status_pill(s):
    if ms(s, STATUS_ENT): return f'<span class="pill p-ent">✅ Entregado</span>'
    if ms(s, STATUS_CAN): return f'<span class="pill p-can">⊘ Cancelado</span>'
    if ms(s, STATUS_DEV): return f'<span class="pill p-dev">↩ Devolución</span>'
    if ms(s, STATUS_TRA): return f'<span class="pill p-tra">🚚 Tránsito</span>'
    return f'<span class="pill p-pen">⏳ Pendiente</span>'
def extraer_base(n):
    w=[x for x in re.sub(r'\s*-\s*',' ',str(n).strip().upper()).split() if not re.match(r'^\d+$',x) and x not in ("X","DE","EL","LA","EN","CON","PARA","POR")]
    return " ".join(w[:2]) if w else n

def detect_country(df):
    cols=df.columns.str.upper()
    if "CIUDAD DESTINO" in cols or "CIUDAD" in cols:
        col_city="CIUDAD DESTINO" if "CIUDAD DESTINO" in cols else "CIUDAD"
        cities=set(df[col_city].dropna().astype(str).str.upper().unique())
        co={"BOGOTA","MEDELLIN","CALI"}; ec={"QUITO","GUAYAQUIL","CUENCA"}; gt={"GUATEMALA","MIXCO","VILLA NUEVA"}
        sco=len(cities&co); sec=len(cities&ec); sgt=len(cities&gt)
        if sco>sec and sco>sgt: return "Colombia"
        if sec>sco and sec>sgt: return "Ecuador"
        if sgt>sco and sgt>sec: return "Guatemala"
    return None

@st.cache_data
def cargar_archivo(fb, ext):
    try:
        buf=io.BytesIO(fb)
        df=pd.read_excel(buf,dtype=str,engine="openpyxl") if ext in ["xlsx","xls"] else pd.read_csv(buf,dtype=str,encoding="latin-1",on_bad_lines="skip")
        df.columns=df.columns.str.strip().str.upper()
        cmap={"ID":["ID","ORDER ID"],"ESTATUS":["ESTATUS","STATUS","ESTADO"],"FECHA":["FECHA","DATE"],"PRODUCTO":["PRODUCTO","PRODUCT"],"CANTIDAD":["CANTIDAD","QTY"],"TOTAL DE LA ORDEN":["TOTAL","PRICE"],"PRECIO PROVEEDOR":["COSTO","COST"],"PRECIO FLETE":["FLETE","SHIPPING"],"COSTO DEVOLUCION FLETE":["COSTO DEVOLUCION","RETURN COST"],"CIUDAD DESTINO":["CIUDAD DESTINO","CITY","CIUDAD"],"GANANCIA":["GANANCIA","PROFIT"]}
        for s,vs in cmap.items():
            for v in vs:
                if v in df.columns and s not in df.columns: df.rename(columns={v:s},inplace=True); break
        for c in ["TOTAL DE LA ORDEN","PRECIO PROVEEDOR","PRECIO FLETE","COSTO DEVOLUCION FLETE","GANANCIA","CANTIDAD"]:
            if c in df.columns: df[c]=pd.to_numeric(df[c].astype(str).str.replace(r"[^\d.\-]","",regex=True),errors="coerce").fillna(0)
        if "FECHA" in df.columns: df["FECHA"]=pd.to_datetime(df["FECHA"],dayfirst=True,errors="coerce")
        return df
    except: return pd.DataFrame()

def fb_get_spend(tok, accs, d1, d2):
    if not tok or not accs: return pd.DataFrame()
    rows=[]; dr=json.dumps({"since":d1,"until":d2})
    for aid in accs:
        try:
            r=requests.get(f"https://graph.facebook.com/v21.0/act_{aid.replace('act_','')}/insights", params={"access_token":tok,"time_range":dr,"fields":"campaign_name,spend","level":"campaign","limit":1000}).json().get("data",[])
            for x in r: rows.append({"campaign_name":x.get("campaign_name","Unknown"),"spend":float(x.get("spend",0))})
        except: pass
    return pd.DataFrame(rows)

def process_data(df, start, end, country_name, g_ads_local, campaign_map):
    mask=(df["FECHA"]>=pd.Timestamp(start))&(df["FECHA"]<=pd.Timestamp(end)+pd.Timedelta(days=1))
    df=df[mask].copy(); 
    if df.empty: return None
    
    # Apply Grouping
    sv=PM.get(country_name,{})
    rv={o.upper().strip():gn for gn,ors in sv.items() for o in ors}
    if "PRODUCTO" in df.columns: df["GRUPO_PRODUCTO"]=df["PRODUCTO"].astype(str).str.upper().str.strip().map(rv).fillna(df["PRODUCTO"])

    agg_r={k:v for k,v in {"TOTAL DE LA ORDEN":"first","ESTATUS":"first","PRECIO FLETE":"first","COSTO DEVOLUCION FLETE":"first","GANANCIA":"sum","FECHA":"first","PRODUCTO":"first","CANTIDAD":"sum","PRECIO PROVEEDOR":"first","GRUPO_PRODUCTO":"first","CIUDAD DESTINO":"first"}.items() if k in df.columns}
    df_ord=df.groupby("ID").agg(agg_r).reset_index() if "ID" in df.columns else df
    
    st_c=df_ord["ESTATUS"].astype(str).str.upper().value_counts()
    def gc(k): return sum(st_c[x] for x in st_c.keys() if ms(x,k))
    n_ent=gc(STATUS_ENT); n_can=gc(STATUS_CAN); n_dev=gc(STATUS_DEV); n_tra=gc(STATUS_TRA); n_tot=len(df_ord)
    
    df_ent=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_ENT))].copy()
    ie=df_ent["TOTAL DE LA ORDEN"].sum(); cpe=(df_ent["PRECIO PROVEEDOR"]*df_ent["CANTIDAD"]).sum(); fe=df_ent["PRECIO FLETE"].sum()
    df_dev=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_DEV))]
    fd=df_dev[["PRECIO FLETE","COSTO DEVOLUCION FLETE"]].max(axis=1).sum() if "COSTO DEVOLUCION FLETE" in df_dev.columns else df_dev["PRECIO FLETE"].sum()
    ft=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_TRA))]["PRECIO FLETE"].sum()
    ur=ie-cpe-fe-fd-ft-g_ads_local
    
    psum=[]
    gcol="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in df_ord.columns else "PRODUCTO"
    if gcol in df_ord.columns:
        for p,sub in df_ord.groupby(gcol):
            ent=sub[sub["ESTATUS"].apply(lambda s:ms(s,STATUS_ENT))]
            psum.append({"Producto":p,"Pedidos":len(sub),"Facturado Entregado":ent["TOTAL DE LA ORDEN"].sum(),"Entregados":len(ent),"Costo_Total":(sub["PRECIO PROVEEDOR"]*sub["CANTIDAD"]).sum()})

    return {"orders":df_ord,"kpis":{"n_tot":n_tot,"n_ent":n_ent,"ing_ent":ie,"costo_prod":cpe,"flete_ent":fe,"flete_dev":fd,"flete_tra":ft,"ads":g_ads_local,"utilidad":ur},"prod_summary":pd.DataFrame(psum)}

# -----------------------------------------------------------------------------
# 💾 STATE & SIDEBAR
# -----------------------------------------------------------------------------
if "files_data" not in st.session_state: st.session_state.files_data={}
cfg=load_cfg(); PM=load_mappings()

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    with st.expander("🔑 Credenciales API", expanded=False):
        fb_tok=st.text_input("FB Token", value=cfg.get("fb_tok",""), type="password")
        if st.button("Guardar"): save_cfg("fb_tok", fb_tok); st.rerun()
    
    if fb_tok:
        accs=fb_get_accounts(fb_tok); amap={f"{a['name']} ({a['id']})":a['id'] for a in accs}
        if st.checkbox("✅ Seleccionar Todas"): st.session_state.sel_accs=list(amap.values())
        sel=st.multiselect("Cuentas Publicitarias", list(amap.keys()), key="ms_accs")
        if not st.session_state.get("sel_all_fb"): st.session_state.sel_accs=[amap[x] for x in sel]
    
    st.divider()
    st.markdown("### 📂 Archivos Cargados")
    for p,m in PAISES.items():
        if p in st.session_state.files_data:
            st.caption(f"✅ {m['flag']} {p}"); 
            if st.button(f"🗑️", key=f"d_{p}"): del st.session_state.files_data[p]; st.rerun()
    st.markdown("---")
    fa=st.file_uploader("Añadir archivo", type=["csv","xlsx"], key="fa")
    if fa:
        df=cargar_archivo(fa.getvalue(),fa.name.split('.')[-1]); det=detect_country(df)
        if det: st.session_state.files_data[det]=df; st.rerun()

# -----------------------------------------------------------------------------
# 🚀 LANDING PAGE
# -----------------------------------------------------------------------------
if not st.session_state.files_data:
    st.title("✈️ T-PILOT v6")
    st.info("Arrastra tus 3 archivos (Colombia, Ecuador, Guatemala) aquí. El sistema los detectará.")
    fls=st.file_uploader("Carga Múltiple", type=["csv","xlsx"], accept_multiple_files=True)
    if fls:
        for f in fls:
            df=cargar_archivo(f.getvalue(),f.name.split('.')[-1]); det=detect_country(df)
            if det: st.session_state.files_data[det]=df
        if st.session_state.files_data: st.rerun()
    st.stop()

# -----------------------------------------------------------------------------
# 📅 MAIN DASHBOARD
# -----------------------------------------------------------------------------
uploaded_data=st.session_state.files_data
c1,c2=st.columns([2,1])
with c1: st.markdown("## ✈️ T-PILOT DASHBOARD")
with c2:
    d1=st.date_input("Desde", datetime.today()-timedelta(days=30))
    d2=st.date_input("Hasta", datetime.today())
ds=d1.strftime("%Y-%m-%d"); de=d2.strftime("%Y-%m-%d")

# ADS & MAPPING
df_ads=pd.DataFrame()
if st.session_state.get("sel_accs") and fb_tok:
    with st.spinner("Conectando con Meta Ads..."): df_ads=fb_get_spend(fb_tok, st.session_state.sel_accs, ds, de)

if not df_ads.empty and uploaded_data:
    with st.expander("🔗 Mapeo de Campañas (Cíclico)", expanded=False):
        cm=load_json(CAMPAIGN_MAP_FILE); all_c=sorted(df_ads["campaign_name"].unique())
        unmapped=[c for c in all_c if c not in cm]; all_p=set()
        for df in uploaded_data.values(): 
            if "PRODUCTO" in df.columns: all_p.update(df["PRODUCTO"].dropna().unique())
        
        cl1,cl2,cl3=st.columns([2,2,1])
        with cl1: sc=st.selectbox("Campaña FB (Sin asignar)", [""]+unmapped)
        with cl2: sp=st.selectbox("Producto Dropi", [""]+sorted(list(all_p)))
        with cl3: 
            st.markdown("<br>",unsafe_allow_html=True)
            if st.button("🔗 Vincular") and sc and sp: cm[sc]=sp; save_json(CAMPAIGN_MAP_FILE,cm); st.rerun()
        
        if cm:
            st.markdown("##### Vínculos Activos")
            ml=[f"{k}  ➡️  {v}" for k,v in cm.items()]
            cd1,cd2=st.columns([3,1])
            with cd1: tu=st.selectbox("Selecciona para Liberar:", [""]+ml)
            with cd2:
                st.markdown("<br>",unsafe_allow_html=True)
                if st.button("🗑️ Liberar") and tu: del cm[tu.split("  ➡️  ")[0]]; save_json(CAMPAIGN_MAP_FILE,cm); st.rerun()

if uploaded_data:
    with st.expander("📦 Agrupación de Productos (Auto-Testeo)", expanded=False):
        for pn,df in uploaded_data.items():
            if "PRODUCTO" not in df.columns: continue
            st.markdown(f"**{PAISES[pn]['flag']} {pn}**")
            cp=sorted(df["PRODUCTO"].dropna().unique()); sv=PM.get(pn,{}); pc=df["PRODUCTO"].value_counts()
            rows=[]
            for p in cp:
                cg=""; found=False
                for gn,ors in sv.items():
                    if p.upper().strip() in [x.upper().strip() for x in ors]: cg=gn; found=True; break
                if not found: cg=f"TESTEO - {PAISES[pn]['iso']}" if pc.get(p,0)<5 else extraer_base(p)
                rows.append({"Original":p,"Grupo":cg})
            with st.form(key=f"f_pg_{pn}"):
                epg=st.data_editor(pd.DataFrame(rows),use_container_width=True,hide_index=True,num_rows="dynamic")
                if st.form_submit_button(f"💾 Guardar {pn}"):
                    ng=defaultdict(list)
                    for _,r in epg.iterrows():
                        if r["Original"] and r["Grupo"]: ng[r["Grupo"]].append(r["Original"])
                    PM[pn]=dict(ng); save_mappings(PM); st.rerun()

# TABS
tabs=st.tabs(list(uploaded_data.keys()))
for i,pn in enumerate(uploaded_data.keys()):
    with tabs[i]:
        df=uploaded_data[pn]; pi=PAISES[pn]
        cm=load_json(CAMPAIGN_MAP_FILE); gm=PM.get(pn,{})
        raw_to_group={r:g for g,rs in gm.items() for r in rs}
        if not df_ads.empty:
            df_ads["Group"]=df_ads["campaign_name"].map(cm).map(raw_to_group).fillna(df_ads["campaign_name"].map(cm)).fillna("Otros")
            pid=df["GRUPO_PRODUCTO"].unique() if "GRUPO_PRODUCTO" in df.columns else df["PRODUCTO"].unique()
            ads_c=df_ads[df_ads["Group"].isin(pid)]
            g_ads=convert_cop_to(ads_c["spend"].sum(), pi["moneda"])
        else: g_ads=0, ads_c=pd.DataFrame()
        
        data=process_data(df, ds, de, pn, g_ads, cm)
        if not data: st.warning("Sin datos en este rango."); continue
        k=data["kpis"]; dfo=data["orders"]; dfp=data["prod_summary"]
        
        t1,t2,t3,t4=st.tabs(["🌡 Termómetro","📊 Proyecciones","💰 Operación Real","📋 Órdenes"])
        
        with t1: # TERMÓMETRO PREMIUM
            st.markdown(f'<div class="row3"><div class="kcard"><div class="icon w">📦</div><div class="lbl">PEDIDOS TOTALES</div><div class="val white">{k["n_tot"]:,}</div><div class="sub">Entregados: {k["n_ent"]}</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO BRUTO</div><div class="val green">{fmt(dfo["TOTAL DE LA ORDEN"].sum(),pn)}</div></div><div class="kcard red"><div class="icon r">📢</div><div class="lbl">GASTO ADS</div><div class="val red">{fmt(k["ads"],pn)}</div></div></div>',unsafe_allow_html=True)
            roas=k["ing_ent"]/k["ads"] if k["ads"]>0 else 0; rp=min(roas/4*100,100)
            st.markdown(f'<div class="thermo"><div style="display:flex;justify-content:space-between;margin-bottom:10px"><span style="color:#94A3B8;font-weight:600">ROAS REAL (Entregado)</span><span style="font-family:JetBrains Mono;font-weight:700;font-size:1.2rem;color:#E2E8F0">{roas:.2f}x</span></div><div class="bar"><div class="mk" style="left:{rp:.0f}%"></div></div><div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#64748B"><span>0x</span><span>2x</span><span>4x+</span></div></div>',unsafe_allow_html=True)
            st.markdown('<div class="section-hdr">Logística</div>',unsafe_allow_html=True)
            c1,c2,c3,c4=st.columns(4)
            c1.metric("✅ Entregado", f"{k['n_ent']} ({pof(k['n_ent'],k['n_tot'])})"); c2.metric("🚚 Tránsito", f"{k['n_tra']} ({pof(k['n_tra'],k['n_tot'])})")
            c3.metric("↩️ Devolución", f"{k['n_dev']} ({pof(k['n_dev'],k['n_tot'])})"); c4.metric("❌ Cancelado", f"{k['n_can']} ({pof(k['n_can'],k['n_tot'])})")

        with t2: # PROYECCIONES VISUALES
            st.markdown('<div class="section-hdr">Simulador de Rentabilidad</div>',unsafe_allow_html=True)
            if not dfp.empty:
                c1,c2=st.columns(2)
                pe=c1.slider("% Entrega Esperado",50,100,85,key=f"pe_{pn}")/100; col=c2.slider("Factor Colchón Dev.",1.0,2.0,1.4,key=f"co_{pn}")
                dfp["Ped_Proy"]=(dfp["Pedidos"]*pe).astype(int); dfp["Tkt"]=dfp["Facturado Entregado"]/dfp["Entregados"].replace(0,1)
                dfp["Ing_Proy"]=dfp["Ped_Proy"]*dfp["Tkt"]; mx=dfp["Ing_Proy"].max()
                rh=""
                for _,r in dfp.iterrows():
                    bp=min(r["Ing_Proy"]/mx*100,100)
                    rh+=f'<div style="margin-bottom:1rem"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-weight:600">{r["Producto"]}</span><span style="color:#94A3B8;font-size:0.8rem">{r["Ped_Proy"]} ped. proy.</span></div><div style="background:#111827;height:24px;border-radius:12px;overflow:hidden;display:flex;align-items:center"><div style="width:{bp:.0f}%;height:100%;background:rgba(16,185,129,0.3);border-radius:12px"></div><span style="margin-left:10px;font-family:JetBrains Mono;font-size:0.85rem;color:#10B981">{fmt(r["Ing_Proy"],pn)}</span></div></div>'
                st.markdown(f'<div class="kcard">{rh}</div>',unsafe_allow_html=True)

        with t3: # OPERACIÓN REAL PREMIUM
            st.markdown(f'<div class="row3"><div class="kcard green"><div class="icon g">💰</div><div class="lbl">INGRESO REAL (COBRADO)</div><div class="val green">{fmt(k["ing_ent"],pn)}</div></div><div class="kcard {"green" if k["utilidad"]>0 else "red"}"><div class="icon {"g" if k["utilidad"]>0 else "r"}">📈</div><div class="lbl">UTILIDAD NETA FINAL</div><div class="val {"green" if k["utilidad"]>0 else "red"}">{fmt(k["utilidad"],pn)}</div><div class="sub">Margen: {pof(k["utilidad"],k["ing_ent"])}</div></div><div class="kcard red"><div class="icon r">📢</div><div class="lbl">GASTO ADS TOTAL</div><div class="val red">{fmt(k["ads"],pn)}</div></div></div>',unsafe_allow_html=True)
            st.markdown('<div class="section-hdr">Cascada Financiera</div>',unsafe_allow_html=True)
            items=[("Ingreso Entregado",k["ing_ent"],1),("Costo Producto",k["costo_prod"],0),("Publicidad (Ads)",k["ads"],0),("Fletes Ida",k["flete_ent"],0),("Fletes Devolución",k["flete_dev"],0),("Fletes Tránsito",k["flete_tra"],0)]
            mx=k["ing_ent"]; rh=""
            for lb,v,pos in items:
                bp=min(v/mx*100,100); bc=C["profit"] if pos else C["loss"]; sg="" if pos else "-"
                rh+=f'<div class="cas-row"><div class="cas-lbl"><span style="color:{bc}">{"●" if pos else "🔻"}</span>{lb}</div><div class="cas-bar-wrap"><div style="width:{bp:.0f}%;height:100%;background:{bc}"></div></div>div class="cas-amt" style="color:{bc}">{sg}{fmt(v,pn)}</div><div class="cas-pct">{pof(v,mx)}</div></div>'
            uc=C["profit"] if k["utilidad"]>0 else C["loss"]
            st.markdown(f'<div class="kcard" style="padding:1rem 2rem">{rh}<div style="border-top:2px solid #1E293B;margin:12px 0"></div><div class="cas-row" style="border:none"><div class="cas-lbl" style="font-weight:700;color:#F1F5F9;font-size:1rem">UTILIDAD FINAL</div><div style="flex:1"></div><div class="cas-amt" style="color:{uc};font-size:1.2rem">{fmt(k["utilidad"],pn)}</div><div class="cas-pct" style="color:{uc};font-weight:700">{pof(k["utilidad"],mx)}</div></div></div>',unsafe_allow_html=True)

            st.markdown('<div class="section-hdr">Detalle por Producto</div>',unsafe_allow_html=True)
            if not dfp.empty and not ads_c.empty:
                adsp=ads_c.groupby("Group")["spend"].sum().reset_index().rename(columns={"Group":"Producto","spend":"Ads_COP"})
                df_fin=pd.merge(dfp,adsp,on="Producto",how="left").fillna(0)
                df_fin["Ads"]=df_fin["Ads_COP"].apply(lambda x:convert_cop_to(x,pi["moneda"]))
                df_fin["ROAS"]=df_fin.apply(lambda x:x["Facturado Entregado"]/x["Ads"] if x["Ads"]>0 else 0, axis=1)
                rh="<thead><tr><th>Producto</th><th>Ped.</th><th>Fact. Ent.</th><th>Ads</th><th>ROAS</th></tr></thead><tbody>"
                for _,r in df_fin.sort_values("Facturado Entregado",ascending=False).iterrows():
                    rc=C["profit"] if r["ROAS"]>=2 else (C["loss"] if r["ROAS"]<1 else C["text"])
                    rh+=f'<tr><td style="font-weight:600">{r["Producto"]}</td><td>{r["Pedidos"]}</td><td class="mono" style="color:{C["profit"]}">{fmt(r["Facturado Entregado"],pn)}</td><td class="mono" style="color:{C["loss"]}">{fmt(r["Ads"],pn)}</td><td class="mono" style="color:{rc};font-weight:700">{r["ROAS"]:.2f}x</td></tr>'
                st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl">{rh}</tbody></table></div>',unsafe_allow_html=True)

        with t4: # ÓRDENES PREMIUM
            st.markdown(f'<div class="section-hdr">Listado de Pedidos ({len(dfo)})</div>',unsafe_allow_html=True)
            cols=[c for c in ["ID","FECHA","ESTATUS","PRODUCTO","TOTAL DE LA ORDEN","CIUDAD DESTINO"] if c in dfo.columns]
            if cols:
                dfo=dfo.sort_values("FECHA",ascending=False)
                pg=st.session_state.get(f"p_{pn}",0); ps=50; tot_p=(len(dfo)-1)//ps+1; start=pg*ps; end=start+ps
                rh="<thead><tr>"+"".join(f"<th>{c.replace('TOTAL DE LA ORDEN','TOTAL')}</th>" for c in cols)+"</tr></thead><tbody>"
                for _,r in dfo.iloc[start:end].iterrows():
                    rd=""
                    for c in cols:
                        v=r[c]
                        if c=="ESTATUS": rd+=f'<td>{status_pill(v)}</td>'
                        elif c in ["TOTAL DE LA ORDEN"]: rd+=f'<td class="mono">{fmt(v,pn)}</td>'
                        elif c=="FECHA": rd+=f'<td>{v.strftime("%Y-%m-%d")}</td>'
                        elif c=="ID": rd+=f'<td class="mono" style="color:{C["sub"]}">{v}</td>'
                        else: rd+=f'<td>{v}</td>'
                    rh+=f"<tr>{rd}</tr>"
                st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl">{rh}</tbody></table></div>',unsafe_allow_html=True)
                c1,c2,c3=st.columns([1,2,1])
                if c1.button("← Anterior", disabled=pg==0, key=f"b1_{pn}"): st.session_state[f"p_{pn}"]-=1; st.rerun()
                c2.markdown(f"<div style='text-align:center;padding-top:8px'>Página {pg+1} de {tot_p}</div>",unsafe_allow_html=True)
                if c3.button("Siguiente →", disabled=pg==tot_p-1, key=f"b2_{pn}"): st.session_state[f"p_{pn}"]+=1; st.rerun()

st.markdown("<br><center style='color:#64748B;font-size:0.8rem'>T-PILOT v6.0 Ultimate · Premium UI + Robust Logic</center>", unsafe_allow_html=True)
