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

# --- Funzioni di supporto ---

def is_valid_direction(current_pos, candidate_pos, direction):
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
    if not isinstance(direction, str):
        direction = str(direction)
    if direction == "verticale":
        return dist_y > dist_x
    elif direction == "orizzontale":
        return dist_y < dist_x
    else:
        return True

def is_valid_direction_filter(entity_i, entity_j, current_pos, candidate_pos, direction, stream, stream_j):
    x1, y1 = current_pos
    x2, y2 = candidate_pos
    dist_x = abs(x1 - x2)
    dist_y = abs(y1 - y2)
    if not isinstance(direction, str):
        direction = str(direction)
    if not isinstance(stream, str):
        stream = str(stream)
    if stream_j is not None and not isinstance(stream_j, str):
        stream_j = str(stream_j)
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
    elif direction == "verticale":
        return dist_y > dist_x
    else:
        return True

def breakdown_path(path, pos):
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
    # Connessione fra Corridoi
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
    # Connessione Macchina -> Corridoio
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

# --- Parte principale ---

def main():
    st.title("Spaghetti Chart - Sito con Carriponte")
    
    # Caricamento file dati per il grafo
    uploaded_file = st.file_uploader("Carica file Excel (xls, xlsx) o CSV", type=["xls", "xlsx", "csv"], key="main_file")
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
    
    # Pulizia delle colonne di coordinate
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
    
    # Costruzione di entrambi i grafi: "ottimale" e "vincolato"
    G = Creazione_G('STD', df_all, max_distance) 
    G_filter = Creazione_G('filter', df_all, max_distance)
    
    st.subheader("Scegli la visualizzazione")
    scelta = st.radio("Scegli il valore:", ("Ottimale", "Corridoi vincolati"), index=0)
    st.write("Hai scelto:", scelta)
    
    if scelta == "Ottimale":
        G_graph = G
    else:
        G_graph = G_filter

    st.write("Colonna con percorsi senza vincoli")
    st.write("Numero totale di nodi:", G_graph.number_of_nodes())
    st.write("Numero totale di archi:", G_graph.number_of_edges())
    
    pos = {node: (data["x"], data["y"]) for node, data in G_graph.nodes(data=True)}
    corridors = [n for n, d in G_graph.nodes(data=True) if d["tag"] == "Corridoio"]
    machines = [n for n, d in G_graph.nodes(data=True) if d["tag"] == "Macchina"]
    
    st.subheader("Grafico dei Nodi")
    display_graph(G_graph, pos, corridors, machines)
    
    # Calcolo percorsi per coppie di macchine (df_results)
    st.subheader("Calcolo dei percorsi per tutte le coppie di macchine")
    results = []
    machine_nodes_sorted = sorted(
        [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"],
        key=lambda n: G.nodes[n]["entity_name"]
    )
    for source, target in itertools.permutations(machine_nodes_sorted, 2):
        source_name = G.nodes[source]["entity_name"]
        target_name = G.nodes[target]["entity_name"]
        collegamento = f"{source_name} --> {target_name}"
        
        # PERCORSO OTTIMALE
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
        
        # PERCORSO VINCOLATO
        if corridor_neighbors:
            nearest_corridor = min(corridor_neighbors, key=lambda n: math.dist(pos[source], pos[n]))
            if nx.has_path(G_filter, nearest_corridor, target):
                sub_path = nx.shortest_path(G_filter, source=nearest_corridor, target=target, weight="weight")
                full_path_greedy = [source] + sub_path
                dettaglio_greedy, total_greedy = breakdown_path(full_path_greedy, pos)
                percorso_greedy = " --> ".join(G_filter.nodes[n]["entity_name"] for n in full_path_greedy)
                length_greedy = total_greedy
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
            "Percorso Vincolato Seguito": percorso_greedy,
            "Dettaglio Distanze Vincolato": dettaglio_greedy,
            "Lunghezza Totale Vincolato": length_greedy
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
    
    # --- Sezione aggiuntiva: Caricamento Excel Flussi per visualizzare percorsi basati sul campo "Path" ---
    st.subheader("Visualizzazione percorsi dal file Excel")
    
    # Caricamento dell'excel dei flussi (usa una chiave diversa)
    flussi_file = st.file_uploader(
        "Carica un file Excel o CSV con le colonne: Flussi, Path, Sequenza",
        type=["xls", "xlsx", "csv"],
        key="flows_file"
    )
    if flussi_file is not None:
        if flussi_file.name.lower().endswith("csv"):
            df_flussi = pd.read_csv(flussi_file)
        else:
            df_flussi = pd.read_excel(flussi_file)
        st.write("Anteprima dei flussi:")
        st.dataframe(df_flussi)
        
        # Filtro in base alla colonna "Flussi"
        flussi_options = sorted(df_flussi["Flussi"].unique())
        selected_flussi = st.multiselect(
            "Seleziona i flussi da visualizzare (filtraggio per 'Flussi')",
            options=flussi_options,
            default=flussi_options
        )
        df_filtered_flussi = df_flussi[df_flussi["Flussi"].isin(selected_flussi)]
        
        # (Facoltativo) Filtro per "Sequenza"
        sequenze_options = sorted(df_filtered_flussi["Sequenza"].unique())
        selected_sequenze = st.multiselect(
            "Seleziona le sequenze da visualizzare",
            options=sequenze_options,
            default=sequenze_options
        )
        df_filtered_flussi = df_filtered_flussi[df_filtered_flussi["Sequenza"].isin(selected_sequenze)]
        
        if df_filtered_flussi.empty:
            st.warning("Non ci sono righe che corrispondono ai filtri selezionati.")
        else:
            # Impostazione dimensioni del grafico per questa sezione
            graph_width = st.slider("Larghezza del grafico", 6, 20, 8, key="graph_width_flussi")
            graph_height = st.slider("Altezza del grafico", 6, 20, 6, key="graph_height_flussi")
            
            # Caricamento immagine di sfondo (opzionale) per questa sezione
            bg_file = st.file_uploader("Carica un'immagine di sfondo (opzionale)", type=["png", "jpg", "jpeg"], key="bg_file_flussi")
            bg_image = None
            if bg_file is not None:
                pil_img = PIL.Image.open(bg_file)
                bg_image = np.array(pil_img)
            
            # Il grafo e pos sono gli stessi; usiamo il mapping già definito
            mapping = {
                data.get("entity_name", f"node_{node}"): node
                for node, data in G_graph.nodes(data=True)
            }
            pos_local = pos
            xs = [pos_local[n][0] for n in G_graph.nodes()]
            ys = [pos_local[n][1] for n in G_graph.nodes()]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            available_colors = ["red", "blue", "green", "orange", "purple", "brown", "pink", "gray", "cyan", "magenta"]
            sequence_color_map = {}
            
            fig_flussi, ax_flussi = plt.subplots(figsize=(graph_width, graph_height))
            fig_flussi.patch.set_facecolor('none')
            ax_flussi.set_facecolor('none')
            
            if bg_image is not None:
                ax_flussi.imshow(bg_image, extent=(min_x, max_x, min_y, max_y), zorder=0, aspect='auto')
            
            # Disegniamo il grafo completo in grigio chiaro
            nx.draw_networkx_nodes(G_graph, pos_local, node_size=50, node_color="lightgray", ax=ax_flussi)
            nx.draw_networkx_edges(G_graph, pos_local, edge_color="lightgray", ax=ax_flussi, arrows=False, alpha=0.5)
            
            legend_patches = []
            used_labels = set()
            for idx, row in df_filtered_flussi.iterrows():
                flusso = row["Flussi"]
                path_str = row["Path"]
                seq = row["Sequenza"]
                
                if seq not in sequence_color_map:
                    sequence_color_map[seq] = available_colors[len(sequence_color_map) % len(available_colors)]
                color = sequence_color_map[seq]
                
                # Dividiamo il campo "Path" per ottenere i nomi dei nodi
                route_names = [p.strip() for p in path_str.split("-->")]
                route_ids = [mapping[name] for name in route_names if name in mapping]
                route_edges = [(route_ids[i], route_ids[i+1]) for i in range(len(route_ids)-1)]
                
                if route_edges:
                    nx.draw_networkx_edges(G_graph, pos_local,
                                           edgelist=route_edges,
                                           width=2,
                                           edge_color=color,
                                           ax=ax_flussi,
                                           arrows=False)
                if route_ids:
                    nx.draw_networkx_nodes(G_graph, pos_local,
                                           nodelist=route_ids,
                                           node_size=150,
                                           node_color=color,
                                           ax=ax_flussi)
                    labels = {nid: G_graph.nodes[nid].get("entity_name", f"node_{nid}") for nid in route_ids}
                    nx.draw_networkx_labels(G_graph, pos_local,
                                            labels,
                                            font_size=9,
                                            ax=ax_flussi,
                                            font_color="black")
                
                leg_label = f"{flusso} - Sequenza {seq}"
                if leg_label not in used_labels:
                    legend_patches.append(mpatches.Patch(color=color, label=leg_label))
                    used_labels.add(leg_label)
            
            ax_flussi.set_title("Percorsi dal file Excel (usando 'Path')")
            ax_flussi.axis("off")
            if legend_patches:
                ax_flussi.legend(handles=legend_patches, loc="upper left", title="Legenda")
            
            st.pyplot(fig_flussi)
            
            st.subheader("Dettagli Flussi")
            st.dataframe(df_filtered_flussi)
    
if __name__ == "__main__":
    main()





