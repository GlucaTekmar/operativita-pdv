# APP.PY DEFINITIVO

import streamlit as st
import pandas as pd
import os
import uuid
import time
from datetime import datetime, date
from pathlib import Path
from streamlit_quill import st_quill

ADMIN_PASSWORD = "GianAri2026"
HOME_URL = "https://eu.jotform.com/app/253605296903360"

BASE_DIR = Path("/var/data")

PDV_FILE = BASE_DIR / "pdv.csv"
MSG_FILE = BASE_DIR / "messaggi.csv"
LOG_FILE = BASE_DIR / "log.csv"

MEDIA_DIR = BASE_DIR / "media"
LOCK_FILE = BASE_DIR / "log.lock"

MEDIA_DIR.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="Operatività PDV", layout="wide")

# --------------------------
# CSS + SFONDO
# --------------------------

st.markdown("""
<style>

.stApp{
background-color:#b30000;
}

.card{
background:white;
border-radius:14px;
padding:22px;
box-shadow:0 5px 15px rgba(0,0,0,0.25);
margin-bottom:25px;
max-width:900px;
width:100%;
}

.header{
display:flex;
justify-content:space-between;
align-items:center;
font-weight:bold;
}

.sep{
border-top:3px solid #b30000;
margin:14px 0;
}

.title{
font-size:22px;
font-weight:bold;
text-align:center;
}

.body{
font-size:18px;
margin-top:12px;
}

</style>
""", unsafe_allow_html=True)

# --------------------------
# FILE SAFE FUNCTIONS
# --------------------------

def backup_file(path):
    bak = path.with_suffix(".bak")
    if path.exists():
        try:
            import shutil
            shutil.copy(path, bak)
        except:
            pass

def ensure_csv(path, columns):

    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path,index=False)
        return

    try:
        df = pd.read_csv(path)
        if df.empty and len(columns)>0:
            pd.DataFrame(columns=columns).to_csv(path,index=False)
    except:
        bak = path.with_suffix(".bak")
        if bak.exists():
            import shutil
            shutil.copy(bak,path)
        else:
            pd.DataFrame(columns=columns).to_csv(path,index=False)

# --------------------------
# INIT FILES
# --------------------------

ensure_csv(PDV_FILE,["pdv_id","pdv_nome"])

ensure_csv(MSG_FILE,[
"msg_id","titolo","msg","pdv_ids","file","data_inizio","data_fine","stato"
])

ensure_csv(LOG_FILE,[
"data","pdv_id","pdv_nome","msg_id","apertura_timestamp","lettura_timestamp"
])

# --------------------------
# CSV READ WRITE
# --------------------------

def read_csv(path):
    try:
        return pd.read_csv(path)
    except:
        return pd.DataFrame()

def write_csv(path, df):
    backup_file(path)
    df.to_csv(path,index=False)

# --------------------------
# LOCK
# --------------------------

def acquire_lock():
    while LOCK_FILE.exists():
        time.sleep(0.1)
    open(LOCK_FILE,"w").close()

def release_lock():
    if LOCK_FILE.exists():
        os.remove(LOCK_FILE)

# --------------------------
# LOG SYSTEM
# --------------------------

def log_open(pdv_id,pdv_nome,msg_id):

    today = date.today().isoformat()

    acquire_lock()

    df = read_csv(LOG_FILE)

    existing = df[
        (df["data"]==today) &
        (df["pdv_id"]==pdv_id) &
        (df["msg_id"]==msg_id)
    ]

    if existing.empty:

        new = {
            "data":today,
            "pdv_id":pdv_id,
            "pdv_nome":pdv_nome,
            "msg_id":msg_id,
            "apertura_timestamp":datetime.now().strftime("%H:%M:%S"),
            "lettura_timestamp":""
        }

        df = pd.concat([df,pd.DataFrame([new])],ignore_index=True)
        write_csv(LOG_FILE,df)

    release_lock()

def log_read(pdv_id,msg_id):

    today = date.today().isoformat()

    acquire_lock()

    df = read_csv(LOG_FILE)

    idx = df[
        (df["data"]==today) &
        (df["pdv_id"]==pdv_id) &
        (df["msg_id"]==msg_id)
    ].index

    if len(idx)>0:

        if df.loc[idx[0],"lettura_timestamp"]=="":
            df.loc[idx[0],"lettura_timestamp"] = datetime.now().strftime("%H:%M:%S")
            write_csv(LOG_FILE,df)

    release_lock()

# --------------------------
# SIDEBAR
# --------------------------

st.sidebar.markdown("### Modalità")

mode = st.sidebar.radio("",["DIPENDENTE","ADMIN"])

st.markdown(f"<a href='{HOME_URL}' target='_self'><button>HOME</button></a>", unsafe_allow_html=True)

pdv_df = read_csv(PDV_FILE)
msg_df = read_csv(MSG_FILE)

# --------------------------
# ADMIN
# --------------------------

if mode=="ADMIN":

    pw = st.sidebar.text_input("Password",type="password")

    if pw!=ADMIN_PASSWORD:
        st.stop()

    admin_page = st.sidebar.radio("Sezione",["MESSAGGI","REPORT"])

    colA,colB = st.columns(2)

    if colA.button("AGGIORNA"):
        st.rerun()

    if colB.button("LOGOUT"):
        st.session_state.clear()
        st.rerun()

    if admin_page=="MESSAGGI":

        st.title("Gestione Messaggi")

        st.subheader("Lista Punti Vendita")

        current_list = "\n".join(pdv_df["pdv_id"].astype(str)+" , "+pdv_df["pdv_nome"].astype(str))

        txt = st.text_area("LISTA PDV (id,nome)",value=current_list,height=200)

        c1,c2 = st.columns(2)

        if c1.button("SALVA"):

            rows=[]

            for r in txt.split("\n"):
                if "," in r:
                    pid,name=r.split(",",1)
                    rows.append({
                        "pdv_id":pid.strip(),
                        "pdv_nome":name.strip()
                    })

            write_csv(PDV_FILE,pd.DataFrame(rows))
            st.success("Lista salvata")
            st.rerun()

        if c2.button("PULISCI LISTA"):
            pd.DataFrame(columns=["pdv_id","pdv_nome"]).to_csv(PDV_FILE,index=False)
            st.success("Lista pulita")
            st.rerun()

        st.divider()

        st.subheader("Nuovo Messaggio")

        titolo = st.text_input("Titolo")

        msg = st_quill()

        pdv_target = st.text_area("PDV destinatari (id uno per riga)")

        c1,c2 = st.columns(2)

        data_inizio = c1.date_input("Data inizio",value=date.today())
        data_fine = c2.date_input("Data fine",value=date.today())

        file = st.file_uploader("Allegato",type=["png","jpg","jpeg","pdf"])

        if st.button("INVIA MESSAGGIO"):

            msg_id=str(uuid.uuid4())

            fname=""

            if file:

                ext=file.name.split(".")[-1]
                fname=f"{msg_id}.{ext}"

                with open(MEDIA_DIR/fname,"wb") as f:
                    f.write(file.getbuffer())

            new={
                "msg_id":msg_id,
                "titolo":titolo,
                "msg":msg,
                "pdv_ids":pdv_target.replace("\n","|"),
                "file":fname,
                "data_inizio":data_inizio,
                "data_fine":data_fine,
                "stato":"ATTIVO"
            }

            msg_df=pd.concat([msg_df,pd.DataFrame([new])],ignore_index=True)
            write_csv(MSG_FILE,msg_df)

            st.success("Messaggio inviato")
            st.rerun()

        st.divider()

        st.subheader("MESSAGGI SALVATI")

        st.dataframe(read_csv(MSG_FILE),use_container_width=True)

    if admin_page=="REPORT":

        st.title("Report Letture")

        st.dataframe(read_csv(LOG_FILE),use_container_width=True)

# --------------------------
# DIPENDENTE
# --------------------------

else:

    st.title("Seleziona PDV")

    if pdv_df.empty:
        st.warning("Nessun PDV disponibile")
        st.stop()

    options = pdv_df["pdv_id"].astype(str)+" - "+pdv_df["pdv_nome"]

    sel = st.selectbox("PDV",options)

    if st.button("ENTRA"):

        pid = sel.split(" - ")[0]
        st.session_state["pdv"]=pid
        st.rerun()

    if "pdv" in st.session_state:

        pid = st.session_state["pdv"]
        pdv_nome = pdv_df[pdv_df["pdv_id"].astype(str)==pid]["pdv_nome"].values[0]

        today=date.today()

        msgs = msg_df[
            (msg_df["pdv_ids"].str.contains(pid,na=False)) &
            (pd.to_datetime(msg_df["data_inizio"]).dt.date<=today) &
            (pd.to_datetime(msg_df["data_fine"]).dt.date>=today)
        ]

        if msgs.empty:

            st.markdown(f"""
            <div class='card'>
            <div class='header'>
            <div>GD MEDIA</div>
            <div>{today}</div>
            </div>

            <div class='sep'></div>

            <div class='title'>NESSUNA ATTIVITÀ</div>

            <div class='sep'></div>

            <div class='body'>
            OGGI SU QUESTO PDV NON SONO PREVISTE PROMO e/o ATTIVITÀ PARTICOLARI.<br><br>
            BUON LAVORO.
            </div>
            </div>
            """,unsafe_allow_html=True)

        for _,m in msgs.iterrows():

            log_open(pid,pdv_nome,m["msg_id"])

            st.markdown(f"""
            <div class='card'>
            <div class='header'>
            <div>GD MEDIA</div>
            <div>{today}</div>
            </div>

            <div class='sep'></div>

            <div class='title'>{m["titolo"]}</div>

            <div class='sep'></div>

            <div class='body'>{m["msg"]}</div>
            </div>
            """,unsafe_allow_html=True)

            if m["file"]:

                path = MEDIA_DIR/m["file"]

                if path.exists():

                    if m["file"].lower().endswith(".pdf"):
                        with open(path,"rb") as f:
                            st.download_button("Apri PDF",f.read(),file_name=m["file"])
                    else:
                        st.image(str(path))

            if st.checkbox("Confermo lettura",key=m["msg_id"]):

                log_read(pid,m["msg_id"])

