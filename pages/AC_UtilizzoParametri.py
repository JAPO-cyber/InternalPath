import streamlit as st
import pandas as pd
import pydeck as pdk
import io

st.title("Gestione e Visualizzazione Parchi di Bergamo")

# 1. Caricamento opzionale del dataframe dei parchi
uploaded_file = st.file_uploader(
    "Carica il file dei parchi (Excel) oppure lascia vuoto per usare il dataset di default",
    type=["xlsx"]
)

if uploaded_file is not None:
    try:
        df_parks = pd.read_excel(uploaded_file)
        st.success("File dei parchi caricato con successo!")
    except Exception as e:
        st.error("Errore nel caricamento del file: " + str(e))
        df_parks = None
if uploaded_file is None or df_parks is None:
    # Dataset di default per i parchi del comune di Bergamo
    data_parks = [
        {"Nome Parco": "Parco dei Colli", "Coordinata X": 9.680, "Coordinata Y": 45.700},
        {"Nome Parco": "Parco Ticinello", "Coordinata X": 9.670, "Coordinata Y": 45.690},
        {"Nome Parco": "Parco Villa Sotto", "Coordinata X": 9.660, "Coordinata Y": 45.710},
        {"Nome Parco": "Parco Comunale", "Coordinata X": 9.680, "Coordinata Y": 45.680},
        {"Nome Parco": "Parco di via XX Settembre", "Coordinata X": 9.690, "Coordinata Y": 45.700},
        {"Nome Parco": "Parco della Rimembranza", "Coordinata X": 9.670, "Coordinata Y": 45.710},
        {"Nome Parco": "Parco del Lago", "Coordinata X": 9.650, "Coordinata Y": 45.700},
        {"Nome Parco": "Parco Nord", "Coordinata X": 9.660, "Coordinata Y": 45.690},
        {"Nome Parco": "Parco Est", "Coordinata X": 9.700, "Coordinata Y": 45.680},
        {"Nome Parco": "Parco Ovest", "Coordinata X": 9.680, "Coordinata Y": 45.720}
    ]
    df_parks = pd.DataFrame(data_parks)

# Aggiungi la colonna "Valore" se non esiste, così l'utente potrà inserire un valore per ogni parco
if "Valore" not in df_parks.columns:
    df_parks["Valore"] = 0

st.subheader("Dati dei parchi")
st.dataframe(df_parks)

# 2. Visualizzazione dei parchi sulla mappa per controllo
# Rinominiamo le colonne in 'lat' e 'lon' per Pydeck
df_map = df_parks.rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})

# Creazione di uno ScatterplotLayer per visualizzare le bolle dei parchi
scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position='[lon, lat]',
    get_fill_color='[0, 100, 200, 180]',  # colore blu con trasparenza
    get_radius=100,                       # dimensione fissa per la visualizzazione
    pickable=True,
    auto_highlight=True,
)

# Impostazione della vista centrata sul comune di Bergamo
view_state = pdk.ViewState(
    latitude=df_map["lat"].mean(),
    longitude=df_map["lon"].mean(),
    zoom=12,
    pitch=0,
)

deck = pdk.Deck(
    layers=[scatter_layer],
    initial_view_state=view_state,
    tooltip={"text": "{Nome Parco}"}
)

st.subheader("Verifica la posizione dei parchi sulla mappa")
st.pydeck_chart(deck)

# 3. Modifica a schermo dei dati tramite data editor
st.subheader("Modifica i dati dei parchi")
edited_df = st.experimental_data_editor(
    df_parks,
    num_rows="dynamic",
    use_container_width=True,
    key="data_editor_parks"
)

# 4. Salvataggio dei dati modificati
if st.button("Salva dati modificati in Excel"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        edited_df.to_excel(writer, index=False, sheet_name='Parchi')
    excel_data = output.getvalue()
    
    st.download_button(
        label="Scarica il file Excel aggiornato",
        data=excel_data,
        file_name="parchi_modificati.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    # Inoltre, si può salvare localmente se necessario
    edited_df.to_excel("parchi_modificati.xlsx", index=False)
    st.success("Dati salvati correttamente!")

