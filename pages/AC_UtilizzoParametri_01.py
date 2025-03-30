import streamlit as st
import pandas as pd
import pydeck as pdk
import io
import altair as alt

# Definisci variabili globali per evitare NameError
indicators = []
weights_dict = {}

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
        inds = df["Indicatore"].tolist()
        weights = df["Peso Relativo"].tolist()
        return inds, dict(zip(inds, weights))
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

def create_assignment_table(df_parks: pd.DataFrame, inds: list) -> pd.DataFrame:
    df = pd.DataFrame()
    df["Nome Parco"] = df_parks["Nome Parco"]
    for ind in inds:
        df[ind] = 0.0
    return df

def calculate_composite_values(df_parks: pd.DataFrame, assignment_df: pd.DataFrame, inds: list, weights_dict: dict) -> pd.DataFrame:
    merged = pd.merge(df_parks[["Nome Parco", "Copertura Vegetale"]], assignment_df, on="Nome Parco", how="left")
    composite_values = []
    for idx, row in merged.iterrows():
        weighted_sum = sum(weights_dict.get(ind, 0) * row.get(ind, 0) for ind in inds)
        composite = row["Copertura Vegetale"] * (1 + weighted_sum)
        composite_values.append(composite)
    if len(composite_values) == len(df_parks):
        df_parks["Composite Value"] = composite_values
    else:
        st.error("Errore nel calcolo dei valori compositi.")
    return df_parks

def calculate_parameters(df_parks: pd.DataFrame, L: int) -> tuple:
    V = df_parks.shape[0]
    max_L = int(V * (V - 1) / 2)
    if V <= 2:
        st.error("Il numero di parchi (V) deve essere maggiore di 2 per calcolare i parametri.")
        return V, max_L, None, None, None
    k = L / (3 * (V - 2))
    if (2 * V - 5) == 0:
        st.error("Il denominatore per il calcolo di ρ è zero.")
        return V, max_L, k, None, None
    rho = (L - (V + 1)) / (2 * V - 5)
    epsilon = k + rho
    return V, max_L, k, rho, epsilon

def prepare_analysis_data(df_parks: pd.DataFrame, assignment_df: pd.DataFrame, inds: list, weights_dict: dict) -> pd.DataFrame:
    # Unisci i dati originali dei parchi con la tabella di assegnazione
    merged = pd.merge(df_parks[["Nome Parco", "Copertura Vegetale"]], assignment_df, on="Nome Parco", how="left")
    # Calcola il breakdown per ciascun parco
    merged["Breakdown"] = merged.apply(
        lambda row: ", ".join(f"{ind}: {weights_dict.get(ind,0)*row.get(ind, 0):.2f}" for ind in inds), axis=1
    )
    # Unisci con il valore composito già calcolato
    analysis_df = pd.merge(merged, df_parks[["Nome Parco", "Composite Value"]], on="Nome Parco", how="left")
    return analysis_df

def display_maps(df_parks: pd.DataFrame):
    df_map = df_parks.copy().rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})
    df_map["radius_composite"] = df_map["Composite Value"] * 10
    df_map["radius_veg"] = df_map["Copertura Vegetale"] * 10
    view_state = pdk.ViewState(
        latitude=df_map["lat"].mean(),
        longitude=df_map["lon"].mean(),
        zoom=12,
        pitch=0,
    )
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

def display_analysis(analysis_df: pd.DataFrame):
    st.markdown("### Analisi Comparativa per Parco")
    # Prepara i dati per il grafico a barre: per ogni parco, mettiamo due valori (originale e composito)
    chart_data = analysis_df.melt(
        id_vars=["Nome Parco", "Copertura Vegetale", "Composite Value", "Breakdown"],
        value_vars=["Copertura Vegetale", "Composite Value"],
        var_name="Tipo Valore", value_name="Valore"
    )
    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Nome Parco:N", title="Parco"),
        y=alt.Y("Valore:Q", title="Valore"),
        color=alt.Color("Tipo Valore:N", scale=alt.Scale(domain=["Copertura Vegetale", "Composite Value"], range=["#1f77b4", "#d62728"])),
        tooltip=["Nome Parco", "Copertura Vegetale", "Composite Value", "Breakdown"]
    ).properties(
        width=700,
        height=400,
        title="Confronto per Parco: Valore Originale vs. Modificato"
    ).interactive()
    st.altair_chart(chart, use_container_width=True)

    st.markdown("Clicca (o passa il mouse) su una barra per vedere il dettaglio delle voci che compongono il valore (Breakdown).")

# ------------------------------
# Interfaccia a Tab per una migliore UX
# ------------------------------
st.set_page_config(layout="wide", page_title="AHP Parchi Bergamo")

tabs = st.tabs(["Dati", "Assegnazione e Calcoli", "Mappe", "Analisi & Download"])

# --- Tab 1: Dati ---
with tabs[0]:
    st.header("Caricamento Dati")
    st.write("Carica il file Excel dei pesi AHP e, se disponibile, il file Excel dei parchi. Se non carichi quest'ultimo, verrà usato un dataset di default.")
    ahp_file = st.file_uploader("File AHP", type=["xlsx"], key="ahp_tab1")
    if ahp_file is not None:
        indicators, weights_dict = load_ahp_data(ahp_file)
    parks_file = st.file_uploader("File dei Parchi (opzionale)", type=["xlsx"], key="parks_tab1")
    if parks_file is not None:
        df_parks = load_parks_data(parks_file)
    if parks_file is None or df_parks is None:
        df_parks = default_parks_data()
    st.subheader("Dati dei Parchi")
    st.dataframe(df_parks, use_container_width=True)

# --- Tab 2: Assegnazione e Calcoli ---
with tabs[1]:
    st.header("Assegnazione Valori e Calcoli")
    if not indicators:
        st.info("Carica il file AHP nella scheda 'Dati' per procedere con l'assegnazione degli indici.")
    else:
        st.write("Modifica la tabella per assegnare un valore (tra 0 e 1) agli indici per ciascun parco.")
        assignment_df = create_assignment_table(df_parks, indicators)
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
        for ind in indicators:
            if (edited_assignment_df[ind] < 0).any() or (edited_assignment_df[ind] > 1).any():
                st.error(f"I valori per l'indicatore '{ind}' devono essere compresi tra 0 e 1. Valori fuori range sono stati limitati.")
                edited_assignment_df[ind] = edited_assignment_df[ind].clip(lower=0, upper=1)
        st.subheader("Tabella di Assegnazione (modificata)")
        st.dataframe(edited_assignment_df, use_container_width=True)
        df_parks = calculate_composite_values(df_parks.copy(), edited_assignment_df, indicators, weights_dict)
        st.subheader("Dati dei Parchi con Valore Composito")
        st.dataframe(df_parks, use_container_width=True)
        L_val = st.slider("Seleziona L (numero di coppie di parchi)", min_value=0, max_value=int(df_parks.shape[0]*(df_parks.shape[0]-1)/2), value=0)
        V, max_L, k, rho, epsilon = calculate_parameters(df_parks, L_val)
        if k is not None and rho is not None:
            st.markdown("#### Parametri")
            st.write(f"**Numero di parchi (V):** {V}")
            st.write(f"**L (coppie):** {L_val} (max: {max_L})")
            st.write(f"**Connettività (k):** {k}")
            st.write(f"**Resilienza (ρ):** {rho}")
            st.write(f"**Epsilon (k+ρ):** {epsilon}")
        # Salva dati in session_state per le altre schede
        st.session_state.df_parks = df_parks
        st.session_state.edited_assignment_df = edited_assignment_df

# --- Tab 3: Mappe ---
with tabs[2]:
    st.header("Visualizzazione delle Mappe")
    if "df_parks" not in st.session_state:
        st.error("Prima calcola i valori compositi nella scheda 'Assegnazione e Calcoli'.")
    else:
        # Copia del dataframe e rinomina per Pydeck
        df_map = st.session_state.df_parks.copy().rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})
        
        # Slider per regolare il fattore di scala dei marker
        scale_factor = st.slider("Regola il fattore di scala dei marker", min_value=5, max_value=20, value=10)
        df_map["radius_composite"] = df_map["Composite Value"] * scale_factor
        df_map["radius_veg"] = df_map["Copertura Vegetale"] * scale_factor
        
        # Stato iniziale della vista
        view_state = pdk.ViewState(
            latitude=df_map["lat"].mean(),
            longitude=df_map["lon"].mean(),
            zoom=12,
            pitch=0,
        )
        
        # Possibilità di scegliere quale mappa visualizzare
        map_option = st.radio(
            "Scegli il tipo di mappa da visualizzare",
            ("Mappa Composite", "Mappa Vegetazione", "Visualizza Entrambe")
        )
        
        if map_option in ("Mappa Composite", "Visualizza Entrambe"):
            st.subheader("Mappa: Copertura Vegetale × (1 + AHP)")
            composite_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position='[lon, lat]',
                get_fill_color='[200,50,80,180]',
                get_radius="radius_composite",
                pickable=True,
                auto_highlight=True,
            )
            composite_deck = pdk.Deck(
                layers=[composite_layer],
                initial_view_state=view_state,
                tooltip={"text": "{Nome Parco}\nComposite: {Composite Value}"}
            )
            st.pydeck_chart(composite_deck)
        
        if map_option in ("Mappa Vegetazione", "Visualizza Entrambe"):
            st.subheader("Mappa: Copertura Vegetale")
            veg_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position='[lon, lat]',
                get_fill_color='[50,150,200,180]',
                get_radius="radius_veg",
                pickable=True,
                auto_highlight=True,
            )
            veg_deck = pdk.Deck(
                layers=[veg_layer],
                initial_view_state=view_state,
                tooltip={"text": "{Nome Parco}\nCopertura: {Copertura Vegetale}"}
            )
            st.pydeck_chart(veg_deck)

# --- Tab 4: Analisi & Download ---
with tabs[3]:
    st.header("Analisi e Download")
    if "df_parks" not in st.session_state or "edited_assignment_df" not in st.session_state:
        st.error("Prima calcola i valori compositi nella scheda 'Assegnazione e Calcoli'.")
    else:
        # Prepara il dataframe di analisi con un breakdown dei contributi
        analysis_df = prepare_analysis_data(
            st.session_state.df_parks,
            st.session_state.edited_assignment_df,
            indicators,
            weights_dict
        )
        
        st.markdown("#### Confronto per Parco: Valore Originale vs. Modificato")
        st.dataframe(
            analysis_df[["Nome Parco", "Copertura Vegetale", "Composite Value", "Breakdown"]],
            use_container_width=True
        )
        
        # Grafico interattivo con Altair: confronto dei due valori per ciascun parco
        chart_data = analysis_df.melt(
            id_vars=["Nome Parco", "Copertura Vegetale", "Composite Value", "Breakdown"],
            value_vars=["Copertura Vegetale", "Composite Value"],
            var_name="Tipo Valore",
            value_name="Valore"
        )
        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X("Nome Parco:N", title="Parco", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("Valore:Q", title="Valore"),
            color=alt.Color(
                "Tipo Valore:N",
                scale=alt.Scale(
                    domain=["Copertura Vegetale", "Composite Value"],
                    range=["#1f77b4", "#d62728"]
                )
            ),
            tooltip=["Nome Parco", "Copertura Vegetale", "Composite Value", "Breakdown"]
        ).properties(
            width=700,
            height=400,
            title="Confronto per Parco: Valore Originale vs. Modificato"
        ).interactive()
        st.altair_chart(chart, use_container_width=True)
        
        # Selezione manuale del parco per vedere il dettaglio del breakdown
        park_selected = st.selectbox(
            "Seleziona un parco per visualizzare il dettaglio del breakdown",
            analysis_df["Nome Parco"].unique()
        )
        breakdown_info = analysis_df.loc[analysis_df["Nome Parco"] == park_selected, "Breakdown"].iloc[0]
        st.markdown(f"**Breakdown per {park_selected}:** {breakdown_info}")
        
        # Download della tabella di analisi in Excel
        if st.button("Scarica tabella di analisi in Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                analysis_df.to_excel(writer, index=False, sheet_name="Analisi")
            st.download_button(
                label="Download Excel",
                data=output.getvalue(),
                file_name="analisi_parchi.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("File Excel generato con successo!")



