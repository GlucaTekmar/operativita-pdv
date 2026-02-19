import os
import re
import json
import base64
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

st.write("VERSIONE NUOVA — TEST")

import gspread
from google.oauth2.service_account import Credentials
from PIL import Image

# -----------------------------
# CONFIG UI / LINKS
# -----------------------------
JOTFORM_HOME_URL = "https://eu.jotform.com/it/app/build/253605296903360"

# -----------------------------
# NOMI FOGLI / COLONNE (BLINDATI)
# -----------------------------
SHEET_FILE_NAME_DEFAULT = "OPERATIVITA"

TAB_ANAGRAFICA = "ANAGRAFICA"
TAB_MESSAGGI = "MESSAGGI"
TAB_CONFERME_PRIMARY = "Conferme"
TAB_CONFERME_ALT = "CONFERME"

# ANAGRAFICA
A_CODICE = "Codice"
A_INSEGNA = "Insegna"
A_CITTA = "Città"

# MESSAGGI
M_ID = "ID"
M_TITOLO = "Titolo"
M_TESTO = "Testo"
M_INIZIO = "Inizio"
M_FINE = "Fine"
M_TARGET = "Target"  # lista codici PDV separati da virgola/righe; fallback: se vuoto uso ID come target singolo

# CONFERME
C_DATA_ORA = "Data_Ora"
C_PDV = "PDV"
C_TITOLO_MSG = "Titolo_Messaggio"

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Operatività PDV", layout="centered", initial_sidebar_state="collapsed")

# -----------------------------
# CSS (BLINDATO)
# -----------------------------
st.markdown(
    """
<style>
    .stApp { background-color: #E30613; }
    .block-container { padding-top: 3.2rem; padding-bottom: 2.5rem; }

    h1,h2,h3,h4,h5,h6,p,label,div,span { color: #FFFFFF !important; }

    /* Inputs */
    .stTextInput input, .stDateInput input, .stNumberInput input {
        background: #111 !important; color: #fff !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        border-radius: 10px !important;
    }
    .stTextArea textarea{
        background: #111 !important; color: #fff !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
        border-radius: 10px !important;
    }
    div[data-baseweb="select"] > div {
        background: #111 !important; color: #fff !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.35) !important;
    }

    /* Buttons */
    .stButton button, .stLinkButton a {
        background: #111 !important; color: #fff !important;
        border: 1px solid rgba(255,255,255,0.6) !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        width: 100% !important;
        padding: 0.7rem 0.9rem !important;
    }

    /* Cards */
    .card-white {
        background: #ffffff;
        color: #111 !important;
        border-radius: 14px;
        padding: 18px 18px;
        margin-top: 14px;
        border: 2px solid rgba(0,0,0,0.35);
    }
    .card-white * { color: #111 !important; }
    .card-title {
        font-weight: 900;
        font-size: 20px;
        margin-bottom: 6px;
    }

    /* Hint */
    .hint {
        font-size: 14px;
        font-weight: 800;
        margin-top: 8px;
        opacity: 0.95;
    }

    /* Hide Streamlit UI chrome (riduce esposizione) */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# LOGO (BLINDATO)
# -----------------------------
def render_logo() -> None:
    try:
        img = Image.open("logo.png")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image(img, use_container_width=True)
    except Exception:
        # se manca, non blocca l'app
        pass

render_logo()


# =========================================================
# SECRETS / ENV (STREAMLIT + RENDER)
# =========================================================
def _get_secret_value(key: str) -> Optional[str]:
    # Streamlit
    try:
        if key in st.secrets:
            v = st.secrets[key]
            return str(v)
    except Exception:
        pass
    # Env
    v = os.environ.get(key)
    if v:
        return v
    return None


def get_service_account_info() -> Dict[str, Any]:
    # Streamlit: st.secrets["gcp_service_account"] come dict
    try:
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass

    # Render/Env: JSON string
    env_json = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if env_json:
        return json.loads(env_json)

    raise RuntimeError("Credenziali mancanti: aggiungi st.secrets['gcp_service_account'] oppure env GCP_SERVICE_ACCOUNT_JSON")


def get_admin_key() -> str:
    v = _get_secret_value("ADMIN_KEY")
    return (v or "").strip()


def get_admin_password() -> str:
    v = _get_secret_value("ADMIN_PASSWORD")
    return (v or "").strip()


def get_sheet_identifier() -> str:
    # Preferibile: ID (open_by_key). In alternativa nome file.
    v = _get_secret_value("SPREADSHEET_ID")
    if v and v.strip():
        return v.strip()

    v2 = _get_secret_value("SPREADSHEET_NAME")
    if v2 and v2.strip():
        return v2.strip()

    # fallback: nome file standard
    return SHEET_FILE_NAME_DEFAULT


# =========================================================
# GOOGLE SHEETS CLIENT
# =========================================================
@st.cache_resource(show_spinner=False)
def get_gspread_client() -> gspread.Client:
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    info = get_service_account_info()
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_spreadsheet() -> gspread.Spreadsheet:
    ident = get_sheet_identifier()
    client = get_gspread_client()

    # Se sembra un ID di Google Sheet, usa open_by_key
    # (pattern tipico: lunghezza > 30, caratteri [-_])
    if len(ident) > 30 and re.fullmatch(r"[A-Za-z0-9\-_]+", ident):
        return client.open_by_key(ident)
    return client.open(ident)


def get_worksheet(tab_name: str) -> gspread.Worksheet:
    sh = get_spreadsheet()
    return sh.worksheet(tab_name)


def get_conferme_worksheet() -> gspread.Worksheet:
    sh = get_spreadsheet()
    try:
        return sh.worksheet(TAB_CONFERME_PRIMARY)
    except Exception:
        return sh.worksheet(TAB_CONFERME_ALT)


# =========================================================
# UTIL: DATAFRAME IO
# =========================================================
def ws_to_df(w: gspread.Worksheet) -> pd.DataFrame:
    records = w.get_all_records()
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def df_to_ws_overwrite(w: gspread.Worksheet, df: pd.DataFrame, headers: List[str]) -> None:
    # forza colonne richieste
    for h in headers:
        if h not in df.columns:
            df[h] = ""
    df = df[headers].copy()

    w.clear()
    w.update([headers] + df.astype(str).fillna("").values.tolist())


def append_row(w: gspread.Worksheet, row: List[Any]) -> None:
    w.append_row([("" if v is None else str(v)) for v in row], value_input_option="USER_ENTERED")


def parse_date_any(v: Any) -> Optional[date]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    try:
        return pd.to_datetime(s, errors="coerce").date()
    except Exception:
        return None


def normalize_targets(v: Any) -> List[str]:
    if v is None:
        return []
    s = str(v).strip()
    if not s:
        return []
    parts = re.split(r"[,\n;|]+", s)
    return [p.strip() for p in parts if p.strip()]


def make_display_row(codice: str, insegna: str, citta: str) -> str:
    return f"{codice} - {insegna} ({citta})"


def embed_image_html(img_bytes: bytes, filename: str) -> str:
    # tenta di dedurre mime
    ext = (filename or "").lower().split(".")[-1]
    mime = "image/png"
    if ext in ("jpg", "jpeg"):
        mime = "image/jpeg"
    elif ext == "gif":
        mime = "image/gif"
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f'<div style="margin-top:12px;"><img src="data:{mime};base64,{b64}" style="max-width:100%;border-radius:12px;border:1px solid rgba(0,0,0,0.25);" /></div>'


# =========================================================
# ROUTING ADMIN (LINK NASCOSTO)
# /?admin=1&key=<ADMIN_KEY>
# =========================================================
qp = st.query_params

ADMIN_MODE = (
    str(qp.get("admin", "")).strip() == "1"
    and str(qp.get("key", "")).strip() == get_admin_key()
    and bool(get_admin_key())
)

# =========================================================
# PRECARICO FOGLI
# =========================================================
try:
    w_anag = get_worksheet(TAB_ANAGRAFICA)
    w_msg = get_worksheet(TAB_MESSAGGI)
    w_conf = get_conferme_worksheet()
except Exception as e:
    st.error("Errore connessione Google Sheet (permessi / nome file / tab).")
    st.caption(str(e))
    st.stop()


# =========================================================
# AREA DIPENDENTI
# =========================================================
def dipendenti_view() -> None:
    st.markdown("## INDICAZIONI DI GIORNATA")
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown("## **CERCA IL TUO PDV:**")

    df_anag = ws_to_df(w_anag)
    if df_anag.empty:
        st.info("Anagrafica non disponibile.")
        st.link_button("HOME", JOTFORM_HOME_URL)
        return

    # validate columns
    for col in (A_CODICE, A_INSEGNA, A_CITTA):
        if col not in df_anag.columns:
            st.error(f"ANAGRAFICA: colonna mancante '{col}'.")
            st.link_button("HOME", JOTFORM_HOME_URL)
            return

    df_anag[A_CODICE] = df_anag[A_CODICE].astype(str).str.strip()
    df_anag[A_INSEGNA] = df_anag[A_INSEGNA].astype(str).fillna("")
    df_anag[A_CITTA] = df_anag[A_CITTA].astype(str).fillna("")

    # display
    df_anag["Display"] = df_anag.apply(lambda r: make_display_row(r[A_CODICE], r[A_INSEGNA], r[A_CITTA]), axis=1)

    options = ["Seleziona..."] + df_anag["Display"].tolist()
    scelta = st.selectbox("", options, index=0)

    st.markdown('<div class="hint"><b>Digita le prime lettere della città per trovare il tuo PDV</b></div>', unsafe_allow_html=True)

    if scelta == "Seleziona...":
        st.link_button("HOME", JOTFORM_HOME_URL)
        return

    codice_pdv = scelta.split(" - ")[0].strip()
    if not codice_pdv:
        st.link_button("HOME", JOTFORM_HOME_URL)
        return

    # read messages
    df_msg = ws_to_df(w_msg)
    if df_msg.empty:
        # fallback generico + presenza
        st.markdown(
            """
            <div class="card-white">
              <div class="card-title">PER QUESTO PDV QUESTA MATTINA NON SONO PREVISTE PROMO E/O ATTIVITÀ PARTICOLARI RISPETTO AL SOLITO. BUON LAVORO</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        presenza = st.checkbox("da fleggare - CONFERMA DI PRESENZA SUL PDV", key=f"pres_only_empty_{codice_pdv}")
        if presenza and st.button("INVIA CONFERMA", key=f"send_pres_only_empty_{codice_pdv}"):
            append_row(w_conf, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), codice_pdv, "NESSUNA INDICAZIONE | PRESENZA"])
            st.success("Presenza registrata.")
        st.link_button("HOME", JOTFORM_HOME_URL)
        return

    # ensure cols exist
    for col in (M_ID, M_TITOLO, M_TESTO, M_INIZIO, M_FINE, M_TARGET):
        if col not in df_msg.columns:
            df_msg[col] = ""

    today = datetime.now().date()

    active_rows: List[pd.Series] = []
    for _, r in df_msg.iterrows():
        titolo = str(r.get(M_TITOLO, "")).strip()
        testo = str(r.get(M_TESTO, "")).strip()

        d_ini = parse_date_any(r.get(M_INIZIO))
        d_fin = parse_date_any(r.get(M_FINE))

        if d_ini and today < d_ini:
            continue
        if d_fin and today > d_fin:
            continue

        targets = normalize_targets(r.get(M_TARGET))
        rid = str(r.get(M_ID, "")).strip()

        # compatibilità: se Target vuoto, usa ID come target singolo (vecchia logica)
        if not targets and rid:
            targets = [rid]

        if targets and (codice_pdv not in targets):
            continue

        if titolo or testo:
            active_rows.append(r)

    if not active_rows:
        st.markdown(
            """
            <div class="card-white">
              <div class="card-title">PER QUESTO PDV QUESTA MATTINA NON SONO PREVISTE PROMO E/O ATTIVITÀ PARTICOLARI RISPETTO AL SOLITO. BUON LAVORO</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        presenza = st.checkbox("da fleggare - CONFERMA DI PRESENZA SUL PDV", key=f"pres_only_{codice_pdv}")
        if presenza and st.button("INVIA CONFERMA", key=f"send_pres_only_{codice_pdv}"):
            append_row(w_conf, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), codice_pdv, "NESSUNA INDICAZIONE | PRESENZA"])
            st.success("Presenza registrata.")
        st.link_button("HOME", JOTFORM_HOME_URL)
        return

    # Mostra tutte le indicazioni attive
    for idx, r in enumerate(active_rows, start=1):
        titolo = str(r.get(M_TITOLO, "")).strip()
        testo = str(r.get(M_TESTO, "")).strip()

        st.markdown(
            f"""
            <div class="card-white">
              <div class="card-title">{titolo}</div>
              <div>{testo}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Conferma di Lettura e di Presenza sul PDV")

        lettura = st.checkbox("da fleggare - CONFERMA DI LETTURA INDICAZIONE", key=f"lett_{codice_pdv}_{idx}")
        presenza = st.checkbox("da fleggare - CONFERMA DI PRESENZA SUL PDV", key=f"pres_{codice_pdv}_{idx}")

        # invio esplicito (evita scritture “a sorpresa”)
        if st.button("INVIA CONFERMA", key=f"send_{codice_pdv}_{idx}"):
            if not (lettura and presenza):
                st.error("Devi fleggare entrambi i campi.")
            else:
                # anti-duplicati base (sessione)
                stamp = f"{today.isoformat()}|{codice_pdv}|{titolo}"
                if st.session_state.get("last_sent") == stamp:
                    st.info("Conferma già inviata.")
                else:
                    append_row(w_conf, [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), codice_pdv, f"{titolo} | LETTURA+PRESENZA"])
                    st.session_state["last_sent"] = stamp
                    st.success("Conferma registrata.")

        st.markdown("---")

    st.link_button("HOME", JOTFORM_HOME_URL)


# =========================================================
# AREA ADMIN
# =========================================================
def admin_view() -> None:
    st.markdown("# 🔒 DASHBOARD AMMINISTRATORE")

    admin_pw = get_admin_password()
    if not admin_pw:
        st.error("ADMIN_PASSWORD mancante in secrets/env.")
        st.stop()

    pw = st.text_input("Password amministratore", type="password")
    if not pw:
        st.stop()
    if pw != admin_pw:
        st.error("Password errata.")
        st.stop()

    # Tabs
    t1, t2, t3 = st.tabs(["1) Anagrafica PDV", "2) Indicazioni operative", "3) Report conferme"])

    # -------------------------
    # TAB 1 — Upload Anagrafica
    # -------------------------
    with t1:
        st.subheader("Caricamento / aggiornamento ANAGRAFICA")
        st.caption("Carica Excel con colonne: Codice | Insegna | Città")

        up = st.file_uploader("Carica file Excel (.xlsx)", type=["xlsx"])
        if up is not None:
            try:
                df = pd.read_excel(up)
            except Exception as e:
                st.error(f"Errore lettura Excel: {e}")
                st.stop()

            # mapping robusto
            cols = list(df.columns)
            # se non ha i nomi esatti, prova a rinominare sulle prime 3
            if not all(c in df.columns for c in [A_CODICE, A_INSEGNA, A_CITTA]):
                if len(cols) >= 3:
                    df = df.iloc[:, :3].copy()
                    df.columns = [A_CODICE, A_INSEGNA, A_CITTA]
                else:
                    st.error("Excel non valido: servono almeno 3 colonne.")
                    st.stop()

            # pulizia
            df[A_CODICE] = df[A_CODICE].astype(str).str.strip()
            df[A_INSEGNA] = df[A_INSEGNA].astype(str).str.strip()
            df[A_CITTA] = df[A_CITTA].astype(str).str.strip()
            df = df[df[A_CODICE] != ""]

            st.markdown("### Anteprima (prime 50 righe)")
            st.dataframe(df.head(50), use_container_width=True, hide_index=True)

            if st.button("SOVRASCRIVI ANAGRAFICA SU GOOGLE SHEET"):
                try:
                    df_to_ws_overwrite(w_anag, df, [A_CODICE, A_INSEGNA, A_CITTA])
                    st.success("ANAGRAFICA aggiornata correttamente.")
                except Exception as e:
                    st.error("Errore scrittura ANAGRAFICA.")
                    st.caption(str(e))

        st.markdown("---")
        st.markdown("### Anagrafica attuale (prime 200 righe)")
        try:
            df_cur = ws_to_df(w_anag)
            if df_cur.empty:
                st.info("Anagrafica vuota.")
            else:
                st.dataframe(df_cur.head(200), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Errore lettura ANAGRAFICA.")
            st.caption(str(e))

    # -------------------------
    # TAB 2 — Nuova indicazione
    # -------------------------
    with t2:
        st.subheader("Nuova indicazione operativa")

        # Carica anagrafica per selezione PDV
        df_anag = ws_to_df(w_anag)
        if df_anag.empty:
            st.warning("Anagrafica vuota: carica prima la lista PDV.")
            st.stop()

        for col in (A_CODICE, A_INSEGNA, A_CITTA):
            if col not in df_anag.columns:
                st.error(f"ANAGRAFICA: colonna mancante '{col}'.")
                st.stop()

        df_anag[A_CODICE] = df_anag[A_CODICE].astype(str).str.strip()
        df_anag[A_INSEGNA] = df_anag[A_INSEGNA].astype(str).fillna("")
        df_anag[A_CITTA] = df_anag[A_CITTA].astype(str).fillna("")
        df_anag["Display"] = df_anag.apply(lambda r: make_display_row(r[A_CODICE], r[A_INSEGNA], r[A_CITTA]), axis=1)

        display_to_code = dict(zip(df_anag["Display"].tolist(), df_anag[A_CODICE].tolist()))
        display_list = df_anag["Display"].tolist()

        titolo = st.text_input("Titolo")
        st.caption("Testo supporta HTML/Markdown semplice (grassetto, link, ecc.).")
        testo = st.text_area("Testo", height=220)

        c1, c2 = st.columns(2)
        with c1:
            d_ini = st.date_input("Inizio validità", value=datetime.now().date())
        with c2:
            d_fin = st.date_input("Fine validità", value=datetime.now().date())

        st.caption("Seleziona i PDV destinatari (puoi cercare scrivendo nella tendina).")
        targets_display = st.multiselect("PDV target", options=display_list)
        targets_codes = [display_to_code[x] for x in targets_display if x in display_to_code]

        img = st.file_uploader("Immagine (opzionale: 1 immagine)", type=["png", "jpg", "jpeg", "gif"])
        img_html = ""
        if img is not None:
            img_bytes = img.read()
            if img_bytes:
                img_html = embed_image_html(img_bytes, img.name)

        st.markdown("### Anteprima")
        preview_html = f"{testo}{img_html}"
        st.markdown(
            f"""
            <div class="card-white">
              <div class="card-title">{titolo}</div>
              <div>{preview_html}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ID messaggio: progressivo (non obbligatorio, ma utile)
        try:
            df_msg = ws_to_df(w_msg)
            next_id = 1
            if not df_msg.empty and M_ID in df_msg.columns:
                ids = []
                for v in df_msg[M_ID].astype(str).tolist():
                    v = v.strip()
                    if v.isdigit():
                        ids.append(int(v))
                next_id = (max(ids) + 1) if ids else 1
        except Exception:
            next_id = 1

        if st.button("PUBBLICA INDICAZIONE"):
            if not titolo and not testo and not img_html:
                st.error("Inserisci almeno Titolo o Testo.")
            elif d_fin < d_ini:
                st.error("La data Fine non può essere precedente alla data Inizio.")
            elif not targets_codes:
                st.error("Seleziona almeno 1 PDV target.")
            else:
                try:
                    # riga: ID, Titolo, Testo, Inizio, Fine, Target
                    # Target = elenco codici separati da virgola
                    append_row(
                        w_msg,
                        [
                            str(next_id),
                            titolo,
                            preview_html,
                            d_ini.strftime("%Y-%m-%d"),
                            d_fin.strftime("%Y-%m-%d"),
                            ",".join(targets_codes),
                        ],
                    )
                    st.success("Indicazione pubblicata e salvata su Google Sheet (MESSAGGI).")
                except Exception as e:
                    st.error("Errore scrittura su MESSAGGI.")
                    st.caption(str(e))

        st.markdown("---")
        st.subheader("MESSAGGI (ultime 50 righe)")
        try:
            df_show = ws_to_df(w_msg)
            if df_show.empty:
                st.info("Nessun messaggio presente.")
            else:
                # mostra colonne principali
                keep = [c for c in [M_ID, M_TITOLO, M_INIZIO, M_FINE, M_TARGET] if c in df_show.columns]
                st.dataframe(df_show[keep].tail(50), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Errore lettura MESSAGGI.")
            st.caption(str(e))

    # -------------------------
    # TAB 3 — Report conferme
    # -------------------------
    with t3:
        st.subheader("Report conferme (log)")
        try:
            df_c = ws_to_df(w_conf)
            if df_c.empty:
                st.info("Nessuna conferma registrata.")
            else:
                st.dataframe(df_c.tail(500), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("Errore lettura Conferme.")
            st.caption(str(e))


# =========================================================
# MAIN
# =========================================================
try:
    if ADMIN_MODE:
        admin_view()
    else:
        dipendenti_view()
except Exception as e:
    st.error("Errore applicazione.")
    st.caption(str(e))









