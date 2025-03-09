import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import io
import PIL.Image
import numpy as np

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

    # Scala del progetto
    st.subheader("Valore di scala del disegno")
    scala = st.slider("Scala per collegare i nodi", 
                      min_value=0.0, max_value=200.0, value=158.3,
                      help="Il GeoJson viene scalato con questo valore per i calcolo dei parametri")
    
    # Rimuove " m", sostituisce la virgola con il punto e converte in float, moltiplicando per la scala
    for col in ["X", "Y", "LenX", "LenY"]:
        df[col] = (df[col].astype(str)
                   .str.replace(" m", "", regex=False)
                   .str.replace(",", ".")
                   .astype(float)
                   * scala)
       
    st.subheader("Anteprima e modifica dei dati")
    edited_data = st.data_editor(df[df.columns[:7]], num_rows="dynamic")
    df.update(edited_data)
    required_cols = ["X", "Y", "LenX", "LenY", "Tag", "Entity Name", "Size", "URL"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Colonna '{col}' mancante nel file.")
            return

    df_corridor = df[df["Tag"] == "Corridoio"].copy()
    df_machine = df[df["Tag"] == "Macchina"].copy()
    df_aree_corridor = df[df["Tag"] == "Area Corridoio"].copy()

    st.subheader("Download aree per macchine")
    df_download_1 = pd.concat([df_aree_corridor, df_machine])
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

    # Traslazione per centrare il rettangolo delle macchine
    df_machine['X'] = df_machine['X'] + df_machine['LenX'] / 2
    df_machine['Y'] = df_machine['Y'] + df_machine['LenY'] / 2
    df_all = pd.concat([df_corridor, df_machine])

    st.subheader("Costruzione del grafo")
    max_distance = st.slider("Distanza massima per collegare i nodi", 
                             min_value=0.0, max_value=20.0, value=5.0,
                             help="Due nodi vengono collegati se la distanza euclidea è ≤ a questo valore.")
    
    # Costruzione di entrambi i grafi: uno "ottimale" e uno con filtro
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

    # Ordinamento dei nodi macchina per nome
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
                
                # Calcolo campi per carroponte e carrello
                presa_carroponte = 0
                componente_carroponte = ""
                metri_carroponte = 0.0
                presa_carrello = 0
                componente_carrello = ""
                metri_carrello = 0.0
                
                for i in range(len(full_path_greedy) - 1):
                    current_node = full_path_greedy[i]
                    next_node = full_path_greedy[i+1]
                    
                    if i != len(full_path_greedy) - 2 and G.nodes[next_node]["tag"] != "Corridoio":
                        continue
                        
                    d = math.dist(pos[current_node], pos[next_node])
                    
                    if i == len(full_path_greedy) - 2 and G.nodes[next_node]["tag"] != "Corridoio":
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
        
        results.append({
            "Collegamento Macchina": collegamento,
            "Percorso Ottimale Seguito": percorso_ottimale,
            "Dettaglio Distanze Ottimale": dettaglio_ottimale,
            "Lunghezza Totale Ottimale": length_euclid,
            "Percorso Vincolato Seguito": percorso_greedy,
            "Dettaglio Distanze Vincolato": dettaglio_greedy,
            "Lunghezza Totale Vincolato": length_greedy,
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
    
    # --------------------------
    # CARICAMENTO E VISUALIZZAZIONE FLUSSI DA EXCEL (con sfondo trasparente)
    # --------------------------
#########################################################################################################################################################################
    st.subheader("Caricamento Excel Flussi (Percorsi colorati, senza frecce)")

flow_file = st.file_uploader(
    "Carica un file Excel o CSV con le colonne: Flussi, Path, Sequenza",
    type=["xls", "xlsx", "csv"]
)

if flow_file is not None:
    # Carichiamo il file in un DataFrame
    if flow_file.name.lower().endswith('.csv'):
        df_flows = pd.read_csv(flow_file)
    else:
        df_flows = pd.read_excel(flow_file)

    # Verifichiamo che siano presenti le colonne necessarie
    required_flows_cols = ["Flussi", "Path", "Sequenza"]
    for col in required_flows_cols:
        if col not in df_flows.columns:
            st.error(f"Colonna '{col}' mancante nel file di flussi.")
            st.stop()

    st.write("Anteprima Flussi:")
    st.dataframe(df_flows)

    # Filtriamo per Flussi
    flussi_unici = sorted(df_flows["Flussi"].unique())
    selected_flussi = st.multiselect(
        "Seleziona uno o più Flussi da visualizzare",
        options=flussi_unici,
        default=flussi_unici
    )
    df_filtered_flows = df_flows[df_flows["Flussi"].isin(selected_flussi)]

    # Filtriamo per Sequenza
    sequenze_uniche = sorted(df_filtered_flows["Sequenza"].unique())
    selected_sequenze = st.multiselect(
        "Seleziona una o più Sequenze da visualizzare",
        options=sequenze_uniche,
        default=sequenze_uniche
    )
    df_filtered_flows = df_filtered_flows[df_filtered_flows["Sequenza"].isin(selected_sequenze)]

    if df_filtered_flows.empty:
        st.warning("Non ci sono righe che corrispondono ai filtri selezionati.")
    else:
        # Impostiamo le dimensioni del grafico
        flow_graph_width = st.slider("Larghezza del grafico (Flussi)", 6, 20, 8)
        flow_graph_height = st.slider("Altezza del grafico (Flussi)", 6, 20, 6)

        # Caricamento dell'immagine di sfondo (opzionale)
        bg_file = st.file_uploader("Carica un'immagine di sfondo (PNG/JPG)", type=["png", "jpg", "jpeg"])
        bg_image = None
        if bg_file is not None:
            pil_img = PIL.Image.open(bg_file)
            bg_image = np.array(pil_img)

        # Si assume che le variabili G_graph e pos siano già definite nel contesto.
        # Creiamo la mappa: entity_name -> ID nodo.
        mapping = {
            data.get("entity_name", f"node_{node}"): node
            for node, data in G_graph.nodes(data=True)
        }
        pos_local = pos  # Dizionario: {nodo: (x, y)}

        # Calcoliamo i limiti per adattare l'immagine di sfondo
        xs = [pos_local[n][0] for n in G_graph.nodes()]
        ys = [pos_local[n][1] for n in G_graph.nodes()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Impostiamo i colori disponibili e la mappa per le sequenze
        available_colors = [
            "red", "blue", "green", "orange", "purple",
            "brown", "pink", "gray", "cyan", "magenta"
        ]
        sequence_color_map = {}

        fig_flow, ax_flow = plt.subplots(figsize=(flow_graph_width, flow_graph_height))
        fig_flow.patch.set_facecolor('none')
        ax_flow.set_facecolor('none')

        # Se presente, disegniamo l'immagine di sfondo
        if bg_image is not None:
            ax_flow.imshow(
                bg_image,
                extent=(min_x, max_x, min_y, max_y),
                zorder=0,
                aspect='auto'
            )

        # Disegniamo l'intero grafo in grigio chiaro (nodi e archi) senza frecce
        nx.draw_networkx_nodes(G_graph, pos_local, node_size=50, node_color="lightgray", ax=ax_flow)
        nx.draw_networkx_edges(G_graph, pos_local, edge_color="lightgray", ax=ax_flow, arrows=False, alpha=0.5)

        df_flow_details = []
        used_sequences = set()

        # Per ogni flusso, estraiamo il percorso e coloriamo TUTTI i nodi e gli archi (inclusi i corridoi)
        for idx, row in df_filtered_flows.iterrows():
            flusso = row["Flussi"]
            path_str = row["Path"]
            seq = row["Sequenza"]

            # Assegniamo un colore per la sequenza
            if seq not in sequence_color_map:
                sequence_color_map[seq] = available_colors[len(sequence_color_map) % len(available_colors)]
            color = sequence_color_map[seq]
            used_sequences.add(seq)

            # Dividiamo il Path per ottenere i nomi dei nodi (il separatore è " --> ")
            route_nodes_names = [p.strip() for p in path_str.split("-->")]
            # Convertiamo i nomi in ID nodi, filtrando quelli non trovati nel mapping
            route_node_ids = [mapping[name] for name in route_nodes_names if name in mapping]

            # Se abbiamo almeno 2 nodi, costruiamo gli archi consecutivi per il percorso
            route_edges = []
            for i in range(len(route_node_ids) - 1):
                n1 = route_node_ids[i]
                n2 = route_node_ids[i+1]
                route_edges.append((n1, n2))
            # Tutti i nodi del percorso (anche se duplicati, li mettiamo in un set)
            route_nodes = set(route_node_ids)

            # Disegniamo gli archi del percorso con il colore assegnato (senza frecce)
            if route_edges:
                nx.draw_networkx_edges(
                    G_graph, pos_local,
                    edgelist=route_edges,
                    width=2,
                    edge_color=color,
                    ax=ax_flow,
                    arrows=False
                )
            # Disegniamo TUTTI i nodi del percorso con il colore assegnato
            if route_nodes:
                nx.draw_networkx_nodes(
                    G_graph, pos_local,
                    nodelist=list(route_nodes),
                    node_size=150,
                    node_color=color,
                    ax=ax_flow
                )
                labels = {
                    n: G_graph.nodes[n].get("entity_name", f"node_{n}")
                    for n in route_nodes
                }
                nx.draw_networkx_labels(
                    G_graph, pos_local,
                    labels,
                    font_size=9,
                    ax=ax_flow,
                    font_color="black"
                )

            df_flow_details.append({
                "Flussi": flusso,
                "Sequenza": seq,
                "Path": path_str,
                "Colore": color
            })

        ax_flow.set_title("Flussi Selezionati (Percorsi colorati, inclusi i corridoi)")
        ax_flow.axis("off")

        # Creiamo la legenda personalizzata per le sequenze
        legend_patches = []
        for seq_item in sorted(used_sequences):
            patch = mpatches.Patch(
                color=sequence_color_map[seq_item],
                label=f"Sequenza: {seq_item}"
            )
            legend_patches.append(patch)
        if legend_patches:
            ax_flow.legend(handles=legend_patches, loc="upper left", title="Legenda Sequenze")

        st.pyplot(fig_flow)

        # Mostriamo i dettagli in una tabella
        if df_flow_details:
            st.subheader("Dettagli Flussi Selezionati")
            st.dataframe(pd.DataFrame(df_flow_details))


##########################################################################################################################################################################
if __name__ == "__main__":
    main()




