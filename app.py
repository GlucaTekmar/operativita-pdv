# =========================================================
# OPERATIVITA PDV — VERSIONE PROFESSIONALE DEFINITIVA
# =========================================================

import os, json, base64
from datetime import datetime
import pandas as pd
import streamlit as st
SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image
from streamlit_quill import st_quill

# ---------------- CONFIG ----------------

JOTFORM_HOME_URL = "https://eu.jotform.com/it/app/build/253605296903360"

TAB_ANAGRAFICA = "ANAGRAFICA"
TAB_MESSAGGI = "MESSAGGI"
TAB_CONFERME = "CONFERME"

A_CODICE = "Codice"
A_INSEGNA = "Insegna"
A_CITTA = "Città"

M_ID = "ID"
M_TITOLO = "Titolo"
M_TESTO = "Testo"
M_INIZIO = "Inizio"
M_FINE = "Fine"
M_TARGET = "Target"

# ---------------- UI ----------------

st.set_page_config("Operatività PDV", layout="centered")

st.markdown("""
<style>
.stApp { background:#E30613; }
h1,h2,h3,p,label { color:white !important; }
.card { background:white; color:black; padding:18px; border-radius:14px; margin:14px 0; }
</style>
""", unsafe_allow_html=True)

try:
    st.image(Image.open("logo.png"), width=260)
except:
    pass

# ---------------- SECRETS ----------------

def S(k):
    try: return st.secrets[k]
    except: return os.getenv(k)

ADMIN_KEY = (S("ADMIN_KEY") or "").strip()
ADMIN_PASSWORD = (S("ADMIN_PASSWORD") or "").strip()
SPREADSHEET_ID = S("SPREADSHEET_ID")

def SA():
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])
    return json.loads(os.getenv("GCP_SERVICE_ACCOUNT_JSON"))

# ---------------- GOOGLE ----------------

@st.cache_resource
def GS():
    creds = Credentials.from_service_account_info(
        SA(),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)

@st.cache_resource
def SH():
    return GS().open_by_key(SPREADSHEET_ID)

def WS(name):
    return SH().worksheet(name)

def DF(ws):
    d = ws.get_all_records()
    return pd.DataFrame(d) if d else pd.DataFrame()

# ---------------- ROUTING ADMIN ----------------

params = st.query_params
ADMIN_MODE = (
    str(params.get("admin","")).strip()=="1"
    and str(params.get("key","")).strip()==ADMIN_KEY
)

# =========================================================
# AREA DIPENDENTI
# =========================================================

def dipendenti_view():

    st.header("INDICAZIONI DI GIORNATA")

    anag = DF(WS(TAB_ANAGRAFICA))
    anag["Display"] = (
        anag[A_CODICE].astype(str)
        + " - "
        + anag[A_INSEGNA]
        + " ("
        + anag[A_CITTA]
        + ")"
    )

    scelta = st.selectbox("CERCA IL TUO PDV", anag["Display"])
    codice = scelta.split(" - ")[0]

    msg = DF(WS(TAB_MESSAGGI))
    oggi = datetime.now().date()

    attivi = []

    for _, r in msg.iterrows():
        ini = pd.to_datetime(r[M_INIZIO]).date() if r[M_INIZIO] else oggi
        fin = pd.to_datetime(r[M_FINE]).date() if r[M_FINE] else oggi
        targets = str(r[M_TARGET]).split(",") if r[M_TARGET] else []

        if ini <= oggi <= fin and (codice in targets or not targets):
            attivi.append(r)

    # ----- NESSUNA INDICAZIONE -----

    if not attivi:

        st.markdown("""
        <div class="card">
        QUESTA MATTINA SU QUESTO PUNTO VENDITA NON SONO PREVISTE PROMO E/O ATTIVITÀ PARTICOLARI.
        BUON LAVORO.
        </div>
        """, unsafe_allow_html=True)

        presenza = st.checkbox("CONFERMA PRESENZA SUL PDV")

        if st.button("INVIA CONFERMA"):
            if presenza:
                WS(TAB_CONFERME).append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    codice,
                    "NESSUNA INDICAZIONE | PRESENZA"
                ])
                st.success("Presenza registrata")
            else:
                st.error("Spunta la casella")

        st.link_button("HOME", JOTFORM_HOME_URL)
        return

    # ----- CON INDICAZIONI -----

    for r in attivi:

        st.markdown(
            f'<div class="card"><b>{r[M_TITOLO]}</b><br>{r[M_TESTO]}</div>',
            unsafe_allow_html=True
        )

        lettura = st.checkbox("CONFERMA LETTURA")
        presenza = st.checkbox("CONFERMA PRESENZA")

        if st.button("INVIA CONFERMA", key=r[M_ID]):
            if lettura and presenza:
                WS(TAB_CONFERME).append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    codice,
                    r[M_TITOLO]
                ])
                st.success("Conferma registrata")
            else:
                st.error("Devi spuntare entrambe")

    st.link_button("HOME", JOTFORM_HOME_URL)

# =========================================================
# AREA ADMIN — PROFESSIONALE
# =========================================================

def admin_view():

    st.title("DASHBOARD AMMINISTRATORE")

    pw = st.text_input("Password", type="password")
    if pw != ADMIN_PASSWORD:
        st.stop()

    t1, t2, t3 = st.tabs([
        "ANAGRAFICA",
        "NUOVA INDICAZIONE",
        "REPORT CONFERME"
    ])

    # --- ANAGRAFICA ---
    with t1:
        file = st.file_uploader("Carica Excel", type="xlsx")
        if file:
            df_new = pd.read_excel(file)
            WS(TAB_ANAGRAFICA).clear()
            WS(TAB_ANAGRAFICA).update(
                [df_new.columns.values.tolist()] + df_new.values.tolist()
            )
            st.success("Anagrafica aggiornata")

    # --- NUOVA INDICAZIONE CON EDITOR ---
    with t2:

        titolo = st.text_input("Titolo")

        st.write("Testo formattato:")
        testo_html = st_quill()

        ini = st.date_input("Inizio")
        fin = st.date_input("Fine")
        target = st.text_input("Codici PDV (virgole)")

        img = st.file_uploader("Immagine", type=["jpg","jpeg","png","gif"])
        pdf = st.file_uploader("PDF", type=["pdf"])

        extra_html = ""

        if img:
            b64 = base64.b64encode(img.read()).decode()
            extra_html += f'<img src="data:image;base64,{b64}" width="100%"><br>'

        if pdf:
            b64 = base64.b64encode(pdf.read()).decode()
            extra_html += f'<a href="data:application/pdf;base64,{b64}" target="_blank">Apri PDF</a>'

        if st.button("PUBBLICA"):
            WS(TAB_MESSAGGI).append_row([
                "",
                titolo,
                testo_html + extra_html,
                ini.strftime("%Y-%m-%d"),
                fin.strftime("%Y-%m-%d"),
                target
            ])
            st.success("Indicazione pubblicata")

    # --- REPORT ---
    with t3:
        st.dataframe(DF(WS(TAB_CONFERME)))

# =========================================================
# MAIN
# =========================================================

if ADMIN_MODE:
    admin_view()
else:
    dipendenti_view()


