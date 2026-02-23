import streamlit as st
import pandas as pd
from datetime import datetime
import os
from io import BytesIO
from streamlit_quill import st_quill

st.set_page_config(layout="wide")

# =========================================================
# CONFIG PERSISTENZA (Render Persistent Disk)
# =========================================================
DATA_DIR = "/data"
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

LOG_FILE = os.path.join(DATA_DIR, "log.csv")
MSG_FILE = os.path.join(DATA_DIR, "messaggi.csv")
PDV_FILE = os.path.join(DATA_DIR, "pdv.csv")

# Imposta qui la tua home Jotform (se vuoi rimandare lì)
HOME_URL = "https://www.jotform.com/"


# =========================================================
# 🎨 CSS DASHBOARD ADMIN (INVARIATO + FIX LEGGIBILITÀ UPLOADER)
# =========================================================
CSS_ADMIN = """
<style>

/* ===== PANNELLO "PRO" (solo look, zero logica) ===== */

/* Sfondo admin grigio visibile */
.stApp { background-color: #E6E6E6 !important; }

/* Contenitore pagina più "card" */
.block-container {
  padding-top: 1.5rem !important;
  padding-bottom: 2rem !important;
}

/* Sezioni: bordi e box (renderizza bene con i separatori) */
hr { border: 1px solid #000 !important; }

/* Input più leggibili */
input, textarea, select {
  background: #fff !important;
  color: #000 !important;
  border: 2px solid #000 !important;
  border-radius: 8px !important;
}

/* Label nere e bold */
label { color:#000 !important; font-weight:800 !important; }

/* Pulsanti rosso aziendale */
.stButton > button, .stDownloadButton > button {
  background: #D50000 !important;
  color: #fff !important;
  border: 1px solid #000 !important;
  font-weight: 800 !important;
  border-radius: 10px !important;
  padding: 10px 16px !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  background: #B30000 !important;
}

/* Messaggi di successo: testo rosso leggibile su azzurro */
div[data-testid="stSuccess"] {
  background-color: #E3F2FD !important;
  color: #D50000 !important;
  font-weight: 800 !important;
  border: 2px solid #000 !important;
}
div[data-testid="stSuccess"] p { color: #D50000 !important; }
div[data-testid="stSuccess"] svg { fill: #D50000 !important; }

/* ===== MESSAGGI OPERAZIONE — TESTO ROSSO ===== */
div[data-testid="stAlert"] { border: 2px solid #000 !important; }
div[data-testid="stAlert"] p { color: #D50000 !important; font-weight: 800 !important; }
div[data-testid="stAlert"] svg { fill: #D50000 !important; }

/* ===== TITOLI/TESTI ADMIN LEGGIBILI ===== */
h1, h2, h3, .stMarkdown, .stTextLabel, label {
  color: #000 !important;
  font-weight: 800 !important;
}

/* FIX: nome file/uploader più leggibile */
div[data-testid="stFileUploader"] * {
  color: #000 !important;
}
div[data-testid="stFileUploader"] small,
div[data-testid="stFileUploader"] span,
div[data-testid="stFileUploader"] p {
  color: #D50000 !important;
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


def safe_strip_lines(text: str):
    return [x.strip() for x in (text or "").splitlines() if x.strip()]


def msg_short_name(html_msg: str, maxlen: int = 60) -> str:
    # Nome "umano" senza cambiare struttura dati: usiamo un estratto
    s = (html_msg or "").replace("\n", " ").strip()
    return (s[:maxlen] + "…") if len(s) > maxlen else s


def msg_status_for_logrow(log_msg: str, msg_df: pd.DataFrame) -> str:
    # Stato per log: attivo/scaduto/nm
    if log_msg in ("PRESENZA", "GENERICO"):
        return "nm"
    if msg_df.empty:
        return "nm"
    m = msg_df[msg_df["msg"] == log_msg]
    if m.empty:
        return "nm"
    r = m.iloc[0]
    try:
        di = datetime.strptime(r["inizio"], "%d-%m-%Y")
        df = datetime.strptime(r["fine"], "%d-%m-%Y")
        oggi = datetime.now()
        return "attivo" if di <= oggi <= df else "scaduto"
    except Exception:
        return "nm"


# =========================================================
# ADMIN
# =========================================================
def admin():
    st.markdown(CSS_ADMIN, unsafe_allow_html=True)

    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image("logo.png", width=260)

    st.title("DASHBOARD ADMIN")

    if st.text_input("Password", type="password") != "GianAri2026":
        st.warning("Inserire password admin")
        return

    # Tasto aggiorna pagina senza logout
    cA, cB, cC = st.columns([1, 1, 3])
    with cA:
        if st.button("AGGIORNA"):
            st.rerun()

    st.markdown("---")

    # ===== PDV =====
    st.header("IMPORT LISTA PDV")

    # Precompila textarea leggendo il file PDV (persistenza percepita corretta)
    pdv_df_existing = load_csv(PDV_FILE, ["ID", "PDV"])
    prefill = ""
    if not pdv_df_existing.empty:
        prefill = "\n".join([f"{r['ID']};{r['PDV']}" for _, r in pdv_df_existing.iterrows()])

    pdv_text = st.text_area("", value=prefill, height=140)

    c1, c2 = st.columns([1, 1])

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
            save_csv(pd.DataFrame(columns=["ID", "PDV"]), PDV_FILE)
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
        df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])

        filename = ""
        if uploaded:
            # Salva sempre su /data/uploads (persistente)
            filename = uploaded.name
            dest_path = os.path.join(UPLOAD_DIR, filename)
            with open(dest_path, "wb") as f:
                f.write(uploaded.getbuffer())

        new = pd.DataFrame([[
            msg,
            data_inizio.strftime("%d-%m-%Y"),
            data_fine.strftime("%d-%m-%Y"),
            "\n".join(safe_strip_lines(pdv_ids)),
            filename
        ]], columns=df.columns)

        save_csv(pd.concat([df, new], ignore_index=True), MSG_FILE)
        st.success("Messaggio salvato")

    st.markdown("---")

    # ===== STORICO MESSAGGI =====
    st.header("STORICO MESSAGGI (PERMANENTE)")

    msg_df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])
    # View più leggibile senza cambiare CSV
    msg_view = msg_df.copy()
    if not msg_view.empty:
        msg_view.insert(0, "nome", msg_view["msg"].apply(lambda x: msg_short_name(x)))
    st.dataframe(msg_view, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("SCARICA CSV", msg_df.to_csv(index=False), "messaggi.csv")
    with c2:
        st.download_button("SCARICA EXCEL", excel_bytes(msg_df), "messaggi.xlsx")
    with c3:
        if st.button("PULISCI MESSAGGI"):
            save_csv(msg_df.iloc[0:0], MSG_FILE)
            st.success("Messaggi puliti")
            st.rerun()

    st.markdown("---")

    # ===== REPORT =====
    st.header("REPORT LETTURE")

    log = load_csv(LOG_FILE, ["data", "pdv", "msg"])
    msg_df_for_status = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])

    # View log con colonne aggiunte (senza modificare log.csv)
    log_view = log.copy()
    if not log_view.empty:
        log_view["Nome Messaggio"] = log_view["msg"].apply(
            lambda m: "Generico" if m in ("PRESENZA", "GENERICO") else msg_short_name(m)
        )
        log_view["Stato"] = log_view["msg"].apply(lambda m: msg_status_for_logrow(m, msg_df_for_status))

    st.dataframe(log_view, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.download_button("SCARICA CSV", log.to_csv(index=False), "report.csv")
    with c2:
        st.download_button("SCARICA EXCEL", excel_bytes(log), "report.xlsx")
    with c3:
        if st.button("PULISCI LOG"):
            save_csv(log.iloc[0:0], LOG_FILE)
            st.success("Log pulito")
            st.rerun()
    with c4:
        if st.button("AGGIORNA LOG"):
            st.rerun()


# =========================================================
# DIPENDENTI (INVARIATA + FIX ID + MESSAGGIO GENERICO + HOME)
# =========================================================
def dipendenti():
    st.markdown("""
    <style>
    .stApp {background:#c40000; color:white;}
    label, p, h1, h2, h3 {color:white !important;}
    </style>
    """, unsafe_allow_html=True)

    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image("logo.png", width=240)

    st.markdown("<h1 style='text-align:center;'>INDICAZIONI OPERATIVE</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;'>SELEZIONA IL TUO PDV</h3>", unsafe_allow_html=True)

    pdv_df = load_csv(PDV_FILE, ["ID", "PDV"])
    if pdv_df.empty:
        st.warning("Archivio PDV vuoto")
        return

    scelta = st.selectbox("", pdv_df["PDV"], index=None, placeholder="Digita la città...")
    st.markdown(
        "<p style='text-align:center;'><b>Digita le prime lettere della Città per trovare il tuo PDV</b></p>",
        unsafe_allow_html=True
    )

    if not scelta:
        return

    pdv_id = str(pdv_df.loc[pdv_df["PDV"] == scelta, "ID"].values[0]).strip()

    msg_df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])
    oggi = datetime.now()

    mostrati = []

    for _, r in msg_df.iterrows():
        ids = [x.strip() for x in (r["pdv_ids"] or "").splitlines() if x.strip()]
        if pdv_id in ids:
            try:
                di = datetime.strptime(r["inizio"], "%d-%m-%Y")
                df = datetime.strptime(r["fine"], "%d-%m-%Y")
                if di <= oggi <= df:
                    mostrati.append(r)
            except Exception:
                pass

    log_df = load_csv(LOG_FILE, ["data", "pdv", "msg"])

    # HOME (sempre disponibile)
    st.markdown(
        f"<div style='text-align:center; margin: 10px 0;'>"
        f"<a href='{HOME_URL}' target='_self' style='color:white; font-weight:800; text-decoration:underline;'>HOME</a>"
        f"</div>",
        unsafe_allow_html=True
    )

    if not mostrati:
        # Messaggio generico richiesto
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
            new = pd.DataFrame([[now_str(), scelta, "PRESENZA"]], columns=log_df.columns)
            save_csv(pd.concat([log_df, new], ignore_index=True), LOG_FILE)
            st.success("Presenza registrata")
        return

    for r in mostrati:
        st.markdown("---")
        st.markdown(r["msg"], unsafe_allow_html=True)

        if r["file"]:
            file_path = os.path.join(UPLOAD_DIR, r["file"])
            if os.path.exists(file_path):
                if r["file"].lower().endswith(".pdf"):
                    with open(file_path, "rb") as f:
                        st.download_button("Scarica allegato", f.read(), r["file"])
                else:
                    st.image(file_path, width=350)

        lettura = st.checkbox("Spunta di PRESA VISIONE", key=r["msg"] + "l")
        presenza = st.checkbox("Spunta CONFERMA DI PRESENZA", key=r["msg"] + "p")

        if lettura and presenza:
            gia = ((log_df["pdv"] == scelta) & (log_df["msg"] == r["msg"])).any()
            if not gia:
                new = pd.DataFrame([[now_str(), scelta, r["msg"]]], columns=log_df.columns)
                save_csv(pd.concat([log_df, new], ignore_index=True), LOG_FILE)
                st.success("Registrato")


# =========================================================
# ROUTER
# =========================================================
if st.query_params.get("admin") == "1":
    admin()
else:
    dipendenti()
