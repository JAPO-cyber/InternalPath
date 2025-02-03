import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import io
from PIL import Image
import matplotlib.pyplot as plt
from collections import defaultdict

def main():
    st.title("Grafo Corridoio-Macchina – Constrained Path using Size")

    # 1. Upload Excel file
    excel_file = st.file_uploader(
        label="Carica un file Excel (X, Y, Tag, Entity Name, Size)",
        type=["xls", "xlsx"]
    )
    
    # 2. (Optional) Upload background image
    bg_image_file = st.file_uploader(
        label="Carica un'immagine di sfondo (jpg, jpeg, png) [Opzionale]",
        type=["jpg", "jpeg", "png"]
    )
    
    if excel_file is not None:
        # Read the DataFrame
        df = pd.read_excel(excel_file)
        st.subheader("Anteprima del DataFrame caricato")
        st.dataframe(df.head())
        
        # Verify required columns
        needed_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
        for c in needed_cols:
            if c not in df.columns:
                st.error(f"Colonna '{c}' mancante nel file Excel.")
                return
        
        # Convert X and Y to numeric
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
        
        # Split into corridor and machine nodes
        df_corridoio = df[df["Tag"] == "Corridoio"].copy()
        df_macchina = df[df["Tag"] == "Macchina"].copy()
        if df_corridoio.empty:
            st.warning("Non ci sono corridoi: impossibile costruire il grafo completo.")
            return
        if df_macchina.empty:
            st.warning("Non ci sono macchine: non ci sono coppie da calcolare.")
        
        # Create the master graph G (which will contain the MST of corridors)
        G = nx.Graph()
        for idx, row in df.iterrows():
            G.add_node(
                idx,
                x=row["X"],
                y=row["Y"],
                tag=row["Tag"],
                name=row["Entity Name"],
                size=row.get("Size", None)
            )
        
        # Euclidean distance function
        def distance(n1, n2):
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))
        
        # --- Build the MST for corridors (for visualization purposes) ---
        corr_indices = df_corridoio.index.tolist()
        G_corr = nx.Graph()
        G_corr.add_nodes_from(corr_indices)
        for i in range(len(corr_indices)):
            for j in range(i + 1, len(corr_indices)):
                n1 = corr_indices[i]
                n2 = corr_indices[j]
                d = distance(n1, n2)
                G_corr.add_edge(n1, n2, weight=d)
        mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')
        for (c1, c2) in mst_corridoi.edges():
            G.add_edge(c1, c2, weight=G_corr[c1][c2]["weight"])
        
        # --- Build the constrained edge graph H using your chain logic ---
        H = nx.Graph()
        # Add all machine nodes to H (with attributes)
        for idx in df_macchina.index:
            H.add_node(idx, **G.nodes[idx])
        # (Corridor nodes will be added as they appear in the chains.)
        
        def choose_corridor_chain(machine_idx, corridor_indices):
            """
            For the given machine, build a chain of corridor nodes by applying the directional constraint at every step.
            
            For the first candidate, filter corridor nodes using the machine’s coordinate and Size condition.
            Then, for subsequent candidates, filter using the previously chosen corridor node.
            If no candidate is found for the first step, return an empty list.
            """
            size_val = G.nodes[machine_idx]["size"]
            direction = size_val.strip().lower() if isinstance(size_val, str) else ""
            machine_x = G.nodes[machine_idx]["x"]
            machine_y = G.nodes[machine_idx]["y"]
            chain = []
            
            if direction == "destro":
                valid_first = [c for c in corridor_indices if G.nodes[c]["x"] > machine_x]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["x"])
            elif direction == "sinistro":
                valid_first = [c for c in corridor_indices if G.nodes[c]["x"] < machine_x]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["x"], reverse=True)
            elif direction == "alto":
                valid_first = [c for c in corridor_indices if G.nodes[c]["y"] > machine_y]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["y"])
            elif direction == "basso":
                valid_first = [c for c in corridor_indices if G.nodes[c]["y"] < machine_y]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["y"], reverse=True)
            else:
                # No directional constraint: return the single nearest corridor.
                candidate = min(corridor_indices, key=lambda c: distance(machine_idx, c))
                return [candidate]
            
            if not sorted_first:
                return []  # no valid candidate for the machine
            
            chain.append(sorted_first[0])
            last = sorted_first[0]
            while True:
                if direction == "destro":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["x"] > G.nodes[last]["x"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["x"])
                elif direction == "sinistro":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["x"] < G.nodes[last]["x"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["x"], reverse=True)
                elif direction == "alto":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["y"] > G.nodes[last]["y"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["y"])
                elif direction == "basso":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["y"] < G.nodes[last]["y"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["y"], reverse=True)
                else:
                    valid_next = []
                
                valid_next = [c for c in valid_next if c not in chain]
                if not valid_next:
                    break
                chain.append(valid_next[0])
                last = valid_next[0]
            return chain
        
        # For each machine, compute its constrained chain and add corresponding edges to H.
        for idx_m in df_macchina.index:
            chain = choose_corridor_chain(idx_m, corr_indices)
            if chain:
                for c in chain:
                    if c not in H:
                        H.add_node(c, **G.nodes[c])
                w1 = distance(idx_m, chain[0])
                H.add_edge(idx_m, chain[0], weight=w1)
                for i in range(len(chain) - 1):
                    w = distance(chain[i], chain[i+1])
                    H.add_edge(chain[i], chain[i+1], weight=w)
            else:
                st.write(f"Nessun nodo corridoio soddisfa il filtro per la macchina '{G.nodes[idx_m]['name']}' con Size '{G.nodes[idx_m]['size']}'.")

        st.write(f"**Nodi in G**: {G.number_of_nodes()}")
        st.write(f"**Archi in G**: {G.number_of_edges()}")
        st.write(f"**Nodi in H (constrained edges)**: {H.number_of_nodes()}")
        st.write(f"**Archi in H (constrained edges)**: {H.number_of_edges()}")
        
        # --- 3) Compute shortest paths between machines using H ---
        st.subheader("Distanze tra coppie di macchine (usando solo vincoli Size)")
        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) < 2:
            st.info("Meno di due macchine, nessuna coppia da calcolare.")
            return
        
        results = []
        edge_usage_count = defaultdict(int)
        for m1, m2 in itertools.combinations(machine_indices, 2):
            try:
                path_nodes = nx.shortest_path(H, m1, m2, weight='weight')
            except nx.NetworkXNoPath:
                st.write(f"Nessun percorso tra {G.nodes[m1]['name']} e {G.nodes[m2]['name']} nel grafo vincolato.")
                continue
            seg_dists = []
            for i in range(len(path_nodes) - 1):
                seg_d = H[path_nodes[i]][path_nodes[i+1]]['weight']
                seg_dists.append(seg_d)
                edge_key = tuple(sorted([path_nodes[i], path_nodes[i+1]]))
                edge_usage_count[edge_key] += 1
            tot_d = sum(seg_dists)
            path_names = [H.nodes[nd]["name"] for nd in path_nodes]
            results.append({
                "Coppia Macchine": f"{H.nodes[m1]['name']} - {H.nodes[m2]['name']}",
                "Percorso (macchine + corridoi)": " -> ".join(path_names),
                "Somma distanze (stringa)": " + ".join(f"{d:.2f}" for d in seg_dists) + f" = {tot_d:.2f}",
                "Valore complessivo": tot_d
            })
        
        # Build results DataFrame; check for key before sorting
        df_results = pd.DataFrame(results)
        if not df_results.empty and "Valore complessivo" in df_results.columns:
            df_results = df_results.sort_values(by="Valore complessivo", ascending=True)
        st.write("Tabella dei risultati (usando solo i vincoli Size):")
        st.dataframe(df_results)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_results.to_excel(writer, index=False, sheet_name="Distanze_coppie")
        st.download_button(
            label="Scarica risultati in Excel",
            data=output.getvalue(),
            file_name="distanze_coppie_macchine.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # --- 4) Visualization of constrained subgraph H ---
        st.subheader("Visualizzazione del sottografo H (solo vincoli Size)")
        if bg_image_file is not None:
            bg_image = Image.open(bg_image_file)
            x_min, x_max = df["X"].min(), df["X"].max()
            y_min, y_max = df["Y"].min(), df["Y"].max()
            if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
                st.warning("Coordinate X/Y non valide, impossibile mostrare l'immagine di sfondo.")
            else:
                fig2, ax2 = plt.subplots(figsize=(10, 8))
                ax2.imshow(bg_image, extent=[x_min, x_max, y_min, y_max],
                           aspect='auto', origin='upper')
                for (n1, n2) in H.edges():
                    x1, y1 = H.nodes[n1]["x"], H.nodes[n1]["y"]
                    x2, y2 = H.nodes[n2]["x"], H.nodes[n2]["y"]
                    ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)
                machine_nodes = [n for n in H.nodes() if H.nodes[n]["tag"] == "Macchina"]
                corridor_nodes = [n for n in H.nodes() if H.nodes[n]["tag"] == "Corridoio"]
                if machine_nodes:
                    x_machine = [H.nodes[n]["x"] for n in machine_nodes]
                    y_machine = [H.nodes[n]["y"] for n in machine_nodes]
                    ax2.scatter(x_machine, y_machine, color='red', marker='s', label='Macchina')
                if corridor_nodes:
                    x_corr = [H.nodes[n]["x"] for n in corridor_nodes]
                    y_corr = [H.nodes[n]["y"] for n in corridor_nodes]
                    ax2.scatter(x_corr, y_corr, color='green', marker='o', label='Corridoio')
                ax2.set_title("Sottografo H – Solo vincoli Size")
                ax2.legend()
                st.pyplot(fig2)
        else:
            st.write("Nessuna immagine di sfondo caricata.")
    else:
        st.write("Carica un file Excel per iniziare.")

if __name__ == "__main__":
    main()


