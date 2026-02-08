"""
Ecommerce Profit Dashboard v4.2
Multi-Country · Dark Finance · Dropi + Facebook + TikTok
Currency Conversion with TRM
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
C = dict(profit="#10B981", loss="#EF4444", warn="#F59E0B", blue="#3B82F6",
         purple="#8B5CF6", orange="#F97316", cyan="#06B6D4", muted="#64748B",
         text="#E2E8F0", sub="#94A3B8", grid="#1E293B", bg="#0B0F19")


def pl(**kw):
    b = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
             font=dict(family="Inter,system-ui,sans-serif", color=C["text"], size=12),
             xaxis=dict(gridcolor=C["grid"], zerolinecolor=C["grid"]),
             yaxis=dict(gridcolor=C["grid"], zerolinecolor=C["grid"]),
             margin=dict(l=40, r=20, t=50, b=40),
             legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11, color=C["sub"])))
    b.update(kw)
    return b


# ═══════════════════════ CSS ═══════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#0B0F19!important;color:#E2E8F0!important;font-family:'Inter',system-ui,sans-serif!important}
header[data-testid="stHeader"]{background:#0B0F19!important}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0F1420,#080C14)!important;border-right:1px solid #1E293B!important}
section[data-testid="stSidebar"] *{color:#E2E8F0!important}
section[data-testid="stSidebar"] .stSelectbox>div>div,
section[data-testid="stSidebar"] .stTextInput>div>div>input,
section[data-testid="stSidebar"] .stDateInput>div>div>input,
section[data-testid="stSidebar"] .stNumberInput>div>div>input,
section[data-testid="stSidebar"] .stMultiSelect>div>div{background:#1E293B!important;border-color:#334155!important;color:#E2E8F0!important;border-radius:.5rem!important}
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
[data-testid="stFileUploader"] label{color:#E2E8F0!important}
[data-testid="stFileUploader"] small{color:#64748B!important}
[data-testid="stFileUploader"] button{background:#1E293B!important;color:#E2E8F0!important;border:1px solid #334155!important}
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
.row2{display:grid;gap:1rem;margin-bottom:1rem}.r2{grid-template-columns:1fr 1fr}.r3{grid-template-columns:1fr 1fr 1fr}.r4{grid-template-columns:1fr 1fr 1fr 1fr}
.section-hdr{font-size:1.05rem;font-weight:700;color:#E2E8F0;border-left:3px solid #10B981;padding-left:12px;margin:1.5rem 0 1rem}

.cas-row{display:flex;align-items:center;padding:11px 0;border-bottom:1px solid #111827}.cas-row:last-child{border-bottom:none}
.cas-lbl{width:155px;font-size:.82rem;color:#94A3B8;flex-shrink:0}.cas-bar-wrap{flex:1;height:26px;position:relative;margin:0 16px}
.cas-bar{height:100%;border-radius:4px;min-width:4px}.cas-amt{width:140px;text-align:right;font-family:'JetBrains Mono',monospace;font-weight:600;font-size:.88rem;flex-shrink:0}

.otbl{width:100%;border-collapse:separate;border-spacing:0;font-size:.83rem}
.otbl th{padding:12px 16px;text-align:left;font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#64748B;background:#111827;border-bottom:1px solid #1E293B}
.otbl td{padding:14px 16px;border-bottom:1px solid rgba(15,20,32,0.8);color:#E2E8F0}
.otbl tr:hover td{background:#131A2B}
.otbl .id{color:#64748B;font-family:'JetBrains Mono',monospace;font-size:.78rem}
.otbl .mono{font-family:'JetBrains Mono',monospace}
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:9999px;font-size:.72rem;font-weight:600}
.p-ent{background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3)}
.p-can{background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3)}
.p-tra{background:rgba(245,158,11,0.15);color:#F59E0B;border:1px solid rgba(245,158,11,0.3)}
.p-dev{background:rgba(249,115,22,0.15);color:#F97316;border:1px solid rgba(249,115,22,0.3)}
.p-env{background:rgba(59,130,246,0.15);color:#3B82F6;border:1px solid rgba(59,130,246,0.3)}
.p-pen{background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)}
.p-nov{background:rgba(139,92,246,0.15);color:#8B5CF6;border:1px solid rgba(139,92,246,0.3)}

.lgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1rem;margin:1rem 0}
.litem{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.1rem;text-align:center}
.litem h3{font-size:1.4rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin:.3rem 0}
.litem p{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;margin:0}
.badge{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:.75rem;font-weight:600;font-family:'JetBrains Mono',monospace}

.thermo{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.2rem 1.5rem;margin:1rem 0}
.thermo .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.thermo .tt{font-size:.78rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#94A3B8}
.thermo .tv{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.15rem;color:#10B981}
.thermo .bar{height:12px;border-radius:6px;background:linear-gradient(90deg,#EF4444 0%,#F59E0B 50%,#10B981 100%);position:relative;margin-bottom:6px}
.thermo .mk{position:absolute;top:-4px;width:3px;height:20px;background:#FFF;border-radius:2px}
.thermo .lb{display:flex;justify-content:space-between;font-size:.68rem;color:#64748B}

.date-bar{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:.8rem 1.5rem;margin-bottom:1.2rem;display:flex;align-items:center;gap:1rem}
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


# ── Currency Conversion ──
@st.cache_data(ttl=3600, show_spinner=False)
def get_trm():
    """Get COP→USD and COP→GTQ rates. Returns dict with rates."""
    rates = {"COP_USD": 4200, "COP_GTQ": 540}  # Fallback defaults
    try:
        # Try exchangerate API
        r = requests.get("https://open.er-api.com/v6/latest/COP", timeout=10)
        if r.status_code == 200:
            d = r.json()
            if "rates" in d:
                rates["COP_USD"] = 1 / d["rates"].get("USD", 1/4200)
                rates["COP_GTQ"] = 1 / d["rates"].get("GTQ", 1/540)
    except Exception:
        pass
    try:
        r2 = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if r2.status_code == 200:
            d2 = r2.json()
            if "rates" in d2:
                rates["COP_USD"] = d2["rates"].get("COP", 4200)
                rates["COP_GTQ"] = d2["rates"].get("COP", 4200) / d2["rates"].get("GTQ", 7.75)
    except Exception:
        pass
    return rates


def convert_cop_to(amount_cop, target_currency, trm_rates):
    """Convert COP amount to target currency."""
    if target_currency == "COP":
        return amount_cop
    elif target_currency == "USD":
        rate = trm_rates.get("COP_USD", 4200)
        return amount_cop / rate if rate > 0 else 0
    elif target_currency == "GTQ":
        rate = trm_rates.get("COP_GTQ", 540)
        return amount_cop / rate if rate > 0 else 0
    return amount_cop


def convert_to_cop(amount, source_currency, trm_rates):
    """Convert any currency TO COP."""
    if source_currency == "COP":
        return amount
    elif source_currency == "USD":
        return amount * trm_rates.get("COP_USD", 4200)
    elif source_currency == "GTQ":
        return amount * trm_rates.get("COP_GTQ", 540)
    return amount


@st.cache_data(show_spinner=False)
def cargar(data_bytes, name):
    import io
    buf = io.BytesIO(data_bytes)
    if name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(buf, dtype=str, engine="openpyxl")
    else:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try: buf.seek(0); df = pd.read_csv(buf, dtype=str, encoding=enc, sep=None, engine="python"); break
            except Exception: continue
        else: buf.seek(0); df = pd.read_csv(buf, dtype=str, encoding="latin-1", on_bad_lines="skip")
    df.columns = df.columns.str.strip().str.upper()
    alias = {"TOTAL DE LA ORDEN":["TOTAL DE LA ORDEN","TOTAL_DE_LA_ORDEN"],"PRECIO PROVEEDOR":["PRECIO PROVEEDOR","PRECIO_PROVEEDOR"],
             "PRECIO FLETE":["PRECIO FLETE","PRECIO_FLETE"],"COSTO DEVOLUCION FLETE":["COSTO DEVOLUCION FLETE","COSTO_DEVOLUCION_FLETE"],
             "GANANCIA":["GANANCIA","PROFIT"],"CANTIDAD":["CANTIDAD","QTY"],"ESTATUS":["ESTATUS","STATUS","ESTADO"],
             "PRODUCTO":["PRODUCTO","PRODUCT"],"FECHA":["FECHA","DATE"],"CIUDAD DESTINO":["CIUDAD DESTINO","CIUDAD"]}
    for canon, vs in alias.items():
        for v in vs:
            if v in df.columns and canon not in df.columns: df.rename(columns={v: canon}, inplace=True); break
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
    cities_co = {"BOGOTA","BOGOTÁ","MEDELLIN","MEDELLÍN","CALI","BARRANQUILLA","CARTAGENA","BUCARAMANGA","PEREIRA","CUCUTA","CÚCUTA","MANIZALES","IBAGUE","IBAGUÉ","PASTO","SANTA MARTA","VILLAVICENCIO","NEIVA","MONTERIA","MONTERÍA","POPAYAN","POPAYÁN","ARMENIA","SINCELEJO","VALLEDUPAR","TUNJA","DOSQUEBRADAS"}
    cities_ec = {"QUITO","GUAYAQUIL","CUENCA","AMBATO","PORTOVIEJO","MACHALA","DURÁN","LOJA","MANTA","SANTO DOMINGO","RIOBAMBA","ESMERALDAS","IBARRA","LATACUNGA"}
    cities_gt = {"GUATEMALA","MIXCO","VILLA NUEVA","QUETZALTENANGO","ESCUINTLA","CHINAUTLA","AMATITLAN","HUEHUETENANGO","COBAN","COBÁN","CHIMALTENANGO","ANTIGUA","JALAPA","JUTIAPA","RETALHULEU","MAZATENANGO","ZACAPA"}
    if "CIUDAD DESTINO" in df.columns:
        ciudades = set(df["CIUDAD DESTINO"].dropna().str.upper().str.strip().unique())
        scores = {"Colombia": len(ciudades & cities_co), "Ecuador": len(ciudades & cities_ec), "Guatemala": len(ciudades & cities_gt)}
        best = max(scores, key=scores.get)
        if scores[best] > 0: return best
    return None

def extraer_base_producto(nombre):
    n = re.sub(r'\s*-\s*', ' ', str(nombre).strip().upper())
    words = [w for w in n.split() if not re.match(r'^\d+$', w) and w not in ("X","DE","EL","LA","EN","CON","PARA","POR")]
    return " ".join(words[:2]) if words else n

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

def fmt(v, pais_name="Colombia"):
    sym = PAISES.get(pais_name, PAISES["Colombia"])["sym"]
    return f"{sym} {v:,.0f}".replace(",", ".")

def fmt_cop(v):
    return f"$ {v:,.0f}".replace(",", ".")

def fb_spend_acct(tok, cid, i, f):
    if not tok or not cid: return 0.0
    cid = cid.strip()
    if not cid.startswith("act_"): cid = f"act_{cid}"
    try:
        r = requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",
            params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"spend","level":"account"},timeout=30)
        d = r.json()
        if "data" in d and d["data"]: return float(d["data"][0].get("spend",0))
    except Exception: pass
    return 0.0

def fb_camps_acct(tok, cid, i, f):
    if not tok or not cid: return pd.DataFrame(columns=["campaign_name","spend"])
    cid = cid.strip()
    if not cid.startswith("act_"): cid = f"act_{cid}"
    try:
        r = requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",
            params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"campaign_name,spend","level":"campaign","limit":500},timeout=30)
        d = r.json()
        if "data" in d: return pd.DataFrame([{"campaign_name":x.get("campaign_name",""),"spend":float(x.get("spend",0))} for x in d["data"]])
    except Exception: pass
    return pd.DataFrame(columns=["campaign_name","spend"])

def fb_list_accts(tok):
    if not tok: return []
    try:
        r = requests.get("https://graph.facebook.com/v21.0/me/adaccounts",
            params={"access_token":tok,"fields":"name,account_id,currency","limit":50},timeout=15)
        d = r.json()
        if "data" in d: return [{"id":a.get("account_id",""),"name":a.get("name",""),"cur":a.get("currency","")} for a in d["data"]]
    except Exception: pass
    return []

def tt_spend_acct(tok, aid, i, f):
    if not tok or not aid: return 0.0
    try:
        r = requests.post("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",
            headers={"Access-Token":tok,"Content-Type":"application/json"},
            json={"advertiser_id":aid,"report_type":"BASIC","data_level":"AUCTION_ADVERTISER","dimensions":["advertiser_id"],"metrics":["spend"],"start_date":i,"end_date":f},timeout=30)
        d = r.json()
        if d.get("code")==0 and d.get("data",{}).get("list"): return float(d["data"]["list"][0]["metrics"].get("spend",0))
    except Exception: pass
    return 0.0

def extraer_prod_camp(n):
    p = [x.strip() for x in str(n).split("-")]
    return p[1].strip().upper() if len(p) >= 2 else n.strip().upper()

def status_pill(s):
    s = s.upper()
    if "ENTREGADO" in s: return '<span class="pill p-ent">✅ Entregado</span>'
    if "CANCELADO" in s: return '<span class="pill p-can">⊘ Cancelado</span>'
    if "DEVOLUCION" in s or "DEVOLUCIÓN" in s: return '<span class="pill p-dev">↩ Devolución</span>'
    if "TRÁNSITO" in s or "TRANSITO" in s: return '<span class="pill p-tra">🚚 En Tránsito</span>'
    if "DESPACHADA" in s or "GUIA" in s or "ENVIADO" in s: return '<span class="pill p-env">✈ Enviado</span>'
    if "NOVEDAD" in s: return '<span class="pill p-nov">⚠ Novedad</span>'
    if "REPARTO" in s or "RUTA" in s or "BODEGA" in s: return '<span class="pill p-tra">📦 En Camino</span>'
    return '<span class="pill p-pen">⏳ Pendiente</span>'

def aggregate_orders(df):
    F = {c: c in df.columns for c in ["ID","ESTATUS","TOTAL DE LA ORDEN","PRODUCTO","CANTIDAD","GANANCIA","PRECIO FLETE","PRECIO PROVEEDOR","COSTO DEVOLUCION FLETE","CIUDAD DESTINO","FECHA","GRUPO_PRODUCTO","PRECIO PROVEEDOR X CANTIDAD"]}
    if not F["ID"]: return df, F
    ag = {}
    for c, fn in [("TOTAL DE LA ORDEN","first"),("ESTATUS","first"),("PRECIO FLETE","first"),("COSTO DEVOLUCION FLETE","first"),("GANANCIA","sum"),("FECHA","first"),("CIUDAD DESTINO","first"),("PRODUCTO","first"),("CANTIDAD","sum"),("PRECIO PROVEEDOR","first"),("PRECIO PROVEEDOR X CANTIDAD","sum"),("GRUPO_PRODUCTO","first")]:
        if c in df.columns: ag[c] = fn
    return (df.groupby("ID").agg(ag).reset_index() if ag else df.copy()), F

def calc_kpis(df_ord, F, g_fb, g_tt):
    n_ord = df_ord["ID"].nunique() if F.get("ID") else len(df_ord)
    fact_bruto = df_ord["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    df_nc = df_ord[df_ord["ESTATUS"]!="CANCELADO"] if F.get("ESTATUS") else df_ord
    fact_neto = df_nc["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    n_desp = len(df_nc); aov = fact_bruto/n_ord if n_ord>0 else 0
    g_ads = g_fb + g_tt; roas = fact_neto/g_ads if g_ads>0 else 0
    sc = df_ord["ESTATUS"].value_counts().to_dict() if F.get("ESTATUS") else {}
    n_ent = sum(v for k,v in sc.items() if "ENTREGADO" in k)
    n_can = sum(v for k,v in sc.items() if "CANCELADO" in k)
    n_tra = sum(v for k,v in sc.items() if any(x in k for x in ["TRANSITO","TRÁNSITO","DESPACHADA","REPARTO","RUTA","BODEGA","GUIA","ENVIADO"]))
    n_dev = sum(v for k,v in sc.items() if "DEVOLUCION" in k or "DEVOLUCIÓN" in k)
    n_nov = sum(v for k,v in sc.items() if "NOVEDAD" in k)
    n_otr = max(0, n_ord-n_ent-n_can-n_tra-n_dev-n_nov)
    n_nc = n_ord - n_can
    pct_can = (n_can/n_ord*100) if n_ord>0 else 0
    pct_ent = (n_ent/n_nc*100) if n_nc>0 else 0
    de = df_ord[df_ord["ESTATUS"]=="ENTREGADO"] if F.get("ESTATUS") else pd.DataFrame()
    ing_real = de["GANANCIA"].sum() if (not de.empty and F.get("GANANCIA")) else 0
    cpr = 0
    if not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns: cpr = de["PRECIO PROVEEDOR X CANTIDAD"].sum()
    elif not de.empty and F.get("PRECIO PROVEEDOR") and F.get("CANTIDAD"): cpr = (de["PRECIO PROVEEDOR"]*de["CANTIDAD"]).sum()
    dd = df_ord[df_ord["ESTATUS"].isin(["DEVOLUCION","DEVOLUCIÓN"])].copy() if F.get("ESTATUS") else pd.DataFrame()
    fl_dev = 0
    if not dd.empty:
        if F.get("PRECIO FLETE") and F.get("COSTO DEVOLUCION FLETE"): fl_dev = dd[["PRECIO FLETE","COSTO DEVOLUCION FLETE"]].max(axis=1).sum()
        elif F.get("PRECIO FLETE"): fl_dev = dd["PRECIO FLETE"].sum()
    dt = df_ord[df_ord["ESTATUS"].isin(["EN TRANSITO","EN TRÁNSITO","EN ESPERA DE RUTA DOMESTICA"])].copy() if F.get("ESTATUS") else pd.DataFrame()
    fl_tra = dt["PRECIO FLETE"].sum() if (not dt.empty and F.get("PRECIO FLETE")) else 0
    u_real = ing_real - cpr - g_ads - fl_dev - fl_tra
    return dict(n_ord=n_ord,fact_bruto=fact_bruto,fact_neto=fact_neto,n_desp=n_desp,aov=aov,g_fb=g_fb,g_tt=g_tt,g_ads=g_ads,roas=roas,
                n_ent=n_ent,n_can=n_can,n_tra=n_tra,n_dev=n_dev,n_nov=n_nov,n_otr=n_otr,n_nc=n_nc,pct_can=pct_can,pct_ent=pct_ent,tasa_ent=pct_ent,
                ing_real=ing_real,cpr=cpr,fl_dev=fl_dev,fl_tra=fl_tra,u_real=u_real)


# ═══════════════════════ TRM ═══════════════════════
trm = get_trm()
trm_usd = trm.get("COP_USD", 4200)
trm_gtq = trm.get("COP_GTQ", 540)


# ═══════════════════════ SIDEBAR ═══════════════════════
cfg = load_cfg()
with st.sidebar:
    st.markdown("### 📊 Profit Dashboard")
    st.caption("Multi-País · Dropi · FB · TT")
    st.divider()
    st.markdown("##### 📢 Publicidad")
    usar_api = st.checkbox("Usar APIs", value=True)
    fb_token = ""; fb_cids = []; tt_token = ""; tt_aids = []
    if usar_api:
        st.markdown("###### 📘 Facebook")
        fb_token = st.text_input("Token FB", type="password", value=cfg.get("fb_token",""), key="fbt")
        if fb_token: save_cfg("fb_token", fb_token)
        fb_accts = fb_list_accts(fb_token)
        if fb_accts:
            opts = {f"{a['name']} ({a['id']})": a["id"] for a in fb_accts}
            opt_keys = list(opts.keys())
            # SELECT ALL button
            if st.button("✅ Seleccionar todas las cuentas FB", key="sel_all_fb"):
                st.session_state["fb_sel"] = opt_keys
            default_sel = st.session_state.get("fb_sel", [])
            valid_def = [x for x in default_sel if x in opt_keys]
            sel = st.multiselect("Cuentas FB", opt_keys, default=valid_def, key="fb_multi")
            st.session_state["fb_sel"] = sel
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
        st.markdown("##### 💵 Ads Manual por País")
        for pn in PAISES:
            ads_manual[pn] = st.number_input(f"Gasto {pn} ({PAISES[pn]['moneda']})", min_value=0.0, value=0.0, step=1000.0, key=f"gm_{pn}")


# ═══════════════════════ INIT ═══════════════════════
for pn in PAISES:
    for k in (f"_b_{pn}", f"_n_{pn}"):
        if k not in st.session_state: st.session_state[k] = None


# ═══════════════════════ TITLE + DATES (VISIBLE!) ═══════════════════════
st.markdown('<p style="text-align:center;font-size:1.8rem;font-weight:800;color:#F1F5F9;letter-spacing:-0.02em;margin-bottom:.5rem">📊 Ecommerce Profit Dashboard</p>', unsafe_allow_html=True)

# Date selector — VISIBLE in main area
hoy = datetime.today().date()
dc1, dc2, dc3 = st.columns([1, 1, 3])
with dc1:
    f_ini = st.date_input("📅 Desde", value=hoy - timedelta(days=30), key="d_ini")
with dc2:
    f_fin = st.date_input("📅 Hasta", value=hoy, key="d_fin")
with dc3:
    st.markdown(f"""
    <div style="padding-top:1.6rem">
        <span style="color:{C['sub']};font-size:.8rem">TRM: <b style="color:{C['text']}">1 USD = {trm_usd:,.0f} COP</b> · <b style="color:{C['text']}">1 GTQ ≈ {trm_gtq:,.0f} COP</b></span>
    </div>
    """, unsafe_allow_html=True)

# Check data
any_data = any(st.session_state.get(f"_b_{pn}") for pn in PAISES)

if not any_data:
    st.divider()
    st.markdown('<p class="section-hdr">Sube tus archivos de Dropi</p>', unsafe_allow_html=True)
    st.markdown("#### 🔍 Auto-detectar país")
    f_auto = st.file_uploader("Arrastra tu archivo aquí o haz clic para seleccionar",
                               type=["csv","xlsx","xls"], key="up_auto_main", label_visibility="collapsed")
    if f_auto:
        temp_df = cargar(f_auto.getvalue(), f_auto.name)
        detected = detect_country(temp_df)
        if detected:
            st.session_state[f"_b_{detected}"] = f_auto.getvalue()
            st.session_state[f"_n_{detected}"] = f_auto.name
            st.success(f"✅ {PAISES[detected]['flag']} {detected} — {len(temp_df):,} filas")
            st.rerun()
        else:
            st.warning("No se pudo detectar. Selecciona manualmente:")
    st.markdown("#### 📁 O sube por país")
    cols_up = st.columns(len(PAISES))
    for i, (pn, pi) in enumerate(PAISES.items()):
        with cols_up[i]:
            f = st.file_uploader(f"{pi['flag']} {pn}", type=["csv","xlsx","xls"], key=f"up_main_{pn}")
            if f: st.session_state[f"_b_{pn}"] = f.getvalue(); st.session_state[f"_n_{pn}"] = f.name; st.rerun()
    st.stop()

# Sidebar uploads when data exists
with st.sidebar:
    st.divider()
    st.markdown("##### 📁 Archivos Dropi")
    for pn, pi in PAISES.items():
        f = st.file_uploader(f"{pi['flag']} {pn}", type=["csv","xlsx","xls"], key=f"up_sb_{pn}")
        if f: st.session_state[f"_b_{pn}"] = f.getvalue(); st.session_state[f"_n_{pn}"] = f.name; st.rerun()
        if st.session_state.get(f"_b_{pn}"): st.caption(f"✅ {st.session_state[f'_n_{pn}']}")


# ═══════════════════════ LOAD DATA ═══════════════════════
si, sf = f_ini.strftime("%Y-%m-%d"), f_fin.strftime("%Y-%m-%d")
country_data = {}
persistent_maps = load_mappings()
gxp = {}  # ← FIX: initialize gxp before any conditional

# Campaigns
all_camps = pd.DataFrame(columns=["campaign_name","spend"])
if usar_api:
    for c in fb_cids: all_camps = pd.concat([all_camps, fb_camps_acct(fb_token, c, si, sf)])

# Total ads in COP
if usar_api:
    gfb_total_cop = sum(fb_spend_acct(fb_token, c, si, sf) for c in fb_cids)  # Already COP
    gtt_total_cop = sum(tt_spend_acct(tt_token, a, si, sf) for a in tt_aids)
else:
    # Manual: user enters in LOCAL currency, convert to COP
    gfb_total_cop = sum(convert_to_cop(ads_manual.get(pn, 0), PAISES[pn]["moneda"], trm) for pn in PAISES)
    gtt_total_cop = 0

# Load countries
country_raw_lens = {}
total_rows_all = 0
for pn in PAISES:
    if st.session_state.get(f"_b_{pn}") is None: continue
    df_raw = cargar(st.session_state[f"_b_{pn}"], st.session_state[f"_n_{pn}"])
    df_f = filtrar_fecha(df_raw, f_ini, f_fin)
    if df_f.empty: continue
    country_raw_lens[pn] = len(df_f)
    total_rows_all += len(df_f)

for pn in PAISES:
    if st.session_state.get(f"_b_{pn}") is None: continue
    df_raw = cargar(st.session_state[f"_b_{pn}"], st.session_state[f"_n_{pn}"])
    df_f = filtrar_fecha(df_raw, f_ini, f_fin)
    if df_f.empty: continue
    moneda_pais = PAISES[pn]["moneda"]

    if "PRODUCTO" in df_f.columns:
        saved = persistent_maps.get(pn, {})
        if saved: df_f = apply_groups(df_f, saved)
        else:
            auto_g = build_product_groups(sorted(df_f["PRODUCTO"].dropna().unique()))
            df_f = apply_groups(df_f, auto_g)
            persistent_maps[pn] = auto_g; save_mappings(persistent_maps)

    df_ord, F = aggregate_orders(df_f)

    # Ads: distribute COP total by country ratio, then convert to local currency
    if usar_api:
        ratio = country_raw_lens.get(pn, 0) / max(total_rows_all, 1)
        gfb_cop = gfb_total_cop * ratio
        gtt_cop = gtt_total_cop * ratio
        # Convert COP ads to local currency for this country
        gfb_local = convert_cop_to(gfb_cop, moneda_pais, trm)
        gtt_local = convert_cop_to(gtt_cop, moneda_pais, trm)
    else:
        gfb_local = ads_manual.get(pn, 0)
        gtt_local = 0
        gfb_cop = convert_to_cop(gfb_local, moneda_pais, trm)
        gtt_cop = 0

    kpis = calc_kpis(df_ord, F, gfb_local, gtt_local)
    kpis["g_fb_cop"] = gfb_cop
    kpis["g_tt_cop"] = gtt_cop
    kpis["g_ads_cop"] = gfb_cop + gtt_cop
    country_data[pn] = {"df": df_f, "df_ord": df_ord, "kpis": kpis, "camps": all_camps, "F": F}

if not country_data:
    st.warning("Sin datos en el rango seleccionado.")
    st.stop()


# ═══════════════════════ PRODUCT MAPPING ═══════════════════════
with st.expander("📦 Agrupación de Productos (persistente)", expanded=False):
    for pn, cd in country_data.items():
        if "PRODUCTO" not in cd["df"].columns: continue
        st.markdown(f"**{PAISES[pn]['flag']} {pn}**")
        saved = persistent_maps.get(pn, {})
        rows = []
        for gn, members in saved.items():
            for m in members: rows.append({"Producto Original":m,"Grupo":gn})
        if not rows:
            for p in sorted(cd["df"]["PRODUCTO"].dropna().unique()): rows.append({"Producto Original":p,"Grupo":extraer_base_producto(p)})
        df_pg = pd.DataFrame(rows)
        edited_pg = st.data_editor(df_pg, use_container_width=True, hide_index=True, key=f"pg_{pn}", num_rows="dynamic")
        if st.button(f"💾 Guardar {pn}", key=f"save_pg_{pn}"):
            ng = defaultdict(list)
            for _,r in edited_pg.iterrows():
                o=str(r.get("Producto Original","")).strip(); g=str(r.get("Grupo","")).strip()
                if o and g: ng[g].append(o)
            persistent_maps[pn] = dict(ng); save_mappings(persistent_maps)
            st.success(f"✅ Guardado {pn}"); st.rerun()

# Campaign mapping
if not all_camps.empty:
    with st.expander("🔗 Mapeo Campañas FB → Grupo Producto", expanded=False):
        grp_list = []
        for pn, cd in country_data.items():
            if "GRUPO_PRODUCTO" in cd["df_ord"].columns: grp_list.extend(cd["df_ord"]["GRUPO_PRODUCTO"].dropna().unique().tolist())
        grp_list = sorted(set(grp_list))
        pfb = sorted(all_camps["campaign_name"].apply(extraer_prod_camp).unique().tolist())
        if "mapeo" not in st.session_state:
            rows = []
            for p in pfb:
                m = p
                for g in grp_list:
                    if p.upper() in g.upper() or g.upper() in p.upper(): m = g; break
                rows.append({"Campaña Facebook":p,"Grupo Producto":m})
            if not rows: rows = [{"Campaña Facebook":g,"Grupo Producto":g} for g in grp_list]
            st.session_state["mapeo"] = pd.DataFrame(rows)
        me = st.data_editor(st.session_state["mapeo"], num_rows="dynamic", use_container_width=True, key="me")
        if st.button("🔄 Actualizar Mapeo", key="btn_mapeo"): st.session_state["mapeo"] = me; st.rerun()

    md = {}
    if "mapeo" in st.session_state:
        for _,r in st.session_state["mapeo"].iterrows():
            a=str(r.get("Campaña Facebook","")).strip().upper(); b=str(r.get("Grupo Producto","")).strip().upper()
            if a and b: md[a]=b
    if md and not all_camps.empty:
        all_camps_copy = all_camps.copy()
        all_camps_copy["pf"] = all_camps_copy["campaign_name"].apply(lambda x: extraer_prod_camp(x).upper())
        all_camps_copy["pd"] = all_camps_copy["pf"].map(md).fillna(all_camps_copy["pf"])
        gxp = all_camps_copy.groupby("pd")["spend"].sum().to_dict()


# ═══════════════════════ TABS ═══════════════════════
tab_names = ["🏠 Dashboard Global"]
for pn in country_data: tab_names.append(f"{PAISES[pn]['flag']} {pn}")
tab_names.append("📢 Publicidad")
tabs = st.tabs(tab_names)


# ═══════════════ TAB: DASHBOARD GLOBAL ═══════════════
with tabs[0]:
    # ── TOTALS (all countries converted to COP) ──
    tot_ord = sum(cd["kpis"]["n_ord"] for cd in country_data.values())
    tot_fact_cop = sum(convert_to_cop(cd["kpis"]["fact_neto"], PAISES[pn]["moneda"], trm) for pn, cd in country_data.items())
    tot_ads_cop = sum(cd["kpis"].get("g_ads_cop", 0) for cd in country_data.values())
    tot_util_cop = tot_fact_cop - tot_ads_cop  # Simplified total
    tot_roas = tot_fact_cop / tot_ads_cop if tot_ads_cop > 0 else 0

    st.markdown(f"""
    <p class="section-hdr">Total Operación (en COP)</p>
    <div class="row2 r4">
        <div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES TOTALES</div><div class="val lg white">{tot_ord:,}</div></div>
        <div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO NETO TOTAL</div><div class="val lg green">{fmt_cop(tot_fact_cop)}</div></div>
        <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO ADS TOTAL</div><div class="val lg red">{fmt_cop(tot_ads_cop)}</div></div>
        <div class="kcard {'green' if tot_util_cop>=0 else 'red'}"><div class="icon {'g' if tot_util_cop>=0 else 'r'}">💰</div><div class="lbl">ROAS GLOBAL</div><div class="val lg {'green' if tot_roas>=2 else 'white'}">{tot_roas:.2f}x</div></div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown('<p class="section-hdr">Detalle por País</p>', unsafe_allow_html=True)

    for pn, cd in country_data.items():
        k = cd["kpis"]; pi = PAISES[pn]
        ut_cls = "green" if k["u_real"] >= 0 else "red"
        ads_cop_txt = f'<span class="trm">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if pi["moneda"] != "COP" else ""
        st.markdown(f"""
        <div class="row2 r4" style="margin-bottom:.5rem">
            <div class="kcard"><div class="icon w">📦</div><div class="lbl">{pi['flag']} {pn.upper()} — ÓRDENES</div><div class="val lg white">{k['n_ord']:,}</div><div class="sub">{k['n_ent']} entregadas · {k['tasa_ent']:.0f}%</div></div>
            <div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO NETO</div><div class="val lg green">{fmt(k['fact_neto'],pn)}</div><div class="sub">ROAS: {k['roas']:.2f}x</div></div>
            <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO ADS</div><div class="val md red">{fmt(k['g_ads'],pn)}</div>{ads_cop_txt}<div class="sub">FB + TT</div></div>
            <div class="kcard {ut_cls}"><div class="icon {'g' if k['u_real']>=0 else 'r'}">💰</div><div class="lbl">UTILIDAD REAL</div><div class="val lg {ut_cls}">{fmt(k['u_real'],pn)}</div></div>
        </div>
        """, unsafe_allow_html=True)

    if len(country_data) > 1:
        st.divider()
        comp = [{"País":f"{PAISES[pn]['flag']} {pn}","Facturado":convert_to_cop(cd["kpis"]["fact_neto"],PAISES[pn]["moneda"],trm),
                 "Ads":cd["kpis"].get("g_ads_cop",0),"Utilidad":convert_to_cop(cd["kpis"]["u_real"],PAISES[pn]["moneda"],trm)}
                for pn, cd in country_data.items()]
        dfc = pd.DataFrame(comp)
        m = dfc.melt(id_vars="País",var_name="Métrica",value_name="COP")
        fc = px.bar(m,x="País",y="COP",color="Métrica",barmode="group",
                    color_discrete_map={"Facturado":C["profit"],"Ads":C["loss"],"Utilidad":C["blue"]})
        fc.update_layout(**pl(title="COMPARATIVA POR PAÍS (COP)"))
        fc.update_traces(hovertemplate="%{y:,.0f}<extra></extra>")
        st.plotly_chart(fc, use_container_width=True, key="ch_comp")

    # Global logistics with %
    t_ord = sum(cd["kpis"]["n_ord"] for cd in country_data.values())
    t_ent = sum(cd["kpis"]["n_ent"] for cd in country_data.values())
    t_can = sum(cd["kpis"]["n_can"] for cd in country_data.values())
    t_tra = sum(cd["kpis"]["n_tra"] for cd in country_data.values())
    t_dev = sum(cd["kpis"]["n_dev"] for cd in country_data.values())
    t_nov = sum(cd["kpis"]["n_nov"] for cd in country_data.values())
    t_otr = sum(cd["kpis"]["n_otr"] for cd in country_data.values())
    t_nc = t_ord - t_can
    def gpof(n, base=t_nc): return f"{(n/base*100):.0f}%" if base else "0%"

    st.markdown(f"""
    <p class="section-hdr">Logística Global — {t_ord:,} órdenes</p>
    <div class="lgrid">
        <div class="litem" style="border-color:rgba(239,68,68,0.3)"><p>❌ CANCELADO</p><h3 style="color:{C['loss']}">{t_can:,}</h3><span class="badge" style="background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3)">{(t_can/t_ord*100):.0f}% total</span></div>
    </div>
    <div class="lgrid">
        <div class="litem" style="border-color:rgba(16,185,129,0.3)"><p>✅ ENTREGADO</p><h3 style="color:{C['profit']}">{t_ent:,}</h3><span class="badge" style="background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3)">{gpof(t_ent)}</span></div>
        <div class="litem" style="border-color:rgba(59,130,246,0.3)"><p>🚚 TRÁNSITO</p><h3 style="color:{C['blue']}">{t_tra:,}</h3><span class="badge" style="background:rgba(59,130,246,0.15);color:#3B82F6;border:1px solid rgba(59,130,246,0.3)">{gpof(t_tra)}</span></div>
        <div class="litem" style="border-color:rgba(245,158,11,0.3)"><p>↩️ DEVOLUCIÓN</p><h3 style="color:{C['warn']}">{t_dev:,}</h3><span class="badge" style="background:rgba(245,158,11,0.15);color:#F59E0B;border:1px solid rgba(245,158,11,0.3)">{gpof(t_dev)}</span></div>
        <div class="litem" style="border-color:rgba(249,115,22,0.3)"><p>⚠️ NOVEDAD</p><h3 style="color:{C['orange']}">{t_nov:,}</h3><span class="badge" style="background:rgba(249,115,22,0.15);color:#F97316;border:1px solid rgba(249,115,22,0.3)">{gpof(t_nov)}</span></div>
        <div class="litem" style="border-color:rgba(100,116,139,0.3)"><p>⏳ OTROS</p><h3 style="color:{C['muted']}">{t_otr:,}</h3><span class="badge" style="background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)">{gpof(t_otr)}</span></div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════ COUNTRY TABS ═══════════════
for idx, (pn, cd) in enumerate(country_data.items()):
    with tabs[idx + 1]:
        k = cd["kpis"]; df_ord = cd["df_ord"]; df_f = cd["df"]; F = cd["F"]; pi = PAISES[pn]
        ct1,ct2,ct3,ct4 = st.tabs(["🌡 Termómetro","📊 Proyecciones","💰 Operación Real","📋 Órdenes"])

        with ct1:
            rc = "green" if k["roas"]>=2 else ("red" if k["roas"]<1 else "white")
            tc = "green" if k["tasa_ent"]>=60 else ("red" if k["tasa_ent"]<40 else "white")
            ads_trm = f'<div class="trm">{fmt_cop(k.get("g_ads_cop",0))} COP</div>' if pi["moneda"]!="COP" else ""
            st.markdown(f"""
            <div class="row2 r3">
                <div class="kcard"><div class="icon w">💰</div><div class="lbl">FACTURADO BRUTO</div><div class="val lg white">{fmt(k['fact_bruto'],pn)}</div><div class="sub">{k['n_ord']:,} órdenes totales</div></div>
                <div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO NETO</div><div class="val lg green">{fmt(k['fact_neto'],pn)}</div><div class="sub">Sin cancelaciones</div></div>
                <div class="kcard"><div class="icon w">🛒</div><div class="lbl">TICKET PROMEDIO</div><div class="val lg white">{fmt(k['aov'],pn)}</div></div>
            </div>
            <div class="row2 r3">
                <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO TOTAL ADS</div><div class="val lg red">{fmt(k['g_ads'],pn)}</div>{ads_trm}<div class="sub">FB: {fmt(k['g_fb'],pn)} · TT: {fmt(k['g_tt'],pn)}</div></div>
                <div class="kcard"><div class="icon g">⚡</div><div class="lbl">ROAS BLENDED</div><div class="val lg {rc}">{k['roas']:.2f}x</div><div class="sub">{"Por encima" if k['roas']>=2 else "Por debajo"} del objetivo</div></div>
                <div class="kcard"><div class="icon g">✅</div><div class="lbl">TASA DE ENTREGA</div><div class="val lg {tc}">{k['tasa_ent']:.0f}%</div><div class="sub">{k['n_ent']} entregadas (excl. canceladas)</div></div>
            </div>
            """, unsafe_allow_html=True)
            rp = min(k["roas"]/4*100,100)
            st.markdown(f'<div class="thermo"><div class="hd"><span class="tt">TERMÓMETRO ROAS</span><span class="tv">{k["roas"]:.2f}x</span></div><div class="bar"><div class="mk" style="left:{rp:.0f}%"></div></div><div class="lb"><span>0x</span><span>2x (Objetivo)</span><span>4x+</span></div></div>', unsafe_allow_html=True)
            if F.get("FECHA") and F.get("TOTAL DE LA ORDEN"):
                daily = df_ord.groupby(df_ord["FECHA"].dt.date).agg(Fac=("TOTAL DE LA ORDEN","sum")).reset_index().rename(columns={"FECHA":"Fecha"})
                gc1,gc2 = st.columns(2)
                with gc1:
                    fig=go.Figure(); fig.add_trace(go.Scatter(x=daily["Fecha"],y=daily["Fac"],mode="lines",fill="tozeroy",fillcolor="rgba(16,185,129,0.1)",line=dict(color=C["profit"],width=2),hovertemplate="%{y:,.0f}<extra></extra>"))
                    fig.update_layout(**pl(title="FACTURACIÓN NETA")); st.plotly_chart(fig, use_container_width=True, key=f"ch_fac_{pn}")
                with gc2:
                    if F.get("ESTATUS"):
                        edf=df_ord["ESTATUS"].value_counts().reset_index(); edf.columns=["E","N"]
                        cm={s:(C["profit"] if "ENTREGADO" in s else C["loss"] if "CANCELADO" in s else C["orange"] if "DEVOLUCION" in s else C["blue"] if "TRANSITO" in s or "DESPACHADA" in s else C["warn"] if "NOVEDAD" in s else C["muted"]) for s in edf["E"]}
                        f3=px.pie(edf,names="E",values="N",hole=.55,color="E",color_discrete_map=cm)
                        f3.update_layout(**pl(showlegend=True,title="DISTRIBUCIÓN POR ESTADO"))
                        f3.update_traces(textinfo="percent",hovertemplate="%{label}: %{value}<extra></extra>"); st.plotly_chart(f3, use_container_width=True, key=f"ch_pie_{pn}")
            nnc = k["n_nc"]
            def pof(n, base=nnc): return f"{(n/base*100):.0f}%" if base else "0%"
            st.markdown(f"""
            <p class="section-hdr">Resumen Logístico — {k['n_ord']:,} órdenes totales</p>
            <div class="lgrid"><div class="litem" style="border-color:rgba(239,68,68,0.3)"><p>❌ CANCELADO</p><h3 style="color:{C['loss']}">{k['n_can']:,}</h3><span class="badge" style="background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3)">{k['pct_can']:.0f}% total</span></div></div>
            <div class="lgrid">
                <div class="litem" style="border-color:rgba(16,185,129,0.3)"><p>✅ ENTREGADO</p><h3 style="color:{C['profit']}">{k['n_ent']:,}</h3><span class="badge" style="background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3)">{pof(k['n_ent'])}</span></div>
                <div class="litem" style="border-color:rgba(59,130,246,0.3)"><p>🚚 TRÁNSITO</p><h3 style="color:{C['blue']}">{k['n_tra']:,}</h3><span class="badge" style="background:rgba(59,130,246,0.15);color:#3B82F6;border:1px solid rgba(59,130,246,0.3)">{pof(k['n_tra'])}</span></div>
                <div class="litem" style="border-color:rgba(245,158,11,0.3)"><p>↩️ DEVOLUCIÓN</p><h3 style="color:{C['warn']}">{k['n_dev']:,}</h3><span class="badge" style="background:rgba(245,158,11,0.15);color:#F59E0B;border:1px solid rgba(245,158,11,0.3)">{pof(k['n_dev'])}</span></div>
                <div class="litem" style="border-color:rgba(249,115,22,0.3)"><p>⚠️ NOVEDAD</p><h3 style="color:{C['orange']}">{k['n_nov']:,}</h3><span class="badge" style="background:rgba(249,115,22,0.15);color:#F97316;border:1px solid rgba(249,115,22,0.3)">{pof(k['n_nov'])}</span></div>
                <div class="litem" style="border-color:rgba(100,116,139,0.3)"><p>⏳ OTROS</p><h3 style="color:{C['muted']}">{k['n_otr']:,}</h3><span class="badge" style="background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)">{pof(k['n_otr'])}</span></div>
            </div>
            """, unsafe_allow_html=True)

        with ct2:
            gcol = "GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in df_f.columns else ("PRODUCTO" if F.get("PRODUCTO") else None)
            if not gcol: st.warning("No hay productos.")
            else:
                productos = sorted(df_f[gcol].dropna().unique())
                ixo = k["fact_neto"]/k["n_desp"] if k["n_desp"]>0 else 0
                sc1,sc2 = st.columns(2)
                with sc1: dg = st.slider("% Entrega",50,100,80,key=f"dg_{pn}")
                with sc2: rb = st.number_input("Colchón Dev.",value=1.40,min_value=1.0,max_value=3.0,step=0.05,key=f"rb_{pn}")
                pe_key = f"pe_{pn}"
                if pe_key not in st.session_state: st.session_state[pe_key] = {}
                for p in productos:
                    if p not in st.session_state[pe_key]: st.session_state[pe_key][p] = float(dg)
                prows = []
                for prod in productos:
                    dp=df_f[df_f[gcol]==prod]; dpnc=dp[dp["ESTATUS"]!="CANCELADO"] if F.get("ESTATUS") else dp
                    uds=dp["CANTIDAD"].sum() if F.get("CANTIDAD") else 0; od=dpnc["ID"].nunique() if F.get("ID") else len(dpnc)
                    pp=dp["PRECIO PROVEEDOR"].mean() if F.get("PRECIO PROVEEDOR") else 0; fp=dp["PRECIO FLETE"].mean() if F.get("PRECIO FLETE") else 0
                    pe=st.session_state[pe_key].get(prod,float(dg)); oe=od*pe/100; odv=od-oe; ue=uds*pe/100; cp=ue*pp; fl=oe*fp+odv*fp*rb
                    ap=gxp.get(prod.upper(),0); ip=oe*ixo; ut=ip-cp-fl-ap
                    prows.append({"Producto":prod,"Órdenes":int(od),"% Entrega":pe,"Ingreso":round(ip),"Costo":round(cp),"Fletes":round(fl),"Ads":round(ap),"Utilidad":round(ut)})
                dfp = pd.DataFrame(prows); ti=dfp["Ingreso"].sum(); tu=dfp["Utilidad"].sum()
                st.markdown(f"""
                <div class="row2 r3">
                    <div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES TOTALES</div><div class="val lg white">{dfp['Órdenes'].sum():,}</div></div>
                    <div class="kcard"><div class="icon g">📊</div><div class="lbl">INGRESO PROYECTADO</div><div class="val lg green">{fmt(ti,pn)}</div></div>
                    <div class="kcard green"><div class="icon g">📈</div><div class="lbl">UTILIDAD PROYECTADA</div><div class="val lg green">{fmt(tu,pn)}</div></div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('<p class="section-hdr">Proyección por Producto</p>', unsafe_allow_html=True)
                mx_p = max(dfp["Ingreso"].max(), 1); bars_html = ""
                for _,r in dfp.iterrows():
                    ip_pct=min(r["Ingreso"]/mx_p*100,100); ut_pct=min(max(r["Utilidad"],0)/mx_p*100,100); ut_col=C["profit"] if r["Utilidad"]>=0 else C["loss"]
                    bars_html += f'<div style="margin-bottom:1.2rem"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="color:{C["text"]};font-weight:600;font-size:.85rem">{r["Producto"]}</span><span style="color:{C["sub"]};font-size:.78rem">{int(r["Órdenes"])} órd · {int(r["% Entrega"])}% ent.</span></div><div style="display:flex;gap:8px;align-items:center"><div style="flex:1;background:#111827;border-radius:4px;height:22px;position:relative;overflow:hidden"><div style="width:{ip_pct:.0f}%;height:100%;background:rgba(16,185,129,0.2);border-radius:4px"></div><div style="position:absolute;top:0;left:0;width:{ut_pct:.0f}%;height:100%;background:{C["profit"]};border-radius:4px;opacity:.7"></div></div><span style="font-family:JetBrains Mono;font-size:.82rem;color:{ut_col};width:130px;text-align:right;font-weight:600">{fmt(r["Utilidad"],pn)}</span></div><div style="display:flex;gap:16px;margin-top:3px;font-size:.7rem;color:{C["sub"]}"><span>Ingreso: {fmt(r["Ingreso"],pn)}</span><span>Costo: -{fmt(r["Costo"],pn)}</span><span>Fletes: -{fmt(r["Fletes"],pn)}</span><span>Ads: -{fmt(r["Ads"],pn)}</span></div></div>'
                st.markdown(f'<div class="kcard" style="padding:1.5rem">{bars_html}</div>', unsafe_allow_html=True)
                with st.expander("📝 Editar % Entrega"):
                    ed=st.data_editor(dfp,column_config={"% Entrega":st.column_config.NumberColumn("% ENTREGA",min_value=0,max_value=100,step=1,format="%d")},disabled=[c for c in dfp.columns if c!="% Entrega"],use_container_width=True,hide_index=True,key=f"pt_{pn}")
                    if ed is not None:
                        for _,r in ed.iterrows(): st.session_state[pe_key][r["Producto"]]=r["% Entrega"]

        with ct3:
            ucls="green" if k["u_real"]>=0 else "red"; mg=(k["u_real"]/k["ing_real"]*100) if k["ing_real"]>0 else 0
            st.markdown(f'<div class="kcard {ucls}" style="padding:2rem;margin-bottom:1.5rem"><div class="icon {"g" if k["u_real"]>=0 else "r"}" style="width:48px;height:48px;font-size:1.3rem">💰</div><div class="lbl">UTILIDAD REAL</div><div class="val xl {ucls}">{fmt(k["u_real"],pn)}</div><div class="sub">Margen: {mg:.0f}%</div></div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="row2 r3">
                <div class="kcard green"><div class="icon g">✅</div><div class="lbl">INGRESO (ENTREGADOS)</div><div class="val md green">{fmt(k['ing_real'],pn)}</div></div>
                <div class="kcard red"><div class="icon r">📦</div><div class="lbl">COSTO PRODUCTO</div><div class="val md red">-{fmt(k['cpr'],pn)}</div></div>
                <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">GASTO ADS</div><div class="val md red">-{fmt(k['g_ads'],pn)}</div></div>
            </div>
            <div class="row2 r2">
                <div class="kcard red"><div class="icon r">⚠️</div><div class="lbl">FLETES DEVOLUCIONES</div><div class="val md red">-{fmt(k['fl_dev'],pn)}</div></div>
                <div class="kcard"><div class="icon b">🚚</div><div class="lbl">FLETES TRÁNSITO</div><div class="val md white">-{fmt(k['fl_tra'],pn)}</div></div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('<p class="section-hdr">Cascada Financiera</p>', unsafe_allow_html=True)
            items=[("Ingreso Entregados",k["ing_real"],True),("Costo Producto",k["cpr"],False),("Gasto Ads",k["g_ads"],False),("Fletes Dev.",k["fl_dev"],False),("Fletes Tránsito",k["fl_tra"],False)]
            mx_c=max(k["ing_real"],1); ch=""
            for lb,vl,pos in items:
                bp=min(vl/mx_c*100,100) if mx_c>0 else 0; bc=C["profit"] if pos else C["loss"]; sg="" if pos else "-"
                ch+=f'<div class="cas-row"><div class="cas-lbl">{lb}</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{bp:.0f}%;background:{bc}"></div></div><div class="cas-amt" style="color:{bc}">{sg}{fmt(vl,pn)}</div></div>'
            up=min(abs(k["u_real"])/mx_c*100,100) if mx_c>0 else 0; uc=C["profit"] if k["u_real"]>=0 else C["loss"]; us="" if k["u_real"]>=0 else "-"
            st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem">{ch}<div style="border-top:2px solid #1E293B;margin:8px 0"></div><div class="cas-row" style="border:none"><div class="cas-lbl" style="font-weight:700;color:#F1F5F9">UTILIDAD REAL</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{up:.0f}%;background:{uc}"></div></div><div class="cas-amt" style="color:{uc};font-size:.95rem">{us}{fmt(abs(k["u_real"]),pn)}</div></div></div>', unsafe_allow_html=True)

        with ct4:
            st.markdown(f'<p class="section-hdr">Órdenes — {len(df_ord):,}</p>', unsafe_allow_html=True)
            cols=[c for c in ["ID","FECHA","PRODUCTO","CANTIDAD","TOTAL DE LA ORDEN","PRECIO FLETE","CIUDAD DESTINO","ESTATUS"] if c in df_ord.columns]
            if cols:
                dfo=df_ord[cols].copy()
                if "FECHA" in dfo.columns: dfo=dfo.sort_values("FECHA",ascending=False)
                nr=len(dfo); hmap={"ID":"ID ORDEN","FECHA":"FECHA","PRODUCTO":"PRODUCTO","CANTIDAD":"CANT.","TOTAL DE LA ORDEN":"TOTAL","PRECIO FLETE":"FLETE","CIUDAD DESTINO":"CIUDAD","ESTATUS":"ESTADO"}
                hdrs="".join(f"<th>{hmap.get(c,c)}</th>" for c in cols); ps=50; opk=f"op_{pn}"
                if opk not in st.session_state: st.session_state[opk]=0
                tp=max(1,(nr-1)//ps+1); s=st.session_state[opk]*ps; e=min(s+ps,nr); rh=""
                for _,row in dfo.iloc[s:e].iterrows():
                    tds=""
                    for c in cols:
                        v=row[c]
                        if c=="ID": tds+=f'<td class="id">ORD-{v}</td>'
                        elif c=="FECHA": tds+=f'<td>{v.strftime("%d %b %Y") if pd.notna(v) else "-"}</td>'
                        elif c in ("TOTAL DE LA ORDEN","PRECIO FLETE"): tds+=f'<td class="mono">{fmt(v,pn)}</td>'
                        elif c=="CANTIDAD": tds+=f'<td style="text-align:center">{int(v)}</td>'
                        elif c=="ESTATUS": tds+=f'<td>{status_pill(str(v))}</td>'
                        elif c=="CIUDAD DESTINO": tds+=f'<td>{str(v).title() if pd.notna(v) else "-"}</td>'
                        else: tds+=f'<td>{v}</td>'
                    rh+=f"<tr>{tds}</tr>"
                st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead><tr>{hdrs}</tr></thead><tbody>{rh}</tbody></table></div>', unsafe_allow_html=True)
                pc1,pc2,pc3=st.columns([1,2,1])
                with pc1:
                    if st.button("← Anterior",disabled=st.session_state[opk]==0,key=f"pv_{pn}"): st.session_state[opk]-=1; st.rerun()
                with pc2: st.markdown(f'<p style="text-align:center;color:#64748B;font-size:.85rem">Pág {st.session_state[opk]+1}/{tp}</p>',unsafe_allow_html=True)
                with pc3:
                    if st.button("Siguiente →",disabled=st.session_state[opk]>=tp-1,key=f"nx_{pn}"): st.session_state[opk]+=1; st.rerun()


# ═══════════════ TAB: PUBLICIDAD ═══════════════
with tabs[-1]:
    st.markdown('<p class="section-hdr">Análisis de Publicidad</p>', unsafe_allow_html=True)
    total_fb_p = sum(cd["kpis"]["g_fb"] for cd in country_data.values())
    total_tt_p = sum(cd["kpis"]["g_tt"] for cd in country_data.values())
    total_ads_p = total_fb_p + total_tt_p
    total_ads_cop_p = sum(cd["kpis"].get("g_ads_cop",0) for cd in country_data.values())
    total_ord_p = sum(cd["kpis"]["n_ord"] for cd in country_data.values())
    total_ent_p = sum(cd["kpis"]["n_ent"] for cd in country_data.values())
    cpa_o = total_ads_cop_p/total_ord_p if total_ord_p>0 else 0
    cpa_e = total_ads_cop_p/total_ent_p if total_ent_p>0 else 0

    st.markdown(f"""
    <div class="row2 r4">
        <div class="kcard purple"><div class="icon p">📢</div><div class="lbl">GASTO TOTAL ADS</div><div class="val lg purple">{fmt_cop(total_ads_cop_p)}</div><div class="sub">En COP consolidado</div></div>
        <div class="kcard blue"><div class="icon b">📘</div><div class="lbl">FACEBOOK</div><div class="val lg blue">{fmt_cop(sum(cd['kpis'].get('g_fb_cop',0) for cd in country_data.values()))}</div></div>
        <div class="kcard"><div class="icon w">🎵</div><div class="lbl">TIKTOK</div><div class="val lg white">{fmt_cop(sum(cd['kpis'].get('g_tt_cop',0) for cd in country_data.values()))}</div></div>
        <div class="kcard red"><div class="icon r">🎯</div><div class="lbl">CPA POR ORDEN</div><div class="val lg red">{fmt_cop(cpa_o)}</div><div class="sub">CPA Entregado: {fmt_cop(cpa_e)}</div></div>
    </div>
    """, unsafe_allow_html=True)

    if len(country_data)>1:
        ads_d=[{"País":f"{PAISES[pn]['flag']} {pn}","Facebook":cd["kpis"].get("g_fb_cop",0),"TikTok":cd["kpis"].get("g_tt_cop",0)} for pn,cd in country_data.items()]
        dfa=pd.DataFrame(ads_d); ma=dfa.melt(id_vars="País",var_name="Plataforma",value_name="COP")
        fa=px.bar(ma,x="País",y="COP",color="Plataforma",barmode="stack",color_discrete_map={"Facebook":C["blue"],"TikTok":C["purple"]})
        fa.update_layout(**pl(title="GASTO POR PAÍS (COP)")); fa.update_traces(hovertemplate="%{y:,.0f}<extra></extra>")
        st.plotly_chart(fa, use_container_width=True, key="ch_ads_pais")

    st.markdown('<p class="section-hdr">Gasto por Producto</p>', unsafe_allow_html=True)
    if gxp:
        prod_ads=pd.DataFrame([{"Producto":k,"Gasto":v} for k,v in sorted(gxp.items(),key=lambda x:-x[1])])
        fp=px.bar(prod_ads,x="Producto",y="Gasto",color_discrete_sequence=[C["purple"]])
        fp.update_layout(**pl(title="GASTO ADS POR PRODUCTO (COP)")); fp.update_traces(hovertemplate="%{y:,.0f}<extra></extra>")
        st.plotly_chart(fp, use_container_width=True, key="ch_ads_prod")
        cpa_rows=[]
        for pn,cd in country_data.items():
            gcol="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in cd["df_ord"].columns else "PRODUCTO"
            if gcol not in cd["df_ord"].columns: continue
            for prod in cd["df_ord"][gcol].dropna().unique():
                dp=cd["df_ord"][cd["df_ord"][gcol]==prod]; n=len(dp); ad=gxp.get(prod.upper(),0)
                if n>0 and ad>0: cpa_rows.append({"Producto":prod,"CPA":round(ad/n),"Órdenes":n})
        if cpa_rows:
            dfcpa=pd.DataFrame(cpa_rows)
            fcpa=px.bar(dfcpa,x="Producto",y="CPA",color_discrete_sequence=[C["orange"]],text="CPA")
            fcpa.update_layout(**pl(title="CPA POR PRODUCTO (COP)")); fcpa.update_traces(texttemplate="%{y:,.0f}",textposition="outside",hovertemplate="CPA: %{y:,.0f}<extra></extra>")
            st.plotly_chart(fcpa, use_container_width=True, key="ch_cpa")
    else:
        st.info("Conecta Facebook Ads para ver gasto por producto.")

    for pn,cd in country_data.items():
        if "FECHA" in cd["df_ord"].columns and cd["kpis"]["g_ads"]>0:
            do=cd["df_ord"].groupby(cd["df_ord"]["FECHA"].dt.date).size().reset_index(name="Ordenes"); do.columns=["Fecha","Ordenes"]
            avg=cd["kpis"]["g_ads"]/max(len(do),1); do["CPA"]=avg/do["Ordenes"].replace(0,1)
            ft=go.Figure()
            ft.add_trace(go.Bar(x=do["Fecha"],y=do["Ordenes"],name="Órdenes",marker_color=C["profit"],hovertemplate="%{y}<extra></extra>"))
            ft.add_trace(go.Scatter(x=do["Fecha"],y=do["CPA"],name="CPA diario",yaxis="y2",line=dict(color=C["orange"],width=2),hovertemplate="%{y:,.0f}<extra></extra>"))
            ft.update_layout(**pl(title=f"ÓRDENES vs CPA — {PAISES[pn]['flag']} {pn}",yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)")))
            st.plotly_chart(ft, use_container_width=True, key=f"ch_trend_{pn}")

st.divider()
loaded=sum(1 for p in PAISES if st.session_state.get(f"_b_{p}"))
st.markdown(f'<div style="text-align:center;color:#475569;font-size:.75rem;padding:.5rem 0">Profit Dashboard v4.2 · {loaded} países · {f_ini.strftime("%d/%m")} – {f_fin.strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)
