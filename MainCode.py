import math
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd
import streamlit as st

###############################
# 1. Classe Punto e Funzioni Ausiliarie
###############################

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
        return (f"Punto(id={self.id}, x={self.x}, y={self.y}, "
                f"categoria={self.categoria}, preferred_direction={self.preferred_direction})")

def euclidean_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def angle_between_points(p1, p2):
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    return math.atan2(dy, dx)  # valore in [-pi, pi]

def adjust_weight_for_preferred_direction(corridor, p_from, p_to, base_weight):
    if corridor.preferred_direction is None:
        return base_weight
    travel_angle = angle_between_points(p_from, p_to)
    diff = abs(travel_angle - corridor.preferred_direction)
    diff = min(diff, 2 * math.pi - diff)
    # Penalità: se diff = 0, moltiplicatore = 1; se diff = pi, moltiplicatore = 2
    penalty_factor = 1 + (diff / math.pi)
    return base_weight * penalty_factor

###############################
# 2. Funzioni per Costruire il Grafo
###############################

def costruisci_grafo_from_data(macchine_list, corridoi_list):
    """
    macchine_list e corridoi_list sono liste di oggetti Punto.
    Se almeno un corridoio ha preferred_direction diverso da None, utilizziamo un grafo diretto.
    """
    # Scegliamo il tipo di grafo
    usa_direzionato = any(c.preferred_direction is not None for c in corridoi_list)
    if usa_direzionato:
        G = nx.DiGraph()
    else:
        G = nx.Graph()
        
    # Aggiungiamo tutti i punti come nodi
    for punto in macchine_list + corridoi_list:
        G.add_node(punto.id, punto=punto)
        
    # Collegamenti macchina <-> corridoio:
    for m in macchine_list:
        # Colleghiamo la macchina al corridoio più vicino (calcolato in termini di distanza euclidea)
        distanze = [(c, euclidean_distance(m, c)) for c in corridoi_list]
        corridoio_vicino, distanza_min = min(distanze, key=lambda x: x[1])
        # Aggiungiamo l'arco dalla macchina al corridoio
        G.add_edge(m.id, corridoio_vicino.id, weight=distanza_min)
        # Se il grafo è diretto, aggiungiamo anche il collegamento inverso senza penalità (se ritenuto opportuno)
        if usa_direzionato:
            G.add_edge(corridoio_vicino.id, m.id, weight=distanza_min)
        else:
            # In grafo non diretto, l'arco è unico.
            pass
        
    # Collegamenti tra corridoi:
    for i, c1 in enumerate(corridoi_list):
        for j, c2 in enumerate(corridoi_list):
            if c1.id == c2.id:
                continue
            base_weight = euclidean_distance(c1, c2)
            # Se il grafo è diretto, calcoliamo il peso con la penalità in base al verso preferenziale di c1
            if usa_direzionato:
                adjusted_weight = adjust_weight_for_preferred_direction(c1, c1, c2, base_weight)
                G.add_edge(c1.id, c2.id, weight=adjusted_weight)
            else:
                # In un grafo non diretto, usiamo semplicemente la distanza
                if not G.has_edge(c1.id, c2.id):
                    G.add_edge(c1.id, c2.id, weight=base_weight)
                    
    return G

def calcola_percorsi_macchine(G, macchine_list):
    """Calcola il percorso minimo tra ogni coppia di macchine usando Dijkstra."""
    percorsi_macchine = {}
    n = len(macchine_list)
    for i in range(n):
        for j in range(i+1, n):
            m1 = macchine_list[i]
            m2 = macchine_list[j]
            try:
                path = nx.dijkstra_path(G, m1.id, m2.id, weight='weight')
                distance = nx.dijkstra_path_length(G, m1.id, m2.id, weight='weight')
                percorsi_macchine[(m1.id, m2.id)] = {"path": path, "distance": distance}
            except nx.NetworkXNoPath:
                percorsi_macchine[(m1.id, m2.id)] = {"path": None, "distance": float('inf')}
    return percorsi_macchine

###############################
# 3. Funzioni per Disegnare il Grafo
###############################

def disegna_grafo(G, background_img=None, extent=None):
    # Posizioni dei nodi in base alle coordinate reali
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
    
    if background_img is not None and extent is not None:
        ax.imshow(background_img, extent=extent, aspect='auto', alpha=0.5)
    
    # Per grafo diretto usiamo frecce
    if isinstance(G, nx.DiGraph):
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, ax=ax)
        nx.draw_networkx_labels(G, pos, ax=ax)
        nx.draw_networkx_edges(G, pos, ax=ax, arrowstyle='->', arrowsize=15)
    else:
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=600, font_weight='bold', ax=ax)
    
    edge_labels = nx.get_edge_attributes(G, 'weight')
    edge_labels = {edge: f"{weight:.2f}" for edge, weight in edge_labels.items()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
    
    ax.set_xlabel("Coordinata X")
    ax.set_ylabel("Coordinata Y")
    ax.axis('equal')
    ax.grid(True)
    ax.set_title("Grafo: Macchine e Corridoi")
    return fig

###############################
# 4. App Streamlit: Import da Excel e Visualizzazione
###############################

st.title("Analisi di Scenari - Grafici per Macchine e Corridoi")

st.markdown("""
Carica uno o più file Excel.  
**Requisiti:**  
- Ogni file deve contenere due sheet (o tabelle) chiamati **"macchine"** e **"corridoi"**.  
- Nel sheet **macchine** devono esserci almeno le colonne:  
  - `id` (identificativo)  
  - `x` (coordinata X)  
  - `y` (coordinata Y)  
- Nel sheet **corridoi** devono esserci almeno le colonne:  
  - `id`  
  - `x`  
  - `y`  
  - (opzionale) `preferred_direction` (in radianti, es. 0, 1.57, ecc.)
""")

uploaded_files = st.file_uploader("Carica file Excel", type=["xlsx"], accept_multiple_files=True)

# Opzionale: carica un'immagine di background (layout della fabbrica)
st.markdown("---")
st.subheader("Opzionale: Carica l'immagine del layout della fabbrica")
uploaded_img = st.file_uploader("Carica un'immagine", type=["png", "jpg", "jpeg"], key="img")
background_img = None
extent = None
if uploaded_img is not None:
    background_img = mpimg.imread(uploaded_img)
    st.image(background_img, caption="Layout della fabbrica", use_column_width=True)
    st.markdown("**Imposta l'estensione dell'immagine:**")
    xmin = st.number_input("xmin", value=0.0, key="xmin")
    xmax = st.number_input("xmax", value=40.0, key="xmax")
    ymin = st.number_input("ymin", value=0.0, key="ymin")
    ymax = st.number_input("ymax", value=50.0, key="ymax")
    extent = [xmin, xmax, ymin, ymax]

if uploaded_files:
    for file in uploaded_files:
        st.markdown("---")
        st.markdown(f"### Scenario: {file.name}")
        
        try:
            # Leggiamo tutti i sheet del file Excel
            sheets = pd.read_excel(file, sheet_name=None)
        except Exception as e:
            st.error(f"Errore nella lettura del file: {e}")
            continue
        
        # Controlliamo se sono presenti i fogli "macchine" e "corridoi"
        if "macchine" not in sheets or "corridoi" not in sheets:
            st.error("Il file deve contenere i fogli 'macchine' e 'corridoi'.")
            continue
        
        # Creiamo le liste di oggetti Punto per macchine e corridoi
        df_macchine = sheets["macchine"]
        df_corridoi = sheets["corridoi"]
        
        macchine_list = []
        corridoi_list = []
        
        # Assumiamo che le colonne siano nominate: id, x, y, (preferred_direction per i corridoi)
        for _, row in df_macchine.iterrows():
            try:
                m = Punto(
                    x=float(row["x"]),
                    y=float(row["y"]),
                    categoria="macchina",
                    id=str(row["id"])
                )
                macchine_list.append(m)
            except Exception as e:
                st.error(f"Errore nella riga delle macchine: {e}")
                
        for _, row in df_corridoi.iterrows():
            try:
                # Se la colonna preferred_direction esiste e non è NaN, la convertiamo in float, altrimenti None
                pd_val = row.get("preferred_direction", None)
                pref_dir = None
                if pd_val is not None and not pd.isna(pd_val):
                    pref_dir = float(pd_val)
                c = Punto(
                    x=float(row["x"]),
                    y=float(row["y"]),
                    categoria="corridoio",
                    id=str(row["id"]),
                    preferred_direction=pref_dir
                )
                corridoi_list.append(c)
            except Exception as e:
                st.error(f"Errore nella riga dei corridoi: {e}")
        
        # Se non sono stati creati dati sufficienti, saltiamo lo scenario
        if not macchine_list or not corridoi_list:
            st.error("Dati insufficienti per costruire il grafo.")
            continue
        
        # Costruiamo il grafo a partire dai dati importati
        G = costruisci_grafo_from_data(macchine_list, corridoi_list)
        percorsi_macchine = calcola_percorsi_macchine(G, macchine_list)
        
        # Visualizziamo i percorsi calcolati
        st.subheader("Percorsi minimi fra macchine")
        for key, info in percorsi_macchine.items():
            m1, m2 = key
            st.markdown(f"**Percorso da {m1} a {m2}:**")
            st.write(f"Path: {info['path']}")
            st.write(f"Distanza totale: {info['distance']:.2f}")
        
        # Disegniamo il grafo e lo visualizziamo
        st.subheader("Grafico del Grafo")
        fig = disegna_grafo(G, background_img=background_img, extent=extent)
        st.pyplot(fig)


