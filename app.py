import streamlit as st
import pandas as pd
import os
import uuid
import base64
import time
from datetime import datetime
from pathlib import Path

ADMIN_PASSWORD = "GianAri2026"
HOME_URL = "https://eu.jotform.com/app/253605296903360"

BASE_DIR = Path("/var/dati")

PDV_FILE = BASE_DIR / "pdv.csv"
MSG_FILE = BASE_DIR / "messaggi.csv"
LOG_FILE = BASE_DIR / "log.csv"

MEDIA_DIR = BASE_DIR / "media"
LOGO_FILE = BASE_DIR / "logo.png"

MEDIA_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="Operatività PDV", layout="wide")

st.markdown("""
<style>
body { background-color:#b30000; }
.main { background-color:#b30000; }
h1,h2,h3,h4,p,label { color:white; }
.stButton>button {
background-color:black;
color:white;
border-radius:6px;
border:none;
padding:8px 14px;
}
</style>
""", unsafe_allow_html=True)

def safe_load_csv(path, columns):

    if not path.exists():
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)

    try:
        df = pd.read_csv(path)
    except:
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)

    return df

def acquire_lock(file):

    lock = str(file) + ".lock"

    while os.path.exists(lock):
        time.sleep(0.05)

    open(lock, "w").close()

    return lock

def release_lock(lock):

    if os.path.exists(lock):
        os.remove(lock)

def safe_save_csv(df, path):

    lock = acquire_lock(path)

    temp = str(path) + ".tmp"
    df.to_csv(temp, index=False)
    os.replace(temp, path)

    release_lock(lock)

def log_event(pdv, msg_id, action):

    today = datetime.now().date().isoformat()

    log = safe_load_csv(LOG_FILE, ["timestamp","pdv","msg_id","azione"])

    if action == "apertura":

        today_logs = log[
            (log["pdv"] == pdv) &
            (log["msg_id"] == msg_id) &
            (log["timestamp"].str.startswith(today))
        ]

        if len(today_logs) > 0:
            return

    if action == "conferma":

        existing = log[
            (log["pdv"] == pdv) &
            (log["msg_id"] == msg_id) &
            (log["azione"] == "conferma") &
            (log["timestamp"].str.startswith(today))
        ]

        if len(existing) > 0:
            return

    new = {
        "timestamp": datetime.now().isoformat(),
        "pdv": pdv,
        "msg_id": msg_id,
        "azione": action
    }

    log = pd.concat([log, pd.DataFrame([new])], ignore_index=True)

    safe_save_csv(log, LOG_FILE)

def save_file(uploaded, msg_id):

    if uploaded is None:
        return ""

    ext = uploaded.name.split(".")[-1].lower()

    filename = f"{msg_id}.{ext}"

    path = MEDIA_DIR / filename

    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())

    return filename

def show_pdf(path):

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    pdf_html = f"""
    <iframe src="data:application/pdf;base64,{b64}"
    width="100%" height="800"></iframe>
    """

    st.markdown(pdf_html, unsafe_allow_html=True)

col1, col2 = st.columns([1,5])

with col1:
    if LOGO_FILE.exists():
        st.image(str(LOGO_FILE), width=120)

with col2:
    st.markdown(f'<a href="{HOME_URL}"><button>HOME</button></a>', unsafe_allow_html=True)

st.markdown("---")

pdv_df = safe_load_csv(PDV_FILE, ["pdv_id","pdv_nome"])

msg_df = safe_load_csv(MSG_FILE, ["msg_id","msg","pdv_ids","file","data"])

mode = st.sidebar.radio("Modalità", ["DIPENDENTE","ADMIN"])

if mode == "ADMIN":

    pwd = st.sidebar.text_input("Password", type="password")

    if pwd != ADMIN_PASSWORD:
        st.stop()

    st.title("Area Admin")

    message = st.text_area("Messaggio")

    pdv_input = st.text_area("PDV destinatari (uno per riga)")

    file = st.file_uploader("Allegato", type=["png","jpg","jpeg","pdf"])

    if st.button("INVIA MESSAGGIO"):

        if message.strip() == "":
            st.error("Messaggio vuoto")
            st.stop()

        pdv_ids = [x.strip() for x in pdv_input.splitlines() if x.strip()]

        msg_id = str(uuid.uuid4())

        filename = save_file(file, msg_id)

        new = {
            "msg_id": msg_id,
            "msg": message,
            "pdv_ids": ",".join(pdv_ids),
            "file": filename,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        msg_df = pd.concat([msg_df, pd.DataFrame([new])], ignore_index=True)

        safe_save_csv(msg_df, MSG_FILE)

        st.success("Messaggio inviato")

    st.markdown("---")

    for _, row in msg_df.sort_values("data", ascending=False).iterrows():

        st.markdown(f"**{row['data']}**")

        st.write(row["msg"])

        if row["file"]:

            file_path = MEDIA_DIR / row["file"]

            if file_path.exists():

                if row["file"].endswith(".pdf"):
                    show_pdf(file_path)
                else:
                    st.image(str(file_path))

        st.markdown("---")

if mode == "DIPENDENTE":

    if "pdv_selected" not in st.session_state:
        st.session_state.pdv_selected = None

    if st.session_state.pdv_selected is None:

        st.title("Seleziona PDV")

        options = pdv_df["pdv_id"] + " - " + pdv_df["pdv_nome"]

        choice = st.selectbox("PDV", options)

        if st.button("ENTRA"):

            st.session_state.pdv_selected = choice.split(" - ")[0]

            st.rerun()

    else:

        pdv_id = st.session_state.pdv_selected

        if st.button("TORNA ALLA LISTA PDV"):
            st.session_state.pdv_selected = None
            st.rerun()

        st.title(f"Messaggi PDV {pdv_id}")

        messages = msg_df[msg_df["pdv_ids"].str.contains(pdv_id, na=False)]

        if len(messages) == 0:
            st.info("Nessun messaggio")

        for _, row in messages.sort_values("data", ascending=False).iterrows():

            st.markdown(f"### {row['data']}")

            st.write(row["msg"])

            log_event(pdv_id, row["msg_id"], "apertura")

            if row["file"]:

                file_path = MEDIA_DIR / row["file"]

                if file_path.exists():

                    if row["file"].endswith(".pdf"):
                        show_pdf(file_path)
                    else:
                        st.image(str(file_path))

            confirm = st.checkbox("Conferma lettura", key=row["msg_id"])

            if confirm:
                log_event(pdv_id, row["msg_id"], "conferma")

            st.markdown("---")
