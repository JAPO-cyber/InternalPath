import streamlit as st
import pandas as pd
import pydeck as pdk
import io
import altair as alt

# ------------------------------
# Funzioni di utilità
# ------------------------------
@st.cache_data(show_spinner=False)
def load_excel(file) -> pd.DataFrame:
    return pd.read_excel(file)

def load_ahp_data(file) -> tuple:
    try:
        df = load_excel(file)
        if "Indicatore" not in df.columns or "Peso Relativo" not in df.columns:
            st.error("Il file AHP deve contenere le colonne 'Indicatore' e 'Peso Relativo'.")
            return [], {}
        indicators = df["Indicatore"].tolist()
        weights = df["Peso Relativo"].tolist()
        weights_dict = dict(zip(indicators, weights))
        return indicators, weights_dict
    except Exception as e:
        st.error(f"Errore nel caricamento del file AHP: {e}")
        return [], {}

def load_parks_data(file) -> pd.DataFrame:
    try:
        df = load_excel(file)
        required = ["Nome Parco", "Coordinata X", "Coordinata Y", "Copertura Vegetale"]
        if not all(col in df.columns for col in required):
            st.error("Il file dei parchi deve contenere le colonne: " + ", ".join(required))
            raise Exception("Colonne mancanti")
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento del file dei parchi: {e}")
        return None

def default_parks_data() -> pd.DataFrame:
    data = [
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
    return pd.DataFrame(data)

def create_assignment_table(df_parks: pd.DataFrame, indicators: list) -> pd.DataFrame:
    df = pd.DataFrame()
    df["Nome Parco"] = df_parks["Nome Parco"]
    for ind in indicators:
        df[ind] = 0.0
    return df

def calculate_composite_values(df_parks: pd.DataFrame, assignment_df: pd.DataFrame, indicators: list, weights_dict: dict) -> pd.DataFrame:
    merged = pd.merge(df_parks[["Nome Parco", "Copertura Vegetale"]], assignment_df, on="Nome Parco", how="left")
    composite_values = []
    for idx, row in merged.iterrows():
        weighted_sum = sum(weights_dict.get(ind, 0) * row.get(ind, 0) for ind in indicators)
        composite = row["Copertura Vegetale"] * (1 + weighted_sum)
        composite_values.append(composite)
    if len(composite_values) == len(df_parks):
        df_parks["Composite Value"] = composite_values
    else:
        st.error("Errore nel calcolo dei valori compositi.")
    return df_parks

def calculate_parameters(df_parks: pd.DataFrame, L: int) -> tuple:
    V = df_parks.shape[0]
    # max coppie non ordinate
    max_L = int(V * (V - 1) / 2)
    if V <= 2:
        st.error("Il numero di parchi (V) deve essere maggiore di 2 per calcolare i parametri.")
        return V, max_L, None, None, None
    # k = L / (3*(V-2))
    k = L / (3 * (V - 2))
    # rho = (L - (V+1)) / (2*V - 5)
    if (2 * V - 5) == 0:
        st.error("Il denominatore per il calcolo di ρ è zero.")
        return V, max_L, k, None, None
    rho = (L - (V + 1)) / (2 * V - 5)
    epsilon = k + rho
    return V, max_L, k, rho, epsilon

def display_maps(df_parks: pd.DataFrame):
    # Prepara i dati per Pydeck
    df_map = df_parks.copy().rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})
    df_map["radius_composite"] = df_map["Composite Value"] * 10
    df_map["radius_veg"] = df_map["Copertura Vegetale"] * 10

    view_state = pdk.ViewState(
        latitude=df_map["lat"].mean(),
        longitude=df_map["lon"].mean(),
        zoom=12,
        pitch=0,
    )

    # Legenda in HTML
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

    col_left, col_right = st.columns(2)

    # Mappa Composite
    left_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position='[lon, lat]',
        get_fill_color='[200,50,80,180]',
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

    # Mappa Vegetazione
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

def display_analysis(df_parks: pd.DataFrame, epsilon: float):
    st.markdown("### Analisi e Download")
    # Calcola φ = (somma dei Composite Value) * (1 + ε)
    phi = df_parks["Composite Value"].sum() * (1 + epsilon)
    # Standard urbanistico: somma di Copertura Vegetale
    urban_standard = df_parks["Copertura Vegetale"].sum()
    if urban_standard != 0:
        percent_increase = ((phi - urban_standard) / urban_standard) * 100
    else:
        percent_increase = None

    st.write(f"**φ (Dotazione di servizi ecosistemici):** {phi:.2f}")
    st.write(f"**Standard urbanistico (Somma Copertura Vegetale):** {urban_standard:.2f}")
    if percent_increase is not None:
        st.write(f"**Aumento percentuale rispetto allo standard:** {percent_increase:.2f}%")

    # Grafico: distribuzione dei valori compositi
    chart_data = df_parks[["Nome Parco", "Composite Value"]]
    bar_chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Nome Parco:N", sort=None, title="Parco"),
        y=alt.Y("Composite Value:Q", title="Valore Composito"),
        tooltip=["Nome Parco", "Composite Value"]
    ).properties(
        width=600,
        height=300,
        title="Distribuzione dei Valori Compositi"
    )
    st.altair_chart(bar_chart, use_container_width=True)

    # Pulsante di download della tabella di assegnazione
    if st.button("Salva tabella assegnazioni in Excel"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_assignment_df.to_excel(writer, index=False, sheet_name='Assegnazioni')
        st.download_button(
            label="Scarica il file Excel delle assegnazioni",
            data=output.getvalue(),
            file_name="assegnazioni_parchi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.success("Tabella salvata correttamente!")

# ------------------------------
# Interfaccia a Tab per migliorare l'esperienza UX
# ------------------------------
tabs = st.tabs(["Dati", "Assegnazione e Calcoli", "Mappe", "Analisi & Download"])

# --- Tab 1: Dati ---
with tabs[0]:
    st.header("Caricamento Dati")
    st.write("Carica il file Excel dei pesi AHP e, se disponibile, il file Excel dei parchi. Se non carichi quest'ultimo, verrà usato un dataset di default.")
    # (I file sono già stati caricati nelle sezioni sopra.)

# --- Tab 2: Assegnazione e Calcoli ---
with tabs[1]:
    st.header("Assegnazione Valori e Calcoli")
    if not indicators:
        st.info("Carica il file AHP per procedere con l'assegnazione degli indici.")
    else:
        st.write("Modifica la tabella per assegnare un valore (tra 0 e 1) agli indici per ciascun parco.")
        # Mostriamo la tabella di assegnazione (già creata sopra)
        st.dataframe(edited_assignment_df, use_container_width=True)
        # Calcolo del valore composito
        df_parks_updated = calculate_composite_values(df_parks.copy(), edited_assignment_df, indicators, weights_dict)
        st.subheader("Dati dei Parchi con Valore Composito")
        st.dataframe(df_parks_updated, use_container_width=True)
        # Parametri: impostiamo L tramite sidebar per questa sezione
        V, max_L, k, rho, epsilon = calculate_parameters(df_parks_updated, st.slider("Seleziona L (numero di coppie di parchi)", min_value=0, max_value=int(df_parks_updated.shape[0]*(df_parks_updated.shape[0]-1)/2), value=0))
        if k is not None and rho is not None:
            st.markdown("#### Parametri")
            st.write(f"**Numero di parchi (V):** {V}")
            st.write(f"**L (coppie):** {L} (max: {max_L})")
            st.write(f"**Connettività (k):** {k}")
            st.write(f"**Resilienza (ρ):** {rho}")
            st.write(f"**Epsilon (k+ρ):** {epsilon}")

# --- Tab 3: Mappe ---
with tabs[2]:
    st.header("Visualizzazione delle Mappe")
    if "Composite Value" not in df_parks.columns:
        st.error("Prima calcola i valori compositi nella sezione 'Assegnazione e Calcoli'.")
    else:
        display_maps(df_parks)

# --- Tab 4: Analisi & Download ---
with tabs[3]:
    st.header("Analisi e Download")
    if "Composite Value" not in df_parks.columns:
        st.error("Prima calcola i valori compositi nella sezione 'Assegnazione e Calcoli'.")
    else:
        display_analysis(df_parks, epsilon if epsilon is not None else 0)
