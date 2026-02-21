import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ================= CONFIG =================
st.set_page_config(page_title="Operatività PDV", layout="centered")

ADMIN_KEY = "admin123"
ADMIN_PASSWORD = "GianAri2026"
HOME_URL = "https://eu.jotform.com/it/app/build/253605296903360"

PDV_FILE = "pdv.csv"
MSG_FILE = "messaggi.csv"
LOG_FILE = "log.csv"

# ================= STILE =================
st.markdown("""
<style>
.stApp {background:#E30613;}
h1,h2,h3,label,p {color:white !important;}
.stButton button {background:#111;color:white;font-weight:bold;border-radius:10px;}
</style>
""", unsafe_allow_html=True)

# ================= UTILITY =================
def load_csv(file, cols):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame(columns=cols)

def save_csv(df, file):
    df.to_csv(file, index=False)

# ================= ROUTING =================
params = st.query_params
ADMIN_MODE = params.get("admin") == "1" and params.get("key") == ADMIN_KEY

# =========================================================
# ================= AREA DIPENDENTI =======================
# =========================================================
def dipendenti():

    st.title("INDICAZIONI OPERATIVE")

    pdv_df = load_csv(PDV_FILE, ["ID","Nome"])

    if pdv_df.empty:
        st.error("Archivio PDV vuoto")
        st.stop()

    scelta = st.selectbox(
        "Seleziona PDV",
        pdv_df["ID"] + " — " + pdv_df["Nome"]
    )

    pdv_id = scelta.split(" — ")[0]

    msg_df = load_csv(MSG_FILE,
        ["Titolo","Testo","PDV","Inizio","Fine","Img","PDF"]
    )

    oggi = datetime.now().date()

    validi = msg_df[
        (msg_df["PDV"].str.contains(pdv_id)) &
        (pd.to_datetime(msg_df["Inizio"]).dt.date <= oggi) &
        (pd.to_datetime(msg_df["Fine"]).dt.date >= oggi)
    ]

    # ======== SE C'È MESSAGGIO =========
    if not validi.empty:

        r = validi.iloc[0]

        st.markdown(f"""
        <div style="background:white;color:black;padding:15px;border-radius:12px;">
        <h3>{r['Titolo']}</h3>
        <p>{r['Testo']}</p>
        </div>
        """, unsafe_allow_html=True)

        if r["Img"]:
            st.image(r["Img"])

        if r["PDF"]:
            st.link_button("Apri PDF", r["PDF"])

        st.markdown("### Conferma")

        lettura = st.checkbox("CONFERMA LETTURA")
        presenza = st.checkbox("CONFERMA PRESENZA")

        if st.button("INVIA"):
            if not (lettura and presenza):
                st.error("Devi confermare entrambi")
            else:
                salva_log(pdv_id, r["Titolo"], True, True)
                st.success("Registrato")

    # ======== NESSUN MESSAGGIO =========
    else:

        st.markdown("""
        <div style="background:white;color:black;padding:15px;border-radius:12px;">
        Nessuna indicazione operativa per oggi.
        </div>
        """, unsafe_allow_html=True)

        presenza = st.checkbox("CONFERMA PRESENZA")

        if st.button("INVIA"):
            if not presenza:
                st.error("Devi confermare presenza")
            else:
                salva_log(pdv_id, "", False, True)
                st.success("Registrato")

    st.link_button("HOME", HOME_URL)

# =========================================================
# ================= AREA ADMIN =============================
# =========================================================
def admin():

    st.title("🔒 DASHBOARD ADMIN")

    if st.text_input("Password", type="password") != ADMIN_PASSWORD:
        st.stop()

    tab1, tab2, tab3 = st.tabs(
        ["PDV","Messaggi","Report Log"]
    )

    # ================= PDV =================
    with tab1:

        st.subheader("Importa elenco PDV")

        testo = st.text_area("Incolla elenco ID;Nome")

        if st.button("IMPORTA"):
            righe = [r.split(";") for r in testo.splitlines() if ";" in r]
            df = pd.DataFrame(righe, columns=["ID","Nome"])
            save_csv(df, PDV_FILE)
            st.success("Archivio aggiornato")

        df = load_csv(PDV_FILE, ["ID","Nome"])
        st.dataframe(df, use_container_width=True)

    # ================= MESSAGGI =================
    with tab2:

        titolo = st.text_input("Titolo")
        testo = st.text_area("Testo formattabile")
        pdv = st.text_input("ID PDV (separati da virgola)")
        inizio = st.date_input("Data inizio")
        fine = st.date_input("Data fine")

        img = st.file_uploader("Immagine")
        pdf = st.file_uploader("PDF")

        img_path = save_file(img)
        pdf_path = save_file(pdf)

        if st.button("SALVA MESSAGGIO"):

            df = load_csv(MSG_FILE,
                ["Titolo","Testo","PDV","Inizio","Fine","Img","PDF"]
            )

            df.loc[len(df)] = [
                titolo, testo, pdv, inizio, fine,
                img_path, pdf_path
            ]

            save_csv(df, MSG_FILE)
            st.success("Messaggio salvato")

    # ================= LOG =================
    with tab3:

        df = load_csv(LOG_FILE,
            ["Data_Ora","PDV","Messaggio","Lettura","Presenza"]
        )

        st.dataframe(df, use_container_width=True)

        st.download_button(
            "Scarica CSV",
            df.to_csv(index=False),
            "report.csv"
        )

        st.download_button(
            "Scarica Excel",
            df.to_excel(index=False),
            "report.xlsx"
        )

        if st.button("PULISCI LOG"):
            save_csv(df.iloc[0:0], LOG_FILE)
            st.success("Log pulito")

# =========================================================
# ================= SUPPORT ================================
# =========================================================
def salva_log(pdv, msg, lettura, presenza):

    df = load_csv(LOG_FILE,
        ["Data_Ora","PDV","Messaggio","Lettura","Presenza"]
    )

    df.loc[len(df)] = [
        datetime.now(),
        pdv,
        msg,
        "SI" if lettura else "NO",
        "SI" if presenza else "NO"
    ]

    save_csv(df, LOG_FILE)

def save_file(file):
    if file:
        path = f"upload_{file.name}"
        with open(path, "wb") as f:
            f.write(file.read())
        return path
    return ""

# =========================================================
# ================= MAIN ==================================
# =========================================================
# ===================== SWITCH PAGINE =====================

params = st.query_params

if "admingianari2026" in params:
    admin()
else:
    dipendenti()


