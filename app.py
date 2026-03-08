import streamlit as st
import pandas as pd
import os
import uuid
import datetime
import shutil
from filelock import FileLock

# =========================
# CONFIG
# =========================

BASE_PATH = "/var/data"
MEDIA_PATH = os.path.join(BASE_PATH, "media")

PDV_FILE = os.path.join(BASE_PATH, "pdv.csv")
MSG_FILE = os.path.join(BASE_PATH, "messaggi.csv")
LOG_FILE = os.path.join(BASE_PATH, "log.csv")

LOGO_URL = "https://raw.githubusercontent.com/GlucaTekmar/operativita-pdv/refs/heads/main/logo.png"

ADMIN_PASSWORD = "GianAri2026"

# =========================
# STORAGE INIT
# =========================

def ensure_storage():

    os.makedirs(BASE_PATH, exist_ok=True)
    os.makedirs(MEDIA_PATH, exist_ok=True)

    if not os.path.exists(PDV_FILE):
        df = pd.DataFrame(columns=["pdv_id","pdv_nome"])
        df.to_csv(PDV_FILE,index=False)

    if not os.path.exists(MSG_FILE):
        df = pd.DataFrame(columns=[
            "msg_id","titolo","msg","pdv_ids","file",
            "data_inizio","data_fine","stato"
        ])
        df.to_csv(MSG_FILE,index=False)

    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=[
            "data","pdv_id","pdv_nome","msg_id",
            "apertura_timestamp","lettura_timestamp"
        ])
        df.to_csv(LOG_FILE,index=False)


# =========================
# LOCKED CSV READ WRITE
# =========================

def read_csv(path):
    lock = FileLock(path + ".lock")
    with lock:
        return pd.read_csv(path)

def write_csv(df,path):
    tmp = path + ".tmp"
    lock = FileLock(path + ".lock")
    with lock:
        df.to_csv(tmp,index=False)
        os.replace(tmp,path)

# =========================
# DATA ACCESS
# =========================

def load_pdv():
    return read_csv(PDV_FILE)

def save_pdv(df):
    write_csv(df,PDV_FILE)

def load_messages():
    return read_csv(MSG_FILE)

def save_messages(df):
    write_csv(df,MSG_FILE)

def load_logs():
    return read_csv(LOG_FILE)

def save_logs(df):
    write_csv(df,LOG_FILE)

# =========================
# LOGIC
# =========================

def append_or_update_log(pdv_id,pdv_nome,msg_id,lettura=False):

    logs = load_logs()

    today = datetime.date.today().isoformat()

    existing = logs[
        (logs["data"]==today) &
        (logs["pdv_id"]==pdv_id) &
        (logs["msg_id"]==msg_id)
    ]

    now = datetime.datetime.now().isoformat()

    if existing.empty:

        new = pd.DataFrame([{
            "data":today,
            "pdv_id":pdv_id,
            "pdv_nome":pdv_nome,
            "msg_id":msg_id,
            "apertura_timestamp":now,
            "lettura_timestamp":now if lettura else ""
        }])

        logs = pd.concat([logs,new],ignore_index=True)

    else:

        if lettura:
            idx = existing.index[0]
            logs.loc[idx,"lettura_timestamp"] = now

    save_logs(logs)

# =========================
# UI
# =========================

def render_header(title):

    st.markdown(
        """
        <style>
        body {background:#c8102e;}
        .main {background:#c8102e;}
        .circolare {
            background:white;
            padding:25px;
            margin-bottom:30px;
            border-radius:6px;
            box-shadow:0 3px 8px rgba(0,0,0,0.2);
        }
        .linea {
            border-top:3px solid #c8102e;
            margin:12px 0;
        }
        .btn{
            background:black;
            color:white;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.image(LOGO_URL,width=200)
    st.title(title)

# =========================
# EMPLOYEE PAGE 1
# =========================

def employee_page_one():

    render_header("SELEZIONA UN PDV)

    pdv = load_pdv()

    if pdv.empty:
        st.warning("Lista PDV non disponibile")
        return

    options = pdv["pdv_nome"].tolist()

    selected = st.selectbox(
        "PDV",
        options,
        index=None,
        placeholder="Digita le prime lettere della Città"
    )

    st.markdown("**Digita le prime lettere della Città**")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("ENTRA"):
            if selected:
                st.session_state["pdv_nome"]=selected
                st.session_state["pdv_id"]=pdv[pdv["pdv_nome"]==selected]["pdv_id"].iloc[0]
                st.session_state["page"]="emp2"
                st.rerun()

    with col2:
        if st.button("HOME"):
            st.markdown("[Vai alla Home](https://eu.jotform.com/app/253605296903360)")

# =========================
# MESSAGE FILTER
# =========================

def get_active_messages(pdv_id):

    msgs = load_messages()

    if msgs.empty:
        return pd.DataFrame()

    today = datetime.date.today()

    def valid(row):

        ids = str(row["pdv_ids"]).split("|")

        if str(pdv_id) not in ids:
            return False

        if row["stato"] != "attivo":
            return False

        start = datetime.date.fromisoformat(row["data_inizio"])
        end = datetime.date.fromisoformat(row["data_fine"])

        return start <= today <= end

    msgs = msgs[msgs.apply(valid,axis=1)]

    return msgs

# =========================
# CIRCOLARE RENDER
# =========================

def render_circular_message(i,row,pdv_nome):

    st.markdown(f"### MESSAGGIO N.{i}")
    st.markdown(f"**{pdv_nome}**")

    st.markdown('<div class="circolare">',unsafe_allow_html=True)

    st.image(LOGO_URL,width=120)

    st.markdown(f"**{row['titolo'].upper()}**")

    st.markdown('<div class="linea"></div>',unsafe_allow_html=True)

    st.write(row["msg"])

    if pd.notna(row["file"]) and row["file"]!="":

        path = os.path.join(MEDIA_PATH,row["file"])

        if os.path.exists(path):

            if path.lower().endswith(".pdf"):
                with open(path,"rb") as f:
                    st.download_button("Apri PDF",f,row["file"])

            else:
                st.image(path)

    st.markdown('</div>',unsafe_allow_html=True)

# =========================
# EMPLOYEE PAGE 2
# =========================

def employee_page_two():

    render_header("CIRCOLARI OPERATIVE")

    pdv_id = st.session_state.get("pdv_id")
    pdv_nome = st.session_state.get("pdv_nome")

    msgs = get_active_messages(pdv_id)

    if msgs.empty:

        st.markdown('<div class="circolare">',unsafe_allow_html=True)
        st.markdown("### NESSUNA PROMO e/o ATTIVITÀ")
        st.write("QUESTA MATTINA SU QUESTO PDV NON SONO PREVISTE PROMO e/o ATTIVITÀ PARTICOLARI. BUON LAVORO")
        st.markdown("</div>",unsafe_allow_html=True)

    else:

        for i,row in enumerate(msgs.itertuples(),1):

            render_circular_message(i,row._asdict(),pdv_nome)

            append_or_update_log(pdv_id,pdv_nome,row.msg_id)

    if st.checkbox("Spunta la CONFERMA DI LETTURA"):

        for msg in msgs["msg_id"]:
            append_or_update_log(pdv_id,pdv_nome,msg,lettura=True)

    col1,col2 = st.columns(2)

    with col1:
        if st.button("TORNA ALLA LISTA PDV"):
            st.session_state["page"]="emp1"
            st.rerun()

    with col2:
        if st.button("HOME"):
            st.markdown("[Vai alla Home](https://eu.jotform.com/app/253605296903360)")

# =========================
# ADMIN LOGIN
# =========================

def admin_login():

    render_header("ADMIN LOGIN")

    pwd = st.text_input("Password",type="password")

    if st.button("Accedi"):

        if pwd == ADMIN_PASSWORD:
            st.session_state["admin"]=True
            st.session_state["page"]="admin1"
            st.rerun()

        else:
            st.error("Password errata")

# =========================
# ADMIN PAGE 1
# =========================

def admin_page_one():

    render_header("ADMIN MESSAGGI")

    st.subheader("LISTA TOTALE PDV")

    pdv = load_pdv()

    text = st.text_area("Incolla lista PDV",value=pdv.to_csv(index=False))

    col1,col2 = st.columns(2)

    with col1:
        if st.button("SALVA"):
            from io import StringIO
            df = pd.read_csv(StringIO(text))
            save_pdv(df)

    with col2:
        if st.button("PULISCI LISTA"):
            save_pdv(pd.DataFrame(columns=["pdv_id","pdv_nome"]))

    st.subheader("CREA MESSAGGIO")

    titolo = st.text_input("Titolo")

    msg = st.text_area("Testo")

    pdv_ids = st.text_area("ID PDV destinatari (uno per riga)")

    data_inizio = st.date_input("Data inizio")
    data_fine = st.date_input("Data fine")

    file = st.file_uploader("PDF o immagine")

    if st.button("SALVA MESSAGGIO"):

        msgs = load_messages()

        msg_id = str(uuid.uuid4())

        filename=""

        if file:

            filename = msg_id + "_" + file.name

            path = os.path.join(MEDIA_PATH,filename)

            with open(path,"wb") as f:
                f.write(file.getbuffer())

        ids = "|".join([x.strip() for x in pdv_ids.splitlines() if x.strip()!=""])

        new = pd.DataFrame([{
            "msg_id":msg_id,
            "titolo":titolo,
            "msg":msg,
            "pdv_ids":ids,
            "file":filename,
            "data_inizio":data_inizio.isoformat(),
            "data_fine":data_fine.isoformat(),
            "stato":"attivo"
        }])

        msgs = pd.concat([msgs,new],ignore_index=True)

        save_messages(msgs)

        st.success("Messaggio salvato")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("REPORT"):
            st.session_state["page"]="admin2"
            st.rerun()

    with col2:
        if st.button("LOGOUT"):
            st.session_state.clear()
            st.rerun()

# =========================
# ADMIN PAGE 2
# =========================

def admin_page_two():

    render_header("REPORT")

    msgs = load_messages()

    logs = load_logs()

    st.subheader("TABELLA MESSAGGI")

    st.dataframe(msgs)

    st.download_button("Scarica CSV",msgs.to_csv(index=False),"messaggi.csv")

    st.subheader("TABELLA LOG")

    st.dataframe(logs)

    st.download_button("Scarica CSV",logs.to_csv(index=False),"log.csv")

    col1,col2 = st.columns(2)

    with col1:
        if st.button("MESSAGGI"):
            st.session_state["page"]="admin1"
            st.rerun()

    with col2:
        if st.button("LOGOUT"):
            st.session_state.clear()
            st.rerun()

# =========================
# MAIN
# =========================

def main():

    ensure_storage()

    if "page" not in st.session_state:
        st.session_state["page"]="emp1"

    query = st.query_params

    if "admin" in query and "admin" not in st.session_state:
        admin_login()
        return

    if st.session_state.get("admin"):

        if st.session_state["page"]=="admin1":
            admin_page_one()

        elif st.session_state["page"]=="admin2":
            admin_page_two()

    else:

        if st.session_state["page"]=="emp1":
            employee_page_one()

        elif st.session_state["page"]=="emp2":
            employee_page_two()

# =========================

if __name__ == "__main__":
    main()

