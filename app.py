"""
Ecommerce Profit Dashboard v5.2
Multi-Country · Dropi + Facebook + TikTok
Fix: Batch Editing (Formularios para evitar recargas constantes)
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
SETTINGS_FILE="dashboard_settings.json"; MAPPING_FILE="product_mappings.json"; CAMP_MAPPING_FILE="campaign_mappings.json"
C=dict(profit="#10B981",loss="#EF4444",warn="#F59E0B",blue="#3B82F6",purple="#8B5CF6",orange="#F97316",cyan="#06B6D4",muted="#64748B",text="#E2E8F0",sub="#94A3B8",grid="#1E293B",bg="#0B0F19")
STATUS_ENT=["ENTREGADO"]; STATUS_CAN=["CANCELADO"]
STATUS_TRA=["EN TRANSITO","EN TRÁNSITO","EN ESPERA DE RUTA DOMESTICA","DESPACHADA","DESPACHADO","ENVIADO","EN REPARTO","EN RUTA","EN BODEGA TRANSPORTADORA","EN BODEGA DESTINO","GUIA IMPRESA","EN ALISTAMIENTO","EN CAMINO","ESPERANDO RUTA"]
STATUS_DEV=["DEVOLUCION","DEVOLUCIÓN","EN DEVOLUCION","EN DEVOLUCIÓN"]; STATUS_NOV=["NOVEDAD","CON NOVEDAD"]

COUNTRY_ALIASES={"CO":"Colombia","COL":"Colombia","COLOMBIA":"Colombia","EC":"Ecuador","ECU":"Ecuador","ECUADOR":"Ecuador","GT":"Guatemala","GUA":"Guatemala","GUATEMALA":"Guatemala"}

def ms(s,pats): return any(p in s.upper().strip() for p in pats)

def pl(**kw):
    b=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Inter,system-ui,sans-serif",color=C["text"],size=12),xaxis=dict(gridcolor=C["grid"],zerolinecolor=C["grid"]),yaxis=dict(gridcolor=C["grid"],zerolinecolor=C["grid"]),margin=dict(l=40,r=20,t=50,b=40),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=11,color=C["sub"])))
    b.update(kw); return b

# ═══ CSS ═══
st.markdown("""<style>
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
hr{border-color:#1E293B!important}
[data-testid="stFileUploader"]>div{background:#111827!important;border:1px dashed #334155!important;border-radius:.75rem!important}
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
.otbl{width:100%;border-collapse:separate;border-spacing:0;font-size:.83rem}
.otbl th{padding:12px 16px;text-align:left;font-size:.68rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:#64748B;background:#111827;border-bottom:1px solid #1E293B}
.otbl td{padding:14px 16px;border-bottom:1px solid rgba(15,20,32,0.8);color:#E2E8F0}.otbl tr:hover td{background:#131A2B}
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:9999px;font-size:.72rem;font-weight:600}
.p-ent{background:rgba(16,185,129,0.15);color:#10B981;border:1px solid rgba(16,185,129,0.3)}.p-can{background:rgba(239,68,68,0.15);color:#EF4444;border:1px solid rgba(239,68,68,0.3)}.p-tra{background:rgba(245,158,11,0.15);color:#F59E0B;border:1px solid rgba(245,158,11,0.3)}.p-dev{background:rgba(249,115,22,0.15);color:#F97316;border:1px solid rgba(249,115,22,0.3)}.p-nov{background:rgba(139,92,246,0.15);color:#8B5CF6;border:1px solid rgba(139,92,246,0.3)}.p-pen{background:rgba(100,116,139,0.15);color:#94A3B8;border:1px solid rgba(100,116,139,0.3)}
.lgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:1rem;margin:1rem 0}
.litem{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1rem;text-align:center}
.litem h3{font-size:1.3rem;font-weight:700;font-family:'JetBrains Mono',monospace;margin:.3rem 0}.litem p{font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#64748B;margin:0}
.badge{display:inline-block;padding:2px 10px;border-radius:9999px;font-size:.75rem;font-weight:600;font-family:'JetBrains Mono',monospace}
.thermo{background:linear-gradient(180deg,#131A2B,#0F1420);border:1px solid #1E293B;border-radius:.75rem;padding:1.2rem 1.5rem;margin:1rem 0}
.thermo .hd{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}.thermo .tt{font-size:.78rem;font-weight:600;text-transform:uppercase;color:#94A3B8}.thermo .tv{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:1.15rem;color:#10B981}
.thermo .bar{height:12px;border-radius:6px;background:linear-gradient(90deg,#EF4444 0%,#F59E0B 50%,#10B981 100%);position:relative;margin-bottom:6px}.thermo .mk{position:absolute;top:-4px;width:3px;height:20px;background:#FFF;border-radius:2px}.thermo .lb{display:flex;justify-content:space-between;font-size:.68rem;color:#64748B}
</style>""", unsafe_allow_html=True)

# ═══ HELPERS ═══
def load_json(p):
    if os.path.exists(p):
        try:
            with open(p) as f: return json.load(f)
        except: pass
    return {}
def save_json(p,d):
    try:
        with open(p,"w") as f: json.dump(d,f,ensure_ascii=False)
    except: pass
def load_cfg(): return load_json(SETTINGS_FILE)
def save_cfg(k,v): s=load_cfg();s[k]=v;save_json(SETTINGS_FILE,s)
def load_mappings(): return load_json(MAPPING_FILE)
def save_mappings(d): save_json(MAPPING_FILE,d)
def load_camp_map(): return load_json(CAMP_MAPPING_FILE)
def save_camp_map(d): save_json(CAMP_MAPPING_FILE,d)

@st.cache_data(ttl=3600,show_spinner=False)
def get_trm():
    rates={"COP_USD":4200,"COP_GTQ":540}
    try:
        r=requests.get("https://open.er-api.com/v6/latest/USD",timeout=10)
        if r.ok: d=r.json(); rates["COP_USD"]=d["rates"].get("COP",4200); rates["COP_GTQ"]=rates["COP_USD"]/d["rates"].get("GTQ",7.75)
    except: pass
    return rates
def cop_to(v,t,trm):
    if t=="COP": return v
    if t=="USD": return v/trm.get("COP_USD",4200)
    if t=="GTQ": return v/trm.get("COP_GTQ",540)
    return v
def to_cop(v,s,trm):
    if s=="COP": return v
    if s=="USD": return v*trm.get("COP_USD",4200)
    if s=="GTQ": return v*trm.get("COP_GTQ",540)
    return v

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
        sc={"Colombia":len(c&co),"Ecuador":len(c&ec),"Guatemala":len(c&gt)}
        b=max(sc,key=sc.get)
        if sc[b]>0: return b
    return None

def extraer_base(n):
    n=re.sub(r'\s*-\s*',' ',str(n).strip().upper())
    w=[x for x in n.split() if not re.match(r'^\d+$',x) and x not in ("X","DE","EL","LA","EN","CON","PARA","POR")]
    return " ".join(w[:2]) if w else n

def build_groups(pl):
    g=defaultdict(list)
    for p in pl: g[extraer_base(p)].append(p)
    return dict(g)

def apply_groups(df,gm):
    rv={}
    for gn,ors in gm.items():
        for o in ors: rv[o.upper().strip()]=gn
    df["GRUPO_PRODUCTO"]=df["PRODUCTO"].str.upper().str.strip().map(rv).fillna(df["PRODUCTO"]);return df

def fmt(v,pn="Colombia"): return f"{PAISES.get(pn,PAISES['Colombia'])['sym']} {v:,.0f}".replace(",",".")
def fmt_cop(v): return f"$ {v:,.0f}".replace(",",".")
def pof(p,w): return f"{(p/w*100):.1f}%" if w else "0%"

def parse_campaign_country(camp_name):
    parts=[x.strip().upper() for x in str(camp_name).split("-")]
    if parts:
        first=parts[0].strip()
        return COUNTRY_ALIASES.get(first,None)
    return None

def agg_orders(df):
    F={c:c in df.columns for c in ["ID","ESTATUS","TOTAL DE LA ORDEN","PRODUCTO","CANTIDAD","GANANCIA","PRECIO FLETE","PRECIO PROVEEDOR","COSTO DEVOLUCION FLETE","CIUDAD DESTINO","FECHA","GRUPO_PRODUCTO","PRECIO PROVEEDOR X CANTIDAD"]}
    if not F["ID"]: return df,F
    ag={}
    for c,fn in [("TOTAL DE LA ORDEN","first"),("ESTATUS","first"),("PRECIO FLETE","first"),("COSTO DEVOLUCION FLETE","first"),("GANANCIA","sum"),("FECHA","first"),("CIUDAD DESTINO","first"),("PRODUCTO","first"),("CANTIDAD","sum"),("PRECIO PROVEEDOR","first"),("PRECIO PROVEEDOR X CANTIDAD","sum"),("GRUPO_PRODUCTO","first")]:
        if c in df.columns: ag[c]=fn
    return (df.groupby("ID").agg(ag).reset_index() if ag else df.copy()),F

def calc_kpis(df_ord,F,gfb,gtt):
    no=df_ord["ID"].nunique() if F.get("ID") else len(df_ord)
    fb=df_ord["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    dnc=df_ord[~df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_CAN))] if F.get("ESTATUS") else df_ord
    fn=dnc["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
    nd=len(dnc);aov=fb/no if no>0 else 0;ga=gfb+gtt;roas=fn/ga if ga>0 else 0
    sc={}
    if F.get("ESTATUS"):
        for s in df_ord["ESTATUS"].unique(): sc[s]=len(df_ord[df_ord["ESTATUS"]==s])
    ne=sum(v for s,v in sc.items() if ms(s,STATUS_ENT));nc=sum(v for s,v in sc.items() if ms(s,STATUS_CAN))
    nt=sum(v for s,v in sc.items() if ms(s,STATUS_TRA));nv=sum(v for s,v in sc.items() if ms(s,STATUS_DEV))
    nn=sum(v for s,v in sc.items() if ms(s,STATUS_NOV));nother=max(0,no-ne-nc-nt-nv-nn)
    nnc=no-nc;pcan=(nc/no*100) if no>0 else 0;pent=(ne/nnc*100) if nnc>0 else 0
    de=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
    ir=de["TOTAL DE LA ORDEN"].sum() if (not de.empty and F.get("TOTAL DE LA ORDEN")) else 0
    cpr=0
    if not de.empty and "PRECIO PROVEEDOR X CANTIDAD" in de.columns: cpr=de["PRECIO PROVEEDOR X CANTIDAD"].sum()
    elif not de.empty and F.get("PRECIO PROVEEDOR") and F.get("CANTIDAD"): cpr=(de["PRECIO PROVEEDOR"]*de["CANTIDAD"]).sum()
    fle=de["PRECIO FLETE"].sum() if (not de.empty and F.get("PRECIO FLETE")) else 0
    dd=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_DEV))].copy() if F.get("ESTATUS") else pd.DataFrame()
    fld=0
    if not dd.empty:
        if F.get("PRECIO FLETE") and F.get("COSTO DEVOLUCION FLETE"): fld=dd[["PRECIO FLETE","COSTO DEVOLUCION FLETE"]].max(axis=1).sum()
        elif F.get("PRECIO FLETE"): fld=dd["PRECIO FLETE"].sum()
    dt=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,STATUS_TRA))].copy() if F.get("ESTATUS") else pd.DataFrame()
    flt=dt["PRECIO FLETE"].sum() if (not dt.empty and F.get("PRECIO FLETE")) else 0
    ur=ir-cpr-ga-fle-fld-flt
    return dict(n_ord=no,fact_bruto=fb,fact_neto=fn,n_desp=nd,aov=aov,g_fb=gfb,g_tt=gtt,g_ads=ga,roas=roas,n_ent=ne,n_can=nc,n_tra=nt,n_dev=nv,n_nov=nn,n_otr=nother,n_nc=nnc,pct_can=pcan,pct_ent=pent,tasa_ent=pent,ing_real=ir,cpr=cpr,fl_ent=fle,fl_dev=fld,fl_tra=flt,u_real=ur)

def status_pill(s):
    s=s.upper()
    if "ENTREGADO" in s: return '<span class="pill p-ent">✅ Entregado</span>'
    if "CANCELADO" in s: return '<span class="pill p-can">⊘ Cancelado</span>'
    if "DEVOLUCION" in s or "DEVOLUCIÓN" in s: return '<span class="pill p-dev">↩ Devolución</span>'
    if ms(s,STATUS_TRA): return '<span class="pill p-tra">🚚 Tránsito</span>'
    if "NOVEDAD" in s: return '<span class="pill p-nov">⚠ Novedad</span>'
    return '<span class="pill p-pen">⏳ Pendiente</span>'

def to_excel(df):
    buf=io.BytesIO();df.to_excel(buf,index=False,engine="openpyxl");return buf.getvalue()

def fb_spend(tok,cid,i,f):
    if not tok or not cid: return 0.0
    cid=cid.strip()
    if not cid.startswith("act_"): cid=f"act_{cid}"
    try:
        r=requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"spend","level":"account"},timeout=30)
        d=r.json()
        if "data" in d and d["data"]: return float(d["data"][0].get("spend",0))
    except: pass
    return 0.0
def fb_camps(tok,cid,i,f):
    if not tok or not cid: return pd.DataFrame(columns=["campaign_name","spend"])
    cid=cid.strip()
    if not cid.startswith("act_"): cid=f"act_{cid}"
    try:
        r=requests.get(f"https://graph.facebook.com/v21.0/{cid}/insights",params={"access_token":tok,"time_range":json.dumps({"since":i,"until":f}),"fields":"campaign_name,spend","level":"campaign","limit":500},timeout=30)
        d=r.json()
        if "data" in d: return pd.DataFrame([{"campaign_name":x.get("campaign_name",""),"spend":float(x.get("spend",0))} for x in d["data"]])
    except: pass
    return pd.DataFrame(columns=["campaign_name","spend"])
def fb_accts(tok):
    if not tok: return []
    try:
        r=requests.get("https://graph.facebook.com/v21.0/me/adaccounts",params={"access_token":tok,"fields":"name,account_id,currency","limit":50},timeout=15)
        d=r.json()
        if "data" in d: return [{"id":a.get("account_id",""),"name":a.get("name",""),"cur":a.get("currency","")} for a in d["data"]]
    except: pass
    return []
def tt_spend(tok,aid,i,f):
    if not tok or not aid: return 0.0
    try:
        r=requests.post("https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",headers={"Access-Token":tok,"Content-Type":"application/json"},json={"advertiser_id":aid,"report_type":"BASIC","data_level":"AUCTION_ADVERTISER","dimensions":["advertiser_id"],"metrics":["spend"],"start_date":i,"end_date":f},timeout=30)
        d=r.json()
        if d.get("code")==0 and d.get("data",{}).get("list"): return float(d["data"]["list"][0]["metrics"].get("spend",0))
    except: pass
    return 0.0

def ai_map_with_country(camps_with_spend, products_by_country, key):
    if not key: return {}
    camp_info = [{"campaign": c["name"], "country_detected": c.get("country","Unknown"), "spend": c["spend"]} for c in camps_with_spend]
    prompt = f"""Eres un asistente que empareja campañas de Facebook con productos de Dropi.
    Campañas: {json.dumps(camp_info, ensure_ascii=False)}
    Productos por país: {json.dumps(products_by_country, ensure_ascii=False)}
    REGLAS:
    1. Empareja cada campaña con el producto del MISMO PAÍS (CO/EC/GT)
    2. Basate en similitud de texto.
    Responde SOLO un JSON: {{"nombre_campaña": "nombre_producto_dropi", ...}}"""
    try:
        r=requests.post("https://api.openai.com/v1/chat/completions",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
            json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":3000},timeout=45)
        txt=r.json()["choices"][0]["message"]["content"].strip()
        txt=re.sub(r'^```json\s*','',txt);txt=re.sub(r'```$','',txt)
        return json.loads(txt)
    except Exception as e: st.error(f"Error IA: {e}"); return {}

def render_logistics(label,k,C_):
    no=k["n_ord"];nc=k["n_can"];ne=k["n_ent"];nt=k["n_tra"];nv=k["n_dev"];nn=k["n_nov"];nother=k["n_otr"];nnc=no-nc
    def p(n): return f"{(n/nnc*100):.0f}%" if nnc else "0%"
    return f"""<p class="section-hdr">{label} — {no:,} órdenes</p>
    <div class="lgrid"><div class="litem" style="border-color:rgba(239,68,68,0.3)"><p>❌ CANCELADO</p><h3 style="color:{C_['loss']}">{nc:,}</h3><span class="badge" style="background:rgba(239,68,68,0.15);color:#EF4444">{(nc/no*100):.0f}% total</span></div></div>
    <div class="lgrid"><div class="litem" style="border-color:rgba(16,185,129,0.3)"><p>✅ ENTREGADO</p><h3 style="color:{C_['profit']}">{ne:,}</h3><span class="badge" style="background:rgba(16,185,129,0.15);color:#10B981">{p(ne)}</span></div><div class="litem" style="border-color:rgba(59,130,246,0.3)"><p>🚚 TRÁNSITO</p><h3 style="color:{C_['blue']}">{nt:,}</h3><span class="badge" style="background:rgba(59,130,246,0.15);color:#3B82F6">{p(nt)}</span></div><div class="litem" style="border-color:rgba(245,158,11,0.3)"><p>↩ DEVOLUCIÓN</p><h3 style="color:{C_['warn']}">{nv:,}</h3><span class="badge" style="background:rgba(245,158,11,0.15);color:#F59E0B">{p(nv)}</span></div><div class="litem" style="border-color:rgba(249,115,22,0.3)"><p>⚠ NOVEDAD</p><h3 style="color:{C_['orange']}">{nn:,}</h3><span class="badge" style="background:rgba(249,115,22,0.15);color:#F97316">{p(nn)}</span></div><div class="litem" style="border-color:rgba(100,116,139,0.3)"><p>⏳ OTROS</p><h3 style="color:{C_['muted']}">{nother:,}</h3><span class="badge" style="background:rgba(100,116,139,0.15);color:#94A3B8">{p(nother)}</span></div></div>"""

def dl_logistics(df_ord,F,label,pats,key):
    if not F.get("ESTATUS"): return
    filt=df_ord[df_ord["ESTATUS"].apply(lambda s:ms(s,pats))]
    if not filt.empty:
        st.download_button(f"📥 {label} ({len(filt)})",to_excel(filt),file_name=f"{label.lower().replace(' ','_')}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key=key)

# ═══ TRM ═══
trm=get_trm();trm_usd=trm.get("COP_USD",4200);trm_gtq=trm.get("COP_GTQ",540)

# ═══ SIDEBAR ═══
cfg=load_cfg()
with st.sidebar:
    st.markdown("### 📊 Dashboard v5.2")
    st.divider()
    st.markdown("##### 📢 Publicidad")
    usar_api=st.checkbox("Usar APIs",value=True)
    fb_token="";fb_cids=[];tt_token="";tt_aids=[]
    if usar_api:
        fb_token=st.text_input("Token FB",type="password",value=cfg.get("fb_token",""),key="fbt")
        if fb_token: save_cfg("fb_token",fb_token)
        accts=fb_accts(fb_token)
        if accts:
            opts={f"{a['name']} ({a['id']})":a["id"] for a in accts};ok=list(opts.keys())
            sel_all=st.checkbox("✅ Seleccionar TODAS",key="sel_all_fb")
            if sel_all: fb_cids=[opts[k] for k in ok];st.caption(f"✅ {len(fb_cids)} cuentas")
            else: sel=st.multiselect("Cuentas FB",ok,key="fb_ms");fb_cids=[opts[l] for l in sel]
        else:
            v=st.text_input("IDs FB (coma)",value=cfg.get("fb_cids",""))
            if v: save_cfg("fb_cids",v);fb_cids=[x.strip() for x in v.split(",") if x.strip()]
        tt_token=st.text_input("Token TT",type="password",value=cfg.get("tt_token",""),key="ttt")
        tt_inp=st.text_input("Adv IDs TT",value=cfg.get("tt_aids",""))
        if tt_token: save_cfg("tt_token",tt_token)
        if tt_inp: save_cfg("tt_aids",tt_inp);tt_aids=[x.strip() for x in tt_inp.split(",") if x.strip()]
        st.caption(f"TRM: 1 USD={trm_usd:,.0f} COP · 1 GTQ≈{trm_gtq:,.0f} COP")
    ads_manual={}
    if not usar_api:
        for pn in PAISES: ads_manual[pn]=st.number_input(f"Ads {pn} ({PAISES[pn]['moneda']})",min_value=0.0,value=0.0,step=1000.0,key=f"gm_{pn}")
    st.divider()
    oai_key=st.text_input("🤖 OpenAI Key",type="password",value=cfg.get("oai_key",""),key="oai")
    if oai_key: save_cfg("oai_key",oai_key)

# ═══ INIT ═══
for pn in PAISES:
    for k in (f"_b_{pn}",f"_n_{pn}"):
        if k not in st.session_state: st.session_state[k]=None

# ═══ TITLE + DATES ═══
st.markdown('<p style="text-align:center;font-size:1.8rem;font-weight:800;color:#F1F5F9;margin-bottom:.5rem">📊 Ecommerce Profit Dashboard</p>',unsafe_allow_html=True)
hoy=datetime.today().date()
dc1,dc2,dc3=st.columns([1,1,3])
with dc1: f_ini=st.date_input("📅 Desde",value=hoy-timedelta(days=30),key="d_ini")
with dc2: f_fin=st.date_input("📅 Hasta",value=hoy,key="d_fin")
with dc3: st.markdown(f'<div style="padding-top:1.6rem"><span style="color:{C["sub"]};font-size:.8rem">TRM: <b style="color:{C["text"]}">1 USD = {trm_usd:,.0f} COP</b> · <b style="color:{C["text"]}">1 GTQ ≈ {trm_gtq:,.0f} COP</b></span></div>',unsafe_allow_html=True)

any_data=any(st.session_state.get(f"_b_{pn}") for pn in PAISES)
if not any_data:
    st.divider()
    st.markdown('<p class="section-hdr">Sube tus archivos</p>',unsafe_allow_html=True)
    st.markdown("Sube **varios archivos** — se auto-detecta el país.")
    files=st.file_uploader("Arrastra aquí",type=["csv","xlsx","xls"],accept_multiple_files=True,key="up_multi")
    if files:
        for f in files:
            td=cargar(f.getvalue(),f.name);det=detect_country(td)
            if det: st.session_state[f"_b_{det}"]=f.getvalue();st.session_state[f"_n_{det}"]=f.name;st.success(f"✅ {PAISES[det]['flag']} {det} — {len(td):,} filas")
            else: st.warning(f"⚠ No detectado: {f.name}")
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
CD={};PM=load_mappings();gxp={};gxp_by_country={}
all_camps=pd.DataFrame(columns=["campaign_name","spend"])
if usar_api:
    for c in fb_cids: all_camps=pd.concat([all_camps,fb_camps(fb_token,c,si,sf)])
# Filter only campaigns with spend > 0
if not all_camps.empty: all_camps=all_camps[all_camps["spend"]>0].copy()

if usar_api: gfb_cop=sum(fb_spend(fb_token,c,si,sf) for c in fb_cids);gtt_cop=sum(tt_spend(tt_token,a,si,sf) for a in tt_aids)
else: gfb_cop=sum(to_cop(ads_manual.get(pn,0),PAISES[pn]["moneda"],trm) for pn in PAISES);gtt_cop=0

crl={};tr=0
for pn in PAISES:
    if not st.session_state.get(f"_b_{pn}"): continue
    df_t=filtrar(cargar(st.session_state[f"_b_{pn}"],st.session_state[f"_n_{pn}"]),f_ini,f_fin)
    if not df_t.empty: crl[pn]=len(df_t);tr+=len(df_t)

for pn in PAISES:
    if not st.session_state.get(f"_b_{pn}"): continue
    df_f=filtrar(cargar(st.session_state[f"_b_{pn}"],st.session_state[f"_n_{pn}"]),f_ini,f_fin)
    if df_f.empty: continue
    mon=PAISES[pn]["moneda"]
    if "PRODUCTO" in df_f.columns:
        sv=PM.get(pn,{})
        country_products=sorted(df_f["PRODUCTO"].dropna().unique())
        if sv:
            valid_sv={}
            cp_set=set(p.upper().strip() for p in country_products)
            for gn,ors in sv.items():
                valid_ors=[o for o in ors if o.upper().strip() in cp_set]
                if valid_ors: valid_sv[gn]=valid_ors
            df_f=apply_groups(df_f,valid_sv if valid_sv else build_groups(country_products))
        else:
            ag=build_groups(country_products);df_f=apply_groups(df_f,ag);PM[pn]=ag;save_mappings(PM)
    df_ord,F=agg_orders(df_f)
    if usar_api:
        r_=crl.get(pn,0)/max(tr,1)
        gfb_local=cop_to(gfb_cop*r_,mon,trm);gtt_local=cop_to(gtt_cop*r_,mon,trm)
        gfb_cop_c=gfb_cop*r_;gtt_cop_c=gtt_cop*r_
    else:
        gfb_local=ads_manual.get(pn,0);gtt_local=0
        gfb_cop_c=to_cop(gfb_local,mon,trm);gtt_cop_c=0
    kpis=calc_kpis(df_ord,F,gfb_local,gtt_local)
    kpis["g_fb_cop"]=gfb_cop_c;kpis["g_tt_cop"]=gtt_cop_c;kpis["g_ads_cop"]=gfb_cop_c+gtt_cop_c
    CD[pn]={"df":df_f,"df_ord":df_ord,"kpis":kpis,"F":F}
if not CD: st.warning("Sin datos.");st.stop()

# ═══ FIX: FORMS FOR BATCH EDITING ═══
with st.expander("📦 Agrupación de Productos (por país)",expanded=False):
    for pn,cd in CD.items():
        if "PRODUCTO" not in cd["df"].columns: continue
        st.markdown(f"**{PAISES[pn]['flag']} {pn}**")
        country_prods=sorted(cd["df"]["PRODUCTO"].dropna().unique())
        sv=PM.get(pn,{});rows=[]
        for gn,ms_ in sv.items():
            for m in ms_:
                if m.upper().strip() in set(p.upper().strip() for p in country_prods):
                    rows.append({"Original":m,"Grupo":gn})
        if not rows:
            for p in country_prods: rows.append({"Original":p,"Grupo":extraer_base(p)})
        
        # FORM STARTS HERE
        with st.form(key=f"form_pg_{pn}"):
            epg=st.data_editor(pd.DataFrame(rows),use_container_width=True,hide_index=True,key=f"pg_{pn}",num_rows="dynamic")
            if st.form_submit_button(f"💾 Guardar Cambios {pn}"):
                ng=defaultdict(list)
                for _,r in epg.iterrows():
                    o=str(r.get("Original","")).strip();g=str(r.get("Grupo","")).strip()
                    if o and g: ng[g].append(o)
                PM[pn]=dict(ng);save_mappings(PM);st.success(f"✅ Guardado");st.rerun()

cm_saved=load_camp_map()
if not all_camps.empty:
    with st.expander("🔗 Mapeo Campañas → Productos (Producto primero)",expanded=False):
        products_by_country={}
        all_prods_flat=[]
        for pn2,cd2 in CD.items():
            gc2="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in cd2["df_ord"].columns else ("PRODUCTO" if cd2["F"].get("PRODUCTO") else None)
            if gc2:
                pp=sorted(cd2["df_ord"][gc2].dropna().unique().tolist())
                products_by_country[pn2]=pp
                for p in pp:
                    label=f"{PAISES[pn2]['flag']} {p}"
                    if label not in all_prods_flat: all_prods_flat.append(label)

        cn=sorted(all_camps["campaign_name"].unique().tolist())
        camp_spend={c:all_camps[all_camps["campaign_name"]==c]["spend"].sum() for c in cn}
        camp_countries={c:parse_campaign_country(c) for c in cn}
        all_assigned=set()
        for prod,camps in cm_saved.items(): all_assigned.update(camps)

        st.markdown(f"**{len(cn)}** campañas con gasto · **{len(all_prods_flat)}** productos")

        ac1,ac2=st.columns([1,2])
        with ac1:
            if st.button("🪄 Auto-Mapear con IA",key="ai_m"):
                if oai_key:
                    camps_info=[{"name":c,"spend":camp_spend[c],"country":camp_countries.get(c,"Unknown")} for c in cn if c not in all_assigned]
                    with st.spinner(f"Mapeando {len(camps_info)} campañas..."):
                        result=ai_map_with_country(camps_info,products_by_country,oai_key)
                    if result:
                        for camp,prod in result.items():
                            if prod not in cm_saved: cm_saved[prod]=[]
                            if camp not in cm_saved[prod]: cm_saved[prod].append(camp)
                        save_camp_map(cm_saved);st.success(f"✅ {len(result)} mapeadas");st.rerun()
                else: st.warning("Ingresa OpenAI Key en sidebar")
        
        st.divider()

        # FORM FOR CAMPAIGN MAPPING
        if "camp_draft" not in st.session_state: st.session_state["camp_draft"]=dict(cm_saved)
        
        with st.form(key="form_camp_map"):
            for prod_label in all_prods_flat:
                prod_name=prod_label.split(" ",1)[1] if " " in prod_label else prod_label
                currently_assigned=st.session_state["camp_draft"].get(prod_name,[])
                other_assigned=set()
                for p2,cs2 in st.session_state["camp_draft"].items():
                    if p2!=prod_name: other_assigned.update(cs2)
                available=[c for c in cn if c not in other_assigned]
                
                # Show all currently assigned + available ones
                # To make multiselect work in form, we need to pre-calculate options
                # Options = Currently Assigned to THIS product + All Unassigned
                
                # Filter logic inside form is hard without rerun. We show all available + current.
                # A user can deselect from here or select from available.
                
                options = sorted(list(set(currently_assigned + available)))
                options_display = [f"{c} (${camp_spend.get(c,0):,.0f})" for c in options]
                options_map = {f"{c} (${camp_spend.get(c,0):,.0f})":c for c in options}
                default_display = [f"{c} (${camp_spend.get(c,0):,.0f})" for c in currently_assigned if c in options]
                
                sel = st.multiselect(f"📦 {prod_label}", options_display, default=default_display)
                st.session_state["camp_draft"][prod_name] = [options_map[s] for s in sel]
            
            if st.form_submit_button("💾 Guardar Todo el Mapeo"):
                cm_saved=dict(st.session_state["camp_draft"])
                save_camp_map(cm_saved)
                st.success("✅ Mapeo guardado")
                st.rerun()

    # Rebuild gxp
    for prod,camps in cm_saved.items():
        total_spend_cop=sum(camp_spend.get(c,0) for c in camps if c in camp_spend) if not all_camps.empty else 0
        if total_spend_cop>0: gxp[prod.upper()]=total_spend_cop

    for pn2 in CD:
        mon2=PAISES[pn2]["moneda"]
        gxp_by_country[pn2]={}
        gc2="GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in CD[pn2]["df_ord"].columns else ("PRODUCTO" if CD[pn2]["F"].get("PRODUCTO") else None)
        if gc2:
            for prod in CD[pn2]["df_ord"][gc2].dropna().unique():
                cop_val=gxp.get(prod.upper(),0)
                if cop_val>0: gxp_by_country[pn2][prod.upper()]=cop_to(cop_val,mon2,trm)

# ═══ TABS ═══
def gcol_of(cd): return "GRUPO_PRODUCTO" if "GRUPO_PRODUCTO" in cd["df_ord"].columns else ("PRODUCTO" if cd["F"].get("PRODUCTO") else None)
tn=["🏠 Dashboard","📊 Proyección Global"]
for pn in CD: tn.append(f"{PAISES[pn]['flag']} {pn}")
tn.append("📢 Publicidad")
tabs=st.tabs(tn)

# ═══ TAB: DASHBOARD ═══
with tabs[0]:
    tot_o=sum(cd["kpis"]["n_ord"] for cd in CD.values())
    tot_f=sum(to_cop(cd["kpis"]["fact_neto"],PAISES[pn]["moneda"],trm) for pn,cd in CD.items())
    tot_a=sum(cd["kpis"].get("g_ads_cop",0) for cd in CD.values())
    tot_u=sum(to_cop(cd["kpis"]["u_real"],PAISES[pn]["moneda"],trm) for pn,cd in CD.items())
    tot_r=tot_f/tot_a if tot_a>0 else 0
    st.markdown(f'<p class="section-hdr">Total Operación (COP)</p><div class="row2 r4"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{tot_o:,}</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO</div><div class="val lg green">{fmt_cop(tot_f)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val lg red">{fmt_cop(tot_a)}</div></div><div class="kcard {"green" if tot_u>=0 else "red"}"><div class="icon {"g" if tot_u>=0 else "r"}">💰</div><div class="lbl">UTILIDAD</div><div class="val lg {"green" if tot_u>=0 else "red"}">{fmt_cop(tot_u)}</div><div class="sub">ROAS: {tot_r:.2f}x</div></div></div>',unsafe_allow_html=True)
    all_daily=[]
    for pn,cd in CD.items():
        if "FECHA" in cd["df_ord"].columns:
            d=cd["df_ord"].groupby(cd["df_ord"]["FECHA"].dt.date).agg(fac=("TOTAL DE LA ORDEN","sum"),ords=("ID","count")).reset_index();d.columns=["Fecha","Fac","Ords"];d["Fac"]=d["Fac"].apply(lambda v:to_cop(v,PAISES[pn]["moneda"],trm))
            all_daily.append(d)
    if all_daily:
        dg_=pd.concat(all_daily).groupby("Fecha").sum().reset_index()
        fig=go.Figure();fig.add_trace(go.Bar(x=dg_["Fecha"],y=dg_["Ords"],name="Órdenes",marker_color=C["blue"],opacity=.6,yaxis="y2"));fig.add_trace(go.Scatter(x=dg_["Fecha"],y=dg_["Fac"],name="Facturación",line=dict(color=C["profit"],width=2.5),fill="tozeroy",fillcolor="rgba(16,185,129,0.08)"))
        fig.update_layout(**pl(title="FACTURACIÓN Y ÓRDENES (COP)",yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)")));st.plotly_chart(fig,use_container_width=True,key="gl_fac")
    st.divider()
    for pn,cd in CD.items():
        k=cd["kpis"];pi=PAISES[pn];uc="green" if k["u_real"]>=0 else "red"
        cn_=f'<span style="font-size:.65rem;color:#475569">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if pi["moneda"]!="COP" else ""
        st.markdown(f'<div class="row2 r4" style="margin-bottom:.5rem"><div class="kcard"><div class="icon w">📦</div><div class="lbl">{pi["flag"]} {pn.upper()}</div><div class="val lg white">{k["n_ord"]:,}</div><div class="sub">{k["n_ent"]} ent · {k["tasa_ent"]:.0f}%</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">FACTURADO</div><div class="val lg green">{fmt(k["fact_neto"],pn)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val md red">{fmt(k["g_ads"],pn)}</div>{cn_}</div><div class="kcard {uc}"><div class="icon {"g" if k["u_real"]>=0 else "r"}">💰</div><div class="lbl">UTILIDAD</div><div class="val lg {uc}">{fmt(k["u_real"],pn)}</div></div></div>',unsafe_allow_html=True)
    st.divider()
    gk={f:sum(cd["kpis"][f] for cd in CD.values()) for f in ["n_ord","n_ent","n_can","n_tra","n_dev","n_nov","n_otr"]};gk["n_nc"]=gk["n_ord"]-gk["n_can"]
    st.markdown(render_logistics("Logística Global",gk,C),unsafe_allow_html=True)
    for pn,cd in CD.items():
        st.markdown(render_logistics(f"Logística {PAISES[pn]['flag']} {pn}",cd["kpis"],C),unsafe_allow_html=True)
        dc1,dc2,dc3,dc4=st.columns(4)
        with dc1: dl_logistics(cd["df_ord"],cd["F"],"Entregados",STATUS_ENT,f"dl_ent_{pn}")
        with dc2: dl_logistics(cd["df_ord"],cd["F"],"Cancelados",STATUS_CAN,f"dl_can_{pn}")
        with dc3: dl_logistics(cd["df_ord"],cd["F"],"Tránsito",STATUS_TRA,f"dl_tra_{pn}")
        with dc4: dl_logistics(cd["df_ord"],cd["F"],"Devolución",STATUS_DEV,f"dl_dev_{pn}")

# ═══ TAB: PROYECCIÓN GLOBAL ═══
with tabs[1]:
    st.markdown('<p class="section-hdr">Proyección Global (COP)</p>',unsafe_allow_html=True)
    gdg=st.slider("% Entrega",50,100,80,key="gdg");grb=st.number_input("Colchón",value=1.40,min_value=1.0,max_value=3.0,step=0.05,key="grb")
    gp_rows=[]
    for pn,cd in CD.items():
        gc=gcol_of(cd)
        if not gc: continue
        k=cd["kpis"];F=cd["F"];mon=PAISES[pn]["moneda"];ixo=k["fact_neto"]/k["n_desp"] if k["n_desp"]>0 else 0
        for prod in cd["df"][gc].dropna().unique():
            dp=cd["df"][cd["df"][gc]==prod];dpnc=dp[~dp["ESTATUS"].apply(lambda s:ms(s,STATUS_CAN))] if F.get("ESTATUS") else dp
            od=dpnc["ID"].nunique() if F.get("ID") else len(dpnc);uds=dp["CANTIDAD"].sum() if F.get("CANTIDAD") else 0
            pp=dp["PRECIO PROVEEDOR"].mean() if F.get("PRECIO PROVEEDOR") else 0;fp=dp["PRECIO FLETE"].mean() if F.get("PRECIO FLETE") else 0
            oe=od*gdg/100;odv=od-oe;ue=uds*gdg/100;cp=ue*pp;fl=oe*fp+odv*fp*grb
            ap_local=gxp_by_country.get(pn,{}).get(prod.upper(),0)
            ip=oe*ixo;ut=ip-cp-fl-ap_local
            gp_rows.append({"País":f"{PAISES[pn]['flag']} {pn}","Producto":prod,"Órdenes":int(od),"Ingreso_COP":to_cop(ip,mon,trm),"Utilidad_COP":to_cop(ut,mon,trm)})
    if gp_rows:
        dfgp=pd.DataFrame(gp_rows);ti=dfgp["Ingreso_COP"].sum();tu=dfgp["Utilidad_COP"].sum();to2=dfgp["Órdenes"].sum()
        st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{to2:,}</div></div><div class="kcard green"><div class="icon g">📊</div><div class="lbl">INGRESO</div><div class="val lg green">{fmt_cop(ti)}</div></div><div class="kcard {"green" if tu>=0 else "red"}"><div class="icon {"g" if tu>=0 else "r"}">📈</div><div class="lbl">UTILIDAD</div><div class="val lg {"green" if tu>=0 else "red"}">{fmt_cop(tu)}</div></div></div>',unsafe_allow_html=True)
        by_c=dfgp.groupby("País").agg({"Ingreso_COP":"sum","Utilidad_COP":"sum","Órdenes":"sum"}).reset_index()
        mx_=max(by_c["Ingreso_COP"].max(),1);bh=""
        for _,r in by_c.iterrows():
            bp=min(r["Ingreso_COP"]/mx_*100,100);utc=C["profit"] if r["Utilidad_COP"]>=0 else C["loss"]
            bh+=f'<div style="display:flex;align-items:center;padding:10px 0;border-bottom:1px solid #111827"><div style="width:160px;color:{C["text"]}">{r["País"]}</div><div style="flex:1;margin:0 12px"><div style="background:#111827;border-radius:3px;height:20px;overflow:hidden"><div style="width:{bp:.0f}%;height:100%;background:{C["profit"]};opacity:.4"></div></div></div><div style="width:120px;text-align:right;font-family:JetBrains Mono;font-size:.82rem;color:{C["text"]}">{fmt_cop(r["Ingreso_COP"])}</div><div style="width:120px;text-align:right;font-family:JetBrains Mono;font-size:.82rem;color:{utc}">{fmt_cop(r["Utilidad_COP"])}</div></div>'
        st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem">{bh}</div>',unsafe_allow_html=True)

# ═══ COUNTRY TABS ═══
for idx,(pn,cd) in enumerate(CD.items()):
    with tabs[idx+2]:
        k=cd["kpis"];df_ord=cd["df_ord"];df_f=cd["df"];F=cd["F"];pi=PAISES[pn];gc=gcol_of(cd);mon=PAISES[pn]["moneda"]
        prods=sorted(df_f[gc].dropna().unique()) if gc else []
        local_gxp=gxp_by_country.get(pn,{})
        ct1,ct2,ct3,ct4=st.tabs(["🌡 Termómetro","📊 Proyecciones","💰 Operación","📋 Órdenes"])

        with ct1:
            at=f'<span style="font-size:.65rem;color:#475569">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if mon!="COP" else ""
            rc="green" if k["roas"]>=2 else ("red" if k["roas"]<1 else "white");tc="green" if k["tasa_ent"]>=60 else ("red" if k["tasa_ent"]<40 else "white")
            st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">💰</div><div class="lbl">BRUTO</div><div class="val lg white">{fmt(k["fact_bruto"],pn)}</div><div class="sub">{k["n_ord"]:,} órdenes</div></div><div class="kcard green"><div class="icon g">📈</div><div class="lbl">NETO</div><div class="val lg green">{fmt(k["fact_neto"],pn)}</div></div><div class="kcard"><div class="icon w">🛒</div><div class="lbl">AOV</div><div class="val lg white">{fmt(k["aov"],pn)}</div></div></div><div class="row2 r3"><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val lg red">{fmt(k["g_ads"],pn)}</div>{at}</div><div class="kcard"><div class="icon g">⚡</div><div class="lbl">ROAS</div><div class="val lg {rc}">{k["roas"]:.2f}x</div></div><div class="kcard"><div class="icon g">✅</div><div class="lbl">ENTREGA</div><div class="val lg {tc}">{k["tasa_ent"]:.0f}%</div><div class="sub">{k["n_ent"]}/{k["n_nc"]}</div></div></div>',unsafe_allow_html=True)
            rp=min(k["roas"]/4*100,100)
            st.markdown(f'<div class="thermo"><div class="hd"><span class="tt">ROAS</span><span class="tv">{k["roas"]:.2f}x</span></div><div class="bar"><div class="mk" style="left:{rp:.0f}%"></div></div><div class="lb"><span>0x</span><span>2x</span><span>4x+</span></div></div>',unsafe_allow_html=True)
            if gc and F.get("FECHA"):
                pf=st.selectbox("Filtrar producto",["Todos"]+prods,key=f"pf_t_{pn}")
                df_ch=df_ord if pf=="Todos" else df_ord[df_ord[gc]==pf]
                daily=df_ch.groupby(df_ch["FECHA"].dt.date).agg(fac=("TOTAL DE LA ORDEN","sum"),ords=("ID","count")).reset_index();daily.columns=["Fecha","Fac","Ords"]
                gc1,gc2=st.columns(2)
                with gc1:
                    fig=go.Figure();fig.add_trace(go.Bar(x=daily["Fecha"],y=daily["Ords"],name="Órdenes",marker_color=C["blue"],opacity=.5,yaxis="y2"));fig.add_trace(go.Scatter(x=daily["Fecha"],y=daily["Fac"],name="Facturación",line=dict(color=C["profit"],width=2),fill="tozeroy",fillcolor="rgba(16,185,129,0.1)"))
                    fig.update_layout(**pl(title="FACTURACIÓN + ÓRDENES",yaxis2=dict(overlaying="y",side="right",gridcolor="rgba(0,0,0,0)")));st.plotly_chart(fig,use_container_width=True,key=f"fac_{pn}")
                with gc2:
                    if F.get("ESTATUS"):
                        edf=df_ch["ESTATUS"].value_counts().reset_index();edf.columns=["E","N"]
                        cm_={s:(C["profit"] if "ENTREGADO" in s else C["loss"] if "CANCELADO" in s else C["orange"] if "DEVOLUCION" in s else C["blue"] if ms(s,STATUS_TRA) else C["muted"]) for s in edf["E"]}
                        f3=px.pie(edf,names="E",values="N",hole=.55,color="E",color_discrete_map=cm_);f3.update_layout(**pl(showlegend=True,title="ESTADOS"));f3.update_traces(textinfo="percent")
                        st.plotly_chart(f3,use_container_width=True,key=f"pie_{pn}")
            st.markdown(render_logistics(f"Logística {pi['flag']} {pn}",k,C),unsafe_allow_html=True)
            dc1,dc2,dc3,dc4=st.columns(4)
            with dc1: dl_logistics(df_ord,F,"Entregados",STATUS_ENT,f"dl_e2_{pn}")
            with dc2: dl_logistics(df_ord,F,"Cancelados",STATUS_CAN,f"dl_c2_{pn}")
            with dc3: dl_logistics(df_ord,F,"Tránsito",STATUS_TRA,f"dl_t2_{pn}")
            with dc4: dl_logistics(df_ord,F,"Devolución",STATUS_DEV,f"dl_d2_{pn}")
            if gc:
                st.markdown('<p class="section-hdr">Resumen por Producto</p>',unsafe_allow_html=True)
                sb=st.selectbox("Ordenar",["Facturado","Pedidos","Ads","Entregados"],key=f"sb_{pn}")
                pr=[]
                for prod in prods:
                    dp=df_ord[df_ord[gc]==prod] if gc in df_ord.columns else pd.DataFrame()
                    if dp.empty: continue
                    np_=len(dp);fp_=dp["TOTAL DE LA ORDEN"].sum() if F.get("TOTAL DE LA ORDEN") else 0
                    ne_=len(dp[dp["ESTATUS"].apply(lambda s:ms(s,STATUS_ENT))]) if F.get("ESTATUS") else 0
                    nc_=len(dp[dp["ESTATUS"].apply(lambda s:ms(s,STATUS_CAN))]) if F.get("ESTATUS") else 0
                    nt_=len(dp[dp["ESTATUS"].apply(lambda s:ms(s,STATUS_TRA))]) if F.get("ESTATUS") else 0
                    nv_=len(dp[dp["ESTATUS"].apply(lambda s:ms(s,STATUS_DEV))]) if F.get("ESTATUS") else 0
                    nnc_=np_-nc_;ap_=local_gxp.get(prod.upper(),0)
                    pr.append({"Producto":prod,"Pedidos":np_,"Facturado":fp_,"Ent":ne_,"Can":nc_,"Tra":nt_,"Dev":nv_,"Ads":ap_,
                               "%Ent":f"{(ne_/nnc_*100):.0f}%" if nnc_ else "-","%Can":f"{(nc_/np_*100):.0f}%" if np_ else "-","%Tra":f"{(nt_/nnc_*100):.0f}%" if nnc_ else "-","%Dev":f"{(nv_/nnc_*100):.0f}%" if nnc_ else "-"})
                if pr:
                    dfpr=pd.DataFrame(pr);sc_={"Facturado":"Facturado","Pedidos":"Pedidos","Ads":"Ads","Entregados":"Ent"}[sb];dfpr=dfpr.sort_values(sc_,ascending=False)
                    h="<tr>"+"".join(f"<th>{c}</th>" for c in ["Producto","Ped","Facturado","Ent","%Ent","Can","%Can","Trá","%Trá","Dev","%Dev","Ads"])+"</tr>";rb=""
                    for _,r in dfpr.iterrows(): rb+=f'<tr><td style="font-weight:500">{r["Producto"]}</td><td>{r["Pedidos"]}</td><td class="mono">{fmt(r["Facturado"],pn)}</td><td style="color:{C["profit"]}">{r["Ent"]}</td><td style="color:{C["profit"]}">{r["%Ent"]}</td><td style="color:{C["loss"]}">{r["Can"]}</td><td style="color:{C["loss"]}">{r["%Can"]}</td><td style="color:{C["blue"]}">{r["Tra"]}</td><td style="color:{C["blue"]}">{r["%Tra"]}</td><td style="color:{C["warn"]}">{r["Dev"]}</td><td style="color:{C["warn"]}">{r["%Dev"]}</td><td style="color:{C["loss"]}" class="mono">{fmt(r["Ads"],pn)}</td></tr>'
                    st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead>{h}</thead><tbody>{rb}</tbody></table></div>',unsafe_allow_html=True)

        with ct2:
            if not gc: st.warning("Sin productos.")
            else:
                sc1,sc2=st.columns(2)
                with sc1: dg=st.slider("% Entrega",50,100,80,key=f"dg_{pn}")
                with sc2: rb_=st.number_input("Colchón",value=1.40,min_value=1.0,max_value=3.0,step=0.05,key=f"rb_{pn}")
                pek=f"pe_{pn}"
                if pek not in st.session_state: st.session_state[pek]={}
                prev_dg=st.session_state.get(f"pdg_{pn}",80)
                for p in prods:
                    if p not in st.session_state[pek]: st.session_state[pek][p]=float(dg)
                    elif st.session_state[pek][p]==prev_dg: st.session_state[pek][p]=float(dg)
                st.session_state[f"pdg_{pn}"]=dg
                pf2=st.selectbox("Filtrar",["Todos"]+prods,key=f"pf_p_{pn}");sb2=st.selectbox("Ordenar",["Utilidad","Ingreso","Órdenes"],key=f"sb_p_{pn}")
                ixo=k["fact_neto"]/k["n_desp"] if k["n_desp"]>0 else 0;prows=[]
                for prod in prods:
                    if pf2!="Todos" and prod!=pf2: continue
                    dp=df_f[df_f[gc]==prod];dpnc=dp[~dp["ESTATUS"].apply(lambda s:ms(s,STATUS_CAN))] if F.get("ESTATUS") else dp
                    uds=dp["CANTIDAD"].sum() if F.get("CANTIDAD") else 0;od=dpnc["ID"].nunique() if F.get("ID") else len(dpnc)
                    pp=dp["PRECIO PROVEEDOR"].mean() if F.get("PRECIO PROVEEDOR") else 0;fp=dp["PRECIO FLETE"].mean() if F.get("PRECIO FLETE") else 0
                    pe=st.session_state[pek].get(prod,float(dg));oe=od*pe/100;odv=od-oe;ue=uds*pe/100;cp=ue*pp;fl=oe*fp+odv*fp*rb_
                    ap_local=local_gxp.get(prod.upper(),0)
                    ip=oe*ixo;ut=ip-cp-fl-ap_local
                    prows.append({"Producto":prod,"Órdenes":int(od),"% Entrega":pe,"Ingreso":round(ip),"Costo":round(cp),"Fletes":round(fl),"Ads":round(ap_local),"Utilidad":round(ut)})
                dfp=pd.DataFrame(prows)
                if not dfp.empty:
                    sc__={"Utilidad":"Utilidad","Ingreso":"Ingreso","Órdenes":"Órdenes"}[sb2];dfp=dfp.sort_values(sc__,ascending=False)
                    ti=dfp["Ingreso"].sum();tu=dfp["Utilidad"].sum()
                    st.markdown(f'<div class="row2 r3"><div class="kcard"><div class="icon w">📦</div><div class="lbl">ÓRDENES</div><div class="val lg white">{dfp["Órdenes"].sum():,}</div></div><div class="kcard green"><div class="icon g">📊</div><div class="lbl">INGRESO</div><div class="val lg green">{fmt(ti,pn)}</div></div><div class="kcard {"green" if tu>=0 else "red"}"><div class="icon {"g" if tu>=0 else "r"}">📈</div><div class="lbl">UTILIDAD</div><div class="val lg {"green" if tu>=0 else "red"}">{fmt(tu,pn)}</div></div></div>',unsafe_allow_html=True)
                    mx_p=max(dfp["Ingreso"].max(),1);bh=""
                    for _,r in dfp.iterrows():
                        ipp=min(r["Ingreso"]/mx_p*100,100);utp=min(max(r["Utilidad"],0)/mx_p*100,100);utc=C["profit"] if r["Utilidad"]>=0 else C["loss"]
                        bh+=f'<div style="margin-bottom:1.2rem"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="color:{C["text"]};font-weight:600">{r["Producto"]}</span><span style="color:{C["sub"]};font-size:.78rem">{int(r["Órdenes"])} · {int(r["% Entrega"])}%</span></div><div style="display:flex;gap:8px;align-items:center"><div style="flex:1;background:#111827;border-radius:4px;height:22px;position:relative;overflow:hidden"><div style="width:{ipp:.0f}%;height:100%;background:rgba(16,185,129,0.2);border-radius:4px"></div><div style="position:absolute;top:0;left:0;width:{utp:.0f}%;height:100%;background:{C["profit"]};border-radius:4px;opacity:.7"></div></div><span style="font-family:JetBrains Mono;font-size:.82rem;color:{utc};width:130px;text-align:right;font-weight:600">{fmt(r["Utilidad"],pn)}</span></div><div style="display:flex;gap:14px;margin-top:3px;font-size:.7rem;color:{C["sub"]}"><span>Ing:{fmt(r["Ingreso"],pn)}</span><span>Cst:-{fmt(r["Costo"],pn)}</span><span>Flt:-{fmt(r["Fletes"],pn)}</span><span>Ads:-{fmt(r["Ads"],pn)}</span></div></div>'
                    st.markdown(f'<div class="kcard" style="padding:1.5rem">{bh}</div>',unsafe_allow_html=True)
                    with st.expander("📝 Editar %"):
                        ed=st.data_editor(dfp,column_config={"% Entrega":st.column_config.NumberColumn("%",min_value=0,max_value=100,step=1,format="%d")},disabled=[c for c in dfp.columns if c!="% Entrega"],use_container_width=True,hide_index=True,key=f"pt_{pn}")
                        if ed is not None:
                            for _,r in ed.iterrows(): st.session_state[pek][r["Producto"]]=r["% Entrega"]

        with ct3:
            ir=k["ing_real"];cpr=k["cpr"];fe=k["fl_ent"];ga=k["g_ads"];fd=k["fl_dev"];ft_=k["fl_tra"];ur=k["u_real"]
            mg=(ur/ir*100) if ir>0 else 0;uc="green" if ur>=0 else "red"
            at2=f'<span style="font-size:.65rem;color:#475569">({fmt_cop(k.get("g_ads_cop",0))} COP)</span>' if mon!="COP" else ""
            st.markdown(f'<div class="kcard {uc}" style="padding:2rem;margin-bottom:1.5rem"><div class="icon {"g" if ur>=0 else "r"}" style="width:48px;height:48px;font-size:1.3rem">💰</div><div class="lbl">UTILIDAD REAL</div><div class="val xl {uc}">{fmt(ur,pn)}</div><div class="pct">Margen: {mg:.1f}%</div></div><div class="row2 r3"><div class="kcard green"><div class="icon g">✅</div><div class="lbl">INGRESO ENT.</div><div class="val md green">{fmt(ir,pn)}</div><div class="pct">100%</div></div><div class="kcard red"><div class="icon r">📦</div><div class="lbl">COSTO PROD.</div><div class="val md red">-{fmt(cpr,pn)}</div><div class="pct">{pof(cpr,ir)}</div></div><div class="kcard red"><div class="icon r">🚚</div><div class="lbl">FLETES ENT.</div><div class="val md red">-{fmt(fe,pn)}</div><div class="pct">{pof(fe,ir)}</div></div></div><div class="row2 r3"><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">ADS</div><div class="val md red">-{fmt(ga,pn)}</div>{at2}<div class="pct">{pof(ga,ir)}</div></div><div class="kcard red"><div class="icon r">⚠️</div><div class="lbl">FLETES DEV.</div><div class="val md red">-{fmt(fd,pn)}</div><div class="pct">{pof(fd,ir)}</div></div><div class="kcard"><div class="icon b">🚚</div><div class="lbl">FLETES TRÁ.</div><div class="val md white">-{fmt(ft_,pn)}</div><div class="pct">{pof(ft_,ir)}</div></div></div>',unsafe_allow_html=True)
            st.markdown('<p class="section-hdr">Cascada Financiera</p>',unsafe_allow_html=True)
            cpf=st.selectbox("Producto",["Todos"]+prods,key=f"cpf_{pn}") if gc else "Todos"
            if cpf!="Todos" and gc:
                dp_c=df_ord[df_ord[gc]==cpf];de_c=dp_c[dp_c["ESTATUS"].apply(lambda s:ms(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
                ir=de_c["TOTAL DE LA ORDEN"].sum() if not de_c.empty else 0
                cpr=de_c["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de_c.empty and "PRECIO PROVEEDOR X CANTIDAD" in de_c.columns) else 0
                fe=de_c["PRECIO FLETE"].sum() if (not de_c.empty and F.get("PRECIO FLETE")) else 0
                ga=local_gxp.get(cpf.upper(),0)
                dd_c=dp_c[dp_c["ESTATUS"].apply(lambda s:ms(s,STATUS_DEV))] if F.get("ESTATUS") else pd.DataFrame()
                fd=dd_c["PRECIO FLETE"].sum() if not dd_c.empty else 0
                dt_c=dp_c[dp_c["ESTATUS"].apply(lambda s:ms(s,STATUS_TRA))] if F.get("ESTATUS") else pd.DataFrame()
                ft_=dt_c["PRECIO FLETE"].sum() if not dt_c.empty else 0;ur=ir-cpr-fe-ga-fd-ft_
            items=[("Ingreso Ent.",ir,True),("Costo Prod.",cpr,False),("Fletes Ent.",fe,False),("Ads",ga,False),("Fletes Dev.",fd,False),("Fletes Trá.",ft_,False)]
            mx_c=max(ir,1);ch=""
            for lb,vl,pos in items:
                bp=min(vl/mx_c*100,100);bc=C["profit"] if pos else C["loss"];sg="" if pos else "-"
                ch+=f'<div class="cas-row"><div class="cas-lbl">{lb}</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{bp:.0f}%;background:{bc}"></div></div><div class="cas-amt" style="color:{bc}">{sg}{fmt(vl,pn)}</div><div class="cas-pct">{pof(vl,ir)}</div></div>'
            up=min(abs(ur)/mx_c*100,100);ucol=C["profit"] if ur>=0 else C["loss"];us="" if ur>=0 else "-"
            st.markdown(f'<div class="kcard" style="padding:1rem 1.5rem">{ch}<div style="border-top:2px solid #1E293B;margin:8px 0"></div><div class="cas-row" style="border-bottom:none"><div class="cas-lbl" style="font-weight:700;color:#F1F5F9">UTILIDAD</div><div class="cas-bar-wrap"><div class="cas-bar" style="width:{up:.0f}%;background:{ucol}"></div></div><div class="cas-amt" style="color:{ucol}">{us}{fmt(abs(ur),pn)}</div><div class="cas-pct" style="color:{ucol}">{pof(abs(ur),k["ing_real"])}</div></div></div>',unsafe_allow_html=True)
            if gc and gc in df_ord.columns:
                st.markdown('<p class="section-hdr">P&L por Producto</p>',unsafe_allow_html=True)
                pnl=[]
                for prod in prods:
                    dp=df_ord[df_ord[gc]==prod];de_p=dp[dp["ESTATUS"].apply(lambda s:ms(s,STATUS_ENT))] if F.get("ESTATUS") else pd.DataFrame()
                    ir_p=de_p["TOTAL DE LA ORDEN"].sum() if not de_p.empty else 0
                    cp_p=de_p["PRECIO PROVEEDOR X CANTIDAD"].sum() if (not de_p.empty and "PRECIO PROVEEDOR X CANTIDAD" in de_p.columns) else 0
                    fe_p=de_p["PRECIO FLETE"].sum() if (not de_p.empty and F.get("PRECIO FLETE")) else 0
                    ap_p=local_gxp.get(prod.upper(),0);ut_p=ir_p-cp_p-fe_p-ap_p
                    pnl.append({"Producto":prod,"Ingreso":ir_p,"Costo":cp_p,"Fletes":fe_p,"Ads":ap_p,"Utilidad":ut_p})
                if pnl:
                    dp_=pd.DataFrame(pnl).sort_values("Ingreso",ascending=False)
                    h2="<tr>"+"".join(f"<th>{c}</th>" for c in ["Producto","Ingreso","Costo","Fletes","Ads","Utilidad","Margen"])+"</tr>";rb2=""
                    for _,r in dp_.iterrows():
                        utc=C["profit"] if r["Utilidad"]>=0 else C["loss"];mg2=pof(r["Utilidad"],r["Ingreso"])
                        rb2+=f'<tr><td>{r["Producto"]}</td><td class="mono">{fmt(r["Ingreso"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Costo"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Fletes"],pn)}</td><td class="mono" style="color:{C["loss"]}">-{fmt(r["Ads"],pn)}</td><td class="mono" style="color:{utc}">{fmt(r["Utilidad"],pn)}</td><td style="color:{utc}">{mg2}</td></tr>'
                    st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead>{h2}</thead><tbody>{rb2}</tbody></table></div>',unsafe_allow_html=True)

        with ct4:
            st.markdown(f'<p class="section-hdr">Órdenes — {len(df_ord):,}</p>',unsafe_allow_html=True)
            cols=[c for c in ["ID","FECHA","PRODUCTO","CANTIDAD","TOTAL DE LA ORDEN","PRECIO FLETE","CIUDAD DESTINO","ESTATUS"] if c in df_ord.columns]
            if cols:
                dfo=df_ord[cols].copy()
                if "FECHA" in dfo.columns: dfo=dfo.sort_values("FECHA",ascending=False)
                nr=len(dfo);hm={"ID":"ID","FECHA":"FECHA","PRODUCTO":"PRODUCTO","CANTIDAD":"CANT.","TOTAL DE LA ORDEN":"TOTAL","PRECIO FLETE":"FLETE","CIUDAD DESTINO":"CIUDAD","ESTATUS":"ESTADO"}
                hd="".join(f"<th>{hm.get(c,c)}</th>" for c in cols);ps=50;opk=f"op_{pn}"
                if opk not in st.session_state: st.session_state[opk]=0
                tp=max(1,(nr-1)//ps+1);s=st.session_state[opk]*ps;e=min(s+ps,nr);rh=""
                for _,row in dfo.iloc[s:e].iterrows():
                    td=""
                    for c in cols:
                        v=row[c]
                        if c=="ID": td+=f'<td style="color:#64748B;font-family:JetBrains Mono;font-size:.78rem">{v}</td>'
                        elif c=="FECHA": td+=f'<td>{v.strftime("%d %b %Y") if pd.notna(v) else "-"}</td>'
                        elif c in ("TOTAL DE LA ORDEN","PRECIO FLETE"): td+=f'<td class="mono">{fmt(v,pn)}</td>'
                        elif c=="CANTIDAD": td+=f'<td style="text-align:center">{int(v)}</td>'
                        elif c=="ESTATUS": td+=f'<td>{status_pill(str(v))}</td>'
                        elif c=="CIUDAD DESTINO": td+=f'<td>{str(v).title() if pd.notna(v) else "-"}</td>'
                        else: td+=f'<td>{v}</td>'
                    rh+=f"<tr>{td}</tr>"
                st.markdown(f'<div class="kcard" style="padding:0;overflow-x:auto"><table class="otbl"><thead><tr>{hd}</tr></thead><tbody>{rh}</tbody></table></div>',unsafe_allow_html=True)
                c1,c2,c3=st.columns([1,2,1])
                with c1:
                    if st.button("←",disabled=st.session_state[opk]==0,key=f"pv_{pn}"): st.session_state[opk]-=1;st.rerun()
                with c2: st.markdown(f'<p style="text-align:center;color:#64748B">{st.session_state[opk]+1}/{tp}</p>',unsafe_allow_html=True)
                with c3:
                    if st.button("→",disabled=st.session_state[opk]>=tp-1,key=f"nx_{pn}"): st.session_state[opk]+=1;st.rerun()
                st.download_button("📥 Todas las órdenes",to_excel(df_ord),file_name=f"ordenes_{pn.lower()}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key=f"dl_all_{pn}")

# ═══ PUBLICIDAD ═══
with tabs[-1]:
    st.markdown('<p class="section-hdr">Publicidad</p>',unsafe_allow_html=True)
    tfc=sum(cd["kpis"].get("g_fb_cop",0) for cd in CD.values());ttc=sum(cd["kpis"].get("g_tt_cop",0) for cd in CD.values());tac=tfc+ttc
    top_=sum(cd["kpis"]["n_ord"] for cd in CD.values());tep=sum(cd["kpis"]["n_ent"] for cd in CD.values())
    cpo=tac/top_ if top_>0 else 0;cpe=tac/tep if tep>0 else 0
    st.markdown(f'<div class="row2 r4"><div class="kcard purple"><div class="icon p">📢</div><div class="lbl">TOTAL</div><div class="val lg purple">{fmt_cop(tac)}</div></div><div class="kcard blue"><div class="icon b">📘</div><div class="lbl">FB</div><div class="val lg blue">{fmt_cop(tfc)}</div></div><div class="kcard"><div class="icon w">🎵</div><div class="lbl">TT</div><div class="val lg white">{fmt_cop(ttc)}</div></div><div class="kcard red"><div class="icon r">🎯</div><div class="lbl">CPA</div><div class="val lg red">{fmt_cop(cpo)}</div><div class="sub">Ent: {fmt_cop(cpe)}</div></div></div>',unsafe_allow_html=True)
    if gxp:
        pa=pd.DataFrame([{"Producto":k,"Gasto COP":v} for k,v in sorted(gxp.items(),key=lambda x:-x[1])])
        fp_=px.bar(pa,x="Producto",y="Gasto COP",color_discrete_sequence=[C["purple"]]);fp_.update_layout(**pl(title="GASTO POR PRODUCTO (COP)"))
        st.plotly_chart(fp_,use_container_width=True,key="ap")
    else: st.info("Mapea campañas → productos.")

st.divider()
st.markdown(f'<div style="text-align:center;color:#475569;font-size:.75rem">Dashboard v5.2 · {sum(1 for p in PAISES if st.session_state.get(f"_b_{p}"))} países · {f_ini.strftime("%d/%m")} – {f_fin.strftime("%d/%m/%Y")}</div>',unsafe_allow_html=True)
