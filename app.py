import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(layout="wide")

# =========================================================
# 🎨 STILE
# =========================================================

st.markdown("""
<style>
.stApp {
    background-color: #E30613;
}

.block-container {
    padding-top: 4rem;
}

h1, h2, h3, h4, h5, h6, p, label, div {
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 🔗 CONNESSIONE GOOGLE SHEETS
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

SPREADSHEET_ID = "11o5dTHZBaeWS0N2crJyGqNbOsIPnLWzIu9q9snYw9hI"

sheet = client.open_by_key(SPREADSHEET_ID)

anagrafica_ws = sheet.worksheet("ANAGRAFICA")
messaggi_ws = sheet.worksheet("MESSAGGI")
conferme_ws = sheet.worksheet("CONFERME")

anagrafica = pd.DataFrame(anagrafica_ws.get_all_records())
messaggi = pd.DataFrame(messaggi_ws.get_all_records())

oggi = datetime.now().date()

# =========================================================
# 🔒 CONTROLLO MODALITÀ ADMIN
# =========================================================

query = st.query_params

admin_mode = (
    "admin" in query
    and query["admin"] == st.secrets["app"]["ADMIN_KEY"]
)

# =========================================================
# 👨‍💼 AREA DIPENDENTI
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
        "Digita per cercare il tuo PDV",
        [""] + anagrafica["Display"].tolist()
    )

    if pdv != "":

        codice_pdv = pdv.split(" - ")[0]

        messaggi_attivi = messaggi[
            messaggi["ID"].astype(str) == codice_pdv
        ]

        # -------------------------------------------------
        # 🔵 SE ESISTE INDICAZIONE OPERATIVA
        # -------------------------------------------------

        if not messaggi_attivi.empty:

            msg = messaggi_attivi.iloc[0]

            st.markdown(f"""
            <div style='background:white;color:black;padding:20px;border-radius:10px'>
            <h3>{msg['Titolo']}</h3>
            <p>{msg['Testo']}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("### Conferma di Lettura e Presenza")

            lettura = st.checkbox("Confermo di aver letto l’indicazione")
            presenza = st.checkbox("Confermo presenza sul PDV")

            if lettura and presenza:

                conferme_ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    codice_pdv,
                    msg["Titolo"]
                ])

                st.success("Registrazione effettuata")

                st.link_button(
                    "TORNA ALLA HOME",
                    "https://form.jotform.com/"
                )

        # -------------------------------------------------
        # 🟡 SE NON ESISTE INDICAZIONE
        # -------------------------------------------------

        else:

            st.markdown("""
            <div style='background:white — color:black;padding:20px;border-radius:10px'>
            <b>
            PER QUESTO PDV OGGI NON SONO PREVISTE ATTIVITÀ PARTICOLARI.
            BUON LAVORO.
            </b>
            </div>
            """, unsafe_allow_html=True)

            presenza = st.checkbox("Confermo presenza sul PDV")

            if presenza:

                conferme_ws.append_row([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    codice_pdv,
                    "NESSUNA INDICAZIONE"
                ])

                st.success("Presenza registrata")

                st.link_button(
                    "TORNA ALLA HOME",
                    "https://form.jotform.com/"
                )

# =========================================================
# 🟣 AREA AMMINISTRATORE
# =========================================================

else:

    st.markdown("# 🔒 DASHBOARD AMMINISTRATORE")

    admin_pass = st.text_input(
        "Password amministratore",
        type="password"
    )

    if admin_pass == st.secrets["app"]["ADMIN_PASSWORD"]:

        st.success("Accesso consentito")

        st.subheader("Nuova indicazione operativa")

        titolo = st.text_input("Titolo")
        testo = st.text_area("Testo")

        codici = st.text_area(
            "Codici PDV (uno per riga o separati da virgola)"
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

            st.success("Indicazione pubblicata")

    else:
        st.warning("Inserire password valida")

