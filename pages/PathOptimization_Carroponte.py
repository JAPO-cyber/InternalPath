import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import matplotlib.pyplot as plt
import io

def is_valid_direction(current_pos, candidate_pos, direction):
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
    x = False
    
    if not isinstance(direction, str):
        direction = str(direction)
    if direction == "verticale":      
        if dist_y > dist_x: 
            x = True 
        else: 
            x = False 
    elif direction == "orizzontale":
        if dist_y < dist_x:
            x = True  
        else:
            x = False
    else:
        x = True
    return x

def is_valid_direction_filter(entity_i, entity_j, current_pos, candidate_pos, direction, stream, stream_j):
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
    x = False
    
    if not isinstance(direction, str):
        direction = str(direction)    
    if not isinstance(stream, str):
        stream = str(stream)

    if stream_j is not None and not isinstance(stream_j, str):
        stream_j = str(stream_j)

    if stream == "destro":
        x = x2 > x1
    elif stream == "sinistro":
        x = x2 < x1
    elif stream == "alto":
        x = y2 > y1
    elif stream == "basso":
        x = y2 < y1
    elif stream == "orizzontale":
        x = dist_y < dist_x
    elif direction == "verticale":
        x = dist_y > dist_x
    else:
        x = True
    
    return x

def breakdown_path(path, pos):
    """
    Restituisce la lista dei segmenti (senza somma finale) e, come secondo valore, il totale numerico.
    Esempio di detail_str: "0.05 + 0.49 + 0.10"
    """
    segments = []
    total = 0.0
    for i in range(len(path) - 1):
        d = math.dist(pos[path[i]], pos[path[i+1]])
        segments.append(d)
        total += d
    
    # Mostriamo solo i segmenti, senza "= somma"
    detail_str = " + ".join(f"{seg:.5f}" for seg in segments)
    return detail_str, total

def display_graph(G, pos, corridors, machines):
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

def Creazione_G(tipologia_grafo, df_all, max_distance):
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
        # Calcolo della distanza euclidea
        dist = math.dist(pos_i, pos_j)
        if dist <= max_distance:
            if tipologia_grafo == "STD":
                if is_valid_direction(pos_i, pos_j, G.nodes[i]["size"]):
                    G.add_edge(i, j, weight=dist)
            else:
                if is_valid_direction_filter(entity_i, entity_j, pos_i, pos_j, G.nodes[i]["size"], G.nodes[i]["stream"], stream_j):
                    G.add_edge(i, j, weight=dist)
    # 2. Connessione Macchina -> Corridoio:
    machine_nodes = [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]
    for machine in machine_nodes:
        machine_pos = (G.nodes[machine]["x"], G.nodes[machine]["y"])
        best_corridor = None
        best_dist = float('inf')
        for corridor in corridor_nodes:
            corridor_pos = (G.nodes[corridor]["x"], G.nodes[corridor]["y"])
            dist = math.dist(machine_pos, corridor_pos)
            if dist < best_dist:
                best_dist = dist
                best_corridor = corridor
        if best_corridor is not None and best_dist <= max_distance:
            G.add_edge(machine, best_corridor, weight=best_dist)
            G.add_edge(best_corridor, machine, weight=best_dist)
    return G

def main():
    st.title("Spaghetti Chart - Sito con Carriponte")
    
    uploaded_file = st.file_uploader("Carica file Excel (xls, xlsx) o CSV", type=["xls", "xlsx", "csv"])
    if not uploaded_file:
        st.info("Carica un file per iniziare.")
        return

    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    for col in ["X", "Y", "LenX", "LenY"]:
        df[col] = df[col].astype(str).str.replace(" m", "", regex=False).str.replace(",", ".").astype(float)
       
    st.subheader("Anteprima e modifica dei dati")
    edited_data = st.data_editor(df[df.columns[:7]], num_rows="dynamic")
    df.update(edited_data)
    required_cols = ["X", "Y","LenX","LenY", "Tag", "Entity Name", "Size", "URL"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Colonna '{col}' mancante nel file.")
            return

    
    
    df_corridor = df[df["Tag"] == "Corridoio"].copy()
    df_machine = df[df["Tag"] == "Macchina"].copy()
    df_aree_corridor= df[df["Tag"] == "Area Corridoio"].copy()

    st.subheader("Download aree per macchine")
    df_download_1=pd.concat([df_aree_corridor, df_machine])    
    towrite = io.BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df_download_1.to_excel(writer, index=False, sheet_name='Aree')
    towrite.seek(0)
    st.download_button(
        label="Scarica file Excel",
        data=towrite,
        file_name="aree e corridoi.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    if df_corridor.empty:
        st.warning("Nessun corridoio presente. Impossibile costruire il grafo.")
        return
    if df_machine.empty:
        st.warning("Nessuna macchina presente.")
        return
    # Modifica del punto macchina da macchina a rettangolo
    df_machine['X'] = df_machine['X'] + df_machine['LenX'] / 2
    df_machine['Y'] = df_machine['Y'] + df_machine['LenY'] / 2
    df_all = pd.concat([df_corridor, df_machine])



    st.subheader("Costruzione del grafo")
    max_distance = st.slider("Distanza massima per collegare i nodi", 
                               min_value=0.0, max_value=1.0, value=0.5,
                               help="Due nodi vengono collegati se la distanza euclidea è ≤ a questo valore.")
    
    G = Creazione_G('STD', df_all, max_distance) 
    G_filter = Creazione_G('filter', df_all, max_distance)
    
    st.subheader("Scegli la visualizzazione")
    scelta = st.radio("Scegli il valore:", ("Ottimale", "Corridoi vincolati"), index=0)
    st.write("Hai scelto:", scelta)
    
    if scelta == "Ottimale":
        G_graph = G
    elif scelta == "Corridoi vincolati":
        G_graph = G_filter

    st.write("Colonna con percorsi senza vincoli")
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

    # Per semplificare la gestione, usiamo sempre G per calcolare l'elenco delle macchine
    machine_nodes_sorted = sorted(
        [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"],
        key=lambda n: G.nodes[n]["entity_name"]
    )

    for source, target in itertools.permutations(machine_nodes_sorted, 2):
        source_name = G.nodes[source]["entity_name"]
        target_name = G.nodes[target]["entity_name"]
        collegamento = f"{source_name} --> {target_name}"
        
        # ----------------------------------------------------------
        # PERCORSO OTTIMALE
        # ----------------------------------------------------------
        corridor_neighbors = [n for n in G.neighbors(source) if G.nodes[n]["tag"] == "Corridoio"]
        
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            if nx.has_path(G, nearest_corridor, target):
                sub_path = nx.shortest_path(G, source=nearest_corridor, target=target, weight="weight")
                full_path = [source] + sub_path
                dettaglio_ottimale, total_ottimale = breakdown_path(full_path, pos)
                
                percorso_ottimale = " --> ".join(G.nodes[n]["entity_name"] for n in full_path)
                length_euclid = total_ottimale
            else:
                percorso_ottimale = "Nessun percorso"
                dettaglio_ottimale = ""
                length_euclid = None
        else:
            percorso_ottimale = "Nessun percorso"
            dettaglio_ottimale = ""
            length_euclid = None
        
        # ----------------------------------------------------------
        # PERCORSO VINCOLATO (G_filter)
        # ----------------------------------------------------------
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            if nx.has_path(G_filter, nearest_corridor, target):
                sub_path = nx.shortest_path(G_filter, source=nearest_corridor, target=target, weight="weight")
                full_path_greedy = [source] + sub_path

                dettaglio_greedy, total_greedy = breakdown_path(full_path_greedy, pos)
                percorso_greedy = " --> ".join(G_filter.nodes[n]["entity_name"] for n in full_path_greedy)
                length_greedy = total_greedy
                
                # --------------------------------------------------
                # Calcolo campi per carroponte e carrello
                # --------------------------------------------------
                presa_carroponte = 0
                componente_carroponte = ""
                metri_carroponte = 0.0
                presa_carrello = 0
                componente_carrello = ""
                metri_carrello = 0.0
                
                for i in range(len(full_path_greedy) - 1):
                    current_node = full_path_greedy[i]
                    next_node = full_path_greedy[i+1]
                    
                    # Se non siamo all'ultimo segmento e il nodo di destinazione non è un Corridoio, lo saltiamo
                    if i != len(full_path_greedy) - 2 and G.nodes[next_node]["tag"] != "Corridoio":
                        continue
                        
                    d = math.dist(pos[current_node], pos[next_node])
                    
                    if i == len(full_path_greedy) - 2 and G.nodes[next_node]["tag"] != "Corridoio":
                        # Uso la lettera del nodo corrente (corridoio)
                        source_letter = G.nodes[current_node]["entity_name"].strip()[0].upper()
                        dest_letter = source_letter
                    else:
                        dest_name = G.nodes[next_node]["entity_name"]
                        dest_letter = dest_name.strip()[0].upper()
                        if G.nodes[current_node]["tag"] == "Corridoio":
                            source_letter = G.nodes[current_node]["entity_name"].strip()[0].upper()
                        else:
                            source_letter = None
                    
                    if dest_letter == "C":
                        if source_letter != "C":
                            presa_carroponte += 1
                        if componente_carroponte == "":
                            componente_carroponte = f"{d:.2f}"
                        else:
                            componente_carroponte += " + " + f"{d:.2f}"
                        metri_carroponte += d
                    elif dest_letter == "V":
                        if source_letter != "V":
                            presa_carrello += 1
                        if componente_carrello == "":
                            componente_carrello = f"{d:.2f}"
                        else:
                            componente_carrello += " + " + f"{d:.2f}"
                        metri_carrello += d

            else:
                percorso_greedy = "Nessun percorso"
                dettaglio_greedy = ""
                length_greedy = None
                presa_carroponte = ""
                componente_carroponte = ""
                metri_carroponte = ""
                presa_carrello = ""
                componente_carrello = ""
                metri_carrello = ""
        else:
            percorso_greedy = "Nessun percorso"
            dettaglio_greedy = ""
            length_greedy = None
            presa_carroponte = ""
            componente_carroponte = ""
            metri_carroponte = ""
            presa_carrello = ""
            componente_carrello = ""
            metri_carrello = ""
        
        # Salviamo i risultati
        results.append({
            "Collegamento Macchina": collegamento,
            "Percorso Ottimale Seguito": percorso_ottimale,
            "Dettaglio Distanze Ottimale": dettaglio_ottimale,  # "0.05 + 0.49 + 0.10"
            "Lunghezza Totale Ottimale": length_euclid,         # 0.64
            "Percorso Vincolato Seguito": percorso_greedy,
            "Dettaglio Distanze Vincolato": dettaglio_greedy,   # "0.05 + 0.49 + 0.10"
            "Lunghezza Totale Vincolato": length_greedy,        # 0.64
            "presa carroponte": presa_carroponte,
            "componente carroponte": componente_carroponte,
            "metri carroponte": metri_carroponte,
            "presa carrello": presa_carrello,
            "componente carrello": componente_carrello,
            "metri carrello": metri_carrello
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


