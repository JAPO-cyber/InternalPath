import streamlit as st
import pandas as pd
import pydeck as pdk
import io

# Imposta il layout a schermo intero (wide) per PC
st.set_page_config(layout="wide", page_title="AHP Parchi Bergamo")

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
            st.error("Il file dei parchi deve contenere le colonne: " + ", ".join(required_cols))
            raise Exception("Colonne mancanti")
    except Exception as e:
        st.error("Errore nel caricamento del file dei parchi: " + str(e))
        df_parks = None

if uploaded_parks is None or df_parks is None:
    # Dataset di default per i parchi
    data_parks = [
        {"Nome Parco": "Parco dei Colli",         "Coordinata X": 9.680, "Coordinata Y": 45.700, "Copertura Vegetale": 40},
        {"Nome Parco": "Parco Ticinello",         "Coordinata X": 9.670, "Coordinata Y": 45.690, "Copertura Vegetale": 50},
        {"Nome Parco": "Parco Villa Sotto",       "Coordinata X": 9.660, "Coordinata Y": 45.710, "Copertura Vegetale": 35},
        {"Nome Parco": "Parco Comunale",          "Coordinata X": 9.680, "Coordinata Y": 45.680, "Copertura Vegetale": 45},
        {"Nome Parco": "Parco di via XX Settembre", "Coordinata X": 9.690, "Coordinata Y": 45.700, "Copertura Vegetale": 55},
        {"Nome Parco": "Parco della Rimembranza", "Coordinata X": 9.670, "Coordinata Y": 45.710, "Copertura Vegetale": 60},
        {"Nome Parco": "Parco del Lago",          "Coordinata X": 9.650, "Coordinata Y": 45.700, "Copertura Vegetale": 30},
        {"Nome Parco": "Parco Nord",              "Coordinata X": 9.660, "Coordinata Y": 45.690, "Copertura Vegetale": 50},
        {"Nome Parco": "Parco Est",               "Coordinata X": 9.700, "Coordinata Y": 45.680, "Copertura Vegetale": 40},
        {"Nome Parco": "Parco Ovest",             "Coordinata X": 9.680, "Coordinata Y": 45.720, "Copertura Vegetale": 65}
    ]
    df_parks = pd.DataFrame(data_parks)

st.subheader("Dati dei Parchi")
st.dataframe(df_parks, use_container_width=True)

# ================================
# 3. Tabella di Assegnazione Valori
# ================================
if indicators:
    st.subheader("Assegna un valore (tra 0 e 1) agli indici per ciascun parco")
    # Crea un dataframe di assegnazione: la prima colonna è "Nome Parco"
    assignment_df = pd.DataFrame()
    assignment_df["Nome Parco"] = df_parks["Nome Parco"]
    for indicator in indicators:
        assignment_df[indicator] = 0.0

    st.markdown("### Modifica la tabella dei valori da assegnare")
    # Usa il data editor se disponibile, ottimizzando lo spazio con use_container_width
    if hasattr(st, "experimental_data_editor"):
        edited_assignment_df = st.experimental_data_editor(assignment_df, num_rows="dynamic", use_container_width=True)
    elif hasattr(st, "data_editor"):
        edited_assignment_df = st.data_editor(assignment_df, num_rows="dynamic", use_container_width=True)
    else:
        st.info("Il data editor non è disponibile. Modifica il CSV sottostante e premi INVIO.")
        csv_text = st.text_area("Modifica CSV", assignment_df.to_csv(index=False))
        try:
            edited_assignment_df = pd.read_csv(io.StringIO(csv_text))
        except Exception as e:
            st.error("Errore nella conversione del CSV: " + str(e))
            edited_assignment_df = assignment_df

    st.subheader("Tabella di assegnazione valori (modificata)")
    st.dataframe(edited_assignment_df, use_container_width=True)

    # ================================
    # 4. Calcolo del Valore Composito
    # ================================
    # Calcolo: Composite = Copertura Vegetale * (1 + sum_i(Peso_i * Valore_i))
    composite_values = []
    merged_df = pd.merge(df_parks[["Nome Parco", "Copertura Vegetale"]], edited_assignment_df, on="Nome Parco", how="left")
    for idx, row in merged_df.iterrows():
        weighted_sum = 0
        for indicator in indicators:
            weight = weights_dict.get(indicator, 0)
            assigned_value = row.get(indicator, 0)
            weighted_sum += weight * assigned_value
        veg_cover = row["Copertura Vegetale"]
        composite = veg_cover * (1 + weighted_sum)
        composite_values.append(composite)
    df_parks["Composite Value"] = composite_values

    st.subheader("Dati dei Parchi con Valore Composito")
    st.dataframe(df_parks, use_container_width=True)
else:
    st.info("Carica il file AHP per assegnare i valori agli indici.")

# ================================
# 5. Visualizzazione su Mappa
# ================================
st.subheader("Visualizzazione dei Parchi su Mappa")

# Prepara i dati per Pydeck (rinomina le colonne per le coordinate)
df_map = df_parks.copy().rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})

# Aggiungi colonne per il raggio dei pallini (fattore di scala 10)
df_map["radius_composite"] = df_map["Composite Value"] * 10
df_map["radius_veg"] = df_map["Copertura Vegetale"] * 10

# Vista iniziale centrata sui parchi
view_state = pdk.ViewState(
    latitude=df_map["lat"].mean(),
    longitude=df_map["lon"].mean(),
    zoom=12,
    pitch=0,
)

# Creazione della legenda in HTML (ottimizzata per PC)
legend_html = """
<div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 14px;">
  <h4 style="margin-bottom: 5px;">Legenda Mappa</h4>
  <ul style="list-style-type: none; padding-left: 0; margin: 0;">
    <li>
      <span style="display:inline-block;width:12px;height:12px;background-color: rgb(200,50,80);margin-right:5px;"></span>
      <strong>Mappa Composite:</strong> Dimensione = Copertura Vegetale × (1 + AHP)
    </li>
    <li>
      <span style="display:inline-block;width:12px;height:12px;background-color: rgb(50,150,200);margin-right:5px;"></span>
      <strong>Mappa Vegetazione:</strong> Dimensione = Copertura Vegetale
    </li>
  </ul>
</div>
"""
st.markdown(legend_html, unsafe_allow_html=True)

# Disposizione delle mappe affiancate in due colonne
col_left, col_right = st.columns(2)

# Mappa di sinistra: dimensione = Composite Value
left_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position='[lon, lat]',
    get_fill_color='[200, 50, 80, 180]',
    get_radius="radius_composite",
    pickable=True,
    auto_highlight=True,
)
left_deck = pdk.Deck(
    layers=[left_layer],
    initial_view_state=view_state,
    tooltip={"text": "{Nome Parco}\nComposite: {Composite Value}"}
)
col_left.subheader("Mappa: Copertura Vegetale × (1 + AHP)")
col_left.pydeck_chart(left_deck)

# Mappa di destra: dimensione = Copertura Vegetale
right_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position='[lon, lat]',
    get_fill_color='[50,150,200,180]',
    get_radius="radius_veg",
    pickable=True,
    auto_highlight=True,
)
right_deck = pdk.Deck(
    layers=[right_layer],
    initial_view_state=view_state,
    tooltip={"text": "{Nome Parco}\nCopertura: {Copertura Vegetale}"}
)
col_right.subheader("Mappa: Copertura Vegetale")
col_right.pydeck_chart(right_deck)

# ================================
# 6. Salvataggio della Tabella di Assegnazione
# ================================
if indicators:
    st.subheader("Salvataggio della Tabella di Assegnazione")
    if st.button("Salva tabella assegnazioni in Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_assignment_df.to_excel(writer, index=False, sheet_name='Assegnazioni')
        excel_data = output.getvalue()
        st.download_button(
            label="Scarica il file Excel delle assegnazioni",
            data=excel_data,
            file_name="assegnazioni_parchi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("Tabella salvata correttamente!")


