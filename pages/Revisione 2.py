import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import matplotlib.pyplot as plt
import io

def is_valid_direction(current_pos, candidate_pos, direction):
    """
    Verifica se il candidato (x2, y2) rispetta la condizione direzionale
    rispetto al punto corrente (x1, y1) in base alla direzione fornita.
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

def greedy_path(G, source, target, pos):
    """
    Algoritmo greedy che, partendo da 'source', seleziona ad ogni passo il nodo adiacente
    che rispetti i seguenti vincoli:
      - Se il candidato non è il target, deve essere di tipo "Corridoio".
      - Se il nodo corrente è di tipo "Corridoio", viene applicata la regola direzionale
        utilizzando il valore della sua colonna "Size" per filtrare i possibili nodi successivi.
      - Se il nodo corrente è una "Macchina" (tipicamente il punto di partenza), non viene
        applicato alcun filtro direzionale.
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

            # Se il candidato non è il target, deve essere un "Corridoio"
            if neigh != target and G.nodes[neigh]["tag"] == "Macchina":
                continue

            # Se il nodo corrente è di tipo "Corridoio", applichiamo la regola direzionale
            if G.nodes[current]["tag"] == "Corridoio":
                direction = G.nodes[current]["size"]
                if not is_valid_direction(pos[current], pos[neigh], direction):
                    continue

            candidates.append(neigh)

        if not candidates:
            return None  # Nessun candidato valido trovato

        # Selezioniamo il candidato più vicino (in distanza euclidea) rispetto al nodo corrente
        next_node = min(candidates, key=lambda n: math.dist(pos[current], pos[n]))
        path.append(next_node)
        visited.add(next_node)
        current = next_node

        # Sicurezza per evitare cicli infiniti
        if len(path) > len(G.nodes()):
            return None

    return path

def breakdown_path(path, pos):
    """
    Data una lista di nodi (path) e il dizionario pos,
    restituisce una stringa con le distanze (in m) di ciascun tratto separate da " + ".
    """
    segments = []
    for i in range(len(path) - 1):
        d = math.dist(pos[path[i]], pos[path[i+1]])
        segments.append(f"{d:.2f}")
    return " + ".join(segments)

def display_graph(G, pos, corridors, machines):
    """
    Visualizza il grafo con:
      - Nodi "Corridoio" in skyblue
      - Nodi "Macchina" in lightgreen
      - Etichette che mostrano l'entity_name ed l'ID
    """
    fig, ax = plt.subplots(figsize=(8, 6))
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.5)
    nx.draw_networkx_nodes(G, pos, nodelist=corridors, node_color="skyblue", label="Corridoio", node_size=100, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=machines, node_color="lightgreen", label="Macchina", node_size=100, ax=ax)
    labels = {node: f"{G.nodes[node]['entity_name']}\n(ID: {node})" for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
    ax.set_title("Grafico dei Nodi")
    ax.legend()
    ax.axis("off")
    st.pyplot(fig)

def main():
    st.title("Collegamento Macchine Tramite Corridoi – Calcolo di tutte le coppie")
    
    # 1. Caricamento del file (Excel o CSV)
    uploaded_file = st.file_uploader("Carica file Excel (xls, xlsx) o CSV", type=["xls", "xlsx", "csv"])
    if not uploaded_file:
        st.info("Carica un file per iniziare.")
        return

    # Determiniamo il tipo di file in base all'estensione
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    st.subheader("Anteprima del DataFrame")
    st.dataframe(df.head())
    
    # 2. Verifica delle colonne necessarie
    required_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Colonna '{col}' mancante nel file.")
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
    
    # Unione dei dati in un unico DataFrame
    df_all = pd.concat([df_corridor, df_machine])
    
    # 3. Costruzione del grafo
    st.subheader("Costruzione del grafo")
    max_distance = st.slider("Distanza massima per collegare i nodi", 
                               min_value=1.0, max_value=500.0, value=50.0,
                               help="Due nodi vengono collegati se la distanza euclidea è ≤ a questo valore.")
    
    G = nx.Graph()
    for idx, row in df_all.iterrows():
        G.add_node(idx, 
                   x=row["X"], 
                   y=row["Y"], 
                   tag=row["Tag"], 
                   entity_name=row["Entity Name"], 
                   size=row["Size"])
    
    # Aggiunta degli archi: si collegano due nodi se la distanza è ≤ max_distance e almeno uno è un Corridoio.
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
    
    # 4. Visualizzazione del grafo
    st.subheader("Grafico dei Nodi")
    display_graph(G, pos, corridors, machines)
    
    # 5. Calcolo dei percorsi per tutte le coppie di macchine
    st.subheader("Calcolo dei percorsi per tutte le coppie di macchine")
    results = []
    # Ordiniamo i nodi macchina (per entity_name ad es.)
    machine_nodes = sorted([n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"],
                           key=lambda n: G.nodes[n]["entity_name"])
    
    for source, target in itertools.combinations(machine_nodes, 2):
        source_name = G.nodes[source]["entity_name"]
        target_name = G.nodes[target]["entity_name"]
        
        # Collegamento macchina (es. "M1 --> M2")
        collegamento = f"{source_name} --> {target_name}"
        
        # Percorso ottimale (Dijkstra)
        if nx.has_path(G, source, target):
            path_euclid = nx.shortest_path(G, source=source, target=target, weight="weight")
            length_euclid = nx.shortest_path_length(G, source=source, target=target, weight="weight")
            percorso_ottimale = " --> ".join(G.nodes[n]["entity_name"] for n in path_euclid)
            dettaglio_ottimale = breakdown_path(path_euclid, pos)
        else:
            percorso_ottimale = "Nessun percorso"
            dettaglio_ottimale = ""
            length_euclid = None
        
        # Percorso greedy basato su Size
        path_greedy = greedy_path(G, source, target, pos)
        if path_greedy is not None:
            length_greedy = sum(math.dist(pos[path_greedy[i]], pos[path_greedy[i+1]])
                                for i in range(len(path_greedy)-1))
            percorso_greedy = " --> ".join(G.nodes[n]["entity_name"] for n in path_greedy)
            dettaglio_greedy = breakdown_path(path_greedy, pos)
        else:
            percorso_greedy = "Nessun percorso"
            dettaglio_greedy = ""
            length_greedy = None
        
        results.append({
            "Collegamento Macchina": collegamento,
            "Percorso Ottimale Seguito": percorso_ottimale,
            "Dettaglio Distanze Ottimale": dettaglio_ottimale,
            "Lunghezza Totale Ottimale": length_euclid,
            "Percorso Greedy Seguito": percorso_greedy,
            "Dettaglio Distanze Greedy": dettaglio_greedy,
            "Lunghezza Totale Greedy": length_greedy,
        })
    
    df_results = pd.DataFrame(results)
    st.subheader("Risultati per tutte le coppie di macchine")
    st.dataframe(df_results)
    
    # 6. Download del file Excel con i risultati
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df_results.to_excel(writer, index=False, sheet_name='Risultati')
        writer.save()
    towrite.seek(0)
    
    st.download_button(
        label="Scarica file Excel",
        data=towrite,
        file_name="risultati_percorsi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    main()





