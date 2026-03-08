import streamlit as st
import pandas as pd
import os
import datetime
import uuid
from filelock import FileLock
from streamlit_searchbox import st_searchbox

st.markdown(""
<style>

.stApp {background-color:#c8102e;
}

[data-testid="stAppViewContainer"] {background-color:#c8102e;
}

[data-testid="stVerticalBlock"] {background-color:#c8102e;
}

[data-testid="stBlock"] {background-color:#c8102e;
}

</style> 
""", unsafe_allow_html=True)
                                  
BASE="/var/data"
MEDIA=f"{BASE}/media"

PDV_FILE=f"{BASE}/pdv.csv"
MSG_FILE=f"{BASE}/messaggi.csv"
LOG_FILE=f"{BASE}/log.csv"

LOGO="https://raw.githubusercontent.com/GlucaTekmar/operativita-pdv/refs/heads/main/logo.png"
ADMIN_PASSWORD="GianAri2026"


# ---------------------------------------------------
# STORAGE
# ---------------------------------------------------

def ensure_storage():

    os.makedirs(BASE,exist_ok=True)
    os.makedirs(MEDIA,exist_ok=True)

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


# ---------------------------------------------------
# DATA
# ---------------------------------------------------

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


# ---------------------------------------------------
# LOG
# ---------------------------------------------------

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
            "apertura_timestamp":datetime.datetime.now(),
            "lettura_timestamp":""
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

        logs.loc[idx[0],"lettura_timestamp"]=datetime.datetime.now()

        save_logs(logs)


# ---------------------------------------------------
# CSS
# ---------------------------------------------------

def css():

    st.markdown("""
    <style>

    .main {background:#c8102e}

    .a4 {
        background:white;
        max-width:700px;
        margin:auto;
        padding:40px;
        border-radius:6px;
        box-shadow:0 5px 15px rgba(0,0,0,0.25)
    }

    .linea {
        border-top:4px solid #c8102e;
        margin:20px 0
    }

    </style>
    """,unsafe_allow_html=True)


# ---------------------------------------------------
# EMPLOYEE PAGE 1
# ---------------------------------------------------

def employee_select():

    css()

    st.image(LOGO,width=200)

    st.title("SELEZIONA PDV")

    pdv=load_pdv()

    names=pdv["pdv_nome"].tolist()

    def search(term):
        return [n for n in names if term.lower() in n.lower()]

    selected=st_searchbox(search)

    if selected:

        st.session_state["pdv_nome"]=selected
        st.session_state["pdv_id"]=pdv[pdv.pdv_nome==selected].pdv_id.iloc[0]

    if st.button("ENTRA"):

        if "pdv_id" in st.session_state:
            st.session_state.page="emp2"
            st.rerun()

    st.markdown("[HOME](https://eu.jotform.com/app/253605296903360)")


# ---------------------------------------------------
# FILTER MSG
# ---------------------------------------------------

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


# ---------------------------------------------------
# EMPLOYEE PAGE 2
# ---------------------------------------------------

def employee_msgs():

    pdv_id = st.session_state["pdv_id"]
    pdv_nome = st.session_state["pdv_nome"]

    st.image(LOGO,width=180)
    st.title("INDICAZIONI OPERATIVE")

    msgs = active_msgs(pdv_id)

    col_left, col_center, col_right = st.columns([1,3,1])

    with col_center:

        if msgs.empty:

            container = st.container(border=True)

            with container:

                col_logo,col_data = st.columns([4,1])
                col_logo.image(LOGO,width=120)
                col_data.write(datetime.date.today())

                st.divider()

                st.subheader("NESSUNA ATTIVITÀ")

                st.markdown("""
QUESTA MATTINA SUL PDV NON SONO PREVISTE PROMO - ATTIVITÀ PARTICOLARI.

**BUON LAVORO**
""")

            log_open(pdv_id,pdv_nome,"GENERICO")

        else:

            for _,row in msgs.iterrows():

                container = st.container(border=True)

                with container:

                    col_logo,col_data = st.columns([4,1])
                    col_logo.image(LOGO,width=120)
                    col_data.write(datetime.date.today())

                    st.divider()

                    st.subheader(row["titolo"])

                    st.markdown(row["msg"])

                    if pd.notna(row["file"]) and row["file"] != "":

                        path = f"{MEDIA}/{row['file']}"

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

                log_open(pdv_id,pdv_nome,row["msg_id"])

    st.write("")

    if st.checkbox("Spunta la CONFERMA DI LETTURA"):

        if not msgs.empty:
            for m in msgs["msg_id"]:
                log_read(pdv_id,m)

    col1,col2 = st.columns(2)

    if col1.button("TORNA ALLA LISTA PDV"):

        st.session_state.page="emp1"
        st.rerun()

    if col2.button("HOME"):

        st.markdown("[HOME](https://eu.jotform.com/app/253605296903360)")

# ---------------------------------------------------
# ADMIN LOGIN
# ---------------------------------------------------

def admin_login():

    st.title("ADMIN")

    pwd=st.text_input("Password",type="password")

    if st.button("Accedi"):

        if pwd==ADMIN_PASSWORD:

            st.session_state.admin=True
            st.session_state.page="admin1"
            st.rerun()


# ---------------------------------------------------
# ADMIN PAGE
# ---------------------------------------------------

def admin_page():

    st.title("AMMINISTRAZIONE")

    col1,col2,col3=st.columns(3)

    if col1.button("AGGIORNA"):
        st.rerun()

    if col2.button("REPORT"):
        st.session_state.page="admin2"
        st.rerun()

    if col3.button("LOGOUT"):
        st.session_state.clear()
        st.rerun()

    st.subheader("LISTA PDV")

    pdv=load_pdv()

    txt=st.text_area("Incolla lista",pdv.to_csv(index=False),height=200)

    if st.button("SALVA LISTA"):

        from io import StringIO

        df=pd.read_csv(StringIO(txt))

        save_pdv(df)

    st.subheader("NUOVO MESSAGGIO")

    titolo=st.text_input("Titolo")

    msg=st.text_area("Messaggio (Markdown)")

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
            "data_fine":d2,
            "stato":"attivo"
        }])

        msgs=pd.concat([msgs,new],ignore_index=True)

        save_msgs(msgs)


# ---------------------------------------------------
# REPORT
# ---------------------------------------------------

def admin_report():

    st.title("REPORT")

    msgs=load_msgs()
    logs=load_logs()

    st.subheader("MESSAGGI")

    msgs["seleziona"]=False

    edited=st.data_editor(msgs)

    if st.button("ELIMINA SELEZIONATI"):

        new=edited[edited.seleziona==False]

        save_msgs(new.drop(columns=["seleziona"]))

    st.download_button("Scarica CSV",msgs.to_csv(index=False),"messaggi.csv")

    st.download_button("Scarica Excel",msgs.to_excel(index=False),"messaggi.xlsx")

    st.subheader("LOG")

    logs["seleziona"]=False

    edited=st.data_editor(logs)

    if st.button("ELIMINA LOG"):

        new=edited[edited.seleziona==False]

        save_logs(new.drop(columns=["seleziona"]))

    st.download_button("Scarica CSV",logs.to_csv(index=False),"log.csv")

    st.download_button("Scarica Excel",logs.to_excel(index=False),"log.xlsx")

    if st.button("TORNA ADMIN"):

        st.session_state.page="admin1"
        st.rerun()


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------

def main():

    ensure_storage()

    if "page" not in st.session_state:
        st.session_state.page="emp1"

    params=st.query_params

    if "admin" in params and "admin" not in st.session_state:

        admin_login()
        return

    if st.session_state.get("admin"):

        if st.session_state.page=="admin1":
            admin_page()

        else:
            admin_report()

    else:

        if st.session_state.page=="emp1":
            employee_select()

        else:
            employee_msgs()


if __name__=="__main__":
    main()



