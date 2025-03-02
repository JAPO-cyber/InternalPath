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
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
    
    if not isinstance(direction, str):
        direction = str(direction)
    if direction == "verticale":
        return dist_y > dist_x
    elif direction == "orizzontale":
        return dist_x > dist_y
    else:
        return True

def is_valid_direction_filter(entity_i, entity_j, current_pos, candidate_pos, direction, stream, stream_j, invert=False):
    """
    Verifica se il candidato (candidate_pos) rispetta il vincolo direzionale.
    Se invert è True, il vincolo di 'stream' viene invertito.
    """
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
    
    # Applica inversione se richiesto
    if invert:
        if stream == "destro":
            stream = "sinistro"
        elif stream == "sinistro":
            stream = "destro"
        elif stream == "alto":
            stream = "basso"
        elif stream == "basso":
            stream = "alto"
    
    # Applicazione dei vincoli in base al campo 'stream'
    if stream == "destro":
        return x2 > x1
    elif stream == "sinistro":
        return x2 < x1
    elif stream == "alto":
        return y2 > y1
    elif stream == "basso":
        return y2 < y1
    elif stream == "orizzontale":
        return dist_y < dist_x
    elif stream == "verticale":
        return dist_y > dist_x
    else:
        return True

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

def Creazione_G(tipologia_grafo, df_all, max_distance, invert=False):
    G = nx.DiGraph()
    for idx, row in df_all.iterrows():
        G.add_node(idx, 
                   x=row["X"], 
                   y=row["Y"], 
                   tag=row["Tag"], 
                   entity_name=row["Entity Name"], 
                   size=row["Size"],
                   stream=row["URL"])
    # 1. Connessione fra Corridoi:
    corridor_nodes = [n for n, d in G.nodes(data=True) if d["tag"] == "Corridoio"] 
    for i, j in itertools.permutations(corridor_nodes, 2):
        entity_i = G.nodes[i]["entity_name"]
        entity_j = G.nodes[j]["entity_name"]
        pos_i = (G.nodes[i]["x"], G.nodes[i]["y"])
        pos_j = (G.nodes[j]["x"], G.nodes[j]["y"])
        stream_j = G.nodes[j]["stream"]
        dist = abs(pos_j[0] - pos_i[0]) + abs(pos_j[1] - pos_i[1])
        if dist <= max_distance:
            if tipologia_grafo == "STD":
                if is_valid_direction(pos_i, pos_j, G.nodes[i]["size"]):
                    G.add_edge(i, j, weight=dist)
            else:
                if is_valid_direction_filter(entity_i, entity_j, pos_i, pos_j, G.nodes[i]["size"], G.nodes[i]["stream"], stream_j, invert=invert):
                    G.add_edge(i, j, weight=dist)
    # 2. Connessione Macchina -> Corridoio:
    machine_nodes = [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]
    for machine in machine_nodes:
        # Verifica se la macchina è già collegata a un corridoio
        if any(G.has_edge(machine, corr) for corr in corridor_nodes):
            continue
        machine_pos = (G.nodes[machine]["x"], G.nodes[machine]["y"])
        best_corridor = None
        best_dist = float('inf')
        # Ottieni il vincolo direzionale dalla macchina (colonna URL)
        machine_direction = G.nodes[machine]["stream"]
        for corridor in corridor_nodes:
            corridor_pos = (G.nodes[corridor]["x"], G.nodes[corridor]["y"])
            # Considera solo i corridoi che rispettano il vincolo direzionale della macchina
            if is_valid_direction_filter(G.nodes[machine]["entity_name"],
                                         G.nodes[corridor]["entity_name"],
                                         machine_pos, corridor_pos,
                                         G.nodes[machine]["size"],
                                         machine_direction,
                                         None,
                                         invert=False):
                d = math.dist(machine_pos, corridor_pos)
                if d < best_dist:
                    best_dist = d
                    best_corridor = corridor
        if best_corridor is not None and best_dist <= max_distance:
            # Colleghiamo la macchina al corridoio più vicino che soddisfa il vincolo (archi in entrambe le direzioni)
            G.add_edge(machine, best_corridor, weight=best_dist)
            G.add_edge(best_corridor, machine, weight=best_dist)
    return G

def main():
    st.title("Collegamento Macchine Tramite Corridoi – Calcolo di tutte le coppie")
    
    # 1. Caricamento del file (Excel o CSV)
    uploaded_file = st.file_uploader("Carica file Excel (xls, xlsx) o CSV", type=["xls", "xlsx", "csv"])
    if not uploaded_file:
        st.info("Carica un file per iniziare.")
        return

    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # 2. Anteprima e modifica del DataFrame (colonne "Entity Name", "Size" e "URL")
    st.subheader("Anteprima e modifica dei dati")
    edited_data = st.data_editor(df[['Entity Name', 'Size', 'URL']], num_rows="dynamic")
    df.update(edited_data)
    
    # Verifica delle colonne necessarie
    required_cols = ["X", "Y", "Tag", "Entity Name", "Size", "URL"]
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
    
    df_all = pd.concat([df_corridor, df_machine])
    
    # 3. Costruzione del grafo
    st.subheader("Costruzione del grafo")
    max_distance = st.slider("Distanza massima per collegare i nodi", 
                               min_value=0.0, max_value=5.0, value=4.0,
                               help="Due nodi vengono collegati se la distanza Manhattan è ≤ a questo valore.")
    
    G = Creazione_G('STD', df_all, max_distance) 
    G_filter = Creazione_G('filter', df_all, max_distance, invert=False)
    G_filter_inv = Creazione_G('filter', df_all, max_distance, invert=True)
    
    st.subheader("Scegli la visualizzazione")
    scelta = st.radio("Scegli il valore:", ("Ottimale", "Corridoi vincolati"), index=0)
    st.write("Hai scelto:", scelta)
    
    if scelta == "Ottimale":
        G_graph = G
    elif scelta == "Corridoi vincolati":
        G_graph = G_filter

    st.write("Numero totale di nodi:", G_graph.number_of_nodes())
    st.write("Numero totale di archi:", G_graph.number_of_edges())
    
    pos = {node: (data["x"], data["y"]) for node, data in G_graph.nodes(data=True)}
    corridors = [n for n, d in G_graph.nodes(data=True) if d["tag"] == "Corridoio"]
    machines = [n for n, d in G_graph.nodes(data=True) if d["tag"] == "Macchina"]
    
    st.subheader("Grafico dei Nodi")
    display_graph(G_graph, pos, corridors, machines)
    
    corridor_edges = []
    for u, v, data_dict in G_graph.edges(data=True):
        if G_graph.nodes[u]["tag"] == "Corridoio" and G_graph.nodes[v]["tag"] == "Corridoio":
            corridor_edges.append({
                "Corridoio 1": G_graph.nodes[u].get("entity_name", f"ID: {u}"),
                "Corridoio 2": G_graph.nodes[v].get("entity_name", f"ID: {v}"),
                "Distanza (m)": data_dict["weight"]
            })
    
    df_corridor_edges = pd.DataFrame(corridor_edges)
    st.subheader("Tabella delle Connessioni fra Corridoi")
    edited_edges = st.data_editor(df_corridor_edges, num_rows="dynamic", key="corridor_edges_editor")
    
    st.subheader("Calcolo dei percorsi per tutte le coppie di macchine")
    results = []
    machine_nodes_sorted = sorted([n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"],
                                  key=lambda n: G.nodes[n]["entity_name"])
    
    for source, target in itertools.permutations(machine_nodes_sorted, 2):
        source_name = G.nodes[source]["entity_name"]
        target_name = G.nodes[target]["entity_name"]
        collegamento = f"{source_name} --> {target_name}"
        
        corridor_neighbors = [n for n in G.neighbors(source) if G.nodes[n]["tag"] == "Corridoio"]
        
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            if nx.has_path(G, nearest_corridor, target):
                sub_path = nx.shortest_path(G, source=nearest_corridor, target=target, weight="weight")
                length_sub = nx.shortest_path_length(G, source=nearest_corridor, target=target, weight="weight")
                full_path = [source] + sub_path
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
        
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            if nx.has_path(G_filter, nearest_corridor, target):
                sub_path = nx.shortest_path(G_filter, source=nearest_corridor, target=target, weight="weight")
                length_sub = nx.shortest_path_length(G_filter, source=nearest_corridor, target=target, weight="weight")
                full_path = [source] + sub_path
                length_greedy = math.dist(pos[source], pos[nearest_corridor]) + length_sub
                percorso_greedy = " --> ".join(G_filter.nodes[n]["entity_name"] for n in full_path)
                dettaglio_greedy = breakdown_path(full_path, pos)
            else:
                percorso_greedy = "Nessun percorso"
                dettaglio_greedy = ""
                length_greedy = None
        else:
            percorso_greedy = "Nessun percorso"
            dettaglio_greedy = ""
            length_greedy = None
        
        corridor_neighbors_return = [n for n in G_filter_inv.neighbors(target) if G_filter_inv.nodes[n]["tag"] == "Corridoio"]
        if corridor_neighbors_return:
            nearest_corridor_return = min(corridor_neighbors_return, key=lambda n: math.dist(pos[target], pos[n]))
            if nx.has_path(G_filter_inv, nearest_corridor_return, source):
                sub_path_return = nx.shortest_path(G_filter_inv, source=nearest_corridor_return, target=source, weight="weight")
                length_sub_return = nx.shortest_path_length(G_filter_inv, source=nearest_corridor_return, target=source, weight="weight")
                full_path_return = [target] + sub_path_return
                length_greedy_return = math.dist(pos[target], pos[nearest_corridor_return]) + length_sub_return
                percorso_greedy_return = " --> ".join(G_filter_inv.nodes[n]["entity_name"] for n in full_path_return)
                dettaglio_greedy_return = breakdown_path(full_path_return, pos)
            else:
                percorso_greedy_return = "Nessun percorso"
                dettaglio_greedy_return = ""
                length_greedy_return = None
        else:
            percorso_greedy_return = "Nessun percorso"
            dettaglio_greedy_return = ""
            length_greedy_return = None
        
        results.append({
            "Collegamento Macchina": collegamento,
            "Percorso Ottimale (Andata)": percorso_ottimale,
            "Dettaglio Distanze Ottimale": dettaglio_ottimale,
            "Lunghezza Totale Ottimale": length_euclid,
            "Percorso Vincolato Andata": percorso_greedy,
            "Dettaglio Distanze Vincolato Andata": dettaglio_greedy,
            "Lunghezza Totale Vincolato Andata": length_greedy,
            "Percorso Vincolato Ritorno": percorso_greedy_return,
            "Dettaglio Distanze Vincolato Ritorno": dettaglio_greedy_return,
            "Lunghezza Totale Vincolato Ritorno": length_greedy_return,
        })
    
    df_results = pd.DataFrame(results)
    st.subheader("Risultati per tutte le coppie di macchine")
    st.dataframe(df_results)
    
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



