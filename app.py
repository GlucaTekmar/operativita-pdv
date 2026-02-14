import streamlit as st
import pandas as pd
from datetime import datetime
import os
import pickle

# --- CONFIGURAZIONE DATABASE E PERSISTENZA ---
DB_FILE = "database_finale.pkl"

def save_data():
    data = {
        'messaggi': st.session_state.messaggi,
        'anagrafica': st.session_state.anagrafica,
        'conferme': st.session_state.conferme
    }
    with open(DB_FILE, 'wb') as f:
        pickle.dump(data, f)

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'rb') as f:
            return pickle.load(f)
    return None

# Inizializzazione dati
saved = load_data()
if 'messaggi' not in st.session_state:
    st.session_state.messaggi = saved['messaggi'] if saved else []
if 'anagrafica' not in st.session_state:
    st.session_state.anagrafica = saved['anagrafica'] if saved else pd.DataFrame(columns=['Codice', 'Insegna', 'Città'])
if 'conferme' not in st.session_state:
    st.session_state.conferme = saved['conferme'] if saved else []

# --- STILE GRAFICO PERSONALIZZATO ---
st.markdown("""
<style>
.stApp { background-color: #E30613; }
h1, h2, h3, p, label, .stMarkdown { color: white !important; }
.stButton>button { 
    background-color: black !important; 
    color: white !important; 
    width: 100%; 
    border: 1px solid white;
    font-weight: bold;
}
.stSelectbox div[data-baseweb="select"] { background-color: white !important; }
.msg-container { 
    background-color: white; 
    color: black !important; 
    padding: 20px; 
    border-radius: 10px; 
    margin-bottom: 15px; 
    border: 3px solid #000;
}
.msg-title { 
    color: #E30613 !important; 
    font-weight: bold; 
    font-size: 22px; 
    border-bottom: 2px solid #eee; 
    margin-bottom: 10px; 
}
.msg-body { color: black !important; line-height: 1.6; }
.msg-body * { color: black !important; }
</style>
""", unsafe_allow_html=True)

# --- INTERFACCIA UTENTE (PDV) ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=250)
else:
    st.title("🔴 EDICOLE - OPERATIVITÀ")

st.subheader("Seleziona il tuo Punto Vendita")
st.caption("Digita le prime lettere della città per trovare il tuo PDV")

if not st.session_state.anagrafica.empty:
    df = st.session_state.anagrafica
    opzioni = df['Codice'].astype(str) + " - " + df['Insegna'] + " (" + df['Città'] + ")"
    scelta = st.selectbox("Cerca il tuo PDV:", ["Seleziona..."] + list(opzioni))
    
    if scelta != "Seleziona...":
        codice_utente = scelta.split(" - ")[0].strip()
        oggi = datetime.now().date()
        
        validi = [
            m for m in st.session_state.messaggi
            if codice_utente in m['target'] and m['inizio'] <= oggi <= m['fine']
        ]
        
        if validi:
            for i, m in enumerate(validi):
                with st.container():
                    st.markdown(f"""
                    <div class="msg-container">
                        <div class="msg-title">{m['titolo']}</div>
                        <div class="msg-body">{m['testo']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"✅ CONFERMA LETTURA: {m['titolo']}", key=f"conf_{i}"):
                        st.session_state.conferme.append({
                            'Data_Ora': datetime.now().strftime("%d/%m/%Y %H:%M"),
                            'PDV': codice_utente,
                            'Titolo_Messaggio': m['titolo']
                        })
                        save_data()
                        st.success("Lettura registrata con successo!")
            
            st.write("---")
            st.link_button("🔙 TORNA ALLA HOME APP", "https://eu.jotform.com/it/app/build/253605296903360")
            
        else:
            st.info("✅ Nessuna indicazione operativa per il tuo PDV oggi.")
            st.link_button("🔙 TORNA ALLA HOME APP", "https://eu.jotform.com/it/app/build/253605296903360")
else:
    st.warning("Sistema in fase di configurazione. Contattare l'amministratore.")

# --- AREA AMMINISTRATORE ---
with st.expander("🔐 Pannello Amministratore"):
    if st.text_input("Password di accesso", type="password") == "admin2026":
        
        st.subheader("1. Caricamento Anagrafica")
        up_anagrafica = st.file_uploader(
            "Carica Excel PDV (Codice, Insegna, Città)",
            type=['xlsx']
        )
        if up_anagrafica:
            st.session_state.anagrafica = pd.read_excel(up_anagrafica)
            save_data()
            st.success("Anagrafica aggiornata!")

        st.subheader("2. Nuova Indicazione")
        with st.form("form_messaggio", clear_on_submit=True):
            tit = st.text_input("Titolo dell'indicazione")
            txt = st.text_area("Testo (supporta tag HTML)")
            c1, c2 = st.columns(2)
            d_ini = c1.date_input("Inizio Validità")
            d_fin = c2.date_input("Fine Validità")
            pdv_target = st.text_area("Incolla Codici PDV (separati da virgola o invio)")
            
            if st.form_submit_button("PUBBLICA INDICAZIONE"):
                lista_target = [
                    c.strip()
                    for c in pdv_target.replace(',', '\n').split('\n')
                    if c.strip()
                ]
                st.session_state.messaggi.append({
                    'titolo': tit,
                    'testo': txt,
                    'inizio': d_ini,
                    'fine': d_fin,
                    'target': lista_target
                })
                save_data()
                st.success(f"Pubblicato per {len(lista_target)} PDV!")

        st.subheader("3. Report Conferme")
        if st.session_state.conferme:
            st.dataframe(pd.DataFrame(st.session_state.conferme))
            if st.button("Pulisci tutti i log"):
                st.session_state.conferme = []
                save_data()
                st.rerun()
