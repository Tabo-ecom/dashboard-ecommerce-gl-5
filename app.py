"""
Ecommerce Profit Dashboard v5.5
Fix: Upload Multiple Files at Start + Cyclic Mapping Logic (Link/Unlink)
"""
import streamlit as st
import pandas as pd
import requests, json, os, re, io
from datetime import datetime, timedelta
from collections import defaultdict

# -----------------------------------------------------------------------------
# 📦 PLOTLY SETUP
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
st.set_page_config(page_title="T-PILOT v5.5", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")

PAISES = {
    "Colombia":  {"flag": "🇨🇴", "moneda": "COP", "sym": "$", "iso": "CO"},
    "Ecuador":   {"flag": "🇪🇨", "moneda": "USD", "sym": "$", "iso": "EC"},
    "Guatemala": {"flag": "🇬🇹", "moneda": "GTQ", "sym": "Q", "iso": "GT"},
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
.kcard { background: linear-gradient(180deg, #131A2B, #0F1420); border: 1px solid #1E293B; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; }
.kcard:hover { border-color: #3B82F6; }
.kcard .lbl { font-size: 0.75rem; color: #94A3B8; font-weight: 600; text-transform: uppercase; }
.kcard .val { font-family: 'JetBrains Mono'; font-size: 1.5rem; font-weight: 700; margin: 4px 0; }
.kcard .sub { font-size: 0.8rem; color: #64748B; display: flex; justify-content: space-between; }
.kcard .pct { font-size: 0.75rem; padding: 2px 6px; border-radius: 4px; font-weight: 600; }
.pill { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; border: 1px solid; }
.p-ent { background: #064E3B; border-color: #059669; color: #34D399; }
.p-can { background: #450A0A; border-color: #DC2626; color: #F87171; }
.p-tra { background: #1E3A8A; border-color: #2563EB; color: #60A5FA; }
.p-dev { background: #431407; border-color: #D97706; color: #FBBF24; }
.p-pen { background: #1E293B; border-color: #475569; color: #94A3B8; }
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
def load_mappings(): return load_json(MAPPING_FILE)
def save_mappings(d): save_json(MAPPING_FILE, d)

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

def status_pill(s):
    s = str(s).upper()
    if "ENTREGADO" in s: return '<span class="pill p-ent">✅ Entregado</span>'
    if "CANCELADO" in s: return '<span class="pill p-can">⊘ Cancelado</span>'
    if "DEVOLUCION" in s or "DEVOLUCIÓN" in s: return '<span class="pill p-dev">↩ Devolución</span>'
    if "TRANSITO" in s or "TRÁNSITO" in s: return '<span class="pill p-tra">🚚 En Tránsito</span>'
    return '<span class="pill p-pen">⏳ Pendiente</span>'

def extraer_base(n):
    n = re.sub(r'\s*-\s*', ' ', str(n).strip().upper())
    w = [x for x in n.split() if not re.match(r'^\d+$', x) and x not in ("X", "DE", "EL", "LA", "EN", "CON", "PARA", "POR")]
    return " ".join(w[:2]) if w else n

# -----------------------------------------------------------------------------
# 🧠 AI LOGIC
# -----------------------------------------------------------------------------
def ia_auto_map(api_key, campaigns, products):
    if not api_key: return {}
    prompt = f"""Empareja Campaña FB (sucia) con Producto Dropi (limpio). Retorna JSON key-value.
    CAMPAÑAS: {campaigns}
    PRODUCTOS: {products}"""
    try:
        res = requests.post("https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}, timeout=20
        ).json()
        return json.loads(res['choices'][0]['message']['content'])
    except Exception as e:
        st.error(f"Error IA: {e}")
        return {}

# -----------------------------------------------------------------------------
# 📡 DATA LOADERS & AUTO-DETECT
# -----------------------------------------------------------------------------
def detect_country(df):
    cols = df.columns.str.upper()
    if "CIUDAD DESTINO" in cols or "CIUDAD" in cols:
        col_city = "CIUDAD DESTINO" if "CIUDAD DESTINO" in cols else "CIUDAD"
        cities = set(df[col_city].dropna().astype(str).str.upper().unique())
        
        # Keywords
        co = {"BOGOTA", "MEDELLIN", "CALI", "BARRANQUILLA"}
        ec = {"QUITO", "GUAYAQUIL", "CUENCA", "AMBATO"}
        gt = {"GUATEMALA", "MIXCO", "VILLA NUEVA", "QUETZALTENANGO"}
        
        score_co = len(cities.intersection(co))
        score_ec = len(cities.intersection(ec))
        score_gt = len(cities.intersection(gt))
        
        if score_co > score_ec and score_co > score_gt: return "Colombia"
        if score_ec > score_co and score_ec > score_gt: return "Ecuador"
        if score_gt > score_co and score_gt > score_ec: return "Guatemala"
    return None

@st.cache_data
def cargar_archivo(file_bytes, ext):
    import io
    try:
        buf = io.BytesIO(file_bytes)
        if ext in ["xlsx", "xls"]:
            df = pd.read_excel(buf, dtype=str, engine="openpyxl")
        else:
            df = pd.read_csv(buf, dtype=str, encoding="latin-1", on_bad_lines="skip", sep=None, engine="python")
        
        df.columns = df.columns.str.strip().str.upper()
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
            "CIUDAD DESTINO": ["CIUDAD DESTINO", "CITY", "CIUDAD"],
            "GANANCIA": ["GANANCIA", "PROFIT"]
        }
        
        renames = {}
        for std, variants in cols_map.items():
            for v in variants:
                if v in df.columns: renames[v] = std; break
        df.rename(columns=renames, inplace=True)
        
        num_cols = ["TOTAL DE LA ORDEN", "PRECIO PROVEEDOR", "PRECIO FLETE", "COSTO DEVOLUCION FLETE", "GANANCIA", "CANTIDAD"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[^\d.\-]","",regex=True), errors="coerce").fillna(0)
        
        if "FECHA" in df.columns:
            df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
            
        return df
    except Exception as e: st.error(f"Error carga: {e}"); return pd.DataFrame()

def fb_get_accounts(tok):
    if not tok: return []
    try:
        return requests.get("https://graph.facebook.com/v21.0/me/adaccounts", params={"access_token": tok, "fields": "name,account_id", "limit": 100}).json().get("data", [])
    except: return []

def fb_get_spend(tok, accs, d1, d2):
    if not tok or not accs: return pd.DataFrame()
    rows = []
    d_range = json.dumps({"since": d1, "until": d2})
    for acc_id in accs:
        id_clean = acc_id.replace("act_", "")
        try:
            url = f"https://graph.facebook.com/v21.0/act_{id_clean}/insights"
            d = requests.get(url, params={"access_token": tok, "time_range": d_range, "fields": "campaign_name,spend", "level": "campaign", "limit": 500}).json().get("data", [])
            for x in d: rows.append({"campaign_name": x.get("campaign_name", "Unknown"), "spend": float(x.get("spend", 0)), "account_id": acc_id})
        except: pass
    return pd.DataFrame(rows)

def apply_groups(df, mapping):
    rv = {}
    for gn, ors in mapping.items():
        for o in ors: rv[o.upper().strip()] = gn
    if "PRODUCTO" in df.columns:
        df["GRUPO_PRODUCTO"] = df["PRODUCTO"].astype(str).str.upper().str.strip().map(rv).fillna(df["PRODUCTO"])
    return df

# -----------------------------------------------------------------------------
# 📊 CALCULATION ENGINE
# -----------------------------------------------------------------------------
def process_data(df, start, end, country_name, g_fb_total, g_tt_total, campaign_map):
    mask = (df["FECHA"] >= pd.Timestamp(start)) & (df["FECHA"] <= pd.Timestamp(end) + pd.Timedelta(days=1))
    df = df[mask].copy()
    if df.empty: return None
    
    agg_rules = {k:v for k,v in {"TOTAL DE LA ORDEN":"first","ESTATUS":"first","PRECIO FLETE":"first","COSTO DEVOLUCION FLETE":"first","GANANCIA":"sum","FECHA":"first","PRODUCTO":"first","CANTIDAD":"sum","PRECIO PROVEEDOR":"first", "GRUPO_PRODUCTO":"first"}.items() if k in df.columns}
    df_ord = df.groupby("ID").agg(agg_rules).reset_index() if "ID" in df.columns else df
    
    st_counts = df_ord["ESTATUS"].astype(str).str.upper().value_counts()
    def get_cnt(keys): return sum(st_counts[k] for k in st_counts.keys() if any(x in k for x in keys))
    
    n_ent = get_cnt(["ENTREGADO"])
    n_can = get_cnt(["CANCELADO"])
    n_dev = get_cnt(["DEVOLUCION", "DEVOLUCIÓN"])
    n_tra = get_cnt(["TRANSITO", "TRÁNSITO", "EN RUTA", "EN CAMINO", "DESPACHADO", "ENVIADO", "PROCESADO", "REPARTO"])
    n_nov = get_cnt(["NOVEDAD"])
    n_tot = len(df_ord)
    n_otr = n_tot - n_ent - n_can - n_dev - n_tra - n_nov
    
    df_ent = df_ord[df_ord["ESTATUS"].astype(str).str.upper().str.contains("ENTREGADO")].copy()
    ing_ent = df_ent["TOTAL DE LA ORDEN"].sum()
    costo_prod_ent = (df_ent["PRECIO PROVEEDOR"] * df_ent["CANTIDAD"]).sum()
    flete_ent = df_ent["PRECIO FLETE"].sum()
    
    df_dev = df_ord[df_ord["ESTATUS"].astype(str).str.upper().str.contains("DEVOLU")]
    flete_dev = df_dev[["PRECIO FLETE", "COSTO DEVOLUCION FLETE"]].max(axis=1).sum() if "COSTO DEVOLUCION FLETE" in df_dev.columns else df_dev["PRECIO FLETE"].sum()
    
    transit_keys = ["TRANSITO", "TRÁNSITO", "EN RUTA", "EN CAMINO", "DESPACHADO", "ENVIADO", "PROCESADO", "REPARTO"]
    df_tra = df_ord[df_ord["ESTATUS"].astype(str).str.upper().str.contains("|".join(transit_keys))]
    flete_tra = df_tra["PRECIO FLETE"].sum()
    
    gasto_ads = g_fb_total + g_tt_total
    utilidad_real = ing_ent - costo_prod_ent - flete_ent - flete_dev - flete_tra - gasto_ads
    
    prod_summary = []
    gcol = "GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in df_ord.columns else "PRODUCTO"
    if gcol in df_ord.columns:
        for prod, sub in df_ord.groupby(gcol):
            fact = sub[sub["ESTATUS"].astype(str).str.upper().str.contains("ENTREGADO", na=False)]["TOTAL DE LA ORDEN"].sum()
            costo = (sub["PRECIO PROVEEDOR"] * sub["CANTIDAD"]).sum()
            prod_summary.append({
                "Producto": prod, "Pedidos": len(sub), "Facturado Entregado": fact,
                "Entregados": len(sub[sub["ESTATUS"].astype(str).str.upper().str.contains("ENTREGADO", na=False)]),
                "Costo_Total": costo
            })
    
    return {
        "orders": df_ord,
        "kpis": {"n_tot": n_tot, "n_ent": n_ent, "n_can": n_can, "n_dev": n_dev, "n_tra": n_tra, "n_nov": n_nov, "n_otr": n_otr,
                 "ing_ent": ing_ent, "costo_prod": costo_prod_ent, "flete_ent": flete_ent, "flete_dev": flete_dev, "flete_tra": flete_tra, "ads": gasto_ads, "utilidad": utilidad_real},
        "prod_summary": pd.DataFrame(prod_summary)
    }

# -----------------------------------------------------------------------------
# 💾 SESSION STATE INIT
# -----------------------------------------------------------------------------
if "files_data" not in st.session_state: st.session_state.files_data = {}

# -----------------------------------------------------------------------------
# 🖥️ SIDEBAR
# -----------------------------------------------------------------------------
cfg = load_cfg()
PM = load_mappings()

with st.sidebar:
    st.markdown("### ⚙️ Configuración")
    with st.expander("🔑 Credenciales", expanded=False):
        fb_tok = st.text_input("FB Token", value=cfg.get("fb_tok",""), type="password")
        oa_key = st.text_input("OpenAI Key", value=cfg.get("oa_key",""), type="password")
        if st.button("Guardar Keys"): save_cfg("fb_tok", fb_tok); save_cfg("oa_key", oa_key); st.rerun()
            
    fb_accounts = fb_get_accounts(fb_tok)
    fb_map = {f"{a['name']} ({a['account_id']})": a['account_id'] for a in fb_accounts}
    
    if "sel_all_fb" not in st.session_state: st.session_state.sel_all_fb = False
    def toggle_sel_all(): st.session_state.fb_selected = list(fb_map.keys()) if st.session_state.sel_all_check else []
    st.checkbox("✅ Seleccionar Todas", key="sel_all_check", on_change=toggle_sel_all)
    sel_acc_names = st.multiselect("Cuentas Publicitarias", list(fb_map.keys()), key="fb_selected")
    sel_acc_ids = [fb_map[n] for n in sel_acc_names]
    
    st.divider()
    # Sidebar Uploaders (Always visible for adding more)
    st.markdown("### 📂 Archivos Cargados")
    for p, meta in PAISES.items():
        if p in st.session_state.files_data:
            st.caption(f"✅ {meta['flag']} {p} (Cargado)")
            if st.button(f"🗑️ Borrar {p}", key=f"del_{p}"):
                del st.session_state.files_data[p]
                st.rerun()
    
    st.markdown("---")
    st.markdown("#### Añadir Archivo")
    f_side = st.file_uploader("Subir archivo adicional", type=["csv","xlsx"], key="up_side")
    if f_side:
        df = cargar_archivo(f_side.getvalue(), f_side.name.split('.')[-1])
        if not df.empty:
            det = detect_country(df)
            if det:
                st.session_state.files_data[det] = df
                st.success(f"Detectado: {det}")
                st.rerun()
            else:
                st.error("No se pudo detectar el país.")

# -----------------------------------------------------------------------------
# 🚀 LANDING PAGE (IF NO DATA)
# -----------------------------------------------------------------------------
if not st.session_state.files_data:
    st.title("✈️ T-PILOT DASHBOARD")
    st.markdown("#### 📂 Carga Inicial")
    st.info("Arrastra tus archivos de Dropi aquí. El sistema detectará el país automáticamente.")
    
    # Large Multi-Uploader
    files = st.file_uploader("Arrastra aquí tus archivos (Colombia, Ecuador, Guatemala)", type=["csv", "xlsx"], accept_multiple_files=True, key="up_main")
    
    if files:
        for f in files:
            df = cargar_archivo(f.getvalue(), f.name.split('.')[-1])
            if not df.empty:
                det = detect_country(df)
                if det:
                    st.session_state.files_data[det] = df
                else:
                    st.warning(f"⚠️ Archivo '{f.name}' ignorado (País no detectado)")
        if st.session_state.files_data:
            st.success("✅ Archivos procesados. Cargando Dashboard...")
            st.rerun()
    
    st.stop() # Stop execution here if no data

# -----------------------------------------------------------------------------
# 📅 DASHBOARD HEADER
# -----------------------------------------------------------------------------
uploaded_data = st.session_state.files_data

c1, c2 = st.columns([2, 1])
with c1: st.markdown("## ✈️ T-PILOT DASHBOARD")
with c2:
    d1 = st.date_input("Desde", datetime.today() - timedelta(days=30))
    d2 = st.date_input("Hasta", datetime.today())
date_start = d1.strftime("%Y-%m-%d"); date_end = d2.strftime("%Y-%m-%d")

# -----------------------------------------------------------------------------
# 📢 ADS FETCH
# -----------------------------------------------------------------------------
if sel_acc_ids and fb_tok:
    with st.spinner("Descargando data de Facebook..."):
        df_ads_raw = fb_get_spend(fb_tok, sel_acc_ids, date_start, date_end)
else: df_ads_raw = pd.DataFrame(columns=["campaign_name", "spend", "account_id"])

# -----------------------------------------------------------------------------
# 🔗 MAPPING SYSTEM (Fix: Cyclic Logic)
# -----------------------------------------------------------------------------
if not df_ads_raw.empty and uploaded_data:
    with st.expander("🔗 Mapeo de Campañas (IA + Manual)", expanded=False):
        
        curr_map = load_json(CAMPAIGN_MAP_FILE)
        all_camps = sorted(df_ads_raw["campaign_name"].unique())
        
        # KEY LOGIC: Unmapped = All - Mapped
        unmapped_camps = [c for c in all_camps if c not in curr_map]
        
        all_prods = set()
        for df in uploaded_data.values():
            if "PRODUCTO" in df.columns: all_prods.update(df["PRODUCTO"].dropna().unique())
        all_prods_list = sorted(list(all_prods))
        
        # 1. LINK SECTION
        c_m1, c_m2, c_m3 = st.columns([2, 2, 1])
        with c_m1: sel_camp = st.selectbox("Campaña FB (Sin asignar)", [""] + unmapped_camps)
        with c_m2: sel_prod = st.selectbox("Producto Dropi", [""] + all_prods_list)
        with c_m3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔗 Vincular") and sel_camp and sel_prod:
                curr_map[sel_camp] = sel_prod
                save_json(CAMPAIGN_MAP_FILE, curr_map)
                st.success("Vinculado!")
                st.rerun()
        
        # 2. AI AUTO
        if st.button("🪄 Auto-Mapear (IA)"):
            if not oa_key: st.error("Falta OpenAI Key")
            else:
                with st.spinner("IA trabajando..."):
                    nm = ia_auto_map(oa_key, unmapped_camps, all_prods_list)
                    if nm:
                        curr_map.update(nm)
                        save_json(CAMPAIGN_MAP_FILE, curr_map)
                        st.success(f"IA vinculó {len(nm)} campañas!")
                        st.rerun()
        
        # 3. UNLINK SECTION
        if curr_map:
            st.markdown("##### Vínculos Activos")
            
            # Simple list for unlinking
            # We convert dict to list of strings "Campaign -> Product" for selectbox
            map_list = [f"{k}  ➡️  {v}" for k,v in curr_map.items()]
            
            c_del1, c_del2 = st.columns([3, 1])
            with c_del1:
                to_unlink_str = st.selectbox("Selecciona para Desvincular (Liberar):", [""] + map_list)
            with c_del2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ Liberar"):
                    if to_unlink_str:
                        # Extract campaign name (part before separator)
                        camp_to_free = to_unlink_str.split("  ➡️  ")[0]
                        if camp_to_free in curr_map:
                            del curr_map[camp_to_free]
                            save_json(CAMPAIGN_MAP_FILE, curr_map)
                            st.success("Liberada! Ahora aparece arriba.")
                            st.rerun()

df_ads_raw["Mapped_Product"] = df_ads_raw["campaign_name"].map(load_json(CAMPAIGN_MAP_FILE)).fillna("Otros")

# -----------------------------------------------------------------------------
# 📦 PRODUCT GROUPING (Fix: Auto-Group Low Volume to TESTEO)
# -----------------------------------------------------------------------------
if uploaded_data:
    with st.expander("📦 Agrupación de Productos (por país)", expanded=False):
        for pn, df in uploaded_data.items():
            if "PRODUCTO" not in df.columns: continue
            
            st.markdown(f"**{PAISES[pn]['flag']} {pn}**")
            country_prods = sorted(df["PRODUCTO"].dropna().unique())
            sv = PM.get(pn, {})
            prod_counts = df["PRODUCTO"].value_counts()
            
            rows = []
            for p in country_prods:
                current_group = ""
                found = False
                for gn, ors in sv.items():
                    if p.upper().strip() in [x.upper().strip() for x in ors]:
                        current_group = gn
                        found = True
                        break
                
                if not found:
                    if prod_counts.get(p, 0) < 5:
                        current_group = f"TESTEO - {PAISES[pn]['iso']}"
                    else:
                        current_group = extraer_base(p)
                
                rows.append({"Original": p, "Grupo": current_group})
            
            with st.form(key=f"form_pg_{pn}"):
                epg = st.data_editor(pd.DataFrame(rows), use_container_width=True, hide_index=True, key=f"pg_{pn}", num_rows="dynamic")
                if st.form_submit_button(f"💾 Guardar Agrupación {pn}"):
                    ng = defaultdict(list)
                    for _, r in epg.iterrows():
                        o = str(r.get("Original", "")).strip()
                        g = str(r.get("Grupo", "")).strip()
                        if o and g: ng[g].append(o)
                    PM[pn] = dict(ng); save_mappings(PM); st.success(f"✅ Guardado"); st.rerun()

# Apply Mappings
for pn, df in uploaded_data.items():
    if "PRODUCTO" in df.columns:
        sv = PM.get(pn, {})
        uploaded_data[pn] = apply_groups(df, sv)

# -----------------------------------------------------------------------------
# 🖥️ DASHBOARD TABS
# -----------------------------------------------------------------------------
main_tabs = st.tabs(["🌎 Resumen Global"] + list(uploaded_data.keys()))

# --- TAB RESUMEN GLOBAL ---
with main_tabs[0]:
    st.markdown("### 🌎 Visión Global (Consolidado COP)")
    st.info("Selecciona un país específico para ver el detalle operativo completo.")

# --- TABS PAÍSES ---
for i, pais in enumerate(uploaded_data.keys()):
    with main_tabs[i+1]:
        df = uploaded_data[pais]
        pi = PAISES[pais]
        
        groups_map = PM.get(pais, {})
        raw_to_group = {}
        for g, raws in groups_map.items():
            for r in raws: raw_to_group[r] = g
            
        df_ads_raw["Group_Assigned"] = df_ads_raw["Mapped_Product"].map(raw_to_group).fillna(df_ads_raw["Mapped_Product"])
        prods_in_data = df["GRUPO_PRODUCTO"].unique() if "GRUPO_PRODUCTO" in df.columns else df["PRODUCTO"].unique()
        df_ads_country = df_ads_raw[df_ads_raw["Group_Assigned"].isin(prods_in_data)]
        
        gasto_ads_cop = df_ads_country["spend"].sum()
        gasto_ads_local = convert_cop_to(gasto_ads_cop, pi["moneda"])
        
        data = process_data(df, date_start, date_end, pais, gasto_ads_local, 0, {})
        
        if not data: st.warning("Sin datos."); continue
        k = data["kpis"]; df_ord = data["orders"]; df_prod = data["prod_summary"]
        
        t1, t2, t3, t4 = st.tabs(["🌡 Termómetro", "📊 Proyecciones", "💰 Operación Real", "📋 Órdenes"])
        
        # 1. TERMÓMETRO
        with t1:
            k1, k2, k3 = st.columns(3)
            k1.markdown(f'<div class="kcard"><div class="lbl">PEDIDOS TOTALES</div><div class="val c-white">{k["n_tot"]:,}</div><div class="sub">Entregados: {k["n_ent"]}</div></div>', unsafe_allow_html=True)
            k2.markdown(f'<div class="kcard"><div class="lbl">FACTURADO BRUTO</div><div class="val c-white">{fmt(df_ord["TOTAL DE LA ORDEN"].sum(), pais)}</div></div>', unsafe_allow_html=True)
            k3.markdown(f'<div class="kcard"><div class="lbl">GASTO ADS</div><div class="val c-red">{fmt(k["ads"], pais)}</div></div>', unsafe_allow_html=True)
            
            st.markdown("#### Logística")
            l1, l2, l3, l4 = st.columns(4)
            l1.metric("✅ Entregado", f"{k['n_ent']} ({k['n_ent']/k['n_tot']*100:.0f}%)")
            l2.metric("🚚 Tránsito", f"{k['n_tra']} ({k['n_tra']/k['n_tot']*100:.0f}%)")
            l3.metric("↩️ Devolución", f"{k['n_dev']} ({k['n_dev']/k['n_tot']*100:.0f}%)")
            l4.metric("❌ Cancelado", f"{k['n_can']} ({k['n_can']/k['n_tot']*100:.0f}%)")

        # 2. PROYECCIONES
        with t2:
            st.markdown("#### 🔮 Simulador de Rentabilidad")
            if not df_prod.empty:
                col_sim1, col_sim2 = st.columns(2)
                with col_sim1: p_entrega = st.slider("Proyección % Entrega", 50, 100, 85, key=f"pe_{pais}")
                with col_sim2: colchon = st.slider("Colchón Devolución", 1.0, 2.0, 1.4, 0.1, key=f"col_{pais}")
                df_sim = df_prod.copy()
                df_sim["Pedidos_Proy"] = (df_sim["Pedidos"] * (p_entrega/100)).astype(int)
                df_sim["Ticket_Prom"] = df_sim["Facturado Entregado"] / df_sim["Entregados"].replace(0,1)
                df_sim["Ingreso_Sim"] = df_sim["Pedidos_Proy"] * df_sim["Ticket_Prom"]
                st.dataframe(df_sim[["Producto", "Pedidos", "Ingreso_Sim"]], use_container_width=True)

        # 3. OPERACIÓN REAL
        with t3:
            st.markdown(f"### {pi['flag']} Resultados Financieros")
            r1, r2, r3 = st.columns(3)
            r1.markdown(f'<div class="kcard"><div class="lbl">INGRESO REAL</div><div class="val c-green">{fmt(k["ing_ent"], pais)}</div></div>', unsafe_allow_html=True)
            util_c = "c-green" if k["utilidad"] > 0 else "c-red"
            r2.markdown(f'<div class="kcard"><div class="lbl">UTILIDAD NETA</div><div class="val {util_c}">{fmt(k["utilidad"], pais)}</div></div>', unsafe_allow_html=True)
            r3.markdown(f'<div class="kcard"><div class="lbl">ADS SPEND</div><div class="val c-red">{fmt(k["ads"], pais)}</div></div>', unsafe_allow_html=True)

            def row_fin(label, val, is_neg=True, icon="🔻"):
                color = "#EF4444" if is_neg else "#10B981"
                pct = (val / k["ing_ent"] * 100) if k["ing_ent"] > 0 else 0
                return f"""<div style="display:flex; justify-content:space-between; padding: 10px 0; border-bottom: 1px solid #1E293B;">
                    <div style="width:40%">{icon} {label}</div>
                    <div style="width:30%; text-align:right; font-family:'JetBrains Mono'; color:{color}">{fmt(val, pais)}</div>
                    <div style="width:20%; text-align:right;"><span class="pct" style="background:#1E293B">{pct:.1f}%</span></div></div>"""
            
            html = f"""<div style="background:#111827; padding:20px; border-radius:12px; border:1px solid #1E293B">
                {row_fin("INGRESO TOTAL", k["ing_ent"], False, "💰")}
                {row_fin("Costo Producto", k["costo_prod"], True, "📦")}
                {row_fin("Publicidad", k["ads"], True, "📢")}
                {row_fin("Fletes Ida", k["flete_ent"], True, "🚚")}
                {row_fin("Fletes Devolución", k["flete_dev"], True, "↩️")}
                {row_fin("Fletes Tránsito", k["flete_tra"], True, "⏳")}
                <div style="border-top: 2px dashed #334155; margin-top:10px; padding-top:10px; display:flex; justify-content:space-between;">
                    <span style="font-weight:700">UTILIDAD FINAL</span>
                    <span style="font-family:'JetBrains Mono'; font-size:1.2rem; color:{util_c}">{fmt(k['utilidad'], pais)}</span>
                </div></div>"""
            st.markdown(html, unsafe_allow_html=True)
            
            st.divider()
            st.markdown("#### 📦 Detalle por Producto")
            if not df_prod.empty:
                ads_by_group = df_ads_country.groupby("Group_Assigned")["spend"].sum().reset_index()
                ads_by_group.columns = ["Producto", "Ads_COP"]
                
                df_final = pd.merge(df_prod, ads_by_group, on="Producto", how="left").fillna(0)
                df_final["Gasto Ads"] = df_final["Ads_COP"].apply(lambda x: convert_cop_to(x, pi["moneda"]))
                df_final["ROAS"] = df_final.apply(lambda x: x["Facturado Entregado"]/x["Gasto Ads"] if x["Gasto Ads"]>0 else 0, axis=1)
                st.dataframe(df_final[["Producto","Pedidos","Entregados","Facturado Entregado","Gasto Ads","ROAS"]], use_container_width=True)

        # 4. ÓRDENES
        with t4:
            st.markdown("#### 📋 Listado de Pedidos")
            cols = [c for c in ["ID", "FECHA", "ESTATUS", "PRODUCTO", "TOTAL DE LA ORDEN", "CIUDAD DESTINO"] if c in df_ord.columns]
            if cols:
                st.dataframe(df_ord[cols].sort_values("FECHA", ascending=False) if "FECHA" in cols else df_ord[cols], use_container_width=True)

st.markdown("<br><center style='color:#475569'>T-PILOT v5.5 · Stable Version</center>", unsafe_allow_html=True)
