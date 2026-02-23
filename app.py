import streamlit as st
import pandas as pd
from datetime import datetime
import os
from io import BytesIO
from streamlit_quill import st_quill

st.set_page_config(layout="wide")


# =========================================================
# 🔒 PERSISTENT STORAGE — RENDER (DEFINITIVO)
# =========================================================

DATA_DIR = "/var/data"
UPLOAD_DIR = "/var/data/uploads"

# creare SOLO sottocartella uploads (il mount NON va creato)
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

LOG_FILE = "/var/data/log.csv"
MSG_FILE = "/var/data/messaggi.csv"
PDV_FILE = "/var/data/pdv.csv"


# =========================================================
# 🎨 CSS DASHBOARD ADMIN (INVARIATO)
# =========================================================

CSS_ADMIN = """
<style>
.stApp { background-color: #E6E6E6 !important; }

.block-container {
  padding-top: 1.5rem !important;
  padding-bottom: 2rem !important;
}

hr { border: 1px solid #000 !important; }

input, textarea, select {
  background: #fff !important;
  color: #000 !important;
  border: 2px solid #000 !important;
  border-radius: 8px !important;
}

label { color:#000 !important; font-weight:800 !important; }

.stButton > button, .stDownloadButton > button {
  background: #D50000 !important;
  color: #fff !important;
  border: 1px solid #000 !important;
  font-weight: 800 !important;
  border-radius: 10px !important;
  padding: 10px 16px !important;
}

div[data-testid="stSuccess"] {
  background-color: #E3F2FD !important;
  color: #D50000 !important;
  font-weight: 800 !important;
  border: 2px solid #000 !important;
}

div[data-testid="stAlert"] p {
  color: #D50000 !important;
  font-weight: 800 !important;
}

h1, h2, h3, .stMarkdown, .stTextLabel, label {
  color: #000 !important;
  font-weight: 800 !important;
}
</style>
"""


# =========================================================
# UTILS
# =========================================================

def load_csv(path, cols):
    if os.path.exists(path):
        return pd.read_csv(path, dtype=str).fillna("")
    return pd.DataFrame(columns=cols)


def save_csv(df, path):
    df.to_csv(path, index=False)


def now_str():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def excel_bytes(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()


# =========================================================
# ADMIN
# =========================================================

def admin():

    st.markdown(CSS_ADMIN, unsafe_allow_html=True)

    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.image("logo.png", width=260)

    st.title("DASHBOARD ADMIN")

    if st.text_input("Password", type="password") != "GianAri2026":
        st.warning("Inserire password admin")
        return

    # ✔️ AGGIORNA PAGINA
    if st.button("AGGIORNA"):
        st.rerun()

    st.markdown("---")

    # ===== PDV =====
    st.header("IMPORT LISTA PDV")

    pdv_existing = load_csv(PDV_FILE, ["ID","PDV"])
    prefill = "\n".join([f"{r['ID']};{r['PDV']}" for _, r in pdv_existing.iterrows()])

    pdv_text = st.text_area("", value=prefill, height=140)

    c1, c2 = st.columns(2)

    with c1:
        if st.button("SALVA LISTA PDV"):

            rows = []
            for line in pdv_text.splitlines():
                if ";" in line:
                    a, b = line.split(";", 1)
                    rows.append([a.strip(), b.strip()])

            save_csv(pd.DataFrame(rows, columns=["ID", "PDV"]), PDV_FILE)
            st.success("Lista PDV salvata")

    with c2:
        if st.button("PULISCI LISTA PDV"):
            save_csv(pd.DataFrame(columns=["ID","PDV"]), PDV_FILE)
            st.success("Lista PDV pulita")

    st.markdown("---")

    # ===== MESSAGGIO =====
    st.header("CREA NUOVO MESSAGGIO")

    st.write("FORMATTATORE TESTO")

    msg = st_quill(html=True)

    uploaded = st.file_uploader(
        "ALLEGATO (immagine o PDF)",
        type=["png", "jpg", "jpeg", "pdf"]
    )

    c1, c2 = st.columns(2)
    with c1:
        data_inizio = st.date_input("DATA INIZIO")
    with c2:
        data_fine = st.date_input("DATA FINE")

    pdv_ids = st.text_area("ID PDV (uno per riga)", height=140)

    if st.button("SALVA MESSAGGIO"):

        df = load_csv(MSG_FILE,
            ["msg","inizio","fine","pdv_ids","file"])

        filename = ""

        if uploaded:
            filename = uploaded.name
            with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
                f.write(uploaded.getbuffer())

        new = pd.DataFrame([[msg,
                             data_inizio.strftime("%d-%m-%Y"),
                             data_fine.strftime("%d-%m-%Y"),
                             pdv_ids.strip(),
                             filename]],
                           columns=df.columns)

        save_csv(pd.concat([df,new]), MSG_FILE)
        st.success("Messaggio salvato")

    st.markdown("---")

    # ===== STORICO MESSAGGI =====
    st.header("STORICO MESSAGGI")

    msg_df = load_csv(MSG_FILE,
        ["msg","inizio","fine","pdv_ids","file"])

    st.dataframe(msg_df, use_container_width=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button("SCARICA CSV",
                           msg_df.to_csv(index=False),
                           "messaggi.csv")

    with c2:
        st.download_button("SCARICA EXCEL",
                           excel_bytes(msg_df),
                           "messaggi.xlsx")

    with c3:
        if st.button("PULISCI MESSAGGI"):
            save_csv(msg_df.iloc[0:0], MSG_FILE)
            st.success("Messaggi puliti")
            st.rerun()

    st.markdown("---")

    # ===== REPORT =====
    st.header("REPORT LETTURE")

    log = load_csv(LOG_FILE, ["data","pdv","msg"])

    st.dataframe(log, use_container_width=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        st.download_button("SCARICA CSV",
                           log.to_csv(index=False),
                           "report.csv")

    with c2:
        st.download_button("SCARICA EXCEL",
                           excel_bytes(log),
                           "report.xlsx")

    with c3:
        if st.button("PULISCI LOG"):
            save_csv(log.iloc[0:0], LOG_FILE)
            st.success("Log pulito")
            st.rerun()


# =========================================================
# DIPENDENTI
# =========================================================

def dipendenti():

    st.markdown("""
    <style>
    .stApp {background:#c40000; color:white;}
    label, p, h1, h2, h3 {color:white !important;}
    </style>
    """, unsafe_allow_html=True)

    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.image("logo.png", width=240)

    st.markdown("<h1 style='text-align:center;'>INDICAZIONI OPERATIVE</h1>",
                unsafe_allow_html=True)

    st.markdown("<h3 style='text-align:center;'>SELEZIONA IL TUO PDV</h3>",
                unsafe_allow_html=True)

    pdv_df = load_csv(PDV_FILE, ["ID","PDV"])

    if pdv_df.empty:
        st.warning("Archivio PDV vuoto")
        return

    scelta = st.selectbox("", pdv_df["PDV"], index=None,
                          placeholder="Digita la città...")

    st.markdown(
        "<p style='text-align:center;'><b>"
        "Digita le prime lettere della Città per trovare il tuo PDV"
        "</b></p>",
        unsafe_allow_html=True)

    if not scelta:
        return

    pdv_id = pdv_df.loc[pdv_df["PDV"]==scelta,"ID"].values[0]

    msg_df = load_csv(MSG_FILE,
        ["msg","inizio","fine","pdv_ids","file"])

    oggi = datetime.now()

    mostrati = []

    for _, r in msg_df.iterrows():

        ids = r["pdv_ids"].splitlines()

        if pdv_id in ids:

            di = datetime.strptime(r["inizio"], "%d-%m-%Y")
            df = datetime.strptime(r["fine"], "%d-%m-%Y")

            if di <= oggi <= df:
                mostrati.append(r)

    log_df = load_csv(LOG_FILE, ["data","pdv","msg"])

    # ===== MESSAGGIO GENERICO =====
    if not mostrati:

        st.markdown("""
        <div style='
            background:white;
            color:black;
            padding:20px;
            border-radius:10px;
            text-align:center;
            font-weight:800;
            font-size:18px;
        '>
        QUESTA MATTINA PER QUESTO PDV NON SONO PREVISTE PROMO/ATTIVITA' PARTICOLARI. BUON LAVORO
        </div>
        """, unsafe_allow_html=True)

        if st.checkbox("Spunta CONFERMA DI PRESENZA"):

            new = pd.DataFrame([[
                now_str(), scelta, "PRESENZA"
            ]], columns=log_df.columns)

            save_csv(pd.concat([log_df,new]), LOG_FILE)
            st.success("Presenza registrata")

        return

    for r in mostrati:

        st.markdown("---")

        st.markdown(r["msg"], unsafe_allow_html=True)

        if r["file"]:
            path = os.path.join(UPLOAD_DIR, r["file"])
            if os.path.exists(path):
                if r["file"].lower().endswith(".pdf"):
                    with open(path, "rb") as f:
                        st.download_button("Scarica allegato",
                                           f.read(),
                                           r["file"])
                else:
                    st.image(path, width=350)

        lettura = st.checkbox("Spunta di PRESA VISIONE",
                              key=r["msg"]+"l")

        presenza = st.checkbox("Spunta CONFERMA DI PRESENZA",
                               key=r["msg"]+"p")

        if lettura and presenza:

            gia = ((log_df["pdv"]==scelta) &
                   (log_df["msg"]==r["msg"])).any()

            if not gia:

                new = pd.DataFrame([[
                    now_str(), scelta, r["msg"]
                ]], columns=log_df.columns)

                save_csv(pd.concat([log_df,new]), LOG_FILE)
                st.success("Registrato")


# =========================================================
# ROUTER
# =========================================================

if st.query_params.get("admin") == "1":
    admin()
else:
    dipendenti()
