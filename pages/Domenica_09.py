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
    I valori validi per 'direction' sono "destro", "sinistro", "alto" e "basso".
    """
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
        
    if direction == "destro":
        if x2 > x1 and dist_x>dist_y: 
            return True
        else:
            return False
    elif direction == "sinistro":
        if x2 < x1 and dist_x>dist_y: 
            return True
        else:
            return False
    elif direction == "alto":
        if y2 > y1 and dist_y>dist_x: 
            return True
        else:
            return False
    elif direction == "basso":
        if y2 < y1 and dist_y>dist_x: 
            return True    
        else:
            return False
    return True

def greedy_path(G, source, target, pos):
    """
    Algoritmo greedy che, partendo da 'source', seleziona ad ogni passo il nodo adiacente
    che rispetta i seguenti vincoli:
      - Se il candidato non è il target, deve essere di tipo "Corridoio".
      - Se il nodo corrente è di tipo "Corridoio", viene applicato il vincolo direzionale 
        (basato su Size). Se il nodo corrente è di tipo Macchina, il vincolo non viene applicato.
      - Al primo salto, se il nodo di partenza è una Macchina, si forza il collegamento 
        con un Corridoio (scartando quindi altri eventuali nodi Macchina).
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

            # Al primo salto: se il nodo corrente è una Macchina, non consideriamo altri nodi Macchina
            if len(path) == 1 and G.nodes[current]["tag"] == "Macchina" and G.nodes[neigh]["tag"] == "Macchina":
                continue

            # Se il candidato non è il target, deve essere un Corridoio
            if neigh != target and G.nodes[neigh]["tag"] == "Macchina":
                continue

            # Applica il controllo direzionale SOLO se il nodo corrente è un Corridoio.
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
    restituisce una stringa con le distanze (in m) di ciascun tratto, separate da " + ".
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
    
    # 2. Anteprima e modifica del DataFrame (solo le colonne "Entity Name" e "Size")
    st.subheader("Anteprima e modifica dei dati (solo 'Entity Name' e 'Size')")
    # Usando la funzione st.data_editor (la versione stabile aggiornata)
    edited_data = st.data_editor(df[['Entity Name', 'Size']], num_rows="dynamic")
    # Aggiorniamo il DataFrame originale con le modifiche
    df.update(edited_data)
    
    # Verifica delle colonne necessarie
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
                               min_value=0.0, max_value=10.0, value=5.0,
                               help="Due nodi vengono collegati se la distanza euclidea è ≤ a questo valore.")
    
    G = nx.Graph()
    for idx, row in df_all.iterrows():
        G.add_node(idx, 
                   x=row["X"], 
                   y=row["Y"], 
                   tag=row["Tag"], 
                   entity_name=row["Entity Name"], 
                   size=row["Size"])
    
    # 1. Connessione fra Corridoi:
#    Si collegano due nodi di tipo Corridoio se:
#      - La distanza euclidea è ≤ max_distance
#      - E solo se il punto di partenza (il primo nodo della coppia) rispetta la condizione direzionale
#        in base al proprio vincolo "Size".
    corridor_nodes = [n for n, d in G.nodes(data=True) if d["tag"] == "Corridoio"]
    for i, j in itertools.combinations(corridor_nodes, 2):
        pos_i = (G.nodes[i]["x"], G.nodes[i]["y"])
        pos_j = (G.nodes[j]["x"], G.nodes[j]["y"])
        
        # Escludi collegamenti se i due punti non sono allineati in una sola dimensione:
        # Se entrambi gli assi variano, significa che il collegamento sarebbe in diagonale.
        # Calcola la distanza "Manhattan" (in questo caso coincide con la distanza euclidea
        # se la variazione è solo lungo un asse)
        dist = abs(pos_j[0] - pos_i[0]) + abs(pos_j[1] - pos_i[1])
        # Distanza euclidea
        #dist = math.dist(pos_i, pos_j)
        if dist <= max_distance:
            if is_valid_direction(pos_i, pos_j, G.nodes[i]["size"]):
                G.add_edge(i, j, weight=dist)
            
    # 2. Connessione Macchina -> Corridoio:
    #    Per ogni Macchina, si collega una sola volta al Corridoio più vicino che rispetti
    #    la condizione direzionale indicata dal Corridoio (il vincolo "Size" viene applicato
    #    solo al Corridoio, non alla Macchina).
    machine_nodes = [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]
    for machine in machine_nodes:
        machine_pos = (G.nodes[machine]["x"], G.nodes[machine]["y"])
        best_corridor = None
        best_dist = float('inf')
        for corridor in corridor_nodes:
            corridor_pos = (G.nodes[corridor]["x"], G.nodes[corridor]["y"])
            dist = math.dist(machine_pos, corridor_pos)
            # Si considera solo la distanza, senza il controllo del vincolo direzionale.
            if dist < best_dist and dist <= max_distance:
                best_dist = dist
                best_corridor = corridor
        if best_corridor is not None:
            G.add_edge(machine, best_corridor, weight=best_dist)
    # --------------------------
    
    st.write("Numero totale di nodi:", G.number_of_nodes())
    st.write("Numero totale di archi:", G.number_of_edges())
    
    # Preparo la posizione dei nodi per la visualizzazione
    pos = {node: (data["x"], data["y"]) for node, data in G.nodes(data=True)}
    corridors = [n for n, d in G.nodes(data=True) if d["tag"] == "Corridoio"]
    machines = [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]
    
    # 4. Visualizzazione del grafo
    st.subheader("Grafico dei Nodi")
    display_graph(G, pos, corridors, machines)

    # Creazione della tabella per le connessioni fra corridoi (solo gli archi tra nodi di tipo Corridoio)
    corridor_edges = []
    for u, v, data_dict in G.edges(data=True):
        # Verifichiamo che entrambi i nodi siano di tipo "Corridoio"
        if G.nodes[u]["tag"] == "Corridoio" and G.nodes[v]["tag"] == "Corridoio":
            corridor_edges.append({
                "Corridoio 1": G.nodes[u].get("entity_name", f"ID: {u}"),
                "Corridoio 2": G.nodes[v].get("entity_name", f"ID: {v}"),
                "Distanza (m)": data_dict["weight"]
            })
    
    # Creiamo il DataFrame dalle connessioni trovate
    df_corridor_edges = pd.DataFrame(corridor_edges)
    
    # Visualizziamo il DataFrame in forma tabellare e permettiamo la modifica interattiva
    st.subheader("Tabella delle Connessioni fra Corridoi")
    edited_edges = st.data_editor(df_corridor_edges, num_rows="dynamic", key="corridor_edges_editor")
    
    # Se desideri anche visualizzare la tabella modificata
    st.write("Tabella modificata:")
    st.dataframe(edited_edges)
    
    # 5. Calcolo dei percorsi per tutte le coppie di macchine
    st.subheader("Calcolo dei percorsi per tutte le coppie di macchine")
    results = []
    machine_nodes_sorted = sorted([n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"],
                                  key=lambda n: G.nodes[n]["entity_name"])
    
    for source, target in itertools.combinations(machine_nodes_sorted, 2):
        source_name = G.nodes[source]["entity_name"]
        target_name = G.nodes[target]["entity_name"]
        collegamento = f"{source_name} --> {target_name}"
        
        # Per imporre il vincolo, se il nodo di partenza è una Macchina
        # cerchiamo il Corridoio più vicino tra i suoi vicini.
        corridor_neighbors = [n for n in G.neighbors(source) if G.nodes[n]["tag"] == "Corridoio"]
        
        # --- Percorso Ottimale (Dijkstra) con vincolo del primo Corridoio ---
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            if nx.has_path(G, nearest_corridor, target):
                sub_path = nx.shortest_path(G, source=nearest_corridor, target=target, weight="weight")
                length_sub = nx.shortest_path_length(G, source=nearest_corridor, target=target, weight="weight")
                full_path = [source] + sub_path  # Forzo il passaggio: Macchina -> Corridoio -> ... -> Target
                length_euclid = math.dist(pos[source], pos[nearest_corridor]) + length_sub
                percorso_ottimale = " --> ".join(G.nodes[n]["entity_name"] for n in full_path)
                dettaglio_ottimale = breakdown_path(full_path, pos)
            else:
                percorso_ottimale = "Nessun percorso"
                dettaglio_ottimale = ""
                length_euclid = None
        else:
            percorso_ottimale = "Nessun percorso"
            dettaglio_ottimale = ""
            length_euclid = None
        
        # --- Percorso Greedy con vincolo del primo Corridoio ---
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            sub_path = greedy_path(G, nearest_corridor, target, pos)
            if sub_path is not None:
                full_path = [source] + sub_path  # Forzo il passaggio: Macchina -> Corridoio -> ... -> Target
                length_greedy = math.dist(pos[source], pos[nearest_corridor]) + sum(
                    math.dist(pos[full_path[i]], pos[full_path[i+1]])
                    for i in range(len(full_path)-1)
                )
                percorso_greedy = " --> ".join(G.nodes[n]["entity_name"] for n in full_path)
                dettaglio_greedy = breakdown_path(full_path, pos)
            else:
                percorso_greedy = "Nessun percorso"
                dettaglio_greedy = ""
                length_greedy = None
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
    towrite.seek(0)
    
    st.download_button(
        label="Scarica file Excel",
        data=towrite,
        file_name="risultati_percorsi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    main()


