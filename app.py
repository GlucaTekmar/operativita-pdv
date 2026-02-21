import os
import io
import base64
import pandas as pd
import streamlit as st
from datetime import datetime, date

st.set_page_config(layout="wide")

LOG_FILE = "log.csv"
MSG_FILE = "messaggi.csv"
PDV_FILE = "pdv.csv"
UPLOAD_DIR = "uploads"

ADMIN_PASSWORD = "GianAri2026"

# =========================================================
# UTILS
# =========================================================

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def load_csv(path: str, cols: list[str]) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
        except Exception:
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    # Garantisce colonne richieste (evita KeyError tipo "pdv_ids")
    for c in cols:
        if c not in df.columns:
            df[c] = ""

    return df[cols].copy()

def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)

def fmt_date_ita(d: date) -> str:
    return d.strftime("%d-%m-%y")

def fmt_dt_ita(dt: datetime) -> str:
    return dt.strftime("%d-%m-%y %H:%M:%S")

def safe_parse_date(s) -> date | None:
    try:
        v = pd.to_datetime(s, errors="coerce")
        if pd.isna(v):
            return None
        return v.date()
    except Exception:
        return None

def read_file_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception:
        return None

def centered_logo(path: str, width: int = 240) -> None:
    if not os.path.exists(path):
        return
    b = read_file_bytes(path)
    if not b:
        return
    b64 = base64.b64encode(b).decode("utf-8")
    st.markdown(
        f"""
        <div style="display:flex; justify-content:center; width:100%; margin-top:6px; margin-bottom:8px;">
            <img src="data:image/png;base64,{b64}" style="width:{width}px; max-width:80vw; height:auto;" />
        </div>
        """,
        unsafe_allow_html=True
    )

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Report") -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return out.getvalue()

def normalize_ids(multiline: str) -> list[str]:
    if multiline is None:
        return []
    lines = str(multiline).splitlines()
    return [x.strip() for x in lines if x and str(x).strip()]

# =========================================================
# STYLES
# =========================================================

def admin_css():
    st.markdown(
        """
        <style>
        .stApp { background: #ffffff !important; color:#111 !important; }
        h1, h2, h3, p, label { color:#111 !important; }

        /* Titoli e label più grandi */
        label, .stMarkdown p { font-size: 16px !important; font-weight: 700 !important; }
        h1 { font-size: 40px !important; }
        h2 { font-size: 28px !important; }
        h3 { font-size: 22px !important; }

        /* Textarea: font grande */
        textarea { font-size: 18px !important; line-height: 1.35 !important; }

        /* Input/select: font grande */
        input, select { font-size: 16px !important; }

        /* Bottoni grandi */
        div.stButton > button, div.stDownloadButton > button {
            font-size: 16px !important;
            padding: 10px 16px !important;
            border-radius: 10px !important;
        }

        /* Dataframe: font più grande */
        .stDataFrame, .stDataFrame div { font-size: 14px !important; }

        /* Toolbar dataframe (non sempre controllabile, ma aumentiamo un po') */
        [data-testid="stDataFrame"] button {
            transform: scale(1.15);
            transform-origin: left center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def dip_css():
    st.markdown(
        """
        <style>
        .stApp { background-color:#b30000 !important; color:white !important; }
        h1, h2, h3, p, label, span, div { color:white !important; }

        /* Selectbox scuro */
        div[data-baseweb="select"] > div {
            background-color: #111 !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            border-radius: 10px !important;
        }

        /* Bottoni grandi */
        div.stButton > button, div.stDownloadButton > button {
            font-size: 16px !important;
            padding: 10px 16px !important;
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# ADMIN VIEW
# =========================================================

def admin():
    admin_css()
    centered_logo("logo.png", width=260)

    st.title("DASHBOARD ADMIN")

    password = st.text_input("Password", type="password")
    if password != ADMIN_PASSWORD:
        st.warning("Inserire password admin")
        return

    st.markdown("---")

    # ===========================
    # IMPORT PDV
    # ===========================
    st.header("IMPORT LISTA PDV (ID;Nome)")

    pdv_text = st.text_area(
        "Incolla elenco PDV",
        height=140,  # 5-6 righe circa
        placeholder="Esempio:\n1115; ESSELUNGA Jenner (Milano)\n1200; CARREFOUR Burolò\n..."
    )

    if st.button("SALVA LISTA PDV"):
        rows = []
        for line in str(pdv_text).splitlines():
            if ";" in line:
                id_, nome = line.split(";", 1)
                id_ = id_.strip()
                nome = nome.strip()
                if id_ and nome:
                    rows.append([id_, nome])

        df = pd.DataFrame(rows, columns=["ID", "PDV"])
        save_csv(df, PDV_FILE)
        st.success(f"Lista PDV salvata ({len(df)} righe)")

    st.markdown("---")

    # ===========================
    # CREA MESSAGGIO
    # ===========================
    st.header("CREA NUOVO MESSAGGIO")

    st.caption("Formattazione: usa Markdown (es. **grassetto**, elenchi con - , link).")

    msg = st.text_area(
        "TESTO MESSAGGIO",
        height=380,
        placeholder="Scrivi qui (supporta Markdown)..."
    )

    uploaded = st.file_uploader(
        "ALLEGA IMMAGINE O PDF",
        type=["png", "jpg", "jpeg", "pdf"]
    )

    col1, col2 = st.columns(2)
    with col1:
        data_inizio = st.date_input("DATA INIZIO", value=date.today())
    with col2:
        data_fine = st.date_input("DATA FINE", value=date.today())

    pdv_ids = st.text_area(
        "INCOLLA ID PDV (UNO PER RIGA)",
        height=140,
        placeholder="Esempio:\n1115\n1200\n1306\n..."
    )

    # Preview formattazione
    with st.expander("ANTEPRIMA MESSAGGIO (come lo vedono i dipendenti)", expanded=False):
        st.markdown(msg if msg else "_(vuoto)_")

    if st.button("SALVA MESSAGGIO"):
        ensure_dir(UPLOAD_DIR)

        msg_df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])

        filename = ""
        if uploaded:
            # Nome file unico per evitare collisioni su Render/Cloud
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = uploaded.name.replace("/", "_").replace("\\", "_")
            filename = f"{ts}_{safe_name}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(uploaded.getbuffer())

        # Salva date come ISO (robusto) e id normalizzati
        new = pd.DataFrame([{
            "msg": msg or "",
            "inizio": data_inizio.isoformat() if data_inizio else "",
            "fine": data_fine.isoformat() if data_fine else "",
            "pdv_ids": "\n".join(normalize_ids(pdv_ids)),
            "file": filename
        }])

        msg_df = pd.concat([msg_df, new], ignore_index=True)
        save_csv(msg_df, MSG_FILE)
        st.success("Messaggio salvato")

    st.markdown("---")

    # ===========================
    # REPORT LOG
    # ===========================
    st.header("REPORT LETTURE")

    log_df = load_csv(LOG_FILE, ["data", "pdv", "msg"])

    # Format date/ora per vista e download
    if not log_df.empty:
        # data è stringa: la convertiamo e riformattiamo, se possibile
        dt_parsed = pd.to_datetime(log_df["data"], errors="coerce")
        log_df["data"] = dt_parsed.dt.strftime("%d-%m-%y %H:%M:%S").fillna(log_df["data"])

    st.dataframe(log_df, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        st.download_button(
            "SCARICA CSV",
            data=log_df.to_csv(index=False).encode("utf-8"),
            file_name="report_log.csv",
            mime="text/csv"
        )
    with c2:
        st.download_button(
            "SCARICA EXCEL",
            data=to_excel_bytes(log_df, sheet_name="Log"),
            file_name="report_log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    if st.button("PULISCI LOG"):
        save_csv(log_df.iloc[0:0], LOG_FILE)
        st.success("Log pulito")

# =========================================================
# DIPENDENTI VIEW
# =========================================================

def dipendenti_view():
    dip_css()
    centered_logo("logo.png", width=260)

    st.markdown("<h1 style='text-align:center; margin-top:0;'>INDICAZIONI<br/>OPERATIVE</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; margin-top:6px;'>SELEZIONA IL TUO PDV</h3>", unsafe_allow_html=True)

    pdv_df = load_csv(PDV_FILE, ["ID", "PDV"])
    if pdv_df.empty:
        st.warning("Archivio PDV vuoto")
        return

    # Selectbox senza label visibile (sparisce "Cerca il tuo PDV")
    scelta = st.selectbox(
        label="",
        options=pdv_df["PDV"].tolist(),
        index=None,  # nessun preselezionato
        placeholder="",
        label_visibility="collapsed"
    )

    st.markdown(
        "<p style='text-align:center; font-size:14px; margin-top:6px;'><b>"
        "DIGITA LE PRIME LETTERE DELLA CITTA' PER TROVARE IL TUO PDV"
        "</b></p>",
        unsafe_allow_html=True
    )

    if not scelta:
        return

    # Recupero ID PDV selezionato
    try:
        pdv_id = pdv_df.loc[pdv_df["PDV"] == scelta, "ID"].values[0]
    except Exception:
        st.error("Errore selezione PDV")
        return

    # Messaggi
    msg_df = load_csv(MSG_FILE, ["msg", "inizio", "fine", "pdv_ids", "file"])

    oggi = datetime.now().date()
    mostrati = []

    for _, r in msg_df.iterrows():
        ids = normalize_ids(r.get("pdv_ids", ""))
        inizio = safe_parse_date(r.get("inizio", ""))
        fine = safe_parse_date(r.get("fine", ""))

        # Se date invalide, il messaggio non viene mostrato (evita crash)
        if not inizio or not fine:
            continue

        if (pdv_id in ids) and (inizio <= oggi <= fine):
            mostrati.append(r)

    if not mostrati:
        st.info("Nessun messaggio")
        return

    log_df = load_csv(LOG_FILE, ["data", "pdv", "msg"])

    for r in mostrati:
        st.markdown("---")
        # Il testo è Markdown (formattazione)
        st.markdown(str(r.get("msg", "")))

        filename = str(r.get("file", "") or "").strip()
        if filename:
            filepath = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                if filename.lower().endswith(".pdf"):
                    b = read_file_bytes(filepath)
                    if b:
                        st.download_button(
                            "SCARICA ALLEGATO",
                            data=b,
                            file_name=filename,
                            mime="application/pdf"
                        )
                else:
                    st.image(filepath, width=360)

        # No doppio log: chiave = PDV + testo messaggio (come da logica originale)
        gia_letto = (
            (log_df["pdv"] == scelta) &
            (log_df["msg"] == str(r.get("msg", "")))
        ).any()

        if gia_letto:
            st.success("Già confermato")
            continue

        if st.checkbox("Confermo lettura e presenza", key=f"chk_{hash(str(r.get('msg','')))}"):
            new = pd.DataFrame([{
                "data": fmt_dt_ita(datetime.now()),
                "pdv": scelta,
                "msg": str(r.get("msg", ""))
            }])

            log_df = pd.concat([log_df, new], ignore_index=True)
            save_csv(log_df, LOG_FILE)
            st.success("Registrato")

# =========================================================
# ROUTING
# =========================================================

params = st.query_params
if params.get("admin") == "1":
    admin()
else:
    dipendenti_view()
