import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================

st.set_page_config(page_title="Operatività PDV", layout="centered")

JOTFORM_HOME = "https://eu.jotform.com/it/app/build/253605296903360"
ADMIN_PASSWORD = "GianAri2026"

SPREADSHEET_ID = "11o5dTHZBaeWS0N2crJyGqNbOsIPnLWzIu9q9snYw9hI"

# =========================================================
# STILE
# =========================================================

st.markdown("""
<style>
.stApp { background-color: #E30613; }

.block-container { padding-top: 4rem; }

h1, h2, h3, h4, h5, h6, p, label, div {
    color: white !important;
}

.box-bianco {
    background: white;
    color: black !important;
    padding: 20px;
    border-radius: 10px;
    margin-top: 20px;
}

.box-bianco * { color: black !important; }

.small-note {
    font-size: 14px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# LOGO
# =========================================================

st.image("logo.png", width=260)

# =========================================================
# GOOGLE SHEETS
# =========================================================

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID)

anagrafica_ws = sheet.worksheet("ANAGRAFICA")
messaggi_ws = sheet.worksheet("MESSAGGI")
conferme_ws = sheet.worksheet("CONFERME")

anagrafica = pd.DataFrame(anagrafica_ws.get_all_records())
messaggi = pd.DataFrame(messaggi_ws.get_all_records())

oggi = datetime.now().date()

# =========================================================
# MODALITÀ ADMIN
# =========================================================

params = st.query_params
admin_mode = params.get("admin") == "1"

# =========================================================
# AREA DIPENDENTI
# =========================================================

if not admin_mode:

    st.markdown("## INDICAZIONI DI GIORNATA")
    st.markdown("## SELEZIONA IL TUO PDV")

    if not anagrafica.empty:

        anagrafica["Display"] = (
            anagrafica["Codice"].astype(str)
            + " - "
            + anagrafica["Insegna"]
            + " ("
            + anagrafica["Città"]
            + ")"
        )

        lista = [""] + anagrafica["Display"].tolist()

        pdv = st.selectbox("", lista, index=0)

        st.markdown(
            "<p class='small-note'>Digita le prime lettere della città per trovare il tuo PDV</p>",
            unsafe_allow_html=True
        )

        if pdv != "":

            codice_pdv = pdv.split(" - ")[0]

            messaggi_attivi = messaggi[
                (messaggi["ID"].astype(str) == codice_pdv)
            ]

            # -------------------------------------------------
            # CON INDICAZIONE
            # -------------------------------------------------

            if not messaggi_attivi.empty:

                msg = messaggi_attivi.iloc[0]

                st.markdown(f"""
                <div class="box-bianco">
                <h3>{msg['Titolo']}</h3>
                <p>{msg['Testo']}</p>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("### Conferma di Lettura e di Presenza sul PDV")

                lettura = st.checkbox(
                    "da fleggare - CONFERMA DI LETTURA INDICAZIONE"
                )
                presenza = st.checkbox(
                    "da fleggare - CONFERMA DI PRESENZA SUL PDV"
                )

                if lettura and presenza:
                    conferme_ws.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        codice_pdv,
                        msg["Titolo"]
                    ])
                    st.success("Conferma registrata")

            # -------------------------------------------------
            # SENZA INDICAZIONE
            # -------------------------------------------------

            else:

                st.markdown("""
                <div class="box-bianco">
                <b>PER QUESTO PDV QUESTA MATTINA NON SONO PREVISTE PROMO E/O ATTIVITÀ PARTICOLARI RISPETTO AL SOLITO. BUON LAVORO</b>
                </div>
                """, unsafe_allow_html=True)

                presenza = st.checkbox(
                    "da fleggare - CONFERMA DI PRESENZA SUL PDV"
                )

                if presenza:
                    conferme_ws.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        codice_pdv,
                        "NESSUNA INDICAZIONE"
                    ])
                    st.success("Presenza registrata")

            st.link_button("HOME", JOTFORM_HOME)

    else:
        st.warning("Anagrafica non disponibile")

# =========================================================
# AREA AMMINISTRATORE
# =========================================================

else:

    st.markdown("# 🔒 DASHBOARD AMMINISTRATORE")

    password = st.text_input("Password", type="password")

    if password == ADMIN_PASSWORD:

        st.success("Accesso consentito")

        st.subheader("Nuova indicazione operativa")

        titolo = st.text_input("Titolo")
        testo = st.text_area("Testo")

        col1, col2 = st.columns(2)
        data_inizio = col1.date_input("Data inizio")
        data_fine = col2.date_input("Data fine")

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
                    data_inizio.strftime("%Y-%m-%d"),
                    data_fine.strftime("%Y-%m-%d")
                ])

            st.success("Indicazione pubblicata")

        st.subheader("Report conferme")

        conferme = pd.DataFrame(conferme_ws.get_all_records())
        if not conferme.empty:
            st.dataframe(conferme)

    else:
        st.warning("Inserire password corretta")
