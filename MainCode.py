import math
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import streamlit as st

# 1. Definizione della classe Punto (aggiungiamo l'attributo preferred_direction)
class Punto:
    def __init__(self, x, y, categoria=None, id=None, preferred_direction=None):
        """
        preferred_direction: angolo in radianti che indica il verso preferenziale (per i corridoi)
        """
        self.x = x
        self.y = y
        self.categoria = categoria  # "macchina" o "corridoio"
        self.id = id                # identificativo unico
        self.preferred_direction = preferred_direction

    def __repr__(self):
        return f"Punto(id={self.id}, x={self.x}, y={self.y}, categoria={self.categoria}, preferred_direction={self.preferred_direction})"

# Funzione per calcolare la distanza euclidea fra due punti
def euclidean_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

# Funzione per calcolare l'angolo (in radianti) dal punto p1 al punto p2
def angle_between_points(p1, p2):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.atan2(dy, dx)  # valore in [-pi, pi]

# Funzione per applicare una penalità se l'angolo di spostamento non è allineato al verso preferito
def adjust_weight_for_preferred_direction(corridor, p_from, p_to, base_weight):
    if corridor.preferred_direction is None:
        return base_weight
    travel_angle = angle_between_points(p_from, p_to)
    # Calcola la differenza angolare (minimale)
    diff = abs(travel_angle - corridor.preferred_direction)
    diff = min(diff, 2 * math.pi - diff)
    # Applichiamo una penalità: ad esempio, se diff=0 => moltiplicatore 1, se diff=pi => moltiplicatore 2
    penalty_factor = 1 + (diff / math.pi)
    return base_weight * penalty_factor

# Funzione per costruire il grafo diretto e calcolare i percorsi
def costruisci_grafo():
    # 2. Configurazione dei punti per macchine e corridoi
    # Le macchine non hanno verso preferenziale
    macchine = [
        Punto(10, 20, categoria="macchina", id="M1"),
        Punto(15, 25, categoria="macchina", id="M2"),
        Punto(30, 40, categoria="macchina", id="M3")
    ]
    
    # Nei corridoi specifichiamo un verso preferenziale (in radianti)
    # Ad esempio:
    # C1: verso est (0 rad), C2: verso nord (pi/2), C3: verso nord-est (pi/4)
    corridoi = [
        Punto(5, 5, categoria="corridoio", id="C1", preferred_direction=0),
        Punto(12, 18, categoria="corridoio", id="C2", preferred_direction=math.pi/2),
        Punto(25, 30, categoria="corridoio", id="C3", preferred_direction=math.pi/4)
    ]
    
    # 3. Creiamo un grafo diretto
    G = nx.DiGraph()
    
    # Aggiungiamo tutti i punti come nodi
    for punto in macchine + corridoi:
        G.add_node(punto.id, punto=punto)
    
    # 3.1. Collegamenti macchina <-> corridoio
    # Per ogni macchina, troviamo il corridoio più vicino e aggiungiamo archi in entrambe le direzioni (senza penalità)
    for m in macchine:
        distanze = [(c, euclidean_distance(m, c)) for c in corridoi]
        corridoio_vicino, distanza_min = min(distanze, key=lambda x: x[1])
        # Aggiungiamo arco da macchina a corridoio
        G.add_edge(m.id, corridoio_vicino.id, weight=distanza_min)
        # Aggiungiamo arco da corridoio a macchina (in questo caso non applichiamo la penalità)
        G.add_edge(corridoio_vicino.id, m.id, weight=distanza_min)
    
    # 3.2. Collegamenti tra corridoi (archi diretti in entrambe le direzioni, con eventuale penalità)
    for i, c1 in enumerate(corridoi):
        for j, c2 in enumerate(corridoi):
            if c1.id == c2.id:
                continue
            base_weight = euclidean_distance(c1, c2)
            # Calcoliamo il peso per l'arco da c1 a c2 usando il verso preferenziale di c1
            adjusted_weight = adjust_weight_for_preferred_direction(c1, c1, c2, base_weight)
            G.add_edge(c1.id, c2.id, weight=adjusted_weight)
    
    # 3.3. (Facoltativo) Se volessimo aggiungere collegamenti macchina–macchina diretti, li omettiamo (come da richiesta)
    
    # 4. Calcoliamo i percorsi minimi (ad es. da una macchina all'altra)
    percorsi_macchine = {}
    for i, m1 in enumerate(macchine):
        for m2 in macchine[i+1:]:
            try:
                # Usando Dijkstra su grafo diretto
                path = nx.dijkstra_path(G, m1.id, m2.id, weight='weight')
                distance = nx.dijkstra_path_length(G, m1.id, m2.id, weight='weight')
                percorsi_macchine[(m1.id, m2.id)] = {"path": path, "distance": distance}
            except nx.NetworkXNoPath:
                percorsi_macchine[(m1.id, m2.id)] = {"path": None, "distance": float('inf')}
    
    return G, percorsi_macchine

# Funzione per disegnare il grafo (sovrapposto a un'immagine se presente)
def disegna_grafo(G, background_img=None, extent=None):
    # Otteniamo le posizioni in base alle coordinate dei punti
    pos = {}
    node_colors = []
    for node in G.nodes():
        punto = G.nodes[node]['punto']
        pos[node] = (punto.x, punto.y)
        if punto.categoria == "macchina":
            node_colors.append('red')
        else:
            node_colors.append('blue')
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Mostriamo l'immagine di background se presente
    if background_img is not None and extent is not None:
        ax.imshow(background_img, extent=extent, aspect='auto', alpha=0.5)
    
    # Disegniamo i nodi ed etichette
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, ax=ax)
    nx.draw_networkx_labels(G, pos, ax=ax)
    
    # Disegniamo gli archi con le frecce (dato che il grafo è diretto)
    nx.draw_networkx_edges(G, pos, ax=ax, arrowstyle='->', arrowsize=15)
    
    # Disegniamo le etichette degli archi (con il peso)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    edge_labels = {edge: f"{weight:.2f}" for edge, weight in edge_labels.items()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
    
    ax.set_xlabel("Coordinata X")
    ax.set_ylabel("Coordinata Y")
    ax.axis('equal')
    ax.grid(True)
    ax.set_title("Grafo Diretto: Macchine e Corridoi (con verso preferenziale)")
    return fig

# Corpo principale dell'app Streamlit
st.title("Grafo con Verso Preferenziale nei Corridoi")

# Caricamento dell'immagine del layout (facoltativo)
st.subheader("Carica il layout della fabbrica")
uploaded_file = st.file_uploader("Scegli un'immagine", type=["png", "jpg", "jpeg"])
background_img = None
extent = None
if uploaded_file is not None:
    background_img = mpimg.imread(uploaded_file)
    st.image(background_img, caption="Layout della fabbrica", use_column_width=True)
    
    st.subheader("Imposta l'estensione dell'immagine")
    st.write("Definisci [xmin, xmax, ymin, ymax] in coordinate reali.")
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

st.subheader("Visualizzazione del Grafo")
fig = disegna_grafo(G, background_img=background_img, extent=extent)
st.pyplot(fig)

