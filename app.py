import streamlit as st
import pandas as pd
from datetime import datetime
import os
from io import BytesIO
from streamlit_quill import st_quill
import re
import html
import base64
import textwrap
import streamlit.components.v1 as components

st.set_page_config(layout="wide")


# =========================================================
# 🔒 STORAGE PERSISTENTE RENDER — MOUNT: /var/dati
# =========================================================
DATA_DIR = "/var/dati"
UPLOAD_DIR = "/var/dati/uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

LOG_FILE = "/var/dati/log.csv"
MSG_FILE = "/var/dati/messaggi.csv"
PDV_FILE = "/var/dati/pdv.csv"

HOME_URL = "https://eu.jotform.com/it/app/build/253605296903360"


# =========================================================
# 🎨 CSS DASHBOARD ADMIN
# =========================================================
CSS_ADMIN = """
<style>
.stApp { background-color: #E6E6E6 !important; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
hr { border: 1px solid #000 !important; }
input, textarea, select {
  background: #fff !important;
  color: #D50000 !important;
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
.stButton > button:hover, .stDownloadButton > button:hover {
  background: #B30000 !important;
}

div[data-testid="stSuccess"] {
  background-color: #E3F2FD !important;
  color: #D50000 !important;
  font-weight: 800 !important;
  border: 2px solid #000 !important;
}
div[data-testid="stSuccess"] p,
div[data-testid="stSuccess"] span { color: #D50000 !important; }

div[data-testid="stAlert"] { border: 2px solid #000 !important; }
div[data-testid="stAlert"] p {
  color: #D50000 !important;
  font-weight: 800 !important;
}

h1, h2, h3, .stMarkdown, label {
  color: #000 !important;
  font-weight: 800 !important;
}
/* Testo file caricato leggibile */
div[data-testid="stFileUploader"] span {
  color: #000 !important;
}

div[data-testid="stFileUploader"] p {
  color: #000 !important;
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


def normalize_lines(text: str) -> str:
    lines = []
    for x in (text or "").splitlines():
        s = x.strip()
        if s:
            lines.append(s)
    return "\n".join(lines)


def strip_html_to_text(s: str) -> str:
    s = s or ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</p\s*>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    return s.strip()


def first_line_title(html_msg: str) -> str:
    txt = strip_html_to_text(html_msg)
    if not txt:
        return "SENZA TITOLO"
    return txt.splitlines()[0].strip() or "SENZA TITOLO"


def stato_msg(inizio: str, fine: str) -> str:
    try:
        di = datetime.strptime(inizio, "%d-%m-%Y").date()
        df = datetime.strptime(fine, "%d-%m-%Y").date()
        oggi = datetime.now().date()
        return "ATTIVO" if di <= oggi <= df else "CHIUSO"
    except Exception:
        return ""


def stato_da_fullmsg(full_msg: str, msg_df: pd.DataFrame) -> str:
    if full_msg in ("PRESENZA", "GENERICO"):
        return "nm"
    if msg_df.empty:
        return ""
    m = msg_df[msg_df["msg"] == full_msg]
    if m.empty:
        return ""
    r = m.iloc[0]
    return stato_msg(r["inizio"], r["fine"])


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

    if st.button("AGGIORNA"):
        st.rerun()

    # ===== DIVISIONE PAGINE ADMIN =====
    tab_operativo, tab_report = st.tabs(["OPERATIVO", "REPORT"])

    # ================= OPERATIVO =================
    with tab_operativo:

        st.header("IMPORT LISTA PDV")

        pdv_existing = load_csv(PDV_FILE, ["ID", "PDV"])
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
                save_csv(pd.DataFrame(columns=["ID", "PDV"]), PDV_FILE)
                st.success("Lista PDV pulita")

        st.markdown("---")

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
                filename = uploaded.name
                with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
                    f.write(uploaded.getbuffer())

            new = pd.DataFrame([[
                msg,
                data_inizio.strftime("%d-%m-%Y"),
                data_fine.strftime("%d-%m-%Y"),
                normalize_lines(pdv_ids),
                filename
            ]], columns=df.columns)

            save_csv(pd.concat([df, new], ignore_index=True), MSG_FILE)
            st.success("Messaggio salvato")

    # ================= REPORT =================
    with tab_report:

        st.header("STORICO MESSAGGI")

        msg_df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])

        view = msg_df.copy()
        if not view.empty:
            view.insert(0, "N°", range(1, len(view) + 1))
            view["MESSAGGIO"] = view["msg"].apply(first_line_title)
            view["STATO"] = view.apply(lambda r: stato_msg(r["inizio"], r["fine"]), axis=1)
            view = view[["N°", "MESSAGGIO", "inizio", "fine", "STATO", "pdv_ids"]]

        st.dataframe(view, use_container_width=True)

        if not msg_df.empty:
            idx_open = st.number_input("Apri messaggio (N°)", min_value=0, max_value=len(msg_df), value=0, step=1)
            if idx_open and 1 <= idx_open <= len(msg_df):
                r = msg_df.iloc[idx_open - 1]
                st.text_area("Contenuto messaggio (copiabile)", r["msg"], height=260)

        if not msg_df.empty:
            del_idx = st.multiselect(
                "Rimuovi manualmente messaggi (seleziona N°)",
                options=list(range(1, len(msg_df) + 1))
            )
            if st.button("ELIMINA RIGHE MESSAGGI SELEZIONATE"):
                if del_idx:
                    keep = msg_df.drop(index=[i - 1 for i in del_idx]).reset_index(drop=True)
                    save_csv(keep, MSG_FILE)
                    st.success("Righe messaggi eliminate")
                    st.rerun()

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

        st.header("REPORT LOG")

        log = load_csv(LOG_FILE, ["data", "pdv", "msg"])

        log_view = log.copy()
        if not log_view.empty:
            log_view.insert(0, "N°", range(1, len(log_view) + 1))
            log_view["messaggio"] = log_view["msg"].apply(
                lambda m: "GENERICO" if m in ("PRESENZA", "GENERICO") else first_line_title(m)
            )
            log_view["stato"] = log_view["msg"].apply(lambda m: stato_da_fullmsg(m, msg_df))
            log_view = log_view[["N°", "data", "pdv", "messaggio", "stato"]]

        st.dataframe(log_view, use_container_width=True)

        if not log.empty:
            del_log_idx = st.multiselect(
                "Rimuovi manualmente righe LOG (seleziona N°)",
                options=list(range(1, len(log) + 1))
            )
            if st.button("ELIMINA RIGHE LOG SELEZIONATE"):
                if del_log_idx:
                    keep = log.drop(index=[i - 1 for i in del_log_idx]).reset_index(drop=True)
                    save_csv(keep, LOG_FILE)
                    st.success("Righe log eliminate")
                    st.rerun()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("SCARICA CSV", log.to_csv(index=False), "report.csv")
        with c2:
            st.download_button("SCARICA EXCEL", excel_bytes(log), "report.xlsx")
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

    st.markdown("""
    <style>
    .msgbox{
    background:#ffffff;
    color:#000000;
    padding:24px;
    border-radius:12px;
    width:100%;
}

   /* Evita testo bianco su sfondo bianco MA mantiene gli altri colori */
   .msgbox [style*="color: rgb(255, 255, 255)"],
   .msgbox [style*="color:rgb(255,255,255)"],
   .msgbox [style*="color:#fff"],
   .msgbox [style*="color:#ffffff"],
   .msgbox span[style*="color: white"],
   .msgbox [style*="color:white"]{
     color:#000 !important;
}
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
        "<p style='text-align:center;'><b>"
        "Digita le prime lettere della Città per trovare il tuo PDV"
        "</b></p>",
        unsafe_allow_html=True
    )

    if not scelta:
        return

    pdv_id = pdv_df.loc[pdv_df["PDV"] == scelta, "ID"].values[0]
    pdv_id = str(pdv_id).strip()

    msg_df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])
    oggi = datetime.now().date()
    mostrati = []

    for _, r in msg_df.iterrows():
        ids = [x.strip() for x in (r["pdv_ids"] or "").splitlines() if x.strip()]
        if pdv_id in ids:
            try:
                di = datetime.strptime(r["inizio"], "%d-%m-%Y").date()
                df = datetime.strptime(r["fine"], "%d-%m-%Y").date()
                if di <= oggi <= df:
                    mostrati.append(r)
            except Exception:
                pass

    log_df = load_csv(LOG_FILE, ["data", "pdv", "msg"])

    # ===== MESSAGGIO GENERICO =====
    if not mostrati:
        st.markdown("""
        <div class='msgbox' style='text-align:center;font-weight:800;font-size:18px;'>
        QUESTA MATTINA PER QUESTO PDV NON SONO PREVISTE PROMO/ATTIVITA' PARTICOLARI. BUON LAVORO
        </div>
        """, unsafe_allow_html=True)

        if st.checkbox("Spunta CONFERMA DI PRESENZA"):
            new = pd.DataFrame([[now_str(), scelta, "PRESENZA"]], columns=log_df.columns)
            save_csv(pd.concat([log_df, new], ignore_index=True), LOG_FILE)
            st.success("Presenza registrata")

        st.link_button("HOME", HOME_URL)
        return

    # ===== MESSAGGI OPERATIVI =====
    for i, r in enumerate(mostrati):
        st.markdown(f"### MESSAGGIO {i+1} DI {len(mostrati)}")
        file_path = None

        # costruisci box con testo messaggio + (se immagine) dentro box
        box_html = f"""
<div style="
    background:white;
    padding:24px;
    border-radius:14px;
    font-family:Arial;
    margin-bottom:25px;
    width:100%;
    box-sizing:border-box;
">

    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        flex-wrap:wrap;
    ">
        <img src="https://raw.githubusercontent.com/GiucaTekmar/operativita-pdv/main/logo.png"
             style="height:45px;">
        <div style="font-size:15px;margin-top:5px;">
            {datetime.now().strftime("%d/%m/%Y")}
        </div>
    </div>

    <hr style="margin:15px 0;">

    <div style="font-size:16px;line-height:1.5;">
        {r['msg']}
    </div>
"""

        if r["file"]:
            file_path = os.path.join(UPLOAD_DIR, r["file"])
            if os.path.exists(file_path):
                if r["file"].lower().endswith(".pdf"):
                    box_html += "<br><br><b>Allegato PDF disponibile sotto</b>"
                else:
                    try:
                        b64 = base64.b64encode(open(file_path, "rb").read()).decode()
                        ext = os.path.splitext(r["file"])[1].lower().replace(".", "")
                        if ext == "jpg":
                            ext = "jpeg"
                        box_html += f"<br><br><img src='data:image/{ext};base64,{b64}' style='max-width:100%;height:auto;'>"
                    except Exception:
                        pass

        box_html += "</div>"

        st.markdown("---")
        st.markdown(textwrap.dedent(box_html), unsafe_allow_html=True)
        st.markdown("---")

        # se PDF: download fuori (Streamlit)
        if r["file"] and file_path and os.path.exists(file_path) and r["file"].lower().endswith(".pdf"):
            with open(file_path, "rb") as f:
                st.download_button("Scarica allegato", f.read(), r["file"], key=f"dl_{pdv_id}_{i}")

        lettura = st.checkbox("Spunta di PRESA VISIONE", key=f"l_{pdv_id}_{i}")
        presenza = st.checkbox("Spunta CONFERMA DI PRESENZA", key=f"p_{pdv_id}_{i}")

        if lettura and presenza:
            gia = ((log_df["pdv"] == scelta) & (log_df["msg"] == r["msg"])).any()
            if not gia:
                new = pd.DataFrame([[now_str(), scelta, r["msg"]]], columns=log_df.columns)
                save_csv(pd.concat([log_df, new], ignore_index=True), LOG_FILE)
                st.success("Registrato")

        st.link_button("HOME", HOME_URL)

# =========================================================
# ROUTER
# =========================================================
if st.query_params.get("admin") == "1":
    admin()
else:
    dipendenti()













