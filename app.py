import streamlit as st
import pandas as pd
import os
import datetime
import uuid
from io import BytesIO
from filelock import FileLock

BASE="/var/data"
MEDIA=f"{BASE}/media"

PDV_FILE=f"{BASE}/pdv.csv"
MSG_FILE=f"{BASE}/messaggi.csv"
LOG_FILE=f"{BASE}/log.csv"

LOGO="https://raw.githubusercontent.com/GlucaTekmar/operativita-pdv/refs/heads/main/logo.png"
ADMIN_PASSWORD="GianAri2026"


# ---------------------------
# STORAGE
# ---------------------------

def ensure_storage():

    os.makedirs(BASE,exist_ok=True)
    os.makedirs(MEDIA,exist_ok=True)

    if not os.path.exists(PDV_FILE):
        pd.DataFrame(columns=["pdv_id","pdv_nome"]).to_csv(PDV_FILE,index=False)

    if not os.path.exists(MSG_FILE):
        pd.DataFrame(columns=[
            "msg_id","titolo","msg","pdv_ids","file","data_inizio","data_fine"
        ]).to_csv(MSG_FILE,index=False)

    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=[
            "data","pdv_id","pdv_nome","msg_id","apertura","lettura"
        ]).to_csv(LOG_FILE,index=False)


def read_csv(path):

    lock=FileLock(path+".lock")

    with lock:
        return pd.read_csv(path)


def write_csv(df,path):

    tmp=path+".tmp"
    lock=FileLock(path+".lock")

    with lock:
        df.to_csv(tmp,index=False)
        os.replace(tmp,path)


# ---------------------------
# LOAD
# ---------------------------

def load_pdv():
    return read_csv(PDV_FILE)

def load_msgs():
    return read_csv(MSG_FILE)

def load_logs():
    return read_csv(LOG_FILE)

def save_msgs(df):
    write_csv(df,MSG_FILE)

def save_logs(df):
    write_csv(df,LOG_FILE)

def save_pdv(df):
    write_csv(df,PDV_FILE)


# ---------------------------
# LOG
# ---------------------------

def log_open(pdv_id,pdv_nome,msg_id):

    logs=load_logs()

    today=str(datetime.date.today())

    exists=logs[
        (logs.data==today) &
        (logs.pdv_id==pdv_id) &
        (logs.msg_id==msg_id)
    ]

    if exists.empty:

        new=pd.DataFrame([{
            "data":today,
            "pdv_id":pdv_id,
            "pdv_nome":pdv_nome,
            "msg_id":msg_id,
            "apertura":datetime.datetime.now(),
            "lettura":""
        }])

        logs=pd.concat([logs,new],ignore_index=True)

        save_logs(logs)


def log_read(pdv_id,msg_id):

    logs=load_logs()

    today=str(datetime.date.today())

    idx=logs[
        (logs.data==today) &
        (logs.pdv_id==pdv_id) &
        (logs.msg_id==msg_id)
    ].index

    if len(idx)>0:

        logs.loc[idx[0],"lettura"]=datetime.datetime.now()

        save_logs(logs)


# ---------------------------
# CSS
# ---------------------------

st.markdown("""
<style>

.stApp {
background:#c8102e;
}

.circolare {
background:white;
padding:30px;
border-radius:8px;
margin:auto;
max-width:700px;
}

</style>
""",unsafe_allow_html=True)


# ---------------------------
# EMPLOYEE PAGE 1
# ---------------------------

def employee_select():

    st.image(LOGO,width=200)

    st.title("SELEZIONA PDV")

    pdv=load_pdv()

    names=pdv["pdv_nome"].tolist()

    selected=st.selectbox("PDV",names)

    if st.button("ENTRA"):

        st.session_state["pdv_nome"]=selected
        st.session_state["pdv_id"]=pdv[pdv.pdv_nome==selected].pdv_id.iloc[0]

        st.session_state.page="emp2"

        st.rerun()


# ---------------------------
# FILTRO MESSAGGI
# ---------------------------

def active_msgs(pdv_id):

    msgs=load_msgs()

    if msgs.empty:
        return msgs

    today=datetime.date.today()

    def valid(r):

        ids=str(r.pdv_ids).split("|")

        if str(pdv_id) not in ids:
            return False

        start=datetime.date.fromisoformat(str(r.data_inizio))
        end=datetime.date.fromisoformat(str(r.data_fine))

        return start<=today<=end

    return msgs[msgs.apply(valid,axis=1)]


# ---------------------------
# EMPLOYEE PAGE 2
# ---------------------------

def employee_msgs():

    pdv_id=st.session_state["pdv_id"]
    pdv_nome=st.session_state["pdv_nome"]

    st.image(LOGO,width=180)
    st.title("INDICAZIONI OPERATIVE")

    msgs=active_msgs(pdv_id)

    if msgs.empty:

        st.markdown('<div class="circolare">',unsafe_allow_html=True)

        st.subheader("NESSUNA ATTIVITÀ")

        st.markdown("**BUON LAVORO**")

        st.markdown("</div>",unsafe_allow_html=True)

        log_open(pdv_id,pdv_nome,"GENERICO")

    else:

        for _,row in msgs.iterrows():

            st.markdown('<div class="circolare">',unsafe_allow_html=True)

            st.subheader(row["titolo"])

            st.markdown(row["msg"])

            if pd.notna(row["file"]) and row["file"]!="":

                path=f"{MEDIA}/{row['file']}"

                if os.path.exists(path):

                    if path.lower().endswith(".pdf"):

                        with open(path,"rb") as f:

                            st.download_button(
                                "Apri PDF",
                                f,
                                file_name=row["file"]
                            )

                    else:

                        st.image(path)

            st.markdown("</div>",unsafe_allow_html=True)

            log_open(pdv_id,pdv_nome,row["msg_id"])

    if st.checkbox("Spunta la CONFERMA DI LETTURA"):

        for m in msgs["msg_id"]:
            log_read(pdv_id,m)


# ---------------------------
# ADMIN LOGIN
# ---------------------------

def admin_login():

    st.title("ADMIN")

    pwd=st.text_input("Password",type="password")

    if st.button("Accedi"):

        if pwd==ADMIN_PASSWORD:

            st.session_state.admin=True
            st.session_state.page="admin_msg"

            st.rerun()


# ---------------------------
# ADMIN MENU
# ---------------------------

def admin_menu():

    col1,col2,col3,col4=st.columns(4)

    if col1.button("MESSAGGI"):
        st.session_state.page="admin_msg"
        st.rerun()

    if col2.button("REPORT"):
        st.session_state.page="admin_rep"
        st.rerun()

    if col3.button("AGGIORNA"):
        st.rerun()

    if col4.button("LOGOUT"):
        st.session_state.clear()
        st.rerun()


# ---------------------------
# ADMIN MESSAGGI
# ---------------------------

def admin_messages():

    admin_menu()

    st.subheader("NUOVO MESSAGGIO")

    titolo=st.text_input("Titolo")

    msg=st.text_area("Messaggio (Markdown supportato)",height=200)

    pdv_ids=st.text_area("ID PDV destinatari")

    d1=st.date_input("Data inizio")
    d2=st.date_input("Data fine")

    file=st.file_uploader("PDF o immagine")

    if st.button("SALVA MESSAGGIO"):

        msgs=load_msgs()

        mid=str(uuid.uuid4())

        fname=""

        if file:

            fname=f"{mid}_{file.name}"

            with open(f"{MEDIA}/{fname}","wb") as f:
                f.write(file.getbuffer())

        ids="|".join([x.strip() for x in pdv_ids.splitlines() if x.strip()!=""])

        new=pd.DataFrame([{
            "msg_id":mid,
            "titolo":titolo,
            "msg":msg,
            "pdv_ids":ids,
            "file":fname,
            "data_inizio":d1,
            "data_fine":d2
        }])

        msgs=pd.concat([msgs,new],ignore_index=True)

        save_msgs(msgs)


# ---------------------------
# ADMIN REPORT
# ---------------------------

def admin_report():

    admin_menu()

    st.subheader("MESSAGGI")

    msgs=load_msgs()

    st.dataframe(msgs)

    st.download_button(
        "Scarica CSV",
        msgs.to_csv(index=False),
        "messaggi.csv"
    )

    buffer=BytesIO()
    msgs.to_excel(buffer,index=False)
    buffer.seek(0)

    st.download_button(
        "Scarica Excel",
        buffer,
        "messaggi.xlsx"
    )

    st.subheader("LOG")

    logs=load_logs()

    st.dataframe(logs)

    st.download_button(
        "Scarica CSV",
        logs.to_csv(index=False),
        "log.csv"
    )

    buffer=BytesIO()
    logs.to_excel(buffer,index=False)
    buffer.seek(0)

    st.download_button(
        "Scarica Excel",
        buffer,
        "log.xlsx"
    )


# ---------------------------
# MAIN
# ---------------------------

def main():

    ensure_storage()

    if "page" not in st.session_state:
        st.session_state.page="emp1"

    params=st.query_params

    if "admin" in params and "admin" not in st.session_state:

        admin_login()
        return

    if st.session_state.get("admin"):

        if st.session_state.page=="admin_msg":
            admin_messages()

        else:
            admin_report()

    else:

        if st.session_state.page=="emp1":
            employee_select()

        else:
            employee_msgs()


if __name__=="__main__":
    main()
