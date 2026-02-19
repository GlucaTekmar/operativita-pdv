# =========================
# WEB-APP OPERATIVITA PDV
# VERSIONE DEFINITIVA — MONO CLIENTE
# Compatibile Streamlit + Render
# =========================

import streamlit as st
import pandas as pd
import datetime as dt
import json
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image

# =========================
# CONFIG PAGINA
# =========================

st.set_page_config(
    page_title="Operatività PDV",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================
# GRAFICA — SFONDO ROSSO
# =========================

st.markdown("""
<style>
.stApp { background-color: #c40018; color: white; }
h1, h2, h3, h4, h5, h6, p, label { color: white !important; }
div[data-baseweb="select"] > div { background: black !important; color: white !important; }
.stTextInput > div > div > input { background: black; color: white; }
.stTextArea textarea { background: black; color: white; }
.stDateInput input { background: black; color: white; }
.stButton button { background-color: black; color: white; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =========================
# LOGO CENTRATO
# =========================

col1, col2, col3 = st.columns([1,2,1])
with col2:
    logo = Image.open("logo.png")
    st.image(logo, use_column_width=True)

# =========================
# CONNESSIONE GOOGLE SHEETS
# =========================

def connect_gsheet():

    creds_dict = dict(st.secrets)

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)

    sheet = client.open("OPERATIVITA")

    return sheet

# =========================
# PARAMETRI ACCESSO
# =========================

params = st.query_params
is_admin = params.get("admin") == "1"
key_ok = params.get("key") == st.secrets["ADMIN_KEY"]

sheet = connect_gsheet()

# =========================
# =========================
# 🔐 AREA ADMIN
# =========================
# =========================

if is_admin and key_ok:

    st.title("🔐 DASHBOARD AMMINISTRATORE")

    password = st.text_input("Password", type="password")

    if password == st.secrets["ADMIN_PASSWORD"]:

        # -------------------------
        # CARICA LISTA PDV
        # -------------------------

        st.subheader("📥 Carica lista PDV (Excel)")

        file = st.file_uploader("Carica file Excel", type=["xlsx"])

        if file:

            df = pd.read_excel(file)

            anagrafica_ws = sheet.worksheet("ANAGRAFICA")
            anagrafica_ws.clear()
            anagrafica_ws.update([df.columns.values.tolist()] + df.values.tolist())

            st.success("Lista PDV aggiornata")

        # -------------------------
        # INSERIMENTO INDICAZIONE
        # -------------------------

        st.subheader("📝 Nuova indicazione operativa")

        titolo = st.text_input("Titolo")
        testo = st.text_area("Testo (puoi incollare anche link)")
        data_inizio = st.date_input("Data inizio")
        data_fine = st.date_input("Data fine")

        anagrafica_df = pd.DataFrame(sheet.worksheet("ANAGRAFICA").get_all_records())

        pdv_list = anagrafica_df["Città"].tolist()

        target = st.multiselect("PDV destinatari", pdv_list)

        if st.button("INVIA INDICAZIONE"):

            msg_ws = sheet.worksheet("MESSAGGI")

            new_row = [
                titolo,
                testo,
                str(data_inizio),
                str(data_fine),
                "|".join(target)
            ]

            msg_ws.append_row(new_row)

            st.success("Indicazione salvata")

        # -------------------------
        # LOG CONFERME
        # -------------------------

        st.subheader("📊 Log conferme")

        conf_ws = sheet.worksheet("CONFERME")
        conf_df = pd.DataFrame(conf_ws.get_all_records())

        st.dataframe(conf_df, use_container_width=True)

    else:
        st.warning("Inserire password corretta")

# =========================
# =========================
# 👤 AREA DIPENDENTI
# =========================
# =========================

else:

    st.markdown("## INDICAZIONI DI GIORNATA")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## CERCA IL TUO PDV:")

    anagrafica_df = pd.DataFrame(sheet.worksheet("ANAGRAFICA").get_all_records())

    pdv_list = anagrafica_df["Città"].tolist()

    pdv = st.selectbox("Seleziona il tuo PDV", pdv_list)

    oggi = dt.date.today()

    msg_df = pd.DataFrame(sheet.worksheet("MESSAGGI").get_all_records())

    visibili = []

    for _, r in msg_df.iterrows():

        inizio = dt.date.fromisoformat(r["Inizio"])
        fine = dt.date.fromisoformat(r["Fine"])

        targets = r["Target"].split("|")

        if inizio <= oggi <= fine and pdv in targets:
            visibili.append(r)

    if visibili:

        for m in visibili:

            st.markdown(f"### {m['Titolo']}")
            st.markdown(m["Testo"])

            if st.button(f"Conferma lettura — {m['Titolo']}"):

                conf_ws = sheet.worksheet("CONFERME")

                conf_ws.append_row([
                    dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    pdv,
                    m["Titolo"]
                ])

                st.success("Conferma registrata")

    else:

        st.info("Oggi su questo Punto Vendita NON sono previste Promo/Attività particolari. Buon lavoro")

