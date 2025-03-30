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

df_parks = None
if uploaded_file is not None:
    try:
        df_parks = pd.read_excel(uploaded_file)
        st.success("File dei parchi caricato con successo!")
    except Exception as e:
        st.error("Errore nel caricamento del file: " + str(e))
        
if df_parks is None:
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

# Aggiungi la colonna "Valore" se non esiste, in modo che l'utente possa inserire un valore per ogni parco
if "Valore" not in df_parks.columns:
    df_parks["Valore"] = 0

st.subheader("Dati dei parchi")
st.dataframe(df_parks)

# 2. Visualizzazione sulla mappa per controllo
# Rinomina le colonne per Pydeck
df_map = df_parks.rename(columns={"Coordinata X": "lon", "Coordinata Y": "lat"})

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=df_map,
    get_position='[lon, lat]',
    get_fill_color='[0, 100, 200, 180]',  # colore blu con trasparenza
    get_radius=100,  # dimensione fissa per la visualizzazione
    pickable=True,
    auto_highlight=True,
)

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

# 3. Modifica dei dati a schermo
st.subheader("Modifica i dati dei parchi")
st.write("Modifica i valori nei campi sottostanti per aggiornare i dati del parco:")

# Creiamo un dataframe modificabile tramite widget (un input per ogni riga)
edited_df = df_parks.copy()
for idx, row in df_parks.iterrows():
    st.markdown(f"**Parco {idx + 1}: {row['Nome Parco']}**")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        nome = st.text_input("Nome Parco", value=row["Nome Parco"], key=f"nome_{idx}")
    with col2:
        cx = st.number_input("Coordinata X", value=row["Coordinata X"], key=f"cx_{idx}", format="%.3f")
    with col3:
        cy = st.number_input("Coordinata Y", value=row["Coordinata Y"], key=f"cy_{idx}", format="%.3f")
    with col4:
        valore = st.number_input("Valore", value=row["Valore"], key=f"val_{idx}")
    
    edited_df.at[idx, "Nome Parco"] = nome
    edited_df.at[idx, "Coordinata X"] = cx
    edited_df.at[idx, "Coordinata Y"] = cy
    edited_df.at[idx, "Valore"] = valore
    st.markdown("---")

st.subheader("Dati aggiornati")
st.dataframe(edited_df)

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
    # Opzionale: salvataggio locale
    edited_df.to_excel("parchi_modificati.xlsx", index=False)
    st.success("Dati salvati correttamente!")

