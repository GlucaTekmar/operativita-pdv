import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os

st.set_page_config(layout="wide")

# ---------- STILE ----------
st.markdown("""
<style>
body {background-color:#E30613;}
.block-container {padding-top:1rem;}
h1, h2, h3, h4, h5, h6, p, label {color:white;}
</style>
""", unsafe_allow_html=True)

# ---------- LOGO ----------


st.image("logo.png", use_container_width=False, width=320)

# ---------- GOOGLE SHEETS CONNECTION ----------
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_NAME = "11o5dTHZBaeWS0N2crJyGqNbOsIPnLWzIu9q9snYw9hI"

sheet = client.open_by_key(SPREADSHEET_NAME)

anagrafica_ws = sheet.worksheet("ANAGRAFICA")
messaggi_ws = sheet.worksheet("MESSAGGI")
conferme_ws = sheet.worksheet("CONFERME")

anagrafica = pd.DataFrame(anagrafica_ws.get_all_records())
messaggi = pd.DataFrame(messaggi_ws.get_all_records())

oggi = datetime.now().date()

# =========================================================
# 🔒 MODALITÀ ADMIN NASCOSTA
# =========================================================

query = st.query_params

admin_mode = False
if "admin" in query and query["admin"] == "1":
    admin_mode = True

# =========================================================
# 🔵 AREA DIPENDENTI
# =========================================================

if not admin_mode:

    st.markdown("## SELEZIONA IL TUO PDV")
    
    anagrafica["Display"] = (
        anagrafica["Codice"].astype(str)
        + " - "
        + anagrafica["Insegna"]
        + " ("
        + anagrafica["Città"]
        + ")"
    )

    pdv = st.selectbox(
        "",
        anagrafica["Display"]
    )

    st.markdown(
        "<p style='font-size:14px'><b>Digita le prime lettere della città per trovare il tuo PDV</b></p>",
        unsafe_allow_html=True
    )

    codice_pdv = pdv.split(" - ")[0]

    messaggi_attivi = messaggi[
        (messaggi["ID"].astype(str) == codice_pdv)
    ]

    # =====================================================
    # SE ESISTE INDICAZIONE OPERATIVA
    # =====================================================

    if not messaggi_attivi.empty:

        msg = messaggi_attivi.iloc[0]

        st.markdown(f"""
        <div style='background:white;color:black;padding:20px;border-radius:10px'>
        <h3>{msg['Titolo']}</h3>
        <p>{msg['Testo']}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### Conferma di Lettura e di Presenza sul PDV")

        lettura = st.checkbox("fleg CONFERMA DI LETTURA INDICAZIONE")
        presenza = st.checkbox("fleg - CONFERMA DI PRESENZA SUL PDV")

        if lettura and presenza:
            conferme_ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                codice_pdv,
                msg["Titolo"]
            ])
            st.success("Lettura registrata con successo!")

    # =====================================================
    # SE NON ESISTE INDICAZIONE
    # =====================================================

    else:

        st.markdown("""
        <div style='background:white;color:black;padding:20px;border-radius:10px'>
        <b>PER QUESTO PDV QUESTA MATTINA NON SONO PREVISTE PROMO E/O ATTIVITÀ PARTICOLARI RISPETTO AL SOLITO. BUON LAVORO</b>
        </div>
        """, unsafe_allow_html=True)

        presenza = st.checkbox("fleg CONFERMA DI PRESENZA SUL PDV")

        if presenza:
            conferme_ws.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                codice_pdv,
                "NESSUNA INDICAZIONE"
            ])
            st.success("Presenza registrata!")

# =========================================================
# 🟣 AREA AMMINISTRATORE NASCOSTA
# =========================================================

else:

    st.markdown("# 🔒 DASHBOARD AMMINISTRATORE")

    admin_pass = st.text_input("Password amministratore", type="password")

    if admin_pass == "GianAri2026":

        st.success("Accesso consentito")

        st.subheader("Nuova indicazione operativa")

        titolo = st.text_input("Titolo")
        testo = st.text_area("Testo")
        codici = st.text_area(
            "Incolla Codici PDV (uno per riga o separati da virgola)"
        )

        if st.button("PUBBLICA INDICAZIONE"):

            lista = [
                c.strip()
                for c in codici.replace(",", "\n").split("\n")
                if c.strip()
            ]

            for codice in lista:
                messaggi_ws.append_row([
                    codice,
                    titolo,
                    testo,
                    oggi.strftime("%Y-%m-%d"),
                    oggi.strftime("%Y-%m-%d"),
                    "PDV"
                ])

            st.success("Indicazione pubblicata con successo!")

    else:
        st.warning("Inserire password valida")


















