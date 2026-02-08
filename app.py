"""
Ecommerce Profit Dashboard v4.3
Multi-Country · Dark Finance · Dropi + Facebook + TikTok
Currency Conversion · AI Campaign Mapping
"""
import streamlit as st
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.express as px
    import plotly.graph_objects as go

import requests, json, os, re
from datetime import datetime, timedelta
from collections import defaultdict

st.set_page_config(page_title="Profit Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

PAISES = {
    "Colombia":  {"flag": "🇨🇴", "moneda": "COP", "sym": "$"},
    "Ecuador":   {"flag": "🇪🇨", "moneda": "USD", "sym": "$"},
    "Guatemala": {"flag": "🇬🇹", "moneda": "GTQ", "sym": "Q"},
}
SETTINGS_FILE = "dashboard_settings.json"
MAPPING_FILE = "product_mappings.json"
CAMP_MAPPING_FILE = "campaign_mappings.json"
C = dict(profit="#10B981", loss="#EF4444", warn="#F59E0B", blue="#3B82F6",
         purple="#8B5CF6", orange="#F97316", cyan="#06B6D4", muted="#64748B",
         text="#E2E8F0", sub="#94A3B8", grid="#1E293B", bg="#0B0F19")

STATUS_ENT = ["ENTREGADO"]
STATUS_CAN = ["CANCELADO"]
STATUS_TRA = ["EN TRANSITO", "EN TRÁNSITO", "EN ESPERA DE RUTA DOMESTICA", "DESPACHADA", "DESPACHADO",
              "ENVIADO", "EN REPARTO", "EN RUTA", "EN BODEGA TRANSPORTADORA", "EN BODEGA DESTINO",
              "GUIA IMPRESA", "EN ALISTAMIENTO", "EN CAMINO", "ESPERANDO RUTA"]
STATUS_DEV = ["DEVOLUCION", "DEVOLUCIÓN", "EN DEVOLUCION", "EN DEVOLUCIÓN"]
STATUS_NOV = ["NOVEDAD", "CON NOVEDAD"]

def match_status(s, patterns):
    s = s.upper().strip()
    return any(p in s for p in patterns)

def pl(**kw):
    b = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             font=dict(family="Inter,system-ui,sans-serif", color=C["text"], size=12),
             xaxis=dict(gridcolor=C["grid"], zerolinecolor=C["grid"]),
             yaxis=dict(gridcolor=C["grid"], zerolinecolor=C["grid"]),
             margin=dict(l=40, r=20, t=50, b=40),
             legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=C["sub"])))
    b.update(kw); return b


# ═══════════════════════ CSS ═══════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#0B0F19!important;color:#E2E8F0!important;font-family:'Inter',system-ui,sans-serif!important}
header[data-testid="stHeader"]{background:#0B0F19!important}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0F1420,#080C14)!important;border-right:1px solid #1E293B!important}
section[data-testid="stSidebar"] *{color:#E2E8F0!important}
section[data-testid="stSidebar"] .stSelectbox>div>div,section[data-testid="stSidebar"] .stTextInput>div>div>input,section[data-testid="stSidebar"] .stDateInput>div>div>input,section[data-testid="stSidebar"] .stNumberInput>div>div>input,section[data-testid="stSidebar"] .stMultiSelect>div>div{background:#1E293B!important;border-color:#334155!important;color:#E2E8F0!important;border-radius:.5rem!important}
section[data-testid="stSidebar"] .stFileUploader>div{background:#111827!important;border:1px dashed #334155!important;border-radius:.75rem!important}
.stTabs [data-baseweb="tab-list"]{background:#111827!important;border-radius:.75rem!important;padding:4px!important;gap:4px!important;border:1px solid #1E293B!important}
.stTabs [data-baseweb="tab"]{border-radius:.5rem!important;color:#64748B!important;font-weight:500!important;padding:8px 16px!important}
.stTabs [data-baseweb="tab"][aria-selected="true"]{background:#10B981!important;color:#0B0F19!important;font-weight:600!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none!important}
div[data-testid="stMetric"]{display:none!important}
[data-testid="stExpander"]{border:1px solid #1E293B!important;border-radius:.75rem!important;background:#111827!important}
.stButton>button{background:linear-gradient(135deg,#10B981,#059669)!important;color:#0B0F19!important;border:none!important;border-radius:.5rem!important;font-weight:600!important}
.stButton>button:hover{box-shadow:0 0 20px rgba(16,185,129,0.3)!important}
hr{border-color:#1E293B!important}
[data-testid="stAlert"]{background:#111827!important;border:1px solid #1E293B!important;border-radius:.75rem!important;color:#E2E8F0!important}
.stMultiSelect>div>div{background:#1E293B!important;border-color:#334155!important;border-radius:.5rem!important}
[data-testid="stSlider"] label{color:#E2E8F0!important}
[data-testid="stDataFrame"]{border-radius:.75rem!important;overflow:hidden!important}
[data-testid="stCheckbox"] label span{color:#E2E8F0!important}
[data-testid="stFileUploader"]>div{background:#111827!important;border:1px dashed #334155!important;border-radius:.75rem!important}
[data-testid="stDateInput"]>div>div>input{background:#1E293B!important;border-color:#334155!important;color:#E2E8F0!important;border-radius:.5rem!important}
.kcard{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.3rem 1.5rem;position:relative;overflow:hidden;transition:all .2s}
.kcard:hover{border-color:rgba(16,185,129,0.4);box-shadow:0 0 20px rgba(16,185,129,0.08)}
.kcard.green{border-color:rgba(16,185,129,0.3)}.kcard.red{border-color:rgba(239,68,68,0.3)}.kcard.blue{border-color:rgba(59,130,246,0.3)}.kcard.purple{border-color:rgba(139,92,246,0.3)}
.kcard .icon{position:absolute;top:1.2rem;right:1.2rem;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1rem;opacity:.7}
.kcard .icon.g{background:rgba(16,185,129,0.15);color:#10B981}.kcard .icon.r{background:rgba(239,68,68,0.15);color:#EF4444}.kcard .icon.b{background:rgba(59,130,246,0.15);color:#3B82F6}.kcard .icon.w{background:rgba(148,163,184,0.15);color:#94A3B8}.kcard .icon.p{background:rgba(139,92,246,0.15);color:#8B5CF6}
.kcard .lbl{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#64748B;margin-bottom:.35rem}
.kcard .val{font-family:'JetBrains Mono',monospace;font-weight:700;margin-bottom:.15rem}
.kcard .val.xl{font-size:2rem}.kcard .val.lg{font-size:1.6rem}.kcard .val.md{font-size:1.3rem}
.kcard .val.green{color:#10B981}.kcard .val.red{color:#EF4444}.kcard .val.white{color:#F1F5F9}.kcard .val.blue{color:#3B82F6}.kcard .val.purple{color:#8B5CF6}
.kcard .sub{font-size:.78rem;color:#64748B}
.kcard .trm{font-size:.65rem;color:#475569;font-family:'JetBrains Mono',monospace}
.kcard .pct{font-size:.72rem;color:#94A3B8;font-family:'JetBrains Mono',monospace;margin-top:2px}
.row2{display:grid;gap:1rem;margin-bottom:1rem}.r2{grid-template-columns:1fr 1fr}.r3{grid-template-columns:1fr 1fr 1fr}.r4{grid-template-columns:1fr 1fr 1fr 1fr}.r5{grid-template-columns:1fr 1fr 1fr 1fr 1fr}
.section-hdr{font-size:1.05rem;font-weight:700;color:#E2E8F0;border-left:3px solid #10B981;padding-left:12px;margin:1.5rem 0 1rem}
.cas-row{display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #111827}.cas-row:last-child{border-bottom:none}
.cas-lbl{width:170px;font-size:.82rem;color:#94A3B8;flex-shrink:0}.cas-bar-wrap{flex:1;height:26px;position:relative;margin:0 16px}
.cas-bar{height:100%;border-radius:4px;min-width:4px}.cas-amt{width:140px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:600;font-size:.88rem;flex-shrink:0}
.cas-pct{width:60px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#64748B;flex-shrink:0}
.otbl{width:100%;border-collapse:separate;border-spacing:0;font-size:.83rem}
.otbl th{padding:12px 16px;text-align:left;font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#64748B;background:#111827;border-bottom:1px solid #1E293B}
.otbl td{padding:14px 16px;border-bottom:1px solid rgba(15,20,32,0.8);color:#E2E8F0}.otbl tr:hover td{background:#131A2B}
.otbl .id{color:#64748B;font-family:'JetBrains Mono',monospace;font-size:.78rem}.otbl .mono{font-family:'JetBrains Mono',monospace}
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:9999px;font-size:.72rem;font-weight:600}
.p-ent{background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3)}.p-can{background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3)}.p-tra{background:rgba(245,158,11,0.15);color:#F59E0B;border:1px solid rgba(245,158,11,0.3)}.p-dev{background:rgba(249,115,22,0.15);color:#F97316;border:1px solid rgba(249,115,22,0.3)}.p-env{background:rgba(59,130,246,0.15);color:#3B82F6;border:1px solid rgba(59,130,246,0.3)}.p-pen{background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)}.p-nov{background:rgba(139,92,246,0.15);color:#8B5CF6;border:1px solid rgba(139,92,246,0.3)}
.lgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin:1rem 0}
.litem{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.1rem;text-align:center}
.litem h3{font-size:1.4rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin:.3rem 0}
.litem p{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;margin:0}
.badge{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:.75rem;font-weight:600;font-family:'JetBrains Mono',monospace}
.thermo{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.2rem 1.5rem;margin:1rem 0}
.thermo .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.thermo .tt{font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#94A3B8}.thermo .tv{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.15rem;color:#10B981}
.thermo .bar{height:12px;border-radius:6px;background:linear-gradient(90deg,#EF4444 0%,#F59E0B 50%,#10B981 100%);position:relative;margin-bottom:6px}.thermo .mk{position:absolute;top:-4px;width:3px;height:20px;background:#FFF;border-radius:2px}.thermo .lb{display:flex;justify-content:space-between;font-size:.68rem;color:#64748B}
.linked{color:#334155!important;font-style:italic}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════ HELPERS ═══════════════════════
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path) as f: return json.load(f)
        except Exception: pass
    return {}
def save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f, ensure_ascii=False)
    except Exception: pass
def load_cfg(): return load_json(SETTINGS_FILE)
def save_cfg(k, v): s = load_cfg(); s[k] = v; save_json(SETTINGS_FILE, s)
def load_mappings(): return load_json(MAPPING_FILE)
def save_mappings(data): save_json(MAPPING_FILE, data)
def load_camp_mappings(): return load_json(CAMP_MAPPING_FILE)
def save_camp_mappings(data): save_json(CAMP_MAPPING_FILE, data)

@st.cache_data(ttl=3600, show_spinner=False)
def get_trm():
    rates = {"COP_USD": 4200, "COP_GTQ": 540}
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if "rates" in d:
                rates["COP_USD"] = d["rates"].get("COP", 4200)
                rates["COP_GTQ"] = d["rates"].get("COP", 4200) / d["rates"].get("GTQ", 7.75)
    except Exception: pass
    return rates

def cop_to(amount_cop, target, trm):
    if target == "COP": return amount_cop
    if target == "USD": return amount_cop / trm.get("COP_USD", 4200)
    if target == "GTQ": return amount_cop / trm.get("COP_GTQ", 540)
    return amount_cop

def to_cop(amount, src, trm):
    if src == "COP": return amount
    if src == "USD": return amount * trm.get("COP_USD", 4200)
    if src == "GTQ": return amount * trm.get("COP_GTQ", 540)
    return amount

@st.cache_data(show_spinner=False)
def cargar(data_bytes, name):
    import io; buf = io.BytesIO(data_bytes)
    if name.lower().endswith((".xlsx",".xls")): df = pd.read_excel(buf, dtype=str, engine="openpyxl")
    else:
        for enc in ("utf-8","latin-1","cp1252"):
            try: buf.seek(0); df = pd.read_csv(buf, dtype=str, encoding=enc, sep=None, engine="python"); break
            except: continue
        else: buf.seek(0); df = pd.read_csv(buf, dtype=str, encoding="latin-1", on_bad_lines="skip")
    df.columns = df.columns.str.strip().str.upper()
    alias = {"TOTAL DE LA ORDEN":["TOTAL DE LA ORDEN","TOTAL_DE_LA_ORDEN"],"PRECIO PROVEEDOR":["PRECIO PROVEEDOR","PRECIO_PROVEEDOR"],"PRECIO FLETE":["PRECIO FLETE","PRECIO_FLETE"],"COSTO DEVOLUCION FLETE":["COSTO DEVOLUCION FLETE","COSTO_DEVOLUCION_FLETE"],"GANANCIA":["GANANCIA","PROFIT"],"CANTIDAD":["CANTIDAD","QTY"],"ESTATUS":["ESTATUS","STATUS","ESTADO"],"PRODUCTO":["PRODUCTO","PRODUCT"],"FECHA":["FECHA","DATE"],"CIUDAD DESTINO":["CIUDAD DESTINO","CIUDAD"]}
    for canon, vs in alias.items():
        for v in vs:
            if v in df.columns and canon not in df.columns: df.rename(columns={v:canon}, inplace=True); break
    for col in ["TOTAL DE LA ORDEN","PRECIO PROVEEDOR","PRECIO PROVEEDOR X CANTIDAD","PRECIO FLETE","COSTO DEVOLUCION FLETE","GANANCIA","CANTIDAD","COMISION"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r"[^\d.\-]","",regex=True).replace("","0")
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "FECHA" in df.columns: df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
    if "ESTATUS" in df.columns: df["ESTATUS"] = df["ESTATUS"].astype(str).str.strip().str.upper()
    return df

def filtrar_fecha(df, ini, fin):
    if "FECHA" not in df.columns: return df
    return df[(df["FECHA"]>=pd.Timestamp(ini))&(df["FECHA"]<=pd.Timestamp(fin)+pd.Timedelta(days=1)-pd.Timedelta(seconds=1))].copy()

def detect_country(df):
    cities_co = {"BOGOTA","BOGOTÁ","MEDELLIN","MEDELLÍN","CALI","BARRANQUILLA","CARTAGENA","BUCARAMANGA","PEREIRA","CUCUTA","CÚCUTA","MANIZALES","IBAGUE","IBAGUÉ","PASTO","SANTA MARTA","VILLAVICENCIO","NEIVA","DOSQUEBRADAS"}
    cities_ec = {"QUITO","GUAYAQUIL","CUENCA","AMBATO","PORTOVIEJO","MACHALA","DURÁN","LOJA","MANTA","SANTO DOMINGO"}
    cities_gt = {"GUATEMALA","MIXCO","VILLA NUEVA","QUETZALTENANGO","ESCUINTLA","CHINAUTLA","HUEHUETENANGO","COBAN","COBÁN","ANTIGUA"}
    if "CIUDAD DESTINO" in df.columns:
        c = set(df["CIUDAD DESTINO"].dropna().str.upper().str.strip().unique())
        sc = {"Colombia":len(c&cities_co),"Ecuador":len(c&cities_ec),"Guatemala":len(c&cities_gt)}
        b = max(sc, key=sc.get)
        if sc[b] > 0: return b
    return None

def extraer_base_producto(nombre):
    n = re.sub(r'\s*-\s*',' ',str(nombre).strip().upper())
    words = [w for w in n.split() if not re.match(r'^\d+$',w) and w not in ("X","DE","EL","LA","EN","CON","PARA","POR")]
    return " ".join(words[:2]) if words else n

def build_product_groups(pl_): return {extraer_base_producto(p):[p] for grp in [defaultdict(list)] for p in pl_ for _ in [grp[extraer_base_producto(p)].append(p)] } or {}

def build_product_groups(product_list):
    groups = defaultdict(list)
    for p in product_list: groups[extraer_base_producto(p)].append(p)
    return dict(groups)

def apply_groups(df, groups_map):
    rev = {}
    for gn, ors in groups_map.items():
        for o in ors: rev[o.upper().strip()] = gn
    df["GRUPO_PRODUCTO"] = df["PRODUCTO"].str.upper().str.strip().map(rev).fillna(df["PRODUCTO"])
    return df

def fmt(v, pn="Colombia"):
    sym = PAISES.get(pn, PAISES["Colombia"])["sym"]
    return f"{sym} {v:,.0f}".replace(",",".")

def fmt_cop(v): return f"$ {v:,.0f}".replace(",",".")

def pct_of(part, whole):
    if whole == 0: return "0%"
    return f"{(part/whole*100):.1f}%"

# ── Facebook / TikTok API ──
def fb_spend_acct(tok,cid,i,f):
    if not tok or not cid: return 0.0
    cid=cid.strip()
    if not cid.startswith("act_"): cid=f"act_{cid}"
    try:
        r=requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"spend","level":"account"},timeout=30)
        d=r.json()
        if "data" in d and d["data"]: return float(d["data"][0].get("spend",0))
    except: pass
    return 0.0

def fb_camps_acct(tok,cid,i,f):
    if not tok or not cid: return pd.DataFrame(columns=["campaign_name","spend"])
    cid=cid.strip()
    if not cid.startswith("act_"): cid=f"act_{cid}"
    try:
        r=requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"campaign_name,spend","level":"campaign","limit":500},timeout=30)
        d=r.json()
        if "data" in d: return pd.DataFrame([{"campaign_name":x.get("campaign_name",""),"spend":float(x.get("spend",0))} for x in d["data"]])
    except: pass
    return pd.DataFrame(columns=["campaign_name","spend"])

def fb_list_accts(tok):
    if not tok: return []
    try:
        r=requests.get("https://graph.facebook.com/v21.0/me/adaccounts",params={"access_token":tok,"fields":"name,account_id,currency","limit":50},timeout=15)
        d=r.json()
        if "data" in d: return [{"id":a.get("account_id",""),"name":a.get("name",""),"cur":a.get("currency","")} for a in d["data"]]
    except: pass
    return []

def tt_spend_acct(tok,aid,i,f):
    if not tok or not aid: return 0.0
    try:
        r=requests.post("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",headers={"Access-Token":tok,"Content-Type":"application/json"},
            json={"advertiser_id":aid,"report_type":"BASIC","data_level":"AUCTION_ADVERTISER","dimensions":["advertiser_id"],"metrics":["spend"],"start_date":i,"end_date":f},timeout=30)
        d=r.json()
        if d.get("code")==0 and d.get("data",{}).get("list"): return float(d["data"]["list"][0]["metrics"].get("spend",0))
    except: pass
    return 0.0

def extraer_prod_camp(n):
    p=[x.strip() for x in str(n).split("-")]
    return p[1].strip().upper() if len(p)>=2 else n.strip().upper()

def status_pill(s):
    s=s.upper()
    if "ENTREGADO" in s: return '<span class="pill p-ent">✅ Entregado</span>'
    if "CANCELADO" in s: return '<span class="pill p-can">⊘ Cancelado</span>'
    if "DEVOLUCION" in s or "DEVOLUCIÓN" in s: return '<span class="pill p-dev">↩ Devolución</span>'
    if match_status(s, STATUS_TRA): return '<span class="pill p-tra">🚚 En Tránsito</span>'
    if "NOVEDAD" in s: return '<span class="pill p-nov">⚠ Novedad</span>'
    return '<span class="pill p-pen">⏳ Pendiente</span>'

def aggregate_orders(df):
    F = {c: c in df.columns for c in ["ID","ESTATUS","TOTAL DE LA ORDEN","PRODUCTO","CANTIDAD","GANANCIA","PRECIO FLETE","PRECIO PROVEEDOR","COSTO DEVOLUCION FLETE","CIUDAD DESTINO","FECHA","GRUPO_PRODUCTO","PRECIO PROVEEDOR X CANTIDAD"]}
    if not F["ID"]: return df, F
    ag = {}
    for c,fn in [("TOTAL DE LA ORDEN","first"),("ESTATUS","first"),("PRECIO FLETE","first"),("COSTO DEVOLUCION FLETE","first"),("GANANCIA","sum"),("FECHA","first"),("CIUDAD DESTINO","first"),("PRODUCTO","first"),("CANTIDAD","sum"),("PRECIO PROVEEDOR","first"),("PRECIO PROVEEDOR X CANTIDAD","sum"),("GRUPO_PRODUCTO","first")]:
        if c in df.columns: ag[c]=fn
    return (df.groupby("ID").agg(ag).reset_index() if ag else df.copy()), F


def calc_kpis(df_ord, F, g_fb, g_tt):
    """KPIs with CORRECTED P&L: ingreso = TOTAL DE LA ORDEN, includes fletes entregados."""
    n_ord = df_ord["ID"].nunique() if F.get("ID") else len(df_ord)
    fact_bruto = df_ord["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    df_nc = df_ord[~df_ord["ESTATUS"].apply(lambda s: match_status(s, STATUS_CAN))] if F.get("ESTATUS") else df_ord
    fact_neto = df_nc["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    n_desp = len(df_nc); aov = fact_bruto/n_ord if n_ord>0 else 0
    g_ads = g_fb + g_tt; roas = fact_neto/g_ads if g_ads>0 else 0

    sc = {}
    if F.get("ESTATUS"):
        for s in df_ord["ESTATUS"].unique():
            sc[s] = len(df_ord[df_ord["ESTATUS"]==s])
    n_ent = sum(v for s,v in sc.items() if match_status(s, STATUS_ENT))
    n_can = sum(v for s,v in sc.items() if match_status(s, STATUS_CAN))
    n_tra = sum(v for s,v in sc.items() if match_status(s, STATUS_TRA))
    n_dev = sum(v for s,v in sc.items() if match_status(s, STATUS_DEV))
    n_nov = sum(v for s,v in sc.items() if match_status(s, STATUS_NOV))
    n_otr = max(0, n_ord-n_ent-n_can-n_tra-n_dev-n_nov)
    n_nc = n_ord - n_can
    pct_can = (n_can/n_ord*100) if n_ord>0 else 0
    pct_ent = (n_ent/n_nc*100) if n_nc>0 else 0

    # ── CORRECTED P&L ──
    de = df_ord[df_ord["ESTATUS"].apply(lambda s: match_status(s, STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
    # FIX #1: Ingreso = TOTAL DE LA ORDEN (not GANANCIA)
    ing_real = de["TOTAL DE LA ORDEN"].sum() if (not de.empty and F.get("TOTAL DE LA ORDEN")) else 0
    # Costo producto
    cpr = 0
    if not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns: cpr = de["PRECIO PROVEEDOR X CANTIDAD"].sum()
    elif not de.empty and F.get("PRECIO PROVEEDOR") and F.get("CANTIDAD"): cpr = (de["PRECIO PROVEEDOR"]*de["CANTIDAD"]).sum()
    # FIX #1b: Fletes entregados
    fl_ent = de["PRECIO FLETE"].sum() if (not de.empty and F.get("PRECIO FLETE")) else 0

    # Fletes devoluciones
    dd = df_ord[df_ord["ESTATUS"].apply(lambda s: match_status(s, STATUS_DEV))].copy() if F.get("ESTATUS") else pd.DataFrame()
    fl_dev = 0
    if not dd.empty:
        if F.get("PRECIO FLETE") and F.get("COSTO DEVOLUCION FLETE"): fl_dev = dd[["PRECIO FLETE","COSTO DEVOLUCION FLETE"]].max(axis=1).sum()
        elif F.get("PRECIO FLETE"): fl_dev = dd["PRECIO FLETE"].sum()

    # FIX #2: Fletes tránsito — use broad matching
    dt = df_ord[df_ord["ESTATUS"].apply(lambda s: match_status(s, STATUS_TRA))].copy() if F.get("ESTATUS") else pd.DataFrame()
    fl_tra = dt["PRECIO FLETE"].sum() if (not dt.empty and F.get("PRECIO FLETE")) else 0

    u_real = ing_real - cpr - g_ads - fl_ent - fl_dev - fl_tra

    return dict(n_ord=n_ord,fact_bruto=fact_bruto,fact_neto=fact_neto,n_desp=n_desp,aov=aov,g_fb=g_fb,g_tt=g_tt,g_ads=g_ads,roas=roas,
                n_ent=n_ent,n_can=n_can,n_tra=n_tra,n_dev=n_dev,n_nov=n_nov,n_otr=n_otr,n_nc=n_nc,pct_can=pct_can,pct_ent=pct_ent,tasa_ent=pct_ent,
                ing_real=ing_real,cpr=cpr,fl_ent=fl_ent,fl_dev=fl_dev,fl_tra=fl_tra,u_real=u_real)


# ── AI Auto-mapping ──
def ai_auto_map(campaigns, products, api_key):
    """Use OpenAI to auto-map campaign names to product names."""
    if not api_key: return {}
    prompt = f"""Eres un asistente que empareja nombres de campañas publicitarias de Facebook con nombres de productos de una tienda Dropi.

Campañas: {json.dumps(campaigns)}
Productos: {json.dumps(products)}

Para cada campaña, identifica el producto más probable basándote en similitud de texto.
Responde SOLO un JSON con este formato exacto, sin explicaciones ni markdown:
{{"campaña1": "producto1", "campaña2": "producto2"}}

Si no encuentras match para una campaña, asígnala al producto más similar."""

    try:
        r = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "gpt-4o-mini", "messages": [{"role":"user","content":prompt}], "temperature": 0.1, "max_tokens": 2000},
            timeout=30)
        d = r.json()
        txt = d["choices"][0]["message"]["content"].strip()
        txt = re.sub(r'^```json\s*','',txt); txt = re.sub(r'```$','',txt)
        return json.loads(txt)
    except Exception as e:
        st.error(f"Error AI: {e}")
        return {}


# ═══════════════════════ TRM ═══════════════════════
trm = get_trm()
trm_usd = trm.get("COP_USD", 4200)
trm_gtq = trm.get("COP_GTQ", 540)


# ═══════════════════════ SIDEBAR ═══════════════════════
cfg = load_cfg()
with st.sidebar:
    st.markdown("### 📊 Profit Dashboard")
    st.caption("v4.3 · Multi-País")
    st.divider()
    st.markdown("##### 📢 Publicidad")
    usar_api = st.checkbox("Usar APIs", value=True)
    fb_token=""; fb_cids=[]; tt_token=""; tt_aids=[]
    if usar_api:
        st.markdown("###### 📘 Facebook")
        fb_token = st.text_input("Token FB", type="password", value=cfg.get("fb_token",""), key="fbt")
        if fb_token: save_cfg("fb_token", fb_token)
        fb_accts = fb_list_accts(fb_token)
        if fb_accts:
            opts = {f"{a['name']} ({a['id']})":a["id"] for a in fb_accts}
            opt_keys = list(opts.keys())
            # FIX #7: Select all with checkbox instead of button
            sel_all = st.checkbox("Seleccionar TODAS las cuentas FB", key="sel_all_fb")
            if sel_all:
                fb_cids = [opts[k] for k in opt_keys]
                st.caption(f"✅ {len(fb_cids)} cuentas seleccionadas")
            else:
                sel = st.multiselect("Cuentas FB", opt_keys, key="fb_multi")
                fb_cids = [opts[l] for l in sel]
        else:
            v = st.text_input("IDs FB (coma)", value=cfg.get("fb_cids",""))
            if v: save_cfg("fb_cids",v); fb_cids=[x.strip() for x in v.split(",") if x.strip()]
        st.markdown("###### 🎵 TikTok")
        tt_token = st.text_input("Token TT", type="password", value=cfg.get("tt_token",""), key="ttt")
        tt_input = st.text_input("Adv IDs TT (coma)", value=cfg.get("tt_aids",""))
        if tt_token: save_cfg("tt_token",tt_token)
        if tt_input: save_cfg("tt_aids",tt_input); tt_aids=[x.strip() for x in tt_input.split(",") if x.strip()]
        st.markdown(f"<p style='font-size:.7rem;color:#475569'>TRM: 1 USD = {trm_usd:,.0f} COP · 1 GTQ = {trm_gtq:,.0f} COP</p>", unsafe_allow_html=True)
    ads_manual = {}
    if not usar_api:
        st.divider()
        st.markdown("##### 💵 Ads Manual")
        for pn in PAISES: ads_manual[pn] = st.number_input(f"Gasto {pn} ({PAISES[pn]['moneda']})",min_value=0.0,value=0.0,step=1000.0,key=f"gm_{pn}")
    st.divider()
    st.markdown("##### 🤖 OpenAI (Auto-Mapeo)")
    oai_key = st.text_input("API Key OpenAI", type="password", value=cfg.get("oai_key",""), key="oai")
    if oai_key: save_cfg("oai_key", oai_key)

# ═══════════════════════ INIT ═══════════════════════
for pn in PAISES:
    for k in (f"_b_{pn}",f"_n_{pn}"):
        if k not in st.session_state: st.session_state[k]=None

# ═══════════════════════ TITLE + DATES ═══════════════════════
st.markdown('<p style="text-align:center;font-size:1.8rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.02em;margin-bottom:.5rem">📊 Ecommerce Profit Dashboard</p>', unsafe_allow_html=True)
hoy = datetime.today().date()
dc1,dc2,dc3 = st.columns([1,1,3])
with dc1: f_ini = st.date_input("📅 Desde", value=hoy-timedelta(days=30), key="d_ini")
with dc2: f_fin = st.date_input("📅 Hasta", value=hoy, key="d_fin")
with dc3: st.markdown(f'<div style="padding-top:1.6rem"><span style="color:{C["sub"]};font-size:.8rem">TRM: <b style="color:{C["text"]}">1 USD = {trm_usd:,.0f} COP</b> · <b style="color:{C["text"]}">1 GTQ ≈ {trm_gtq:,.0f} COP</b></span></div>', unsafe_allow_html=True)

any_data = any(st.session_state.get(f"_b_{pn}") for pn in PAISES)
if not any_data:
    st.divider()
    st.markdown('<p class="section-hdr">Sube tus archivos de Dropi</p>', unsafe_allow_html=True)
    st.markdown("#### 🔍 Auto-detectar país")
    fa = st.file_uploader("Arrastra aquí",type=["csv","xlsx","xls"],key="up_auto",label_visibility="collapsed")
    if fa:
        td = cargar(fa.getvalue(),fa.name); det = detect_country(td)
        if det: st.session_state[f"_b_{det}"]=fa.getvalue(); st.session_state[f"_n_{det}"]=fa.name; st.success(f"✅ {PAISES[det]['flag']} {det}"); st.rerun()
        else: st.warning("No detectado. Sube manualmente:")
    st.markdown("#### 📁 O por país")
    for i,(pn,pi) in enumerate(PAISES.items()):
        f=st.file_uploader(f"{pi['flag']} {pn}",type=["csv","xlsx","xls"],key=f"up_m_{pn}")
        if f: st.session_state[f"_b_{pn}"]=f.getvalue(); st.session_state[f"_n_{pn}"]=f.name; st.rerun()
    st.stop()

with st.sidebar:
    st.divider(); st.markdown("##### 📁 Archivos")
    for pn,pi in PAISES.items():
        f=st.file_uploader(f"{pi['flag']} {pn}",type=["csv","xlsx","xls"],key=f"up_sb_{pn}")
        if f: st.session_state[f"_b_{pn}"]=f.getvalue(); st.session_state[f"_n_{pn}"]=f.name; st.rerun()
        if st.session_state.get(f"_b_{pn}"): st.caption(f"✅ {st.session_state[f'_n_{pn}']}")

# ═══════════════════════ LOAD DATA ═══════════════════════
si,sf = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")
country_data = {}; persistent_maps = load_mappings(); gxp = {}

all_camps = pd.DataFrame(columns=["campaign_name","spend"])
if usar_api:
    for c in fb_cids: all_camps = pd.concat([all_camps, fb_camps_acct(fb_token,c,si,sf)])
if usar_api:
    gfb_total_cop = sum(fb_spend_acct(fb_token,c,si,sf) for c in fb_cids)
    gtt_total_cop = sum(tt_spend_acct(tt_token,a,si,sf) for a in tt_aids)
else:
    gfb_total_cop = sum(to_cop(ads_manual.get(pn,0),PAISES[pn]["moneda"],trm) for pn in PAISES); gtt_total_cop = 0

country_raw_lens = {}; total_rows_all = 0
for pn in PAISES:
    if not st.session_state.get(f"_b_{pn}"): continue
    df_t = filtrar_fecha(cargar(st.session_state[f"_b_{pn}"],st.session_state[f"_n_{pn}"]),f_ini,f_fin)
    if not df_t.empty: country_raw_lens[pn]=len(df_t); total_rows_all+=len(df_t)

for pn in PAISES:
    if not st.session_state.get(f"_b_{pn}"): continue
    df_f = filtrar_fecha(cargar(st.session_state[f"_b_{pn}"],st.session_state[f"_n_{pn}"]),f_ini,f_fin)
    if df_f.empty: continue
    mon = PAISES[pn]["moneda"]
    if "PRODUCTO" in df_f.columns:
        sv = persistent_maps.get(pn,{})
        if sv: df_f = apply_groups(df_f,sv)
        else:
            ag = build_product_groups(sorted(df_f["PRODUCTO"].dropna().unique()))
            df_f = apply_groups(df_f,ag); persistent_maps[pn]=ag; save_mappings(persistent_maps)
    df_ord, F = aggregate_orders(df_f)
    if usar_api:
        r = country_raw_lens.get(pn,0)/max(total_rows_all,1)
        gfb_c = cop_to(gfb_total_cop*r,mon,trm); gtt_c = cop_to(gtt_total_cop*r,mon,trm)
        gfb_cop_c = gfb_total_cop*r; gtt_cop_c = gtt_total_cop*r
    else:
        gfb_c = ads_manual.get(pn,0); gtt_c = 0
        gfb_cop_c = to_cop(gfb_c,mon,trm); gtt_cop_c = 0
    kpis = calc_kpis(df_ord,F,gfb_c,gtt_c)
    kpis["g_fb_cop"]=gfb_cop_c; kpis["g_tt_cop"]=gtt_cop_c; kpis["g_ads_cop"]=gfb_cop_c+gtt_cop_c
    country_data[pn] = {"df":df_f,"df_ord":df_ord,"kpis":kpis,"camps":all_camps,"F":F}

if not country_data: st.warning("Sin datos."); st.stop()

# ═══════ PRODUCT & CAMPAIGN MAPPINGS ═══════
with st.expander("📦 Agrupación de Productos", expanded=False):
    for pn,cd in country_data.items():
        if "PRODUCTO" not in cd["df"].columns: continue
        st.markdown(f"**{PAISES[pn]['flag']} {pn}**")
        sv = persistent_maps.get(pn,{})
        rows=[]
        for gn,ms in sv.items():
            for m in ms: rows.append({"Producto Original":m,"Grupo":gn})
        if not rows:
            for p in sorted(cd["df"]["PRODUCTO"].dropna().unique()): rows.append({"Producto Original":p,"Grupo":extraer_base_producto(p)})
        epg=st.data_editor(pd.DataFrame(rows),use_container_width=True,hide_index=True,key=f"pg_{pn}",num_rows="dynamic")
        if st.button(f"💾 Guardar {pn}",key=f"spg_{pn}"):
            ng=defaultdict(list)
            for _,r in epg.iterrows():
                o=str(r.get("Producto Original","")).strip(); g=str(r.get("Grupo","")).strip()
                if o and g: ng[g].append(o)
            persistent_maps[pn]=dict(ng); save_mappings(persistent_maps); st.success(f"✅ {pn}"); st.rerun()

# ── FIX #3: New Campaign Mapping UI ──
camp_map_saved = load_camp_mappings()
if not all_camps.empty:
    with st.expander("🔗 Mapeo Campañas → Productos (selección por dropdown)", expanded=False):
        grp_list = []
        for pn,cd in country_data.items():
            if "GRUPO_PRODUCTO" in cd["df_ord"].columns:
                grp_list.extend(cd["df_ord"]["GRUPO_PRODUCTO"].dropna().unique().tolist())
        grp_list = sorted(set(grp_list))
        camp_names = sorted(all_camps["campaign_name"].unique().tolist())

        if not camp_map_saved: camp_map_saved = {}
        product_options = ["-- Sin asignar --"] + grp_list

        # FIX #4: AI Auto-map button
        ac1,ac2 = st.columns([1,2])
        with ac1:
            if st.button("🪄 Auto-Mapear con IA", key="ai_map"):
                if oai_key:
                    with st.spinner("Consultando IA..."):
                        result = ai_auto_map(camp_names, grp_list, oai_key)
                        if result:
                            camp_map_saved.update(result)
                            save_camp_mappings(camp_map_saved)
                            st.success(f"✅ {len(result)} campañas mapeadas"); st.rerun()
                else: st.warning("Ingresa tu API Key de OpenAI en la barra lateral")
        with ac2:
            st.caption(f"{len(camp_names)} campañas · {len(grp_list)} productos · {sum(1 for c in camp_names if camp_map_saved.get(c,''))} ya enlazadas")

        st.divider()
        # Show each campaign with a selectbox
        for camp in camp_names:
            current = camp_map_saved.get(camp, "-- Sin asignar --")
            is_linked = current != "-- Sin asignar --" and current in grp_list
            label_color = "✅" if is_linked else "⚪"
            idx = product_options.index(current) if current in product_options else 0
            new_val = st.selectbox(f"{label_color} {camp}", product_options, index=idx, key=f"cm_{camp}")
            if new_val != current:
                camp_map_saved[camp] = new_val
                save_camp_mappings(camp_map_saved)

        if st.button("💾 Guardar Todo", key="save_cm"):
            save_camp_mappings(camp_map_saved); st.success("✅ Mapeo guardado"); st.rerun()

    # Build gxp from saved mapping
    for camp in camp_names:
        prod = camp_map_saved.get(camp, "")
        if prod and prod != "-- Sin asignar --":
            spend = all_camps[all_camps["campaign_name"]==camp]["spend"].sum()
            gxp[prod.upper()] = gxp.get(prod.upper(), 0) + spend


# ═══════════════════════ TABS ═══════════════════════
tab_names = ["🏠 Dashboard Global"]
for pn in country_data: tab_names.append(f"{PAISES[pn]['flag']} {pn}")
tab_names.append("📢 Publicidad")
tabs = st.tabs(tab_names)


# ═══════════════ TAB: DASHBOARD GLOBAL ═══════════════
with tabs[0]:
    tot_ord=sum(cd["kpis"]["n_ord"] for cd in country_data.values())
    tot_fact_cop=sum(to_cop(cd["kpis"]["fact_neto"],PAISES[pn]["moneda"],trm) for pn,cd in country_data.items())
    tot_ads_cop=sum(cd["kpis"].get("g_ads_cop",0) for cd in country_data.values())
    tot_ing_cop=sum(to_cop(cd["kpis"]["ing_real"],PAISES[pn]["moneda"],trm) for pn,cd in country_data.items())
    tot_util_cop=sum(to_cop(cd["kpis"]["u_real"],PAISES[pn]["moneda"],trm) for pn,cd in country_data.items())
    tot_roas=tot_fact_cop/tot_ads_cop if tot_ads_cop>0 else 0

    st.markdown(f"""
    <p class="section-hdr">Total Operación (COP)</p>
    <div class="row2 r4">
        <div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES TOTALES</div><div class="val lg white">{tot_ord:,}</div></div>
        <div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO NETO</div><div class="val lg green">{fmt_cop(tot_fact_cop)}</div></div>
        <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO ADS</div><div class="val lg red">{fmt_cop(tot_ads_cop)}</div></div>
        <div class="kcard {'green' if tot_util_cop>=0 else 'red'}"><div class="icon {'g' if tot_util_cop>=0 else 'r'}">💰</div><div class="lbl">UTILIDAD REAL</div><div class="val lg {'green' if tot_util_cop>=0 else 'red'}">{fmt_cop(tot_util_cop)}</div><div class="sub">ROAS: {tot_roas:.2f}x</div></div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()
    st.markdown('<p class="section-hdr">Por País</p>', unsafe_allow_html=True)
    for pn,cd in country_data.items():
        k=cd["kpis"];pi=PAISES[pn];uc="green" if k["u_real"]>=0 else "red"
        cop_note=f'<div class="trm">{fmt_cop(k.get("g_ads_cop",0))} COP</div>' if pi["moneda"]!="COP" else ""
        st.markdown(f'<div class="row2 r4" style="margin-bottom:.5rem"><div class="kcard"><div class="icon w">📦</div><div class="lbl">{pi["flag"]} {pn.upper()}</div><div class="val lg white">{k["n_ord"]:,}</div><div class="sub">{k["n_ent"]} ent · {k["tasa_ent"]:.0f}%</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO</div><div class="val lg green">{fmt(k["fact_neto"],pn)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val md red">{fmt(k["g_ads"],pn)}</div>{cop_note}</div><div class="kcard {uc}"><div class="icon {"g" if k["u_real"]>=0 else "r"}">💰</div><div class="lbl">UTILIDAD</div><div class="val lg {uc}">{fmt(k["u_real"],pn)}</div></div></div>', unsafe_allow_html=True)

    # Global logistics with %
    t_ord=sum(cd["kpis"]["n_ord"] for cd in country_data.values()); t_ent=sum(cd["kpis"]["n_ent"] for cd in country_data.values()); t_can=sum(cd["kpis"]["n_can"] for cd in country_data.values()); t_tra=sum(cd["kpis"]["n_tra"] for cd in country_data.values()); t_dev=sum(cd["kpis"]["n_dev"] for cd in country_data.values()); t_nov=sum(cd["kpis"]["n_nov"] for cd in country_data.values()); t_otr=sum(cd["kpis"]["n_otr"] for cd in country_data.values()); t_nc=t_ord-t_can
    def gpof(n): return f"{(n/t_nc*100):.0f}%" if t_nc else "0%"
    st.markdown(f"""<p class="section-hdr">Logística Global — {t_ord:,} órdenes</p>
    <div class="lgrid"><div class="litem" style="border-color:rgba(239,68,68,0.3)"><p>❌ CANCELADO</p><h3 style="color:{C['loss']}">{t_can:,}</h3><span class="badge" style="background:rgba(239,68,68,0.15);color:#EF4444">{(t_can/t_ord*100):.0f}% total</span></div></div>
    <div class="lgrid"><div class="litem" style="border-color:rgba(16,185,129,0.3)"><p>✅ ENTREGADO</p><h3 style="color:{C['profit']}">{t_ent:,}</h3><span class="badge" style="background:rgba(16,185,129,0.15);color:#10B981">{gpof(t_ent)}</span></div><div class="litem" style="border-color:rgba(59,130,246,0.3)"><p>🚚 TRÁNSITO</p><h3 style="color:{C['blue']}">{t_tra:,}</h3><span class="badge" style="background:rgba(59,130,246,0.15);color:#3B82F6">{gpof(t_tra)}</span></div><div class="litem" style="border-color:rgba(245,158,11,0.3)"><p>↩️ DEVOLUCIÓN</p><h3 style="color:{C['warn']}">{t_dev:,}</h3><span class="badge" style="background:rgba(245,158,11,0.15);color:#F59E0B">{gpof(t_dev)}</span></div><div class="litem" style="border-color:rgba(249,115,22,0.3)"><p>⚠️ NOVEDAD</p><h3 style="color:{C['orange']}">{t_nov:,}</h3><span class="badge" style="background:rgba(249,115,22,0.15);color:#F97316">{gpof(t_nov)}</span></div><div class="litem" style="border-color:rgba(100,116,139,0.3)"><p>⏳ OTROS</p><h3 style="color:{C['muted']}">{t_otr:,}</h3><span class="badge" style="background:rgba(100,116,139,0.15);color:#94A3B8">{gpof(t_otr)}</span></div></div>""", unsafe_allow_html=True)


# ═══════════════ COUNTRY TABS ═══════════════
for idx,(pn,cd) in enumerate(country_data.items()):
    with tabs[idx+1]:
        k=cd["kpis"];df_ord=cd["df_ord"];df_f=cd["df"];F=cd["F"];pi=PAISES[pn]
        ct1,ct2,ct3,ct4 = st.tabs(["🌡 Termómetro","📊 Proyecciones","💰 Operación Real","📋 Órdenes"])

        with ct1:
            rc="green" if k["roas"]>=2 else ("red" if k["roas"]<1 else "white"); tc="green" if k["tasa_ent"]>=60 else ("red" if k["tasa_ent"]<40 else "white")
            at=f'<div class="trm">{fmt_cop(k.get("g_ads_cop",0))} COP</div>' if pi["moneda"]!="COP" else ""
            st.markdown(f"""<div class="row2 r3"><div class="kcard"><div class="icon w">💰</div><div class="lbl">FACTURADO BRUTO</div><div class="val lg white">{fmt(k['fact_bruto'],pn)}</div><div class="sub">{k['n_ord']:,} órdenes</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO NETO</div><div class="val lg green">{fmt(k['fact_neto'],pn)}</div></div><div class="kcard"><div class="icon w">🛒</div><div class="lbl">AOV</div><div class="val lg white">{fmt(k['aov'],pn)}</div></div></div>
            <div class="row2 r3"><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO ADS</div><div class="val lg red">{fmt(k['g_ads'],pn)}</div>{at}</div><div class="kcard"><div class="icon g">⚡</div><div class="lbl">ROAS</div><div class="val lg {rc}">{k['roas']:.2f}x</div></div><div class="kcard"><div class="icon g">✅</div><div class="lbl">TASA ENTREGA</div><div class="val lg {tc}">{k['tasa_ent']:.0f}%</div><div class="sub">{k['n_ent']} de {k['n_nc']}</div></div></div>""", unsafe_allow_html=True)
            rp=min(k["roas"]/4*100,100)
            st.markdown(f'<div class="thermo"><div class="hd"><span class="tt">TERMÓMETRO ROAS</span><span class="tv">{k["roas"]:.2f}x</span></div><div class="bar"><div class="mk" style="left:{rp:.0f}%"></div></div><div class="lb"><span>0x</span><span>2x</span><span>4x+</span></div></div>', unsafe_allow_html=True)
            if F.get("FECHA") and F.get("TOTAL DE LA ORDEN"):
                daily=df_ord.groupby(df_ord["FECHA"].dt.date).agg(Fac=("TOTAL DE LA ORDEN","sum")).reset_index().rename(columns={"FECHA":"Fecha"})
                gc1,gc2=st.columns(2)
                with gc1:
                    fig=go.Figure(); fig.add_trace(go.Scatter(x=daily["Fecha"],y=daily["Fac"],mode="lines",fill="tozeroy",fillcolor="rgba(16,185,129,0.1)",line=dict(color=C["profit"],width=2),hovertemplate="%{y:,.0f}<extra></extra>"))
                    fig.update_layout(**pl(title="FACTURACIÓN")); st.plotly_chart(fig,use_container_width=True,key=f"fac_{pn}")
                with gc2:
                    if F.get("ESTATUS"):
                        edf=df_ord["ESTATUS"].value_counts().reset_index();edf.columns=["E","N"]
                        cm={s:(C["profit"] if "ENTREGADO" in s else C["loss"] if "CANCELADO" in s else C["orange"] if "DEVOLUCION" in s else C["blue"] if match_status(s,STATUS_TRA) else C["warn"] if "NOVEDAD" in s else C["muted"]) for s in edf["E"]}
                        f3=px.pie(edf,names="E",values="N",hole=.55,color="E",color_discrete_map=cm)
                        f3.update_layout(**pl(showlegend=True,title="ESTADOS"));f3.update_traces(textinfo="percent",hovertemplate="%{label}: %{value}<extra></extra>")
                        st.plotly_chart(f3,use_container_width=True,key=f"pie_{pn}")
            # Logistics
            nnc=k["n_nc"]
            def pof(n): return f"{(n/nnc*100):.0f}%" if nnc else "0%"
            st.markdown(f"""<p class="section-hdr">Logística — {k['n_ord']:,} órdenes</p>
            <div class="lgrid"><div class="litem" style="border-color:rgba(239,68,68,0.3)"><p>❌ CANCELADO</p><h3 style="color:{C['loss']}">{k['n_can']:,}</h3><span class="badge" style="background:rgba(239,68,68,0.15);color:#EF4444">{k['pct_can']:.0f}% total</span></div></div>
            <div class="lgrid"><div class="litem" style="border-color:rgba(16,185,129,0.3)"><p>✅ ENTREGADO</p><h3 style="color:{C['profit']}">{k['n_ent']:,}</h3><span class="badge" style="background:rgba(16,185,129,0.15);color:#10B981">{pof(k['n_ent'])}</span></div><div class="litem" style="border-color:rgba(59,130,246,0.3)"><p>🚚 TRÁNSITO</p><h3 style="color:{C['blue']}">{k['n_tra']:,}</h3><span class="badge" style="background:rgba(59,130,246,0.15);color:#3B82F6">{pof(k['n_tra'])}</span></div><div class="litem" style="border-color:rgba(245,158,11,0.3)"><p>↩️ DEVOLUCIÓN</p><h3 style="color:{C['warn']}">{k['n_dev']:,}</h3><span class="badge" style="background:rgba(245,158,11,0.15);color:#F59E0B">{pof(k['n_dev'])}</span></div><div class="litem" style="border-color:rgba(249,115,22,0.3)"><p>⚠️ NOVEDAD</p><h3 style="color:{C['orange']}">{k['n_nov']:,}</h3><span class="badge" style="background:rgba(249,115,22,0.15);color:#F97316">{pof(k['n_nov'])}</span></div><div class="litem" style="border-color:rgba(100,116,139,0.3)"><p>⏳ OTROS</p><h3 style="color:{C['muted']}">{k['n_otr']:,}</h3><span class="badge" style="background:rgba(100,116,139,0.15);color:#94A3B8">{pof(k['n_otr'])}</span></div></div>""", unsafe_allow_html=True)

            # FIX #6: Product summary in Termómetro
            gcol = "GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in df_ord.columns else ("PRODUCTO" if F.get("PRODUCTO") else None)
            if gcol:
                st.markdown('<p class="section-hdr">Resumen por Producto</p>', unsafe_allow_html=True)
                sort_by = st.selectbox("Ordenar por", ["Facturado","Pedidos","Gasto Ads"], key=f"sort_{pn}")
                prod_rows = []
                for prod in df_f[gcol].dropna().unique():
                    dp = df_ord[df_ord[gcol]==prod] if gcol in df_ord.columns else pd.DataFrame()
                    if dp.empty: continue
                    n_p = len(dp); fac_p = dp["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
                    ent_p = len(dp[dp["ESTATUS"].apply(lambda s: match_status(s,STATUS_ENT))]) if F.get("ESTATUS") else 0
                    ads_p = gxp.get(prod.upper(),0)
                    prod_rows.append({"Producto":prod,"Pedidos":n_p,"Entregados":ent_p,"Facturado":fac_p,"Ads":ads_p})
                if prod_rows:
                    dfpr = pd.DataFrame(prod_rows)
                    sort_col = {"Facturado":"Facturado","Pedidos":"Pedidos","Gasto Ads":"Ads"}[sort_by]
                    dfpr = dfpr.sort_values(sort_col, ascending=False)
                    mx_f = max(dfpr["Facturado"].max(),1)
                    ph = ""
                    for _,r in dfpr.iterrows():
                        bp = min(r["Facturado"]/mx_f*100,100)
                        ph += f'<div style="display:flex;align-items:center;padding:8px 0;border-bottom:1px solid #111827"><div style="width:200px;font-size:.82rem;color:{C["text"]}">{r["Producto"]}</div><div style="flex:1;margin:0 12px"><div style="background:#111827;border-radius:3px;height:18px;overflow:hidden"><div style="width:{bp:.0f}%;height:100%;background:{C["profit"]};opacity:.5;border-radius:3px"></div></div></div><div style="width:100px;text-align:right;font-family:JetBrains Mono;font-size:.78rem;color:{C["text"]}">{fmt(r["Facturado"],pn)}</div><div style="width:70px;text-align:right;font-size:.75rem;color:{C["sub"]}">{int(r["Pedidos"])} ord</div><div style="width:70px;text-align:right;font-size:.75rem;color:{C["sub"]}">{int(r["Entregados"])} ent</div><div style="width:90px;text-align:right;font-family:JetBrains Mono;font-size:.75rem;color:{C["loss"]}">{fmt(r["Ads"],pn)}</div></div>'
                    st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem">{ph}</div>', unsafe_allow_html=True)

        with ct2:
            gcol="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in df_f.columns else ("PRODUCTO" if F.get("PRODUCTO") else None)
            if not gcol: st.warning("Sin productos.")
            else:
                productos=sorted(df_f[gcol].dropna().unique()); ixo=k["fact_neto"]/k["n_desp"] if k["n_desp"]>0 else 0
                sc1,sc2=st.columns(2)
                with sc1: dg=st.slider("% Entrega",50,100,80,key=f"dg_{pn}")
                with sc2: rb=st.number_input("Colchón",value=1.40,min_value=1.0,max_value=3.0,step=0.05,key=f"rb_{pn}")
                pek=f"pe_{pn}"
                if pek not in st.session_state: st.session_state[pek]={}
                for p in productos:
                    if p not in st.session_state[pek]: st.session_state[pek][p]=float(dg)
                prows=[]
                for prod in productos:
                    dp=df_f[df_f[gcol]==prod];dpnc=dp[~dp["ESTATUS"].apply(lambda s:match_status(s,STATUS_CAN))] if F.get("ESTATUS") else dp
                    uds=dp["CANTIDAD"].sum() if F.get("CANTIDAD") else 0;od=dpnc["ID"].nunique() if F.get("ID") else len(dpnc)
                    pp=dp["PRECIO PROVEEDOR"].mean() if F.get("PRECIO PROVEEDOR") else 0;fp=dp["PRECIO FLETE"].mean() if F.get("PRECIO FLETE") else 0
                    pe=st.session_state[pek].get(prod,float(dg));oe=od*pe/100;odv=od-oe;ue=uds*pe/100;cp=ue*pp;fl=oe*fp+odv*fp*rb;ap=gxp.get(prod.upper(),0);ip=oe*ixo;ut=ip-cp-fl-ap
                    prows.append({"Producto":prod,"Órdenes":int(od),"% Entrega":pe,"Ingreso":round(ip),"Costo":round(cp),"Fletes":round(fl),"Ads":round(ap),"Utilidad":round(ut)})
                dfp=pd.DataFrame(prows);ti=dfp["Ingreso"].sum();tu=dfp["Utilidad"].sum()
                st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{dfp["Órdenes"].sum():,}</div></div><div class="kcard"><div class="icon g">📊</div><div class="lbl">INGRESO PROY.</div><div class="val lg green">{fmt(ti,pn)}</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">UTILIDAD PROY.</div><div class="val lg green">{fmt(tu,pn)}</div></div></div>', unsafe_allow_html=True)
                st.markdown('<p class="section-hdr">Proyección por Producto</p>',unsafe_allow_html=True)
                mx_p=max(dfp["Ingreso"].max(),1);bh=""
                for _,r in dfp.iterrows():
                    ip_pct=min(r["Ingreso"]/mx_p*100,100);ut_pct=min(max(r["Utilidad"],0)/mx_p*100,100);utc=C["profit"] if r["Utilidad"]>=0 else C["loss"]
                    bh+=f'<div style="margin-bottom:1.2rem"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="color:{C["text"]};font-weight:600;font-size:.85rem">{r["Producto"]}</span><span style="color:{C["sub"]};font-size:.78rem">{int(r["Órdenes"])} órd · {int(r["% Entrega"])}%</span></div><div style="display:flex;gap:8px;align-items:center"><div style="flex:1;background:#111827;border-radius:4px;height:22px;position:relative;overflow:hidden"><div style="width:{ip_pct:.0f}%;height:100%;background:rgba(16,185,129,0.2);border-radius:4px"></div><div style="position:absolute;top:0;left:0;width:{ut_pct:.0f}%;height:100%;background:{C["profit"]};border-radius:4px;opacity:.7"></div></div><span style="font-family:JetBrains Mono;font-size:.82rem;color:{utc};width:130px;text-align:right;font-weight:600">{fmt(r["Utilidad"],pn)}</span></div><div style="display:flex;gap:16px;margin-top:3px;font-size:.7rem;color:{C["sub"]}"><span>Ingreso: {fmt(r["Ingreso"],pn)}</span><span>Costo: -{fmt(r["Costo"],pn)}</span><span>Fletes: -{fmt(r["Fletes"],pn)}</span><span>Ads: -{fmt(r["Ads"],pn)}</span></div></div>'
                st.markdown(f'<div class="kcard" style="padding:1.5rem">{bh}</div>',unsafe_allow_html=True)
                with st.expander("📝 Editar % Entrega"):
                    ed=st.data_editor(dfp,column_config={"% Entrega":st.column_config.NumberColumn("% ENTREGA",min_value=0,max_value=100,step=1,format="%d")},disabled=[c for c in dfp.columns if c!="% Entrega"],use_container_width=True,hide_index=True,key=f"pt_{pn}")
                    if ed is not None:
                        for _,r in ed.iterrows(): st.session_state[pek][r["Producto"]]=r["% Entrega"]

        # ── FIX #1,#2,#5: OPERACIÓN REAL with correct P&L + participation % ──
        with ct3:
            ir=k["ing_real"];cpr=k["cpr"];fe=k["fl_ent"];ga=k["g_ads"];fd=k["fl_dev"];ft_=k["fl_tra"];ur=k["u_real"]
            mg=(ur/ir*100) if ir>0 else 0; uc="green" if ur>=0 else "red"
            at2=f'<div class="trm">{fmt_cop(k.get("g_ads_cop",0))} COP</div>' if pi["moneda"]!="COP" else ""
            st.markdown(f'<div class="kcard {uc}" style="padding:2rem;margin-bottom:1.5rem"><div class="icon {"g" if ur>=0 else "r"}" style="width:48px;height:48px;font-size:1.3rem">💰</div><div class="lbl">UTILIDAD REAL</div><div class="val xl {uc}">{fmt(ur,pn)}</div><div class="pct">Margen: {mg:.1f}% del ingreso</div></div>', unsafe_allow_html=True)
            st.markdown(f"""<div class="row2 r3">
                <div class="kcard green"><div class="icon g">✅</div><div class="lbl">INGRESO ENTREGADOS</div><div class="val md green">{fmt(ir,pn)}</div><div class="pct">Base 100%</div><div class="sub">TOTAL DE LA ORDEN (Entregados)</div></div>
                <div class="kcard red"><div class="icon r">📦</div><div class="lbl">COSTO PRODUCTO</div><div class="val md red">-{fmt(cpr,pn)}</div><div class="pct">{pct_of(cpr,ir)} del ingreso</div></div>
                <div class="kcard red"><div class="icon r">🚚</div><div class="lbl">FLETES ENTREGADOS</div><div class="val md red">-{fmt(fe,pn)}</div><div class="pct">{pct_of(fe,ir)} del ingreso</div></div>
            </div>
            <div class="row2 r3">
                <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO ADS</div><div class="val md red">-{fmt(ga,pn)}</div>{at2}<div class="pct">{pct_of(ga,ir)} del ingreso</div></div>
                <div class="kcard red"><div class="icon r">⚠️</div><div class="lbl">FLETES DEV.</div><div class="val md red">-{fmt(fd,pn)}</div><div class="pct">{pct_of(fd,ir)} del ingreso</div></div>
                <div class="kcard"><div class="icon b">🚚</div><div class="lbl">FLETES TRÁNSITO</div><div class="val md white">-{fmt(ft_,pn)}</div><div class="pct">{pct_of(ft_,ir)} del ingreso</div></div>
            </div>""", unsafe_allow_html=True)

            # Cascade with %
            st.markdown('<p class="section-hdr">Cascada Financiera</p>',unsafe_allow_html=True)
            items=[("Ingreso Entregados",ir,True),("Costo Producto",cpr,False),("Fletes Entregados",fe,False),("Gasto Ads",ga,False),("Fletes Dev.",fd,False),("Fletes Tránsito",ft_,False)]
            mx_c=max(ir,1);ch=""
            for lb,vl,pos in items:
                bp=min(vl/mx_c*100,100);bc=C["profit"] if pos else C["loss"];sg="" if pos else "-";pc=pct_of(vl,ir)
                ch+=f'<div class="cas-row"><div class="cas-lbl">{lb}</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{bp:.0f}%;background:{bc}"></div></div><div class="cas-amt" style="color:{bc}">{sg}{fmt(vl,pn)}</div><div class="cas-pct">{pc}</div></div>'
            up=min(abs(ur)/mx_c*100,100);ucol=C["profit"] if ur>=0 else C["loss"];us="" if ur>=0 else "-"
            st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem">{ch}<div style="border-top:2px solid #1E293B;margin:8px 0"></div><div class="cas-row" style="border:none"><div class="cas-lbl" style="font-weight:700;color:#F1F5F9">UTILIDAD REAL</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{up:.0f}%;background:{ucol}"></div></div><div class="cas-amt" style="color:{ucol};font-size:.95rem">{us}{fmt(abs(ur),pn)}</div><div class="cas-pct" style="color:{ucol}">{pct_of(abs(ur),ir)}</div></div></div>', unsafe_allow_html=True)

            # Product summary in Operación Real
            if gcol and gcol in df_ord.columns:
                st.markdown('<p class="section-hdr">P&L por Producto</p>',unsafe_allow_html=True)
                pnl_rows=[]
                for prod in df_ord[gcol].dropna().unique():
                    dp=df_ord[df_ord[gcol]==prod]
                    de_p=dp[dp["ESTATUS"].apply(lambda s:match_status(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
                    ir_p=de_p["TOTAL DE LA ORDEN"].sum() if not de_p.empty else 0
                    cp_p=de_p["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de_p.empty and "PRECIO PROVEEDOR X CANTIDAD" in de_p.columns) else 0
                    fe_p=de_p["PRECIO FLETE"].sum() if (not de_p.empty and F.get("PRECIO FLETE")) else 0
                    ap_p=gxp.get(prod.upper(),0)
                    ut_p=ir_p-cp_p-fe_p-ap_p
                    pnl_rows.append({"Producto":prod,"Ingreso":ir_p,"Costo":cp_p,"Fletes":fe_p,"Ads":ap_p,"Utilidad":ut_p})
                if pnl_rows:
                    dfpnl=pd.DataFrame(pnl_rows).sort_values("Ingreso",ascending=False)
                    mx_pnl=max(dfpnl["Ingreso"].max(),1); prh=""
                    for _,r in dfpnl.iterrows():
                        bp=min(r["Ingreso"]/mx_pnl*100,100);utc=C["profit"] if r["Utilidad"]>=0 else C["loss"]
                        mg_p=pct_of(r["Utilidad"],r["Ingreso"])
                        prh+=f'<div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #111827"><div style="width:180px;font-size:.82rem;color:{C["text"]};font-weight:500">{r["Producto"]}</div><div style="flex:1;margin:0 12px"><div style="background:#111827;border-radius:3px;height:16px;overflow:hidden"><div style="width:{bp:.0f}%;height:100%;background:{C["profit"]};opacity:.4;border-radius:3px"></div></div></div><div style="width:100px;text-align:right;font-family:JetBrains Mono;font-size:.78rem;color:{C["text"]}">{fmt(r["Ingreso"],pn)}</div><div style="width:90px;text-align:right;font-family:JetBrains Mono;font-size:.78rem;color:{utc}">{fmt(r["Utilidad"],pn)}</div><div style="width:60px;text-align:right;font-size:.72rem;color:{utc}">{mg_p}</div></div>'
                    st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem"><div style="display:flex;padding:0 0 8px;border-bottom:1px solid #1E293B;margin-bottom:4px"><div style="width:180px;font-size:.68rem;color:#64748B;text-transform:uppercase">Producto</div><div style="flex:1"></div><div style="width:100px;text-align:right;font-size:.68rem;color:#64748B">Ingreso</div><div style="width:90px;text-align:right;font-size:.68rem;color:#64748B">Utilidad</div><div style="width:60px;text-align:right;font-size:.68rem;color:#64748B">Margen</div></div>{prh}</div>',unsafe_allow_html=True)

        with ct4:
            st.markdown(f'<p class="section-hdr">Órdenes — {len(df_ord):,}</p>',unsafe_allow_html=True)
            cols=[c for c in ["ID","FECHA","PRODUCTO","CANTIDAD","TOTAL DE LA ORDEN","PRECIO FLETE","CIUDAD DESTINO","ESTATUS"] if c in df_ord.columns]
            if cols:
                dfo=df_ord[cols].copy()
                if "FECHA" in dfo.columns: dfo=dfo.sort_values("FECHA",ascending=False)
                nr=len(dfo);hmap={"ID":"ID","FECHA":"FECHA","PRODUCTO":"PRODUCTO","CANTIDAD":"CANT.","TOTAL DE LA ORDEN":"TOTAL","PRECIO FLETE":"FLETE","CIUDAD DESTINO":"CIUDAD","ESTATUS":"ESTADO"}
                hdrs="".join(f"<th>{hmap.get(c,c)}</th>" for c in cols);ps=50;opk=f"op_{pn}"
                if opk not in st.session_state: st.session_state[opk]=0
                tp=max(1,(nr-1)//ps+1);s=st.session_state[opk]*ps;e=min(s+ps,nr);rh=""
                for _,row in dfo.iloc[s:e].iterrows():
                    tds=""
                    for c in cols:
                        v=row[c]
                        if c=="ID": tds+=f'<td class="id">{v}</td>'
                        elif c=="FECHA": tds+=f'<td>{v.strftime("%d %b %Y") if pd.notna(v) else "-"}</td>'
                        elif c in ("TOTAL DE LA ORDEN","PRECIO FLETE"): tds+=f'<td class="mono">{fmt(v,pn)}</td>'
                        elif c=="CANTIDAD": tds+=f'<td style="text-align:center">{int(v)}</td>'
                        elif c=="ESTATUS": tds+=f'<td>{status_pill(str(v))}</td>'
                        elif c=="CIUDAD DESTINO": tds+=f'<td>{str(v).title() if pd.notna(v) else "-"}</td>'
                        else: tds+=f'<td>{v}</td>'
                    rh+=f"<tr>{tds}</tr>"
                st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead><tr>{hdrs}</tr></thead><tbody>{rh}</tbody></table></div>',unsafe_allow_html=True)
                pc1,pc2,pc3=st.columns([1,2,1])
                with pc1:
                    if st.button("←",disabled=st.session_state[opk]==0,key=f"pv_{pn}"): st.session_state[opk]-=1;st.rerun()
                with pc2: st.markdown(f'<p style="text-align:center;color:#64748B;font-size:.85rem">{st.session_state[opk]+1}/{tp}</p>',unsafe_allow_html=True)
                with pc3:
                    if st.button("→",disabled=st.session_state[opk]>=tp-1,key=f"nx_{pn}"): st.session_state[opk]+=1;st.rerun()


# ═══════════════ TAB: PUBLICIDAD ═══════════════
with tabs[-1]:
    st.markdown('<p class="section-hdr">Publicidad</p>',unsafe_allow_html=True)
    tfc=sum(cd["kpis"].get("g_fb_cop",0) for cd in country_data.values());ttc=sum(cd["kpis"].get("g_tt_cop",0) for cd in country_data.values());tac=tfc+ttc
    to_p=sum(cd["kpis"]["n_ord"] for cd in country_data.values());te_p=sum(cd["kpis"]["n_ent"] for cd in country_data.values())
    cpa_o=tac/to_p if to_p>0 else 0;cpa_e=tac/te_p if te_p>0 else 0
    st.markdown(f'<div class="row2 r4"><div class="kcard purple"><div class="icon p">📢</div><div class="lbl">GASTO TOTAL</div><div class="val lg purple">{fmt_cop(tac)}</div></div><div class="kcard blue"><div class="icon b">📘</div><div class="lbl">FACEBOOK</div><div class="val lg blue">{fmt_cop(tfc)}</div></div><div class="kcard"><div class="icon w">🎵</div><div class="lbl">TIKTOK</div><div class="val lg white">{fmt_cop(ttc)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">CPA ORDEN</div><div class="val lg red">{fmt_cop(cpa_o)}</div><div class="sub">CPA Ent: {fmt_cop(cpa_e)}</div></div></div>',unsafe_allow_html=True)
    if gxp:
        pa=pd.DataFrame([{"Producto":k,"Gasto":v} for k,v in sorted(gxp.items(),key=lambda x:-x[1])])
        fp=px.bar(pa,x="Producto",y="Gasto",color_discrete_sequence=[C["purple"]]);fp.update_layout(**pl(title="GASTO POR PRODUCTO (COP)"));fp.update_traces(hovertemplate="%{y:,.0f}<extra></extra>")
        st.plotly_chart(fp,use_container_width=True,key="ap")
        cpa_r=[]
        for pn2,cd2 in country_data.items():
            gc2="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in cd2["df_ord"].columns else "PRODUCTO"
            if gc2 not in cd2["df_ord"].columns: continue
            for pr in cd2["df_ord"][gc2].dropna().unique():
                dp2=cd2["df_ord"][cd2["df_ord"][gc2]==pr];n2=len(dp2);a2=gxp.get(pr.upper(),0)
                if n2>0 and a2>0: cpa_r.append({"Producto":pr,"CPA":round(a2/n2),"N":n2})
        if cpa_r:
            dfc=pd.DataFrame(cpa_r);fc2=px.bar(dfc,x="Producto",y="CPA",color_discrete_sequence=[C["orange"]],text="CPA");fc2.update_layout(**pl(title="CPA POR PRODUCTO"));fc2.update_traces(texttemplate="%{y:,.0f}",textposition="outside",hovertemplate="%{y:,.0f}<extra></extra>")
            st.plotly_chart(fc2,use_container_width=True,key="cpa")
    else: st.info("Conecta Facebook Ads y mapea campañas.")

st.divider()
ld=sum(1 for p in PAISES if st.session_state.get(f"_b_{p}"))
st.markdown(f'<div style="text-align:center;color:#475569;font-size:.75rem">Profit Dashboard v4.3 · {ld} países · {f_ini.strftime("%d/%m")} – {f_fin.strftime("%d/%m/%Y")}</div>',unsafe_allow_html=True)
