import streamlit as st
import pandas as pd
import os
import datetime
import uuid
from filelock import FileLock
from streamlit_searchbox import st_searchbox
from streamlit_quill import st_quill
import base64

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

BASE_PATH="/var/data"
MEDIA_PATH=f"{BASE_PATH}/media"

PDV_FILE=f"{BASE_PATH}/pdv.csv"
MSG_FILE=f"{BASE_PATH}/messaggi.csv"
LOG_FILE=f"{BASE_PATH}/log.csv"

ADMIN_PASSWORD="GianAri2026"

LOGO_URL="https://raw.githubusercontent.com/GlucaTekmar/operativita-pdv/refs/heads/main/logo.png"

# ---------------------------------------------------
# STORAGE INIT
# ---------------------------------------------------

def ensure_storage():

    os.makedirs(BASE_PATH,exist_ok=True)
    os.makedirs(MEDIA_PATH,exist_ok=True)

    if not os.path.exists(PDV_FILE):
        pd.DataFrame(columns=["pdv_id","pdv_nome"]).to_csv(PDV_FILE,index=False)

    if not os.path.exists(MSG_FILE):
        pd.DataFrame(columns=[
            "msg_id","titolo","msg","pdv_ids","file","data_inizio","data_fine","stato"
        ]).to_csv(MSG_FILE,index=False)

    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=[
            "data","pdv_id","pdv_nome","msg_id","apertura_timestamp","lettura_timestamp"
        ]).to_csv(LOG_FILE,index=False)

# ---------------------------------------------------
# CSV SAFE IO
# ---------------------------------------------------

def read_csv(path):

    lock=FileLock(path+".lock")

    with lock:
        if os.path.exists(path):
            return pd.read_csv(path)
        else:
            return pd.DataFrame()

def write_csv(df,path):

    lock=FileLock(path+".lock")
    tmp=path+".tmp"

    with lock:
        df.to_csv(tmp,index=False)
        os.replace(tmp,path)

# ---------------------------------------------------
# DATA
# ---------------------------------------------------

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

# ---------------------------------------------------
# LOG SYSTEM
# ---------------------------------------------------

def log_open(pdv_id,pdv_nome,msg_id):

    logs=load_logs()

    today=str(datetime.date.today())

    exists=logs[
        (logs["data"]==today)&
        (logs["pdv_id"]==pdv_id)&
        (logs["msg_id"]==msg_id)
    ]

    if exists.empty:

        new=pd.DataFrame([{
            "data":today,
            "pdv_id":pdv_id,
            "pdv_nome":pdv_nome,
            "msg_id":msg_id,
            "apertura_timestamp":datetime.datetime.now(),
            "lettura_timestamp":""
        }])

        logs=pd.concat([logs,new],ignore_index=True)

        save_logs(logs)

def log_read(pdv_id,msg_id):

    logs=load_logs()

    today=str(datetime.date.today())

    idx=logs[
        (logs["data"]==today)&
        (logs["pdv_id"]==pdv_id)&
        (logs["msg_id"]==msg_id)
    ].index

    if len(idx)>0:
        logs.loc[idx[0],"lettura_timestamp"]=datetime.datetime.now()
        save_logs(logs)

# ---------------------------------------------------
# FILTER MSG
# ---------------------------------------------------

def get_active_messages(pdv_id):

    msgs=load_messages()

    if msgs.empty:
        return pd.DataFrame()

    today=datetime.date.today()

    def valid(r):

        ids=str(r["pdv_ids"]).split("|")

        if str(pdv_id) not in ids:
            return False

        if r["stato"]!="attivo":
            return False

        start=datetime.date.fromisoformat(r["data_inizio"])
        end=datetime.date.fromisoformat(r["data_fine"])

        return start<=today<=end

    return msgs[msgs.apply(valid,axis=1)]

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

def header(title):

    st.markdown("""
    <style>

    .main {background:#c8102e}

    .circular{
        background:white;
        padding:30px;
        margin-bottom:40px;
        border-radius:8px;
        box-shadow:0 4px 10px rgba(0,0,0,0.25)
    }

    .linea{
        border-top:4px solid #c8102e;
        margin:20px 0
    }

    </style>
    """,unsafe_allow_html=True)

    st.image(LOGO_URL,width=180)

    st.title(title)

# ---------------------------------------------------
# EMPLOYEE PAGE 1
# ---------------------------------------------------

def page_employee_1():

    header("SELEZIONA PDV")

    pdv=load_pdv()

    names=pdv["pdv_nome"].tolist()

    def search(term):

        return [n for n in names if term.lower() in n.lower()]

    selected=st_searchbox(search,key="pdvbox")

    if selected:

        st.session_state["pdv_nome"]=selected
        st.session_state["pdv_id"]=pdv[pdv["pdv_nome"]==selected]["pdv_id"].iloc[0]

    col1,col2=st.columns(2)

    if col1.button("ENTRA"):

        if "pdv_id" in st.session_state:

            st.session_state["page"]="emp2"
            st.rerun()

    if col2.button("HOME"):

        st.markdown("[HOME](https://eu.jotform.com/app/253605296903360)")

# ---------------------------------------------------
# RENDER CIRCOLARE
# ---------------------------------------------------

def render_msg(i,row,pdv_nome):

    st.markdown(f"### MESSAGGIO N.{i}")
    st.markdown(f"**{pdv_nome}**")

    st.markdown('<div class="circular">',unsafe_allow_html=True)

    col1,col2=st.columns([3,1])

    col1.image(LOGO_URL,width=120)

    col2.write(datetime.date.today())

    st.markdown('<div class="linea"></div>',unsafe_allow_html=True)

    st.markdown(f"## {row['titolo']}")

    st.markdown(row["msg"],unsafe_allow_html=True)

    if pd.notna(row["file"]) and row["file"]!="":

        path=f"{MEDIA_PATH}/{row['file']}"

        if os.path.exists(path):

            if path.lower().endswith(".pdf"):

                with open(path,"rb") as f:

                    b64=base64.b64encode(f.read()).decode()

                    href=f'<a href="data:application/pdf;base64,{b64}" target="_blank">Apri PDF</a>'

                    st.markdown(href,unsafe_allow_html=True)

            else:

                st.image(path)

    st.markdown('</div>',unsafe_allow_html=True)

# ---------------------------------------------------
# EMPLOYEE PAGE 2
# ---------------------------------------------------

def page_employee_2():

    header("INDICAZIONI OPERATIVE")

    pdv_id=st.session_state["pdv_id"]
    pdv_nome=st.session_state["pdv_nome"]

    msgs=get_active_messages(pdv_id)

    if msgs.empty:

        st.markdown('<div class="circular">',unsafe_allow_html=True)

        st.markdown("## NESSUNA ATTIVITÀ")

        st.write("""
QUESTA MATTINA SUL PDV NON SONO PREVISTE PROMO - ATTIVITÀ PARTICOLARI.

BUON LAVORO
""")

        st.markdown('</div>',unsafe_allow_html=True)

        log_open(pdv_id,pdv_nome,"GENERICO")

    else:

        for i,row in enumerate(msgs.to_dict("records"),1):

            render_msg(i,row,pdv_nome)

            log_open(pdv_id,pdv_nome,row["msg_id"])

    if st.checkbox("Spunta la CONFERMA DI LETTURA"):

        if not msgs.empty:

            for m in msgs["msg_id"]:
                log_read(pdv_id,m)

    col1,col2=st.columns(2)

    if col1.button("TORNA ALLA LISTA PDV"):

        st.session_state["page"]="emp1"
        st.rerun()

    if col2.button("HOME"):

        st.markdown("[HOME](https://eu.jotform.com/app/253605296903360)")

# ---------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------

def admin_login():

    header("ADMIN")

    pwd=st.text_input("Password",type="password")

    if st.button("Accedi"):

        if pwd==ADMIN_PASSWORD:

            st.session_state["admin"]=True
            st.session_state["page"]="admin1"

            st.rerun()

# ---------------------------------------------------
# ADMIN PAGE 1
# ---------------------------------------------------

def admin_page1():

    st.title("AMMINISTRAZIONE")

    col1,col2,col3=st.columns(3)

    if col1.button("AGGIORNA"):
        st.rerun()

    if col2.button("REPORT"):
        st.session_state["page"]="admin2"
        st.rerun()

    if col3.button("LOGOUT"):
        st.session_state.clear()
        st.rerun()

    st.subheader("LISTA PDV")

    pdv=load_pdv()

    text=st.text_area("Lista PDV",value=pdv.to_csv(index=False),height=200)

    if st.button("SALVA LISTA"):

        from io import StringIO

        df=pd.read_csv(StringIO(text))

        save_pdv(df)

    if st.button("PULISCI LISTA"):

        save_pdv(pd.DataFrame(columns=["pdv_id","pdv_nome"]))

    st.subheader("NUOVO MESSAGGIO")

    titolo=st.text_input("Titolo")

    msg=st_quill(placeholder="Testo messaggio")

    pdv_ids=st.text_area("ID PDV destinatari")

    data_i=st.date_input("Data inizio")
    data_f=st.date_input("Data fine")

    file=st.file_uploader("PDF o immagine")

    if st.button("SALVA MESSAGGIO"):

        msgs=load_messages()

        msg_id=str(uuid.uuid4())

        fname=""

        if file:

            fname=f"{msg_id}_{file.name}"

            with open(f"{MEDIA_PATH}/{fname}","wb") as f:
                f.write(file.getbuffer())

        ids="|".join([x.strip() for x in pdv_ids.splitlines() if x.strip()!=""])

        new=pd.DataFrame([{
            "msg_id":msg_id,
            "titolo":titolo,
            "msg":msg,
            "pdv_ids":ids,
            "file":fname,
            "data_inizio":data_i,
            "data_fine":data_f,
            "stato":"attivo"
        }])

        msgs=pd.concat([msgs,new],ignore_index=True)

        save_messages(msgs)

# ---------------------------------------------------
# ADMIN PAGE 2
# ---------------------------------------------------

def admin_page2():

    st.title("REPORT")

    msgs=load_messages()
    logs=load_logs()

    st.subheader("MESSAGGI")

    st.dataframe(msgs)

    st.download_button("Scarica CSV",msgs.to_csv(index=False),"messaggi.csv")

    st.download_button("Scarica Excel",msgs.to_excel(index=False),"messaggi.xlsx")

    st.subheader("LOG")

    st.dataframe(logs)

    st.download_button("Scarica CSV",logs.to_csv(index=False),"log.csv")

    st.download_button("Scarica Excel",logs.to_excel(index=False),"log.xlsx")

    col1,col2=st.columns(2)

    if col1.button("MESSAGGI"):

        st.session_state["page"]="admin1"
        st.rerun()

    if col2.button("LOGOUT"):

        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def main():

    ensure_storage()

    if "page" not in st.session_state:
        st.session_state["page"]="emp1"

    params=st.query_params

    if "admin" in params and "admin" not in st.session_state:
        admin_login()
        return

    if st.session_state.get("admin"):

        if st.session_state["page"]=="admin1":
            admin_page1()

        else:
            admin_page2()

    else:

        if st.session_state["page"]=="emp1":
            page_employee_1()

        else:
            page_employee_2()

if __name__=="__main__":
    main()
