"""
Ecommerce Profit Dashboard v5.0
Multi-Country · AI Mapping · Dark Finance · Precise Accounting
"""
import streamlit as st
import pandas as pd
import requests, json, os, re
from datetime import datetime, timedelta
from collections import defaultdict

# -----------------------------------------------------------------------------
# 📦 INSTALL PLOTLY IF MISSING
# -----------------------------------------------------------------------------
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plotly"])
    import plotly.express as px
    import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# ⚙️ CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="T-PILOT v5", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

PAISES = {
    "Colombia":  {"flag": "🇨🇴", "moneda": "COP", "sym": "$"},
    "Ecuador":   {"flag": "🇪🇨", "moneda": "USD", "sym": "$"},
    "Guatemala": {"flag": "🇬🇹", "moneda": "GTQ", "sym": "Q"},
}
SETTINGS_FILE = "dashboard_settings.json"
MAPPING_FILE = "product_mappings.json"
CAMPAIGN_MAP_FILE = "campaign_mappings.json"

# Colors
C = dict(profit="#10B981", loss="#EF4444", warn="#F59E0B", blue="#3B82F6",
         purple="#8B5CF6", orange="#F97316", cyan="#06B6D4", muted="#64748B",
         text="#E2E8F0", sub="#94A3B8", grid="#1E293B", bg="#0B0F19")

# -----------------------------------------------------------------------------
# 🎨 CSS STYLES
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
.stApp { background:#0B0F19; color:#E2E8F0; font-family:'Inter',sans-serif; }
/* Cards */
.kcard {
    background: linear-gradient(180deg, #131A2B, #0F1420);
    border: 1px solid #1E293B; border-radius: 12px; padding: 1.2rem;
    position: relative; transition: all 0.2s; margin-bottom: 1rem;
}
.kcard:hover { border-color: #3B82F6; }
.kcard .lbl { font-size: 0.75rem; color: #94A3B8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.kcard .val { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; font-weight: 700; margin: 4px 0; }
.kcard .sub { font-size: 0.8rem; color: #64748B; display: flex; justify-content: space-between; }
.kcard .pct { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
/* Colors */
.c-green { color: #10B981; } .c-red { color: #EF4444; } .c-blue { color: #3B82F6; } .c-white { color: #F8FAFC; }
/* Grid System */
.g4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; }
.g3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
/* Pills */
.pill { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid; }
.p-ent { background: #064E3B; border-color: #059669; color: #34D399; }
.p-can { background: #450A0A; border-color: #DC2626; color: #F87171; }
.p-tra { background: #1E3A8A; border-color: #2563EB; color: #60A5FA; }
.p-dev { background: #431407; border-color: #D97706; color: #FBBF24; }
/* Custom Tables */
.ctbl { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.ctbl th { text-align: left; color: #64748B; padding: 8px; border-bottom: 1px solid #1E293B; }
.ctbl td { padding: 10px 8px; border-bottom: 1px solid #111827; color: #E2E8F0; }
.ctbl tr:hover { background: #111827; }
/* Inputs Override */
div[data-testid="stSelectbox"] > div > div { background-color: #1E293B; color: white; border: 1px solid #334155; }
div[data-testid="stTextInput"] > div > div { background-color: #1E293B; color: white; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 🛠️ HELPER FUNCTIONS
# -----------------------------------------------------------------------------
def load_json(path):
    if os.path.exists(path):
        try:
            with open(path) as f: return json.load(f)
        except: pass
    return {}

def save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f, indent=2)
    except: pass

def load_cfg(): return load_json(SETTINGS_FILE)
def save_cfg(k, v): s = load_cfg(); s[k] = v; save_json(SETTINGS_FILE, s)

@st.cache_data(ttl=3600)
def get_trm():
    rates = {"COP_USD": 4200, "COP_GTQ": 540}
    try:
        r = requests.get("https://open.er-api.com/v6/latest/COP", timeout=5)
        if r.status_code == 200:
            d = r.json().get("rates", {})
            if "USD" in d: rates["COP_USD"] = 1 / d["USD"]
            if "GTQ" in d: rates["COP_GTQ"] = 1 / d["GTQ"]
    except: pass
    return rates

trm = get_trm()

def convert_to_cop(val, curr):
    if curr == "USD": return val * trm["COP_USD"]
    if curr == "GTQ": return val * trm["COP_GTQ"]
    return val

def convert_cop_to(val_cop, target_curr):
    if target_curr == "USD": return val_cop / trm["COP_USD"]
    if target_curr == "GTQ": return val_cop / trm["COP_GTQ"]
    return val_cop

def fmt(v, p="Colombia"):
    sym = PAISES.get(p, PAISES["Colombia"])["sym"]
    return f"{sym} {v:,.0f}"

def pl(**kw):
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C["text"], family="Inter"),
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(gridcolor=C["grid"]), yaxis=dict(gridcolor=C["grid"])
    )
    layout.update(kw)
    return layout

# -----------------------------------------------------------------------------
# 🧠 AI LOGIC
# -----------------------------------------------------------------------------
def ia_auto_map(api_key, campaigns, products):
    if not api_key: return {}
    
    prompt = f"""
    Eres un experto en Ecommerce. Tienes dos listas:
    1. CAMPAÑAS DE FACEBOOK (Nombres sucios)
    2. PRODUCTOS DE DROPI (Nombres limpios)
    
    Tu tarea: Empareja cada Campaña con el Producto que más se le parezca por nombre.
    Retorna SOLO un JSON válido key-value: {{"Nombre Campaña": "Nombre Producto"}}.
    Si no hay coincidencia clara, ignora esa campaña.
    
    CAMPAÑAS: {campaigns}
    PRODUCTOS: {products}
    """
    
    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }, timeout=20
        ).json()
        return json.loads(res['choices'][0]['message']['content'])
    except Exception as e:
        st.error(f"Error IA: {e}")
        return {}

# -----------------------------------------------------------------------------
# 📡 DATA LOADERS
# -----------------------------------------------------------------------------
@st.cache_data
def cargar_archivo(file_bytes, ext):
    import io
    try:
        buf = io.BytesIO(file_bytes)
        if ext in ["xlsx", "xls"]:
            df = pd.read_excel(buf, dtype=str, engine="openpyxl")
        else:
            df = pd.read_csv(buf, dtype=str, encoding="latin-1", on_bad_lines="skip", sep=None, engine="python")
        
        # Cleanup
        df.columns = df.columns.str.strip().str.upper()
        
        # Map Columns
        cols_map = {
            "ID": ["ID", "ORDER ID", "NUMERO DE ORDEN"],
            "ESTATUS": ["ESTATUS", "STATUS", "ESTADO"],
            "FECHA": ["FECHA", "DATE", "CREATED_AT"],
            "PRODUCTO": ["PRODUCTO", "PRODUCT", "ITEM"],
            "CANTIDAD": ["CANTIDAD", "QTY", "UNIDADES"],
            "TOTAL DE LA ORDEN": ["TOTAL DE LA ORDEN", "TOTAL", "PRICE"],
            "PRECIO PROVEEDOR": ["PRECIO PROVEEDOR", "COSTO", "COST"],
            "PRECIO FLETE": ["PRECIO FLETE", "SHIPPING COST"],
            "COSTO DEVOLUCION FLETE": ["COSTO DEVOLUCION FLETE", "RETURN COST"],
            "CIUDAD DESTINO": ["CIUDAD DESTINO", "CITY"],
            "GANANCIA": ["GANANCIA", "PROFIT"]
        }
        
        renames = {}
        for std, variants in cols_map.items():
            for v in variants:
                if v in df.columns:
                    renames[v] = std
                    break
        df.rename(columns=renames, inplace=True)
        
        # Numeric cleanup
        num_cols = ["TOTAL DE LA ORDEN", "PRECIO PROVEEDOR", "PRECIO FLETE", "COSTO DEVOLUCION FLETE", "GANANCIA", "CANTIDAD"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[^\d.\-]","",regex=True), errors="coerce").fillna(0)
        
        # Date cleanup
        if "FECHA" in df.columns:
            df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
            
        return df
    except Exception as e:
        st.error(f"Error cargando archivo: {e}")
        return pd.DataFrame()

def fb_get_accounts(tok):
    if not tok: return []
    try:
        r = requests.get("https://graph.facebook.com/v21.0/me/adaccounts", 
                         params={"access_token": tok, "fields": "name,account_id", "limit": 100})
        return r.json().get("data", [])
    except: return []

def fb_get_spend(tok, accs, d1, d2):
    # Returns DataFrame: [campaign_name, spend, account_id]
    if not tok or not accs: return pd.DataFrame()
    
    rows = []
    d_range = json.dumps({"since": d1, "until": d2})
    
    for acc_id in accs:
        id_clean = acc_id.replace("act_", "")
        try:
            url = f"https://graph.facebook.com/v21.0/act_{id_clean}/insights"
            p = {"access_token": tok, "time_range": d_range, "fields": "campaign_name,spend", "level": "campaign", "limit": 500}
            d = requests.get(url, params=p).json().get("data", [])
            for x in d:
                rows.append({
                    "campaign_name": x.get("campaign_name", "Unknown"),
                    "spend": float(x.get("spend", 0)),
                    "account_id": acc_id
                })
        except: pass
    return pd.DataFrame(rows)

# -----------------------------------------------------------------------------
# 📊 CALCULATION ENGINE
# -----------------------------------------------------------------------------
def process_data(df, start, end, country_name, g_fb_total, g_tt_total, campaign_map):
    # 1. Filter Date
    mask = (df["FECHA"] >= pd.Timestamp(start)) & (df["FECHA"] <= pd.Timestamp(end) + pd.Timedelta(days=1))
    df = df[mask].copy()
    
    if df.empty: return None
    
    # 2. Assign Products based on Campaign Mapping (or raw name)
    # We need to map ADS SPEND to PRODUCTS
    # Logic: df (Orders) has "PRODUCTO". Ads data has "campaign_name".
    # We need to distribute Ads Spend into Products.
    
    # 3. Aggregate Orders
    # Group by Order ID to avoid duplicate totals if multiple lines per order
    agg_rules = {
        "TOTAL DE LA ORDEN": "first",
        "ESTATUS": "first",
        "PRECIO FLETE": "first",
        "COSTO DEVOLUCION FLETE": "first",
        "GANANCIA": "sum",
        "FECHA": "first",
        "PRODUCTO": "first", # Simplified
        "CANTIDAD": "sum",
        "PRECIO PROVEEDOR": "first"
    }
    # Only use available columns
    agg_rules = {k:v for k,v in agg_rules.items() if k in df.columns}
    
    df_ord = df.groupby("ID").agg(agg_rules).reset_index() if "ID" in df.columns else df
    
    # 4. Status Counters
    st_counts = df_ord["ESTATUS"].astype(str).str.upper().value_counts()
    
    def get_cnt(keys):
        return sum(st_counts[k] for k in st_counts.keys() if any(x in k for x in keys))
    
    n_ent = get_cnt(["ENTREGADO"])
    n_can = get_cnt(["CANCELADO"])
    n_dev = get_cnt(["DEVOLUCION", "DEVOLUCIÓN"])
    # Corrección Punto 2: Fletes Tránsito
    n_tra = get_cnt(["TRANSITO", "TRÁNSITO", "EN RUTA", "EN CAMINO", "DESPACHADO", "ENVIADO", "PROCESADO", "REPARTO"])
    n_nov = get_cnt(["NOVEDAD"])
    n_tot = len(df_ord)
    n_otr = n_tot - n_ent - n_can - n_dev - n_tra - n_nov
    
    # 5. Financials (Corrección Punto 1)
    
    # Delivered Subset
    df_ent = df_ord[df_ord["ESTATUS"].astype(str).str.upper().str.contains("ENTREGADO")].copy()
    
    # Ingreso Real (Total Orden, no Ganancia)
    ing_ent = df_ent["TOTAL DE LA ORDEN"].sum()
    
    # Costos Directos de lo Entregado
    costo_prod_ent = (df_ent["PRECIO PROVEEDOR"] * df_ent["CANTIDAD"]).sum()
    flete_ent = df_ent["PRECIO FLETE"].sum() # Flete de ida de lo entregado
    
    # Costos Operativos Globales
    # Fletes Devolución
    df_dev = df_ord[df_ord["ESTATUS"].astype(str).str.upper().str.contains("DEVOLU")]
    flete_dev = 0
    if not df_dev.empty:
        # Some returns have specific return cost, others just regular freight
        if "COSTO DEVOLUCION FLETE" in df_dev.columns:
            flete_dev = df_dev[["PRECIO FLETE", "COSTO DEVOLUCION FLETE"]].max(axis=1).sum()
        else:
            flete_dev = df_dev["PRECIO FLETE"].sum()
            
    # Fletes Tránsito (Pérdida potencial o costo hundido temporal)
    # Corrección: Asegurar que sume
    transit_keys = ["TRANSITO", "TRÁNSITO", "EN RUTA", "EN CAMINO", "DESPACHADO", "ENVIADO", "PROCESADO", "REPARTO"]
    df_tra = df_ord[df_ord["ESTATUS"].astype(str).str.upper().str.contains("|".join(transit_keys))]
    flete_tra = df_tra["PRECIO FLETE"].sum()
    
    # Ads Spend Distribution
    # This assumes g_fb_total is already filtered/converted for this country
    gasto_ads = g_fb_total + g_tt_total
    
    # Utility Equation
    utilidad_real = ing_ent - costo_prod_ent - flete_ent - flete_dev - flete_tra - gasto_ads
    
    # 6. Product Summary Data (Punto 6)
    # Create a summary per product
    prod_summary = []
    if "PRODUCTO" in df_ord.columns:
        # Ads distribution per product logic requires Mapping.
        # Simple Logic: Distribute Ads based on Orders % for now if map not precise, 
        # OR use the Campaign Map if available.
        
        # Let's map spend first if we have Campaign Map
        ads_per_prod = defaultdict(float)
        # We need the raw campaigns df here ideally. 
        # For this structure, we'll assume linear distribution of unmapped ads 
        # or handle it in the UI section.
        
        for prod, sub in df_ord.groupby("PRODUCTO"):
            n_o = len(sub)
            fact = sub[sub["ESTATUS"].str.contains("ENTREGADO", na=False)]["TOTAL DE LA ORDEN"].sum()
            prod_summary.append({
                "Producto": prod,
                "Pedidos": n_o,
                "Facturado Entregado": fact,
                "Entregados": len(sub[sub["ESTATUS"].str.contains("ENTREGADO", na=False)])
            })
    
    return {
        "orders": df_ord,
        "kpis": {
            "n_tot": n_tot, "n_ent": n_ent, "n_can": n_can, "n_dev": n_dev, "n_tra": n_tra, "n_nov": n_nov, "n_otr": n_otr,
            "ing_ent": ing_ent, 
            "costo_prod": costo_prod_ent, 
            "flete_ent": flete_ent, 
            "flete_dev": flete_dev, 
            "flete_tra": flete_tra,
            "ads": gasto_ads,
            "utilidad": utilidad_real
        },
        "prod_summary": pd.DataFrame(prod_summary)
    }

# -----------------------------------------------------------------------------
# 🖥️ SIDEBAR & SETUP
# -----------------------------------------------------------------------------
cfg = load_cfg()

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    
    # API KEYS
    with st.expander("🔑 Credenciales", expanded=False):
        fb_tok = st.text_input("FB Token", value=cfg.get("fb_tok",""), type="password")
        oa_key = st.text_input("OpenAI Key", value=cfg.get("oa_key",""), type="password")
        if st.button("Guardar Keys"):
            save_cfg("fb_tok", fb_tok)
            save_cfg("oa_key", oa_key)
            st.rerun()
            
    # FB ACCOUNTS SELECTOR (Fix 7)
    fb_accounts = fb_get_accounts(fb_tok)
    fb_map = {f"{a['name']} ({a['account_id']})": a['account_id'] for a in fb_accounts}
    
    # Select All Logic
    if "sel_all_fb" not in st.session_state: st.session_state.sel_all_fb = False
    
    def toggle_sel_all():
        if st.session_state.sel_all_check:
            st.session_state.fb_selected = list(fb_map.keys())
        else:
            st.session_state.fb_selected = []

    st.checkbox("✅ Seleccionar Todas", key="sel_all_check", on_change=toggle_sel_all)
    
    sel_acc_names = st.multiselect("Cuentas Publicitarias", list(fb_map.keys()), key="fb_selected")
    sel_acc_ids = [fb_map[n] for n in sel_acc_names]
    
    st.divider()
    
    # UPLOADS
    st.markdown("### 📂 Archivos")
    uploaded_data = {}
    for p, meta in PAISES.items():
        f = st.file_uploader(f"{meta['flag']} {p}", type=["csv","xlsx"], key=f"up_{p}")
        if f:
            df = cargar_archivo(f.getvalue(), f.name.split('.')[-1])
            if not df.empty:
                uploaded_data[p] = df
                st.success(f"{len(df)} pedidos")

# -----------------------------------------------------------------------------
# 📅 DATE & MAIN LAYOUT
# -----------------------------------------------------------------------------
c1, c2 = st.columns([2, 1])
with c1:
    st.markdown("## ✈️ T-PILOT DASHBOARD")
with c2:
    d1 = st.date_input("Desde", datetime.today() - timedelta(days=30))
    d2 = st.date_input("Hasta", datetime.today())

date_start = d1.strftime("%Y-%m-%d")
date_end = d2.strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# 📢 ADS DATA FETCHING
# -----------------------------------------------------------------------------
if sel_acc_ids and fb_tok:
    with st.spinner("Descargando data de Facebook..."):
        df_ads_raw = fb_get_spend(fb_tok, sel_acc_ids, date_start, date_end)
else:
    df_ads_raw = pd.DataFrame(columns=["campaign_name", "spend", "account_id"])

# -----------------------------------------------------------------------------
# 🔗 MAPPING SYSTEM (Fix 3 & 4)
# -----------------------------------------------------------------------------
if not df_ads_raw.empty and uploaded_data:
    with st.expander("🔗 Mapeo de Productos (IA + Manual)", expanded=False):
        
        # Load existing map
        curr_map = load_json(CAMPAIGN_MAP_FILE)
        
        # Get unique campaigns from Ads Data
        all_camps = sorted(df_ads_raw["campaign_name"].unique())
        # Filter out already mapped
        unmapped_camps = [c for c in all_camps if c not in curr_map]
        
        # Get unique products from Dropi Data
        all_prods = set()
        for df in uploaded_data.values():
            if "PRODUCTO" in df.columns:
                all_prods.update(df["PRODUCTO"].dropna().unique())
        all_prods = sorted(list(all_prods))
        
        # UI for Mapping
        c_m1, c_m2, c_m3 = st.columns([2, 2, 1])
        with c_m1:
            sel_camp = st.selectbox("Campaña FB (Sin asignar)", [""] + unmapped_camps)
        with c_m2:
            sel_prod = st.selectbox("Producto Dropi", [""] + all_prods)
        with c_m3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔗 Vincular"):
                if sel_camp and sel_prod:
                    curr_map[sel_camp] = sel_prod
                    save_json(CAMPAIGN_MAP_FILE, curr_map)
                    st.success("Vinculado!")
                    st.rerun()
        
        # AI Auto-Map
        if st.button("🪄 Auto-Mapear con IA"):
            if not oa_key:
                st.error("Falta la OpenAI Key en configuración")
            else:
                with st.spinner("La IA está analizando nombres..."):
                    new_maps = ia_auto_map(oa_key, unmapped_camps, all_prods)
                    if new_maps:
                        curr_map.update(new_maps)
                        save_json(CAMPAIGN_MAP_FILE, curr_map)
                        st.success(f"IA vinculó {len(new_maps)} campañas!")
                        st.rerun()
        
        # Show Mapped Table
        if curr_map:
            st.markdown("##### Vínculos Activos")
            df_map = pd.DataFrame(list(curr_map.items()), columns=["Campaña", "Producto Asignado"])
            st.dataframe(df_map, use_container_width=True, height=200)
            
            # Unlink option
            to_unlink = st.selectbox("Desvincular:", [""] + list(curr_map.keys()))
            if st.button("🗑️ Borrar Vínculo"):
                if to_unlink in curr_map:
                    del curr_map[to_unlink]
                    save_json(CAMPAIGN_MAP_FILE, curr_map)
                    st.rerun()

# Apply Map to Ads Data
df_ads_raw["Mapped_Product"] = df_ads_raw["campaign_name"].map(load_json(CAMPAIGN_MAP_FILE)).fillna("Otros")

# -----------------------------------------------------------------------------
# 🖥️ DASHBOARD TABS
# -----------------------------------------------------------------------------
tabs = st.tabs(list(uploaded_data.keys()))

for i, pais in enumerate(uploaded_data.keys()):
    with tabs[i]:
        df = uploaded_data[pais]
        pi = PAISES[pais]
        
        # Filter Ads for this country (Assuming Campaign Name contains Country Code or relying on manual mapping if complex)
        # Simplified: We take total ads and assume user selected correct accounts for the context, 
        # OR we can try to filter by currency/account logic. 
        # For v5, let's take totals converted to Local Currency.
        
        # Calculate Ads Spend for this "View"
        # Strategy: Sum spend of campaigns mapped to products present in this country's file
        prods_in_country = df["PRODUCTO"].unique() if "PRODUCTO" in df.columns else []
        
        # Filter ads that map to products in this country
        df_ads_country = df_ads_raw[df_ads_raw["Mapped_Product"].isin(prods_in_country)]
        
        # Spend is in Account Currency (usually COP). Convert to Country Currency.
        # Assuming Ads Data comes in COP (standard for Latam accounts).
        gasto_ads_cop = df_ads_country["spend"].sum()
        
        # Add unmapped ads proportionally? (Optional, skipping for precision)
        
        gasto_ads_local = convert_cop_to(gasto_ads_cop, pi["moneda"])
        
        # PROCESS DATA
        data = process_data(df, date_start, date_end, pais, gasto_ads_local, 0, {})
        
        if not data:
            st.warning("Sin datos en este rango.")
            continue
            
        k = data["kpis"]
        
        # --- TERMÓMETRO ---
        st.markdown(f"### {pi['flag']} Operación Real ({pi['moneda']})")
        
        # Top KPI Row
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="kcard"><div class="lbl">PEDIDOS TOTALES</div><div class="val c-white">{k["n_tot"]:,}</div><div class="sub">Entregados: {k["n_ent"]}</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kcard"><div class="lbl">INGRESO ENTREGADO</div><div class="val c-green">{fmt(k["ing_ent"], pais)}</div><div class="sub">Facturación Real</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kcard"><div class="lbl">GASTO PUBLICIDAD</div><div class="val c-red">{fmt(k["ads"], pais)}</div><div class="sub">FB + TikTok</div></div>', unsafe_allow_html=True)
        
        util_color = "c-green" if k["utilidad"] > 0 else "c-red"
        margin = (k["utilidad"] / k["ing_ent"] * 100) if k["ing_ent"] > 0 else 0
        k4.markdown(f'<div class="kcard"><div class="lbl">UTILIDAD NETA</div><div class="val {util_color}">{fmt(k["utilidad"], pais)}</div><div class="sub">Margen Real: {margin:.1f}%</div></div>', unsafe_allow_html=True)
        
        # --- CASCADA DE UTILIDAD (Fix 1 & 5) ---
        st.markdown("#### 📉 Desglose Financiero")
        
        def row_fin(label, val, is_neg=True, icon="🔻"):
            color = "#EF4444" if is_neg else "#10B981"
            pct = (val / k["ing_ent"] * 100) if k["ing_ent"] > 0 else 0
            return f"""
            <div style="display:flex; justify-content:space-between; padding: 12px 0; border-bottom: 1px solid #1E293B; align-items:center">
                <div style="width:40%"><span style="margin-right:10px">{icon}</span>{label}</div>
                <div style="width:30%; text-align:right; font-family:'JetBrains Mono'; color:{color}">{fmt(val, pais)}</div>
                <div style="width:20%; text-align:right;"><span class="pct" style="background:rgba(255,255,255,0.1)">{pct:.1f}%</span></div>
            </div>
            """
            
        html_cascade = f"""
        <div style="background:#111827; padding:20px; border-radius:12px; border:1px solid #1E293B">
            {row_fin("INGRESO TOTAL (Entregado)", k["ing_ent"], False, "💰")}
            {row_fin("Costo Producto", k["costo_prod"], True, "📦")}
            {row_fin("Publicidad (Ads)", k["ads"], True, "📢")}
            {row_fin("Fletes Entregados (Ida)", k["flete_ent"], True, "🚚")}
            {row_fin("Fletes Devolución", k["flete_dev"], True, "↩️")}
            {row_fin("Fletes en Tránsito", k["flete_tra"], True, "⏳")}
            <div style="border-top: 2px dashed #334155; margin-top:10px; padding-top:10px; display:flex; justify-content:space-between; align-items:center">
                <span style="font-weight:700; font-size:1.1rem">UTILIDAD FINAL</span>
                <span style="font-family:'JetBrains Mono'; font-size:1.4rem; font-weight:700; color:{'#10B981' if k['utilidad']>0 else '#EF4444'}">
                    {fmt(k['utilidad'], pais)}
                </span>
            </div>
        </div>
        """
        st.markdown(html_cascade, unsafe_allow_html=True)
        
        st.divider()
        
        # --- RESUMEN POR PRODUCTO (Fix 6) ---
        st.markdown("#### 📦 Rendimiento por Producto")
        
        df_prod = data["prod_summary"]
        if not df_prod.empty:
            # Merge with Ads Data calculated before
            # We aggregate ads spend by Mapped_Product from df_ads_country
            ads_by_prod = df_ads_country.groupby("Mapped_Product")["spend"].sum().reset_index()
            # Rename for merge
            ads_by_prod.columns = ["Producto", "Ads_COP"]
            
            # Merge
            df_final = pd.merge(df_prod, ads_by_prod, on="Producto", how="left").fillna(0)
            
            # Convert Ads to local currency
            df_final["Gasto Ads"] = df_final["Ads_COP"].apply(lambda x: convert_cop_to(x, pi["moneda"]))
            
            # Calc KPIs
            df_final["CPA"] = df_final.apply(lambda x: x["Gasto Ads"] / x["Pedidos"] if x["Pedidos"] > 0 else 0, axis=1)
            df_final["ROAS"] = df_final.apply(lambda x: x["Facturado Entregado"] / x["Gasto Ads"] if x["Gasto Ads"] > 0 else 0, axis=1)
            
            # Format
            st.dataframe(
                df_final[["Producto", "Pedidos", "Entregados", "Facturado Entregado", "Gasto Ads", "CPA", "ROAS"]].style
                .format({
                    "Facturado Entregado": lambda x: fmt(x, pais),
                    "Gasto Ads": lambda x: fmt(x, pais),
                    "CPA": lambda x: fmt(x, pais),
                    "ROAS": "{:.2f}x"
                })
                .background_gradient(subset=["ROAS"], cmap="RdYlGn", vmin=0.5, vmax=3)
                , use_container_width=True
            )
        else:
            st.info("No hay datos de productos.")

st.markdown("<br><center style='color:#475569'>T-PILOT v5.0 · Powered by AI</center>", unsafe_allow_html=True)
