import streamlit as st
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import folium
from streamlit_folium import folium_static

# Funzione per calcolare i centroidi delle aree verdi e costruire la rete
def create_graph(gdf):
    G = nx.Graph()
    
    # Aggiungere i nodi con peso basato sull'area
    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        G.add_node(idx, pos=(centroid.x, centroid.y), area=row.geometry.area)

    # Creare connessioni basate sulla distanza tra centroidi (puoi personalizzarlo)
    threshold = st.slider("Distanza massima tra nodi per connetterli (metri)", 50, 1000, 500)
    for i, row1 in gdf.iterrows():
        for j, row2 in gdf.iterrows():
            if i < j:
                dist = row1.geometry.centroid.distance(row2.geometry.centroid)
                if dist < threshold:
                    G.add_edge(i, j, weight=1/dist)  # Ponderazione con distanza inversa

    return G

# Funzione per calcolare gli indicatori della rete
def compute_metrics(G):
    N = G.number_of_nodes()
    E = G.number_of_edges()
    
    # Alpha (circuitazione)
    alpha = (E - N + 1) / (2 * N - 5) if N > 2 else 0

    # Beta (connessioni medie per nodo)
    beta = E / N if N > 0 else 0

    # Gamma (percentuale di connessioni presenti su massimo possibile)
    max_edges = 3 * (N - 2)  # Formula per grafi planari
    gamma = E / max_edges if max_edges > 0 else 0

    return alpha, beta, gamma

# Funzione per visualizzare il grafo con Matplotlib
def plot_graph(G):
    pos = nx.get_node_attributes(G, 'pos')
    areas = nx.get_node_attributes(G, 'area')
    
    plt.figure(figsize=(8, 6))
    nx.draw(G, pos, with_labels=True, node_size=[a*0.0005 for a in areas.values()], node_color='lightgreen', edge_color='gray', linewidths=0.5)
    plt.title("Rete delle Aree Verdi")
    st.pyplot(plt)

# Funzione per visualizzare le aree verdi su una mappa interattiva
def plot_map(gdf):
    m = folium.Map(location=[gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()], zoom_start=13)
    for _, row in gdf.iterrows():
        folium.GeoJson(row.geometry, style_function=lambda x: {"fillColor": "green", "color": "black", "weight": 1}).add_to(m)
    folium_static(m)

# Streamlit UI
st.title("🌿 Analisi della Connettività delle Aree Verdi")
st.write("Carica un file **GeoJSON o Shapefile** contenente le aree verdi e analizzeremo la loro connettività come una rete di grafi.")

uploaded_file = st.file_uploader("Carica un file vettoriale (.geojson o .shp)", type=["geojson", "shp"])

if uploaded_file:
    gdf = gpd.read_file(uploaded_file)
    st.write(f"✅ File caricato con **{len(gdf)} aree verdi**")
    
    # Visualizzazione della mappa
    st.subheader("Mappa delle Aree Verdi")
    plot_map(gdf)

    # Creazione della rete e calcolo degli indicatori
    G = create_graph(gdf)
    alpha, beta, gamma = compute_metrics(G)

    # Visualizzazione del grafo
    st.subheader("📌 Grafo delle Aree Verdi")
    plot_graph(G)

    # Visualizzazione degli indicatori
    st.subheader("📊 Indicatori di Connettività")
    st.write(f"**Alpha (Circuitazione)**: {alpha:.3f}")
    st.write(f"**Beta (Densità di Connessioni)**: {beta:.3f}")
    st.write(f"**Gamma (Connettività Relativa)**: {gamma:.3f}")