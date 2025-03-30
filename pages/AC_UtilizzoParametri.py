import streamlit as st
import pandas as pd
import pydeck as pdk
import io

# ================================
# Titolo e descrizione della pagina
# ================================
st.title("Assegnazione Valori AHP ai Parchi e Visualizzazione su Mappa")
st.write("Carica i file necessari, assegna un valore (tra 0 e 1) agli indici per ciascun parco e visualizza i risultati su due mappe affiancate.")

# ================================
# 1. Caricamento file AHP
# ================================
ahp_file = st.file_uploader("Carica il file Excel dei pesi AHP (colonne: 'Indicatore' e 'Peso Relativo')", type=["xlsx"], key="ahp")
if ahp_file is not None:
    try:
        ahp_df = pd.read_excel(ahp_file)
        st.success("File AHP caricato con successo!")
        if "Indicatore" not in ahp_df.columns or "Peso Relativo" not in ahp_df.columns:
            st.error("Il file AHP deve contenere le colonne 'Indicatore' e 'Peso Relativo'.")
            indicators = []
            weights_dict = {}
        else:
            indicators = ahp_df["Indicatore"].tolist()
            weights = ahp_df["Peso Relativo"].tolist()
            weights_dict = dict(zip(indicators, weights))
            st.write("Indicatori trovati:", indicators)
    except Exception as e:
        st.error("Errore nel caricamento del file AHP: " + str(e))
        indicators = []
        weights_dict = {}
else:
    st.warning("Carica il file AHP per procedere.")
    indicators = []
    weights_dict = {}

# ================================
# 2. Caricamento dataset Parchi
# ================================
uploaded_parks = st.file_uploader("Carica il file Excel dei parchi (opzionale)", type=["xlsx"], key="parks")
df_parks = None
if uploaded_parks is not None:
    try:
        df_parks = pd.read_excel(uploaded_parks)
        st.success("File dei parchi caricato!")
        required_cols = ["Nome Parco", "Coordinata X", "Coordinata Y", "Copertura Vegetale"]
        if not all(col in df_parks.columns for col in required_cols):

