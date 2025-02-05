import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import matplotlib.pyplot as plt

def is_valid_direction(current_pos, candidate_pos, direction):
    """
    Verifica se il candidato (x2,y2) rispetta la condizione direzionale 
    rispetto al punto corrente (x1,y1) in base alla direzione scelta.
    """
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    if direction == "destro":
        return x2 > x1
    elif direction == "sinistro":
        return x2 < x1
    elif direction == "alto":
        return y2 > y1
    elif direction == "basso":
        return y2 < y1
    return False

def greedy_path(G, source, target, pos, direction):
    """
    Algoritmo greedy che, partendo da 'source', seleziona a ogni passo il nodo adiacente 
    (che sia un corridoio oppure il nodo target) che rispetta la condizione direzionale e 
    che sia il più vicino (in distanza euclidea) al nodo corrente.
    
    Restituisce la lista di nodi che compongono il percorso oppure None se non ne trova uno.
    """
    path = [source]
    visited = set(path)
    current = source

    while current != target:
        candidates = []
        for neigh in G.neighbors(current):
            if neigh in visited:
                continue
            # Considera il vicino se è il nodo target o se è un corridoio
            if neigh == target or G.nodes[neigh]["tag"] == "Corridoio":
                # Controlla la regola direzionale
                if is_valid_direction(pos[current], pos[neigh], direction):
                    candidates.append(neigh)
        if not candidates:
            return None  # Nessun candidato valido, impossibile proseguire
        # Seleziona il candidato con distanza minima dal nodo corrente
        next_node = min(candidates, key=lambda n: math.dist(pos[current], pos[n]))
        path.append(next_node)
        visited.add(next_node)
        current = next_node
        if len(path) > len(G.nodes()):
            return None  # Sicurezza per evitare cicli infiniti
    return path

def display_graph(G, pos, corridors, machines):
    """
    Visualizza il grafo con i nodi etichettati e colori distinti:
      - Corridoi: skyblue
      - Macchine: lightgreen
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Disegna gli archi con un'opacità ridotta
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.5)
    
    # Disegna i nodi
    nx.draw_networkx_nodes(G, pos, nodelist=corridors, node_color="skyblue", label="Corridoio", node_size=100, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=machines, node_color="lightgreen", label="Macchina", node_size=100, ax=ax)
    
    # Aggiunge le etichette per ogni nodo (mostra il nome e l'ID)
    labels = {node: f"{G.nodes[node]['entity_name']}\n(ID: {node})" for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
    
    ax.set_title("Grafico dei Nodi")
    ax.legend()
    ax.axis("off")
    st.pyplot(fig)

def main():
    st.title("Collegamento Macchine Tramite Corridoi – Percorsi e Visualizzazione")
    
    # 1. Caricamento del file Excel
    excel_file = st.file_uploader("Carica file Excel (X, Y, Tag, Entity Name, Size)", type=["xls", "xlsx"])
    if not excel_file:
        st.info("Carica un file Excel per iniziare.")
        return

    df = pd.read_excel(excel_file)
    st.subheader("Anteprima del DataFrame")
    st.dataframe(df.head())
    
    # 2. Verifica delle colonne necessarie
    required_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Colonna '{col}' mancante nel file Excel.")
            return

    # Conversione delle coordinate in numerico
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    
    # Separiamo i nodi in base al Tag
    df_corridor = df[df["Tag"] == "Corridoio"].copy()
    df_machine = df[df["Tag"] == "Macchina"].copy()
    
    if df_corridor.empty:
        st.warning("Nessun corridoio presente. Impossibile costruire il grafo.")
        return
    if df_machine.empty:
        st.warning("Nessuna macchina presente.")
        return
    
    # Uniamo i dati in un unico DataFrame
    df_all = pd.concat([df_corridor, df_machine])
    
    # 3. Costruzione del grafo
    st.subheader("Costruzione del grafo")
    max_distance = st.slider("Distanza massima per collegare i nodi", 
                               min_value=1.0, max_value=500.0, value=50.0,
                               help="Due nodi vengono collegati se la distanza euclidea è ≤ a questo valore.")
    
    G = nx.Graph()
    
    # Aggiungiamo i nodi; utilizziamo l'indice del DataFrame come ID
    for idx, row in df_all.iterrows():
        G.add_node(idx, 
                   x=row["X"], 
                   y=row["Y"], 
                   tag=row["Tag"], 
                   entity_name=row["Entity Name"], 
                   size=row["Size"])
    
    # Aggiungiamo gli archi: solo se la distanza ≤ max_distance e se almeno uno dei due nodi è un Corridoio
    nodes = list(G.nodes(data=True))
    for (i, data_i), (j, data_j) in itertools.combinations(nodes, 2):
        dist = math.dist((data_i["x"], data_i["y"]), (data_j["x"], data_j["y"]))
        if dist <= max_distance:
            if data_i["tag"] == "Corridoio" or data_j["tag"] == "Corridoio":
                G.add_edge(i, j, weight=dist)
    
    st.write("Numero totale di nodi:", G.number_of_nodes())
    st.write("Numero totale di archi:", G.number_of_edges())
    
    # Preparo la posizione dei nodi per la visualizzazione
    pos = {node: (data["x"], data["y"]) for node, data in G.nodes(data=True)}
    corridors = [n for n, d in G.nodes(data=True) if d["tag"] == "Corridoio"]
    machines = [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]
    
    # 4. Visualizzazione del grafo dei nodi
    st.subheader("Grafico dei Nodi")
    display_graph(G, pos, corridors, machines)
    
    # 5. Calcolo dei percorsi tra macchine (tramite corridoi)
    st.subheader("Calcolo dei percorsi tra macchine (tramite corridoi)")
    
    # Creiamo le opzioni per selezionare le macchine
    machine_options = [(n, f"{d['entity_name']} (ID: {n})") 
                       for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]
    machine_options = sorted(machine_options, key=lambda x: x[1])
    
    start_machine = st.selectbox("Macchina di Partenza", machine_options, format_func=lambda x: x[1])
    end_machine = st.selectbox("Macchina di Destinazione", machine_options, format_func=lambda x: x[1])
    
    # Selezione della direzione per il percorso basato su Size
    direction = st.selectbox("Direzione per il percorso basato su Size", 
                             ["destro", "sinistro", "alto", "basso"])
    
    if st.button("Calcola Percorsi"):
        source = start_machine[0]
        target = end_machine[0]
        
        st.markdown("### Percorso con distanza euclidea minima (Dijkstra)")
        if nx.has_path(G, source, target):
            path_euclid = nx.shortest_path(G, source=source, target=target, weight="weight")
            path_euclid_str = " -> ".join(f"{G.nodes[n]['entity_name']} (ID: {n})" for n in path_euclid)
            st.write(path_euclid_str)
            
            # Evidenzia il percorso calcolato con Dijkstra
            path_edges = list(zip(path_euclid, path_euclid[1:]))
            fig_e, ax_e = plt.subplots(figsize=(8, 6))
            nx.draw_networkx_edges(G, pos, ax=ax_e, alpha=0.3)
            nx.draw_networkx_nodes(G, pos, nodelist=corridors, node_color="skyblue", node_size=100, ax=ax_e)
            nx.draw_networkx_nodes(G, pos, nodelist=machines, node_color="lightgreen", node_size=100, ax=ax_e)
            nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color="red", width=2, ax=ax_e)
            ax_e.set_title("Percorso Euclideo Minimo (Dijkstra)")
            ax_e.axis("off")
            st.pyplot(fig_e)
        else:
            st.error("Nessun percorso trovato con il metodo euclideo.")
        
        st.markdown("### Percorso basato sulla regola Size (Algoritmo Greedy)")
        path_greedy = greedy_path(G, source, target, pos, direction)
        if path_greedy is not None:
            path_greedy_str = " -> ".join(f"{G.nodes[n]['entity_name']} (ID: {n})" for n in path_greedy)
            st.write(path_greedy_str)
            
            # Evidenzia il percorso calcolato con l'algoritmo greedy
            path_edges_g = list(zip(path_greedy, path_greedy[1:]))
            fig_g, ax_g = plt.subplots(figsize=(8, 6))
            nx.draw_networkx_edges(G, pos, ax=ax_g, alpha=0.3)
            nx.draw_networkx_nodes(G, pos, nodelist=corridors, node_color="skyblue", node_size=100, ax=ax_g)
            nx.draw_networkx_nodes(G, pos, nodelist=machines, node_color="lightgreen", node_size=100, ax=ax_g)
            nx.draw_networkx_edges(G, pos, edgelist=path_edges_g, edge_color="purple", width=2, ax=ax_g)
            ax_g.set_title("Percorso basato su Size (Greedy)")
            ax_g.axis("off")
            st.pyplot(fig_g)
        else:
            st.error("Nessun percorso trovato con il metodo basato su Size.")

if __name__ == "__main__":
    main()






