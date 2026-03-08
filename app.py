
import base64
import html
import io
import re
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_quill import st_quill


# =========================
# CONFIG
# =========================
ADMIN_PASSWORD = "GianAri2026"
HOME_URL = "https://eu.jotform.com/app/253685296983368"

BASE_DIR = Path("/var/data")
BASE_DIR.mkdir(parents=True, exist_ok=True)

PDV_FILE = BASE_DIR / "pdv.csv"
MSG_FILE = BASE_DIR / "messaggi.csv"
LOG_FILE = BASE_DIR / "log.csv"
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

LOGO_FILE = Path("logo.png")

PDV_COLUMNS = ["pdv_id", "pdv_nome"]
MSG_COLUMNS = ["msg_id", "titolo", "msg", "pdv_ids", "file", "data_inizio", "data_fine", "stato"]
LOG_COLUMNS = ["data", "pdv_id", "pdv_nome", "msg_id", "apertura_timestamp", "lettura_timestamp"]


# =========================
# FILE INIT
# =========================
def ensure_csv(path: Path, columns: list[str]) -> None:
    if not path.exists():
        pd.DataFrame(columns=columns).to_csv(path, index=False)


ensure_csv(PDV_FILE, PDV_COLUMNS)
ensure_csv(MSG_FILE, MSG_COLUMNS)
ensure_csv(LOG_FILE, LOG_COLUMNS)


# =========================
# PAGE
# =========================
st.set_page_config(page_title="Operatività PDV", layout="wide")


# =========================
# HELPERS
# =========================
def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return date.today().isoformat()


def safe_read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except Exception:
        df = pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].fillna("")


def save_csv(df: pd.DataFrame, path: Path, columns: list[str]) -> None:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = ""
    out = out[columns].fillna("")
    out.to_csv(path, index=False)




def maybe_seed_from_repo(disk_path: Path, repo_path: Path, columns: list[str]) -> None:
    if not repo_path.exists():
        return
    disk_df = safe_read_csv(disk_path, columns)
    repo_df = safe_read_csv(repo_path, columns)
    if disk_df.empty and not repo_df.empty:
        save_csv(repo_df, disk_path, columns)
def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dati")
    return buffer.getvalue()


def logo_data_uri() -> str:
    if not LOGO_FILE.exists():
        return ""
    mime = "image/png"
    encoded = base64.b64encode(LOGO_FILE.read_bytes()).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


LOGO_URI = logo_data_uri()


def render_top_header() -> None:
    left, center, right = st.columns([1, 3, 1])
    with center:
        if LOGO_URI:
            st.markdown(
                f'<div style="text-align:center;margin-bottom:10px;"><img src="{LOGO_URI}" style="height:74px;"></div>',
                unsafe_allow_html=True,
            )
    with left:
        st.markdown(
            f'<a href="{HOME_URL}" target="_self" class="btn-link btn-link-dark">HOME</a>',
            unsafe_allow_html=True,
        )


def render_logout() -> None:
    if st.button("LOGOUT", key="logout_top"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.query_params.clear()
        st.rerun()


def query_admin_mode() -> bool:
    return st.query_params.get("admin", "0") == "1"


def sanitize_text(text: str) -> str:
    return html.escape(str(text)).replace("\n", "<br>")


def normalize_ids(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[|,\n;]+", str(raw))
    return [p.strip() for p in parts if p.strip()]


def current_pdv_name() -> str:
    return st.session_state.get("employee_selected_pdv_name", "")


def parse_message_title_and_body(raw_html: str, fallback_title: str = "") -> tuple[str, str]:
    raw_html = raw_html or ""
    plain = re.sub(r"<[^>]+>", "\n", raw_html)
    plain = re.sub(r"\n+", "\n", plain).strip()
    lines = [ln.strip() for ln in plain.split("\n") if ln.strip()]
    if fallback_title.strip():
        title = fallback_title.strip()
        body_html = raw_html
    elif lines:
        title = lines[0]
        body_html = raw_html
        # remove first line if editor content already contains title as first line
        if len(lines) > 1:
            first = re.escape(lines[0])
            body_html = re.sub(first, "", body_html, count=1, flags=re.IGNORECASE)
    else:
        title = "NESSUNA ATTIVITÀ"
        body_html = "Oggi su questo PDV non sono previste promo e/o attività particolari.<br><br>Buon lavoro."
    title = title.upper()
    return title, body_html.strip()


def save_uploaded_file(uploaded_file, current_existing: str = "") -> str:
    if uploaded_file is None:
        return current_existing
    suffix = Path(uploaded_file.name).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{suffix}"
    target = MEDIA_DIR / unique_name
    target.write_bytes(uploaded_file.getbuffer())
    return unique_name


def get_media_path(filename: str) -> Path | None:
    if not filename:
        return None
    target = MEDIA_DIR / filename
    return target if target.exists() else None


def media_is_image(path: Path) -> bool:
    return path.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]


def media_is_pdf(path: Path) -> bool:
    return path.suffix.lower() == ".pdf"


def active_messages_for_pdv(pdv_id: str) -> pd.DataFrame:
    df = safe_read_csv(MSG_FILE, MSG_COLUMNS)
    if df.empty:
        return df
    today = today_str()
    df["data_inizio"] = df["data_inizio"].astype(str)
    df["data_fine"] = df["data_fine"].astype(str)
    df["stato"] = df["stato"].astype(str).str.upper()

    mask_date = (df["data_inizio"] <= today) & (df["data_fine"] >= today)
    mask_state = (df["stato"].eq("ATTIVO")) | (df["stato"].eq(""))
    df = df[mask_date & mask_state].copy()

    if df.empty:
        return df

    df = df[df["pdv_ids"].apply(lambda x: str(pdv_id) in normalize_ids(str(x)))].copy()
    return df.reset_index(drop=True)


def upsert_open_log(pdv_id: str, pdv_nome: str, msg_id: str) -> None:
    logs = safe_read_csv(LOG_FILE, LOG_COLUMNS)
    today = today_str()
    msg_id = str(msg_id)

    mask = (
        (logs["data"] == today)
        & (logs["pdv_id"].astype(str) == str(pdv_id))
        & (logs["msg_id"].astype(str) == msg_id)
    )
    if mask.any():
        return

    new_row = pd.DataFrame(
        [{
            "data": today,
            "pdv_id": str(pdv_id),
            "pdv_nome": str(pdv_nome),
            "msg_id": msg_id,
            "apertura_timestamp": now_ts(),
            "lettura_timestamp": ""
        }]
    )
    logs = pd.concat([logs, new_row], ignore_index=True)
    save_csv(logs, LOG_FILE, LOG_COLUMNS)


def mark_read_log(pdv_id: str, msg_id: str) -> None:
    logs = safe_read_csv(LOG_FILE, LOG_COLUMNS)
    today = today_str()
    mask = (
        (logs["data"] == today)
        & (logs["pdv_id"].astype(str) == str(pdv_id))
        & (logs["msg_id"].astype(str) == str(msg_id))
    )
    if mask.any():
        idx = logs[mask].index[0]
        if not str(logs.at[idx, "lettura_timestamp"]).strip():
            logs.at[idx, "lettura_timestamp"] = now_ts()
            save_csv(logs, LOG_FILE, LOG_COLUMNS)


def build_generic_message() -> dict:
    return {
        "msg_id": "GENERICO",
        "titolo": "NESSUNA ATTIVITÀ",
        "msg": "Oggi su questo PDV non sono previste promo e/o attività particolari.<br><br>Buon lavoro.",
        "file": "",
        "data_inizio": today_str(),
        "data_fine": today_str(),
    }


def render_circular_message(message_number: int, message: dict, pdv_nome: str) -> None:
    titolo, body_html = parse_message_title_and_body(message.get("msg", ""), message.get("titolo", ""))
    msg_date = today_str()
    st.markdown(
        f"""
        <div class="circular-sheet">
            <div class="msg-num">MESSAGGIO N.{message_number}</div>
            <div class="pdv-target">{sanitize_text(pdv_nome)}</div>

            <div class="sheet-head">
                <div class="sheet-logo-wrap">{f'<img src="{LOGO_URI}" class="sheet-logo">' if LOGO_URI else '<div class="sheet-logo-fallback">LOGO</div>'}</div>
                <div class="sheet-date">{sanitize_text(msg_date)}</div>
            </div>

            <div class="sep-red"></div>

            <div class="sheet-title">{sanitize_text(titolo)}</div>

            <div class="sep-red"></div>

            <div class="sheet-body">{body_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    media_name = message.get("file", "")
    media_path = get_media_path(media_name) if media_name else None
    if media_path:
        cols = st.columns([1, 1, 4])
        with cols[0]:
            if media_is_pdf(media_path):
                st.download_button(
                    "Apri PDF",
                    data=media_path.read_bytes(),
                    file_name=media_path.name,
                    mime="application/pdf",
                    key=f"pdf_{message.get('msg_id', message_number)}",
                )
        with cols[1]:
            if media_is_image(media_path):
                st.button("Immagine", key=f"img_label_{message.get('msg_id', message_number)}", disabled=True)
        if media_is_image(media_path):
            st.image(str(media_path), use_column_width=True)
    st.markdown('<div class="sheet-end-sep"></div>', unsafe_allow_html=True)


def admin_message_dataframe() -> pd.DataFrame:
    df = safe_read_csv(MSG_FILE, MSG_COLUMNS)
    if df.empty:
        return pd.DataFrame(columns=["select"] + MSG_COLUMNS)
    out = df.copy()
    out.insert(0, "select", False)
    return out


def admin_log_dataframe() -> pd.DataFrame:
    df = safe_read_csv(LOG_FILE, LOG_COLUMNS)
    if df.empty:
        return pd.DataFrame(columns=["select"] + LOG_COLUMNS)
    out = df.copy()
    out.insert(0, "select", False)
    return out



maybe_seed_from_repo(PDV_FILE, Path("pdv.csv"), PDV_COLUMNS)
maybe_seed_from_repo(MSG_FILE, Path("messaggi.csv"), MSG_COLUMNS)

# =========================
# CSS
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background: #c40000;
    }

    .block-container {
        padding-top: 1.0rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    h1, h2, h3, h4, h5, h6, p, label, span, div {
        color: white;
    }

    .white-small-note {
        color: white;
        font-weight: 700;
        font-size: 0.92rem;
        margin-top: 8px;
        margin-bottom: 18px;
    }

    .btn-link, .btn-link:visited {
        display: inline-block;
        padding: 10px 18px;
        border-radius: 10px;
        text-decoration: none;
        font-weight: 700;
        border: 2px solid #ffffff;
        margin-bottom: 12px;
    }

    .btn-link-dark, .btn-link-dark:visited {
        background: #0f1633;
        color: white !important;
        border: none;
    }

    .circular-sheet {
        background: #ffffff;
        border-radius: 8px;
        padding: 26px 30px;
        margin-top: 18px;
        margin-bottom: 10px;
        box-shadow: 0 10px 22px rgba(0,0,0,0.18);
    }

    .msg-num {
        color: #111111;
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: 0.3px;
        margin-bottom: 4px;
    }

    .pdv-target {
        color: #111111;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 16px;
    }

    .sheet-head {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        margin-bottom: 12px;
    }

    .sheet-logo {
        height: 52px;
        width: auto;
        object-fit: contain;
    }

    .sheet-logo-fallback {
        color: #111111;
        font-weight: 800;
        font-size: 0.95rem;
    }

    .sheet-date {
        color: #111111;
        font-weight: 700;
        font-size: 0.98rem;
    }

    .sep-red, .sheet-end-sep {
        height: 3px;
        background: #c40000;
        margin: 10px 0 18px 0;
        opacity: 0.95;
    }

    .sheet-title {
        color: #111111;
        text-align: center;
        font-size: 1.3rem;
        font-weight: 900;
        text-transform: uppercase;
        margin: 2px 0;
    }

    .sheet-body, .sheet-body * {
        color: #111111 !important;
        font-size: 1.04rem;
        line-height: 1.65;
    }

    .sheet-body ul, .sheet-body ol {
        margin-top: 0.6rem;
        margin-bottom: 0.6rem;
        padding-left: 1.35rem;
    }

    .admin-title {
        color: white;
        font-weight: 900;
        font-size: 2rem;
        margin-bottom: 0.6rem;
    }

    .stDataFrame, .stTable, .stAlert {
        color: #111111;
    }

    div[data-testid="stDataFrame"] div, div[data-testid="stDataEditor"] div {
        color: #111111;
    }

    @media (max-width: 768px) {
        .block-container {
            padding-left: 16px;
            padding-right: 16px;
        }

        .circular-sheet {
            padding: 18px 16px;
            border-radius: 6px;
        }

        .sheet-title {
            font-size: 1.12rem;
        }

        .sheet-body, .sheet-body * {
            font-size: 0.98rem;
        }

        .sheet-logo {
            height: 42px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# ADMIN
# =========================
def render_pdv_manager() -> None:
    st.markdown('<div class="admin-title">Gestione Messaggi</div>', unsafe_allow_html=True)
    st.subheader("Lista Punti Vendita")

    current_pdv_df = safe_read_csv(PDV_FILE, PDV_COLUMNS)
    current_pdv_text = "\n".join(
        [f"{row['pdv_id']},{row['pdv_nome']}" for _, row in current_pdv_df.iterrows()]
    )

    pdv_text = st.text_area(
        "LISTA PDV (id,nome)",
        value=current_pdv_text,
        height=220,
        key="pdv_text_area_admin"
    )

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("SALVA", key="save_pdv_btn"):
            rows = []
            for raw in pdv_text.splitlines():
                raw = raw.strip()
                if not raw or "," not in raw:
                    continue
                left, right = raw.split(",", 1)
                rows.append({"pdv_id": left.strip(), "pdv_nome": right.strip()})
            df = pd.DataFrame(rows, columns=PDV_COLUMNS)
            save_csv(df, PDV_FILE, PDV_COLUMNS)
            st.success("Lista PDV salvata.")
            st.rerun()

    with col_b:
        if st.button("PULISCI LISTA", key="clear_pdv_btn"):
            save_csv(pd.DataFrame(columns=PDV_COLUMNS), PDV_FILE, PDV_COLUMNS)
            st.success("Lista PDV pulita.")
            st.rerun()


def render_message_manager() -> None:
    st.subheader("Nuovo Messaggio")

    if "edit_msg_id" not in st.session_state:
        st.session_state.edit_msg_id = ""
    if "edit_titolo" not in st.session_state:
        st.session_state.edit_titolo = ""
    if "edit_pdv_ids" not in st.session_state:
        st.session_state.edit_pdv_ids = ""
    if "edit_data_inizio" not in st.session_state:
        st.session_state.edit_data_inizio = date.today()
    if "edit_data_fine" not in st.session_state:
        st.session_state.edit_data_fine = date.today()
    if "edit_file" not in st.session_state:
        st.session_state.edit_file = ""
    if "editor_nonce" not in st.session_state:
        st.session_state.editor_nonce = 0
    if "editor_initial_html" not in st.session_state:
        st.session_state.editor_initial_html = ""

    titolo = st.text_input("Titolo", value=st.session_state.edit_titolo, key="msg_title_input")
    editor_html = st_quill(
        value=st.session_state.editor_initial_html,
        html=True,
        toolbar="full",
        key=f"msg_editor_{st.session_state.editor_nonce}",
    )

    pdv_ids_text = st.text_area(
        "PDV destinatari (id uno per riga)",
        value=st.session_state.edit_pdv_ids,
        height=120,
        key="msg_pdv_ids"
    )

    col1, col2 = st.columns(2)
    with col1:
        data_inizio = st.date_input("Data inizio", value=st.session_state.edit_data_inizio, key="data_inizio_msg")
    with col2:
        data_fine = st.date_input("Data fine", value=st.session_state.edit_data_fine, key="data_fine_msg")

    uploaded = st.file_uploader(
        "Allegato",
        type=["png", "jpg", "jpeg", "pdf", "webp"],
        key="msg_uploader"
    )

    info_cols = st.columns([1, 4])
    with info_cols[0]:
        if st.button("INVIA MESSAGGIO", key="send_msg_btn"):
            msg_df = safe_read_csv(MSG_FILE, MSG_COLUMNS)
            edit_id = st.session_state.edit_msg_id.strip()
            saved_file = save_uploaded_file(uploaded, st.session_state.edit_file)
            new_row = {
                "msg_id": edit_id if edit_id else str(uuid.uuid4()),
                "titolo": titolo.strip(),
                "msg": editor_html or "",
                "pdv_ids": "|".join(normalize_ids(pdv_ids_text.replace("\n", "|"))),
                "file": saved_file,
                "data_inizio": data_inizio.isoformat(),
                "data_fine": data_fine.isoformat(),
                "stato": "ATTIVO",
            }

            if edit_id and (msg_df["msg_id"].astype(str) == edit_id).any():
                idx = msg_df[msg_df["msg_id"].astype(str) == edit_id].index[0]
                for k, v in new_row.items():
                    msg_df.at[idx, k] = v
            else:
                msg_df = pd.concat([msg_df, pd.DataFrame([new_row])], ignore_index=True)

            save_csv(msg_df, MSG_FILE, MSG_COLUMNS)

            st.session_state.edit_msg_id = ""
            st.session_state.edit_titolo = ""
            st.session_state.edit_pdv_ids = ""
            st.session_state.edit_data_inizio = date.today()
            st.session_state.edit_data_fine = date.today()
            st.session_state.edit_file = ""
            st.session_state.editor_initial_html = ""
            st.session_state.editor_nonce += 1
            st.success("Messaggio salvato.")
            st.rerun()

    with info_cols[1]:
        if st.session_state.edit_file:
            st.caption(f"Allegato attuale: {st.session_state.edit_file}")


def render_report_page() -> None:
    st.markdown('<div class="admin-title">Report</div>', unsafe_allow_html=True)

    st.subheader("Messaggi salvati")
    msg_df = safe_read_csv(MSG_FILE, MSG_COLUMNS)
    msg_view = msg_df.copy()
    msg_view.insert(0, "select", False)

    edited_msg = st.data_editor(
        msg_view,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="msg_table_editor",
        column_config={"select": st.column_config.CheckboxColumn("Seleziona")},
        disabled=[c for c in msg_view.columns if c != "select"],
    )

    msg_cols = st.columns(5)
    with msg_cols[0]:
        st.download_button(
            "SCARICA CSV",
            data=msg_df.to_csv(index=False).encode("utf-8"),
            file_name="messaggi.csv",
            mime="text/csv",
            key="dl_msg_csv",
        )
    with msg_cols[1]:
        st.download_button(
            "SCARICA EXCEL",
            data=df_to_excel_bytes(msg_df),
            file_name="messaggi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_msg_xlsx",
        )
    with msg_cols[2]:
        if st.button("ELIMINA MESSAGGI SELEZIONATI", key="delete_msg_selected"):
            selected_ids = edited_msg.loc[edited_msg["select"] == True, "msg_id"].astype(str).tolist()
            if selected_ids:
                msg_df = msg_df[~msg_df["msg_id"].astype(str).isin(selected_ids)].copy()
                save_csv(msg_df, MSG_FILE, MSG_COLUMNS)
                st.success("Messaggi selezionati eliminati.")
                st.rerun()
    with msg_cols[3]:
        if st.button("PULISCI MESSAGGI", key="clear_msgs"):
            save_csv(pd.DataFrame(columns=MSG_COLUMNS), MSG_FILE, MSG_COLUMNS)
            st.success("Messaggi puliti.")
            st.rerun()
    with msg_cols[4]:
        if st.button("APRI MESSAGGIO", key="open_prev_msg"):
            selected = edited_msg.loc[edited_msg["select"] == True]
            if len(selected) == 1:
                row = selected.iloc[0]
                st.session_state.edit_msg_id = row["msg_id"]
                st.session_state.edit_titolo = row["titolo"]
                st.session_state.edit_pdv_ids = str(row["pdv_ids"]).replace("|", "\n")
                st.session_state.edit_data_inizio = pd.to_datetime(row["data_inizio"]).date() if str(row["data_inizio"]).strip() else date.today()
                st.session_state.edit_data_fine = pd.to_datetime(row["data_fine"]).date() if str(row["data_fine"]).strip() else date.today()
                st.session_state.edit_file = row["file"]
                st.session_state.editor_initial_html = row["msg"]
                st.session_state.editor_nonce += 1
                st.success("Messaggio richiamato nella pagina Gestione Messaggi.")
            else:
                st.warning("Seleziona un solo messaggio.")
    st.divider()

    st.subheader("Report letture")
    log_df = safe_read_csv(LOG_FILE, LOG_COLUMNS)
    log_view = log_df.copy()
    log_view.insert(0, "select", False)

    edited_log = st.data_editor(
        log_view,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="log_table_editor",
        column_config={"select": st.column_config.CheckboxColumn("Seleziona")},
        disabled=[c for c in log_view.columns if c != "select"],
    )

    log_cols = st.columns(4)
    with log_cols[0]:
        st.download_button(
            "SCARICA CSV",
            data=log_df.to_csv(index=False).encode("utf-8"),
            file_name="log.csv",
            mime="text/csv",
            key="dl_log_csv",
        )
    with log_cols[1]:
        st.download_button(
            "SCARICA EXCEL",
            data=df_to_excel_bytes(log_df),
            file_name="log.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_log_xlsx",
        )
    with log_cols[2]:
        if st.button("ELIMINA LOG SELEZIONATI", key="delete_log_selected"):
            selected_rows = edited_log.loc[edited_log["select"] == True, LOG_COLUMNS]
            if not selected_rows.empty:
                merged = log_df.merge(selected_rows.drop_duplicates(), how="left", indicator=True)
                log_df = merged[merged["_merge"] == "left_only"][LOG_COLUMNS]
                save_csv(log_df, LOG_FILE, LOG_COLUMNS)
                st.success("Log selezionati eliminati.")
                st.rerun()
    with log_cols[3]:
        if st.button("PULISCI LOG", key="clear_logs"):
            save_csv(pd.DataFrame(columns=LOG_COLUMNS), LOG_FILE, LOG_COLUMNS)
            st.success("Log puliti.")
            st.rerun()


def render_admin_page() -> None:
    render_top_header()
    render_logout()

    if not st.session_state.get("admin_ok", False):
        st.markdown('<div class="admin-title">Accesso Admin</div>', unsafe_allow_html=True)
        pwd = st.text_input("Password", type="password", key="admin_pwd")
        if st.button("ENTRA IN ADMIN", key="admin_enter"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Password errata.")
        return

    tab_gestione, tab_report = st.tabs(["MESSAGGI", "REPORT"])
    with tab_gestione:
        render_pdv_manager()
        st.divider()
        render_message_manager()
    with tab_report:
        render_report_page()


# =========================
# EMPLOYEE
# =========================
def employee_page_one() -> None:
    render_top_header()
    st.markdown("<h1>Seleziona PDV</h1>", unsafe_allow_html=True)

    pdv_df = safe_read_csv(PDV_FILE, PDV_COLUMNS)
    pdv_df["label"] = pdv_df["pdv_id"].astype(str) + " - " + pdv_df["pdv_nome"].astype(str)
    options = pdv_df["label"].tolist()

    c1, c2 = st.columns([12, 1])
    with c1:
        selected_label = st.selectbox(
            "PDV",
            options=options,
            index=None,
            placeholder="Seleziona un PDV",
            key="employee_pdv_select",
        )
    with c2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("✕", key="clear_pdv_select"):
            st.session_state["employee_pdv_select"] = None
            st.rerun()

    st.markdown('<div class="white-small-note">Digita le prime lettere della città</div>', unsafe_allow_html=True)

    if st.button("ENTRA", key="employee_enter_btn"):
        if not selected_label:
            st.warning("Seleziona un PDV.")
            return
        pdv_id = selected_label.split(" - ", 1)[0].strip()
        pdv_name = selected_label.split(" - ", 1)[1].strip()
        st.session_state.employee_selected_pdv_id = pdv_id
        st.session_state.employee_selected_pdv_name = pdv_name
        st.session_state.employee_page = 2
        st.rerun()


def employee_page_two() -> None:
    render_top_header()

    pdv_id = st.session_state.get("employee_selected_pdv_id", "")
    pdv_nome = st.session_state.get("employee_selected_pdv_name", "")

    top_cols = st.columns([1, 1, 5])
    with top_cols[0]:
        if st.button("TORNA ALLA LISTA PDV", key="back_to_pdv_list"):
            st.session_state.employee_page = 1
            st.rerun()
    with top_cols[1]:
        st.markdown(
            f'<a href="{HOME_URL}" target="_self" class="btn-link btn-link-dark">HOME</a>',
            unsafe_allow_html=True,
        )

    active_df = active_messages_for_pdv(pdv_id)

    messages_to_show = []
    if active_df.empty:
        generic = build_generic_message()
        messages_to_show.append(generic)
        upsert_open_log(pdv_id, pdv_nome, generic["msg_id"])
    else:
        for _, row in active_df.iterrows():
            messages_to_show.append(row.to_dict())
            upsert_open_log(pdv_id, pdv_nome, row["msg_id"])

    for i, msg in enumerate(messages_to_show, start=1):
        render_circular_message(i, msg, pdv_nome)

    st.markdown(
        """
        <div style="background:#ffffff;border-radius:8px;padding:20px;margin-top:12px;box-shadow:0 10px 22px rgba(0,0,0,0.18);">
            <div style="color:#111111;font-size:1rem;font-weight:800;margin-bottom:8px;">Conferme</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    read_key = f"read_confirm_{pdv_id}_{today_str()}"
    read_confirm = st.checkbox("Spunta la CONFERMA DI LETTURA", key=read_key)

    if read_confirm:
        for msg in messages_to_show:
            mark_read_log(pdv_id, msg["msg_id"])
        st.success("Conferma di lettura registrata.")


# =========================
# APP ROUTER
# =========================
if query_admin_mode():
    render_admin_page()
else:
    if "employee_page" not in st.session_state:
        st.session_state.employee_page = 1

    if st.session_state.employee_page == 1:
        employee_page_one()
    else:
        employee_page_two()
