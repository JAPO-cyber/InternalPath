import streamlit as st
import pandas as pd
import pydeck as pdk
import io

st.title("Assegnazione Valori AHP ai Parchi e Visualizzazione su Mappa")

# --------------------------
# 1. Caricamento file AHP
# --------------------------
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

# --------------------------
# 2. Caricamento dataset Parchi
# --------------------------
uploaded_parks = st.file_uploader("Carica il file Excel dei parchi (opzionale)", type=["xlsx"], key="parks")
df_parks = None
if uploaded_parks is not None:
    try:
        df_parks = pd.read_excel(uploaded_parks)
        st.success("File dei parchi caricato!")
        # Verifica le colonne necessarie
        required_cols = ["Nome Parco", "Coordinata X", "Coordinata Y", "Copertura Vegetale"]
        if not all(col in df_parks.columns for col in required_cols):
            st.error("Il file dei parchi deve contenere le colonne: " + ", ".join(required_cols))
            raise Exception("Colonne mancanti")
    except Exception as e:
        st.error("Errore nel caricamento del file dei parchi: " + str(e))
        df_parks = None

if uploaded_parks is None or df_parks is None:
    # Dataset di default con la colonna "Copertura Vegetale"
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
st.dataframe(df_parks)

# --------------------------
# 3. Tabella di Assegnazione Valori
# --------------------------
if indicators:
    st.subheader("Assegna un valore (tra 0 e 1) agli indici per ogni parco")
    # Crea un dataframe per la tabella di assegnazione; la prima colonna è "Nome Parco"
    assignment_df = pd.DataFrame()
    assignment_df["Nome Parco"] = df_parks["Nome Parco"]
    
    # Per ogni indicatore, crea una serie di input (uno per ogni parco)
    for indicator in indicators:
        st.markdown(f"#### Valori per l'indicatore: **{indicator}**")
        values = []
        for idx, row in df_parks.iterrows():
            val = st.number_input(
                label=f"{row['Nome Parco']} - {indicator}",
                min_value=0.0,
                max_value=1.0,
                value=0.0,
                step=0.01,
                key=f"{indicator}_{idx}"
            )
            values.append(val)
        assignment_df[indicator] = values
    
    st.subheader("Tabella di assegnazione valori")
    st.dataframe(assignment_df)
    
    # Calcolo del valore composito per ogni parco:
    # composite = Copertura Vegetale + somma(per ogni indicatore: (Peso AHP * valore assegnato))
    composite_values = []
    for idx, row in assignment_df.iterrows():
        weighted_sum = 0
        for indicator in indicators:
            weight = weights_dict.get(indicator, 0)
            assigned = row[indicator]
            weighted_sum += weight * assigned
        veg_cover = df_parks.loc[idx, "Copertura Vegetale"]
        composite = veg_cover + weighted_sum
        composite_values.append(composite)
    
    # Aggiungiamo la colonna "Composite Value" al dataframe dei parchi
    df_parks["Composite Value"] = composite_values
else:
    st.info("Carica il file AHP per assegnare valori agli indici.")

# --------------------------
# 4. Visualizzazione su Mappa in due colonne
# --------------------------
st.subheader("Visualizzazione dei Parchi su Mappa")

# Prepara i dati per Pydeck: rinomina le colonne per le coordinate
df_map = df_parks.rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})

# Creiamo due colonne per visualizzare le mappe affiancate
col_left, col_right = st.columns(2)

# Mappa di sinistra: dimensione = Copertura Vegetale + (Peso AHP * Valore)
if "Composite Value" in df_parks.columns:
    left_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[lon, lat]',
        get_fill_color='[200, 50, 80, 180]',
        # Moltiplichiamo per un fattore di scala (ad esempio 10) per evidenziare la dimensione
        get_radius="Composite Value * 10",
        pickable=True,
        auto_highlight=True,
    )
    left_deck = pdk.Deck(
        layers=[left_layer],
        initial_view_state=pdk.ViewState(
            latitude=df_map["lat"].mean(),
            longitude=df_map["lon"].mean(),
            zoom=12,
            pitch=0,
        ),
        tooltip={"text": "{Nome Parco}"}
    )
    col_left.subheader("Mappa con dimensione = Copertura Vegetale + AHP")
    col_left.pydeck_chart(left_deck)

# Mappa di destra: dimensione = Copertura Vegetale
right_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position='[lon, lat]',
    get_fill_color='[50, 150, 200, 180]',
    get_radius="Copertura Vegetale * 10",
    pickable=True,
    auto_highlight=True,
)
right_deck = pdk.Deck(
    layers=[right_layer],
    initial_view_state=pdk.ViewState(
        latitude=df_map["lat"].mean(),
        longitude=df_map["lon"].mean(),
        zoom=12,
        pitch=0,
    ),
    tooltip={"text": "{Nome Parco}"}
)
col_right.subheader("Mappa con dimensione = Copertura Vegetale")
col_right.pydeck_chart(right_deck)

# --------------------------
# 5. Salvataggio della Tabella di Assegnazione
# --------------------------
if indicators:
    if st.button("Salva tabella assegnazioni in Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            assignment_df.to_excel(writer, index=False, sheet_name='Assegnazioni')
        excel_data = output.getvalue()
        st.download_button(
            label="Scarica il file Excel delle assegnazioni",
            data=excel_data,
            file_name="assegnazioni_parchi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("Tabella salvata correttamente!")

