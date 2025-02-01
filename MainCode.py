import math
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import pandas as pd
import streamlit as st
from io import StringIO, BytesIO

"""
======================================
CONFIGURAZIONE DEI PERCORSI STANDARD - PAGINA 1
======================================

Questa pagina rappresenta la configurazione iniziale dei percorsi.
- Definizione della classe Punto e delle funzioni ausiliarie.
- Costruzione del grafo basato sui punti (macchine e corridoi).
- Calcolo dei percorsi minimi (inclusi tutti i punti corridoio attraversati).
- Generazione del file Excel riassuntivo e visualizzazione del grafo.

I risultati verranno salvati in st.session_state["computed_results"] per poterli utilizzare in altre pagine.
"""

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
        # Se il grafo è diretto, aggiungiamo anche il collegamento inverso senza penalità
        if usa_direzionato:
            G.add_edge(corridoio_vicino.id, m.id, weight=distanza_min)
        
    # Collegamenti tra corridoi:
    for i, c1 in enumerate(corridoi_list):
        for j, c2 in enumerate(corridoi_list):
            if c1.id == c2.id:
                continue
            base_weight = euclidean_distance(c1, c2)
            if usa_direzionato:
                adjusted_weight = adjust_weight_for_preferred_direction(c1, c1, c2, base_weight)
                G.add_edge(c1.id, c2.id, weight=adjusted_weight)
            else:
                if not G.has_edge(c1.id, c2.id):
                    G.add_edge(c1.id, c2.id, weight=base_weight)
                    
    return G

def calcola_percorsi_macchine(G, macchine_list):
    """Calcola il percorso minimo tra ogni coppia di macchine usando Dijkstra.
       Il percorso restituito è una lista completa di nodi (macchine e corridoi) attraversati.
    """
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
# 3. Funzione per Disegnare il Grafo (con dimensioni differenti per macchine e corridoi)
###############################

def disegna_grafo(G, background_img=None, extent=None):
    # Posizioni dei nodi in base alle coordinate reali
    pos = {}
    node_colors = []
    node_sizes = []  # Dimensione specifica per ogni nodo

    for node in G.nodes():
        punto = G.nodes[node]['punto']
        pos[node] = (punto.x, punto.y)
        if punto.categoria == "macchina":
            node_colors.append('red')
            node_sizes.append(600)  # Dimensione maggiore per le macchine
        else:
            node_colors.append('blue')
            node_sizes.append(300)  # Dimensione ridotta per i corridoi

    fig, ax = plt.subplots(figsize=(8, 6))
    
    if background_img is not None and extent is not None:
        ax.imshow(background_img, extent=extent, aspect='auto', alpha=0.5)
    
    if isinstance(G, nx.DiGraph):
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
        nx.draw_networkx_labels(G, pos, ax=ax)
        nx.draw_networkx_edges(G, pos, ax=ax, arrowstyle='->', arrowsize=15)
    else:
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=node_sizes, font_weight='bold', ax=ax)
    
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
# 4. Funzione per Generare il File Excel Riassuntivo
###############################

def genera_excel(percorsi_macchine):
    """
    Genera un file Excel (in memoria) con una riga per ogni coppia di macchine,
    contenente le colonne: Machine1, Machine2, Path e Distance.
    Il campo "Path" contiene tutti i punti (macchine e corridoi) attraversati.
    """
    rows = []
    for (m1, m2), info in percorsi_macchine.items():
        rows.append({
            "Machine1": m1,
            "Machine2": m2,
            "Path": " -> ".join(info["path"]) if info["path"] is not None else None,
            "Distance": info["distance"]
        })
    df = pd.DataFrame(rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Connections")
    processed_data = output.getvalue()
    return processed_data

###############################
# 5. Pagina 1: Import, Esempi CSV, Elaborazione e Salvataggio Risultati
###############################

st.title("Configurazione dei Percorsi - Pagina 1")

st.markdown("""
Carica un file Excel o CSV per lo scenario.
**Requisiti:**
- Per Excel: il file deve contenere due fogli/tabelle chiamati **"macchine"** e **"corridoi"**.
- Per CSV: carica separatamente due file (uno per macchine e uno per corridoi) con nomi **macchine** e **corridoi**.

Se non carichi alcun file, verranno usati i dati di default.
""")

# --- Esempi CSV e Download ---
st.subheader("Esempi di file CSV di partenza")
default_macchine_csv = """id,x,y
A1_M1,10,20
A1_M2,10,30
A1_M3,20,20
A1_M4,20,30
A2_M1,40,20
A2_M2,40,30
A2_M3,50,20
A2_M4,50,30
A3_M1,70,20
A3_M2,70,30
A3_M3,80,20
A3_M4,80,30
"""
default_corridoi_csv = """id,x,y,preferred_direction
C1,0,25,0
C2,30,25,0
C3,60,25,0
C4,90,25,3.1416
C5,45,35,1.5708
C6,45,15,-1.5708
"""
st.markdown("#### File CSV per le macchine")
st.code(default_macchine_csv, language='csv')
st.download_button(
    label="Scarica macchine.csv",
    data=default_macchine_csv,
    file_name="macchine.csv",
    mime="text/csv"
)
st.markdown("#### File CSV per i corridoi")
st.code(default_corridoi_csv, language='csv')
st.download_button(
    label="Scarica corridoi.csv",
    data=default_corridoi_csv,
    file_name="corridoi.csv",
    mime="text/csv"
)

# --- Caricamento File ---
uploaded_excel = st.file_uploader("Carica file Excel", type=["xlsx"], key="excel")
uploaded_csv_macchine = st.file_uploader("Carica CSV per macchine", type=["csv"], key="csv_macchine")
uploaded_csv_corridoi = st.file_uploader("Carica CSV per corridoi", type=["csv"], key="csv_corridoi")

# --- Opzionale: Immagine Layout ---
st.markdown("---")
st.subheader("Opzionale: Carica immagine del layout della fabbrica")
uploaded_img = st.file_uploader("Carica un'immagine", type=["png", "jpg", "jpeg"], key="img")
background_img = None
extent = None
if uploaded_img is not None:
    background_img = mpimg.imread(uploaded_img)
    st.image(background_img, caption="Layout della fabbrica", use_column_width=True)
    st.markdown("**Imposta l'estensione dell'immagine:**")
    xmin = st.number_input("xmin", value=0.0, key="xmin")
    xmax = st.number_input("xmax", value=100.0, key="xmax")
    ymin = st.number_input("ymin", value=0.0, key="ymin")
    ymax = st.number_input("ymax", value=50.0, key="ymax")
    extent = [xmin, xmax, ymin, ymax]

# --- Elaborazione Dati ---
macchine_list = []
corridoi_list = []

# Se è stato caricato un file Excel, lo usiamo
if uploaded_excel is not None:
    try:
        sheets = pd.read_excel(uploaded_excel, sheet_name=None)
    except Exception as e:
        st.error(f"Errore nella lettura del file Excel: {e}")
    else:
        if "macchine" not in sheets or "corridoi" not in sheets:
            st.error("Il file Excel deve contenere i fogli 'macchine' e 'corridoi'.")
        else:
            df_macchine = sheets["macchine"]
            df_corridoi = sheets["corridoi"]
            st.success("File Excel caricato correttamente.")
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

# Se non sono stati caricati file Excel, proviamo con CSV
elif uploaded_csv_macchine is not None and uploaded_csv_corridoi is not None:
    try:
        df_macchine = pd.read_csv(uploaded_csv_macchine)
        df_corridoi = pd.read_csv(uploaded_csv_corridoi)
        st.success("File CSV caricati correttamente.")
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
    except Exception as e:
        st.error(f"Errore nella lettura dei file CSV: {e}")

# Se nessun file è stato caricato, uso i dati di default
if not macchine_list or not corridoi_list:
    st.info("Nessun file caricato. Utilizzo dei dati di default.")
    df_macchine = pd.read_csv(StringIO(default_macchine_csv))
    df_corridoi = pd.read_csv(StringIO(default_corridoi_csv))
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
            st.error(f"Errore nella riga delle macchine (default): {e}")
    for _, row in df_corridoi.iterrows():
        try:
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
            st.error(f"Errore nella riga dei corridoi (default): {e}")

# --- Elaborazione e Visualizzazione ---
if not macchine_list or not corridoi_list:
    st.error("Dati insufficienti per costruire il grafo.")
else:
    # Costruzione del grafo e calcolo dei percorsi
    G = costruisci_grafo_from_data(macchine_list, corridoi_list)
    percorsi_macchine = calcola_percorsi_macchine(G, macchine_list)

    st.subheader("Percorsi minimi fra macchine")
    for key, info in percorsi_macchine.items():
        m1, m2 = key
        st.markdown(f"**Percorso da {m1} a {m2}:**")
        st.write(f"Path: {' -> '.join(info['path']) if info['path'] is not None else 'Nessun percorso'}")
        st.write(f"Distanza totale: {info['distance']:.2f}")

    st.subheader("Grafico del Grafo")
    fig = disegna_grafo(G, background_img=background_img, extent=extent)
    st.pyplot(fig)
    
    # Genera il file Excel riassuntivo e abilita il download
    excel_data = genera_excel(percorsi_macchine)
    st.download_button(
        label="Scarica file Excel con i collegamenti",
        data=excel_data,
        file_name="machine_connections.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Salva i risultati nello stato della sessione per renderli accessibili in altre pagine
    st.session_state["computed_results"] = {
        "percorsi_macchine": percorsi_macchine,
        "excel_data": excel_data,
        "graph": G,
        "macchine": macchine_list,
        "corridoi": corridoi_list
    }

