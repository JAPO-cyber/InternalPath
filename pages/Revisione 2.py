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
                size=row.get("Size", "")
            )
        
        # Function for weighted distance with directional constraints
        def weighted_distance(n1, n2):
            x1, y1, pref = G.nodes[n1]["x"], G.nodes[n1]["y"], G.nodes[n1].get("size", "")
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            base_weight = math.dist((x1, y1), (x2, y2))
            
            if pref == "destro" and x2 < x1:
                return base_weight * 1000  # Penalizzazione più severa
            elif pref == "sinistro" and x2 > x1:
                return base_weight * 1000
            elif pref == "alto" and y2 < y1:
                return base_weight * 1000
            elif pref == "basso" and y2 > y1:
                return base_weight * 1000
            else:
                return base_weight * 1.0  # Mantiene il peso standard se segue la direzione
        
        # --- Build the constrained corridor connections respecting Size constraints ---
        corr_indices = df_corridoio.index.tolist()
        G_corr = nx.Graph()
        G_corr.add_nodes_from(corr_indices)
        for i in range(len(corr_indices)):
            for j in range(i + 1, len(corr_indices)):
                n1, n2 = corr_indices[i], corr_indices[j]
                d = weighted_distance(n1, n2)
                G_corr.add_edge(n1, n2, weight=d)
        mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')
        for (c1, c2) in mst_corridoi.edges():
            G.add_edge(c1, c2, weight=G_corr[c1][c2]["weight"])
        
        # Ensure sequential connection of corridor nodes following size constraints
        for idx in df_corridoio.index:
            size_val = G.nodes[idx]["size"]
            if size_val == "destro":
                valid_corridors = [c for c in df_corridoio.index if G.nodes[c]["x"] > G.nodes[idx]["x"]]
            elif size_val == "sinistro":
                valid_corridors = [c for c in df_corridoio.index if G.nodes[c]["x"] < G.nodes[idx]["x"]]
            elif size_val == "alto":
                valid_corridors = [c for c in df_corridoio.index if G.nodes[c]["y"] > G.nodes[idx]["y"]]
            elif size_val == "basso":
                valid_corridors = [c for c in df_corridoio.index if G.nodes[c]["y"] < G.nodes[idx]["y"]]
            else:
                valid_corridors = df_corridoio.index.tolist()
            
            if valid_corridors:
                next_corridor = min(valid_corridors, key=lambda c: weighted_distance(idx, c))
                G.add_edge(idx, next_corridor, weight=weighted_distance(idx, next_corridor))
        
        # Compute shortest paths between machine nodes
        st.subheader("Percorsi ottimizzati tra macchine con direzioni vincolate")
        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) >= 2:
            for m1, m2 in itertools.combinations(machine_indices, 2):
                try:
                    path_nodes = nx.shortest_path(G, m1, m2, weight='weight')
                    path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
                    
                    fig, ax = plt.subplots(figsize=(10, 8))
                    for (n1, n2) in path_edges:
                        x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
                        x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
                        ax.plot([x1, x2], [y1, y2], color='red', linewidth=2)
                    
                    st.pyplot(fig)
                except nx.NetworkXNoPath:
                    st.write(f"Nessun percorso trovato tra {G.nodes[m1]['name']} e {G.nodes[m2]['name']}")

if __name__ == "__main__":
    main()





