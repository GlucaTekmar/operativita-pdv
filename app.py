import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io

st.set_page_config(page_title="Operatività PDV", layout="wide")

ADMIN_PASSWORD = "GianAri2026"
HOME_URL = "https://www.jotform.com"

PDV_FILE = "pdv.csv"
MSG_FILE = "messaggi.csv"
LOG_FILE = "log.csv"

# ================= UTILITY =================

def load_csv(file, columns):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=columns)

def save_csv(df, file):
    df.to_csv(file, index=False)

# ================= LOG PER PDV =================

def log_esiste(pdv):
    df = load_csv(LOG_FILE,
                  ["Data_Ora", "PDV", "Messaggio", "Lettura", "Presenza"])
    return pdv in df["PDV"].values

def salva_log(pdv, msg, lettura, presenza):

    if log_esiste(pdv):
        return  # evita duplicato per lo stesso PDV

    df = load_csv(LOG_FILE,
                  ["Data_Ora", "PDV", "Messaggio", "Lettura", "Presenza"])

    df.loc[len(df)] = [
        datetime.now(),
        pdv,
        msg,
        "SI" if lettura else "NO",
        "SI" if presenza else "NO"
    ]

    save_csv(df, LOG_FILE)

# ================= AREA DIPENDENTI =================

def dipendenti_view():

    st.markdown(
        "<h1 style='text-align:center;color:white'>INDICAZIONI OPERATIVE</h1>",
        unsafe_allow_html=True
    )

    pdv_df = load_csv(PDV_FILE, ["ID", "Nome"])

    if pdv_df.empty:
        st.warning("Archivio PDV vuoto")
        return

    scelta = st.selectbox("SELEZIONA IL TUO PDV", pdv_df["Nome"])

    msg_df = load_csv(MSG_FILE,
                      ["PDV", "Messaggio", "Inizio", "Fine"])

    oggi = datetime.now().date()
    msg_attivo = None

    for _, r in msg_df.iterrows():
        if r["PDV"] == scelta:
            if r["Inizio"] <= str(oggi) <= r["Fine"]:
                msg_attivo = r["Messaggio"]

    gia_confermato = log_esiste(scelta)

    # ===== CON MESSAGGIO =====

    if msg_attivo:

        st.info(msg_attivo)

        if gia_confermato:
            st.success("Già confermato per questo PDV")
            st.link_button("HOME", HOME_URL)
            return

        lettura = st.checkbox("Confermo lettura")
        presenza = st.checkbox("Confermo presenza")

        if st.button("CONFERMA"):

            if not lettura or not presenza:
                st.error("Devi spuntare entrambi i flag")
                return

            salva_log(scelta, msg_attivo, lettura, presenza)

            st.success("Registrazione completata")
            st.link_button("HOME", HOME_URL)

    # ===== SENZA MESSAGGIO =====

    else:

        st.warning("Nessuna indicazione per oggi")

        if gia_confermato:
            st.success("Presenza già registrata per questo PDV")
            st.link_button("HOME", HOME_URL)
            return

        presenza = st.checkbox("Confermo presenza")

        if st.button("CONFERMA PRESENZA"):

            if not presenza:
                st.error("Devi confermare la presenza")
                return

            salva_log(scelta, "NESSUN MESSAGGIO", False, presenza)

            st.success("Presenza registrata")
            st.link_button("HOME", HOME_URL)

# ================= AREA ADMIN =================

def admin():

    st.title("🔒 DASHBOARD ADMIN")

    if st.text_input("Password", type="password") != ADMIN_PASSWORD:
        st.stop()

    tab1, tab2, tab3 = st.tabs(
        ["PDV", "Messaggi", "Report Log"]
    )

    # ----- PDV -----
    with tab1:

        testo = st.text_area("Incolla elenco ID;Nome")

        if st.button("IMPORTA PDV"):
            righe = [r.split(";") for r in testo.splitlines() if ";" in r]
            df = pd.DataFrame(righe, columns=["ID", "Nome"])
            save_csv(df, PDV_FILE)
            st.success("Archivio aggiornato")

        st.dataframe(load_csv(PDV_FILE, ["ID", "Nome"]))

    # ----- MESSAGGI -----
    with tab2:

        pdv_df = load_csv(PDV_FILE, ["ID", "Nome"])

        if pdv_df.empty:
            st.warning("Caricare prima i PDV")
            return

        pdv = st.selectbox("PDV", pdv_df["Nome"])
        msg = st.text_area("Messaggio")

        inizio = st.date_input("Data inizio")
        fine = st.date_input("Data fine")

        if st.button("SALVA MESSAGGIO"):

            df = load_csv(MSG_FILE,
                          ["PDV", "Messaggio", "Inizio", "Fine"])

            df.loc[len(df)] = [
                pdv,
                msg,
                str(inizio),
                str(fine)
            ]

            save_csv(df, MSG_FILE)
            st.success("Messaggio salvato")

        st.dataframe(load_csv(MSG_FILE,
                              ["PDV", "Messaggio", "Inizio", "Fine"]))

    # ----- LOG -----
    with tab3:

        df = load_csv(LOG_FILE,
                      ["Data_Ora", "PDV", "Messaggio", "Lettura", "Presenza"])

        st.dataframe(df, use_container_width=True)

        st.download_button(
            "Scarica CSV",
            df.to_csv(index=False).encode("utf-8"),
            "report.csv",
            "text/csv"
        )

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)

        st.download_button(
            "Scarica Excel",
            buffer.getvalue(),
            file_name="report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        if st.button("PULISCI LOG"):
            save_csv(df.iloc[0:0], LOG_FILE)
            st.success("Log pulito")

# ================= SWITCH =================

params = st.query_params

if "admingianari2026" in params:
    admin()
else:
    dipendenti_view()


