import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

st.set_page_config(layout="wide", page_title="Mappa con Folium")

# Esempio di dataframe con coordinate e nome dei parchi
data = {
    'Nome Parco': ['Parco A', 'Parco B', 'Parco C'],
    'lat': [45.70, 45.71, 45.69],
    'lon': [9.67, 9.68, 9.66],
    'Copertura Vegetale': [40, 55, 50]
}
df = pd.DataFrame(data)

# Crea la mappa centrata sulla media delle coordinate
m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13)

# Aggiungi marker o cerchi per ogni parco
for idx, row in df.iterrows():
    folium.CircleMarker(
        location=[row['lat'], row['lon']],
        radius=row['Copertura Vegetale'] / 5,  # Puoi regolare il fattore di scala
        popup=row['Nome Parco'],
        color='blue',
        fill=True,
        fill_color='blue',
        fill_opacity=0.6
    ).add_to(m)

# Visualizza la mappa in Streamlit
st.subheader("Mappa dei Parchi con Folium")
st_folium(m, width=700, height=500)
