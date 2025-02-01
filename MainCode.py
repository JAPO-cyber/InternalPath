import math
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import streamlit as st

# 1. Definizione della classe Punto
class Punto:
    def __init__(self, x, y, categoria=None, id=None):
        self.x = x
        self.y = y
        self.categoria = categoria  # "macchina" o "corridoio"
        self.id = id                # identificativo unico

    def __repr__(self):
        return f"Punto(id={self.id}, x={self.x}, y={self.y}, categoria={self.categoria})"

# Funzione per calcolare la distanza euclidea fra due punti
def euclidean_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

# Funzione per costruire il grafo e calcolare i percorsi
def costruisci_grafo():
    # 2. Configurazione dei punti per macchine e corridoi
    macchine = [
        Punto(10, 20, categoria="macchina", id="M1"),
        Punto(15, 25, categoria="macchina", id="M2"),
        Punto(30, 40, categoria="macchina", id="M3")
    ]
    
    corridoi = [
        Punto(5, 5, categoria="corridoio", id="C1"),
        Punto(12, 18, categoria="corridoio", id="C2"),
        Punto(25, 30, categoria="corridoio", id="C3")
    ]
    
    # 3. Costruiamo il grafo
    G = nx.Graph()
    
    # Aggiungiamo tutti i punti come nodi, associando ogni oggetto Punto come attributo
    for punto in macchine + corridoi:
        G.add_node(punto.id, punto=punto)
    
    # 3.1. Per ogni macchina, aggiungiamo l'arco con il corridoio più vicino
    for m in macchine:
        # Calcoliamo la distanza verso ogni corridoio
        distanze = [(c, euclidean_distance(m, c)) for c in corridoi]
        # Selezioniamo il corridoio con la distanza minima
        corridoio_vicino, distanza_min = min(distanze, key=lambda x: x[1])
        # Aggiungiamo l'arco macchina <-> corridoio
        G.add_edge(m.id, corridoio_vicino.id, weight=distanza_min)
    
    # 3.2. Aggiungiamo archi tra tutti i corridoi (tra ogni coppia)
    for i, c1 in enumerate(corridoi):
        for c2 in corridoi[i+1:]:
            d = euclidean_distance(c1, c2)
            G.add_edge(c1.id, c2.id, weight=d)
    
    # 4. Calcoliamo il percorso minimo (che passa per i corridoi) tra ogni coppia di macchine
    percorsi_macchine = {}
    
    for i, m1 in enumerate(macchine):
        for m2 in macchine[i+1:]:
            try:
                path = nx.dijkstra_path(G, m1.id, m2.id, weight='weight')
                distance = nx.dijkstra_path_length(G, m1.id, m2.id, weight='weight')
                percorsi_macchine[(m1.id, m2.id)] = {"path": path, "distance": distance}
            except nx.NetworkXNoPath:
                percorsi_macchine[(m1.id, m2.id)] = {"path": None, "distance": float('inf')}
    
    return G, percorsi_macchine

# Funzione per disegnare il grafo con un'immagine di background
def disegna_grafo(G, background_img=None, extent=None):
    # Prepariamo le posizioni dei nodi in base alle coordinate (x,y)
    pos = {}
    node_colors = []
    for node in G.nodes():
        punto = G.nodes[node]['punto']
        pos[node] = (punto.x, punto.y)
        # Colore in base alla categoria
        if punto.categoria == "macchina":
            node_colors.append('red')
        else:
            node_colors.append('blue')
    
    # Creiamo la figura
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Se è presente un'immagine di background, la mostriamo
    if background_img is not None and extent is not None:
        ax.imshow(background_img, extent=extent, aspect='auto', alpha=0.5)
    
    # Disegniamo il grafo sopra l'immagine
    nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=600, font_weight='bold', ax=ax)
    
    # Disegniamo le etichette degli archi con i pesi (arrotondati a 2 decimali)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    edge_labels = {edge: f"{weight:.2f}" for edge, weight in edge_labels.items()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
    
    # Impostiamo le etichette degli assi e la scala
    ax.set_xlabel("Coordinata X")
    ax.set_ylabel("Coordinata Y")
    ax.axis('equal')
    ax.grid(True)
    ax.set_title("Grafo: Macchine e Corridoi con Layout Fabbrica")
    
    return fig

# Corpo principale dell'app Streamlit
st.title("Visualizzazione del Grafo: Macchine e Corridoi sovrapposti al Layout")

# Caricamento dell'immagine del layout
st.subheader("Carica l'immagine del layout della fabbrica")
uploaded_file = st.file_uploader("Scegli un'immagine", type=["png", "jpg", "jpeg"])

# Se l'immagine è caricata, la processiamo
background_img = None
extent = None
if uploaded_file is not None:
    background_img = mpimg.imread(uploaded_file)
    st.image(background_img, caption="Layout della fabbrica caricato", use_column_width=True)
    
    st.subheader("Imposta l'estensione dell'immagine")
    st.write("Definisci il rettangolo di estensione [xmin, xmax, ymin, ymax] che corrisponde alle coordinate reali dell'immagine.")
    xmin = st.number_input("xmin", value=0.0)
    xmax = st.number_input("xmax", value=40.0)
    ymin = st.number_input("ymin", value=0.0)
    ymax = st.number_input("ymax", value=50.0)
    
    extent = [xmin, xmax, ymin, ymax]

# Costruiamo il grafo e calcoliamo i percorsi
G, percorsi_macchine = costruisci_grafo()

st.subheader("Percorsi minimi fra macchine")
for key, info in percorsi_macchine.items():
    m1, m2 = key
    st.markdown(f"**Percorso da {m1} a {m2}:**")
    st.write(f"Path: {info['path']}")
    st.write(f"Distanza totale: {info['distance']:.2f}")

st.subheader("Grafico del Grafo con il Layout della Fabbrica")
fig = disegna_grafo(G, background_img=background_img, extent=extent)
st.pyplot(fig)
