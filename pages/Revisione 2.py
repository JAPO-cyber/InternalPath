import streamlit as st
import pandas as pd
import networkx as nx
import math

def main():
    st.title("Esempio di collegamento macchina-corridoio con colonna 'Size'")

    # Caricamento Excel
    excel_file = st.file_uploader("Carica un file Excel con colonne X, Y, Tag, Entity Name, Size", type=["xls", "xlsx"])
    if excel_file is None:
        st.write("Carica un file Excel per continuare.")
        return

    df = pd.read_excel(excel_file)

    # Controllo colonne
    needed_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
    for col in needed_cols:
        if col not in df.columns:
            st.error(f"Colonna '{col}' mancante nel file Excel.")
            return

    # Pulizia base
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    df_corridoio = df[df["Tag"] == "Corridoio"].copy()
    df_macchina = df[df["Tag"] == "Macchina"].copy()

    if df_corridoio.empty:
        st.warning("Nessun corridoio presente. Impossibile costruire il grafo completo.")
        return

    # Creazione grafo
    G = nx.Graph()

    # Aggiungiamo tutti i nodi (corridoio + macchina)
    for idx, row in df.iterrows():
        G.add_node(
            idx,
            x=row["X"],
            y=row["Y"],
            tag=row["Tag"],
            name=row["Entity Name"],
            size=row.get("Size", None)  # Ora la colonna è 'Size' con la S maiuscola
        )

    # Funzione di distanza euclidea
    def distance(n1, n2):
        x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
        x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
        return math.dist((x1, y1), (x2, y2))

    # --- ESEMPIO: colleghiamo i corridoi con un MST (come prima) ---
    corr_indices = df_corridoio.index.tolist()
    G_corr = nx.Graph()
    G_corr.add_nodes_from(corr_indices)

    for i in range(len(corr_indices)):
        for j in range(i + 1, len(corr_indices)):
            c1 = corr_indices[i]
            c2 = corr_indices[j]
            dist_c = distance(c1, c2)
            G_corr.add_edge(c1, c2, weight=dist_c)

    mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')
    for (c1, c2) in mst_corridoi.edges():
        w = G_corr[c1][c2]["weight"]
        G.add_edge(c1, c2, weight=w)

    # --- Funzione di "filtro corridoi" in base a Size ---
    def filtra_corridoi_per_size(macchina_idx, corridoi_indices):
        """
        Ritorna la lista di corridoi 'filtrati' in base alla colonna 'Size'
        della macchina_idx.
        
        Se 'Size' è vuoto/NaN, ritorna tutti i corridoi (nessun filtro).
        Altrimenti, filtra in base a:
         - Sinistro: X_corr < X_m
         - Destro:   X_corr > X_m
         - Alto:     Y_corr > Y_m
         - Basso:    Y_corr < Y_m
        """
        size_val = G.nodes[macchina_idx]["size"]
        # Coordinate della macchina
        xm, ym = G.nodes[macchina_idx]["x"], G.nodes[macchina_idx]["y"]

        if pd.isna(size_val) or size_val == "" or size_val.strip() == "":
            # 'vuoto' => nessun filtro
            return corridoi_indices

        if size_val == "Sinistro":
            # Corridoi con X < xm
            filtered = [c for c in corridoi_indices if G.nodes[c]["x"] < xm]
            return filtered

        elif size_val == "Destro":
            # Corridoi con X > xm
            filtered = [c for c in corridoi_indices if G.nodes[c]["x"] > xm]
            return filtered

        elif size_val == "Alto":
            # Corridoi con Y > ym
            filtered = [c for c in corridoi_indices if G.nodes[c]["y"] > ym]
            return filtered

        elif size_val == "Basso":
            # Corridoi con Y < ym
            filtered = [c for c in corridoi_indices if G.nodes[c]["y"] < ym]
            return filtered

        else:
            # Se c'è qualche valore fuori standard, non filtriamo
            return corridoi_indices

    # --- Collegamento macchine ai corridoi in base a Size ---
    for idx_m, row_m in df_macchina.iterrows():
        # 1) filtra corridoi in base a Size
        candidati = filtra_corridoi_per_size(idx_m, corr_indices)

        # 2) se nessuno corrisponde al filtro, fallback su tutti i corridoi
        if not candidati:
            candidati = corr_indices

        # 3) trova il più vicino tra i 'candidati'
        nearest_dist = float("inf")
        nearest_corr = None
        for c_idx in candidati:
            d_mc = distance(idx_m, c_idx)
            if d_mc < nearest_dist:
                nearest_dist = d_mc
                nearest_corr = c_idx

        # 4) aggiungiamo l'arco
        if nearest_corr is not None:
            G.add_edge(idx_m, nearest_corr, weight=nearest_dist)

    st.write(f"Grafo creato con {G.number_of_nodes()} nodi e {G.number_of_edges()} archi.")

    # Prosegui con le elaborazioni successive (cammini più brevi, grafici, ecc.)
    st.write("Implementazione completata. Esempio di logica 'Size' applicata.")

if __name__ == "__main__":
    main()



