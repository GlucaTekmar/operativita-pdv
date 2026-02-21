import streamlit as st
import pandas as pd
from datetime import datetime
import os

st.set_page_config(layout="wide")

LOG_FILE = "log.csv"
MSG_FILE = "messaggi.csv"
PDV_FILE = "pdv.csv"


# =========================================================
# UTILS
# =========================================================

def load_csv(path, cols):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=cols)


def save_csv(df, path):
    df.to_csv(path, index=False)


# =========================================================
# LOGO
# =========================================================

if os.path.exists("logo.png"):
    st.image("logo.png", width=200)


# =========================================================
# ADMIN VIEW
# =========================================================

def admin():

    st.title("DASHBOARD ADMIN")

    # ---------- PASSWORD ----------
    password = st.text_input("Password", type="password")

    if password != "GianAri2026":
        st.warning("Inserire password admin")
        return

    # =====================================================
    # CARICAMENTO LISTA PDV
    # =====================================================

    st.header("Lista PDV (ID;Nome)")

    pdv_text = st.text_area(
        "Incolla elenco PDV",
        height=250
    )

    if st.button("SALVA LISTA PDV"):

        rows = []

        for line in pdv_text.splitlines():
            if ";" in line:
                id_, nome = line.split(";", 1)
                rows.append([id_.strip(), nome.strip()])

        df = pd.DataFrame(rows, columns=["ID", "PDV"])
        save_csv(df, PDV_FILE)

        st.success("Lista PDV salvata")

    # =====================================================
    # CREAZIONE MESSAGGIO
    # =====================================================

    st.header("Nuovo messaggio")

    msg = st.text_area(
        "Messaggio (stile WhatsApp)",
        height=300
    )

    st.caption("Supporta link copiati da WhatsApp")

    data_inizio = st.date_input("Data inizio")
    data_fine = st.date_input("Data fine")

    pdv_ids = st.text_area(
        "Incolla ID PDV (uno per riga)",
        height=150
    )

    uploaded = st.file_uploader(
        "Allega immagine o PDF",
        type=["png", "jpg", "jpeg", "pdf"]
    )

    if st.button("SALVA MESSAGGIO"):

        df = load_csv(MSG_FILE, [
            "msg", "inizio", "fine", "pdv_ids", "file"
        ])

        filename = ""

        if uploaded:
            filename = uploaded.name
            with open(filename, "wb") as f:
                f.write(uploaded.getbuffer())

        new = pd.DataFrame([[
            msg,
            data_inizio,
            data_fine,
            pdv_ids,
            filename
        ]], columns=df.columns)

        df = pd.concat([df, new], ignore_index=True)
        save_csv(df, MSG_FILE)

        st.success("Messaggio salvato")

    # =====================================================
    # REPORT LOG
    # =====================================================

    st.header("Report letture")

    log = load_csv(LOG_FILE, [
        "data", "pdv", "msg"
    ])

    st.dataframe(log, use_container_width=True)

    st.download_button(
        "Scarica CSV",
        log.to_csv(index=False),
        "report.csv"
    )

    if st.button("PULISCI LOG"):
        save_csv(log.iloc[0:0], LOG_FILE)
        st.success("Log pulito")


# =========================================================
# DIPENDENTI VIEW
# =========================================================

def dipendenti_view():

    st.markdown(
        """
        <style>
        body {background-color:#b30000;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("INDICAZIONI OPERATIVE")

    pdv_df = load_csv(PDV_FILE, ["ID", "PDV"])

    if pdv_df.empty:
        st.warning("Archivio PDV vuoto")
        return

    scelta = st.selectbox(
        "Seleziona PDV",
        pdv_df["PDV"]
    )

    pdv_id = pdv_df.loc[
        pdv_df["PDV"] == scelta, "ID"
    ].values[0]

    msg_df = load_csv(MSG_FILE, [
        "msg", "inizio", "fine", "pdv_ids", "file"
    ])

    oggi = datetime.now().date()

    mostrati = []

    for _, r in msg_df.iterrows():

        ids = str(r["pdv_ids"]).splitlines()

        if (
            pdv_id in ids and
            pd.to_datetime(r["inizio"]).date() <= oggi <= pd.to_datetime(r["fine"]).date()
        ):
            mostrati.append(r)

    if not mostrati:
        st.info("Nessun messaggio")
        return

    log_df = load_csv(LOG_FILE, [
        "data", "pdv", "msg"
    ])

    for r in mostrati:

        st.markdown("---")

        st.markdown(r["msg"], unsafe_allow_html=True)

        if r["file"]:
            if r["file"].lower().endswith(".pdf"):
                st.download_button(
                    "Scarica allegato",
                    open(r["file"], "rb"),
                    file_name=r["file"]
                )
            else:
                st.image(r["file"], width=350)

        gia_letto = (
            (log_df["pdv"] == scelta) &
            (log_df["msg"] == r["msg"])
        ).any()

        if gia_letto:
            st.success("Già confermato")
            continue

        flag = st.checkbox(
            "Confermo lettura e presenza",
            key=r["msg"]
        )

        if flag:

            new = pd.DataFrame([[
                datetime.now(),
                scelta,
                r["msg"]
            ]], columns=log_df.columns)

            log_df = pd.concat([log_df, new], ignore_index=True)
            save_csv(log_df, LOG_FILE)

            st.success("Registrato")


# =========================================================
# SWITCH PAGINE
# =========================================================

params = st.query_params

if params.get("admin") == "1":
    admin()
else:
    dipendenti_view()
