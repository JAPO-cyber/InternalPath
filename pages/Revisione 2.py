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
    st.title("Grafo Corridoio-Macchina con colonna 'Size' (confronto su X,Y del corridoio)")

    # 1. Caricamento file Excel
    excel_file = st.file_uploader(
        label="Carica un file Excel (X, Y, Tag, Entity Name, Size)",
        type=["xls", "xlsx"]
    )

    # 2. (Opzionale) Caricamento immagine di sfondo
    bg_image_file = st.file_uploader(
        label="Carica un'immagine di sfondo (jpg, jpeg, png) [Opzionale]",
        type=["jpg", "jpeg", "png"]
    )

    if excel_file is not None:
        # Legge il DataFrame
        df = pd.read_excel(excel_file)

        # Visualizza anteprima
        st.subheader("Anteprima del DataFrame caricato")
        st.dataframe(df.head())

        # Assicuriamoci di avere le colonne necessarie
        needed_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
        for c in needed_cols:
            if c not in df.columns:
                st.error(f"Colonna '{c}' mancante nel file Excel.")
                return

        # Convertiamo X, Y in numerico
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Suddividi in corridoi e macchine
        df_corridoio = df[df["Tag"] == "Corridoio"].copy()
        df_macchina = df[df["Tag"] == "Macchina"].copy()

        if df_corridoio.empty:
            st.warning("Non ci sono corridoi: impossibile costruire il grafo completo.")
            return
        if df_macchina.empty:
            st.warning("Non ci sono macchine: non ci sono coppie da calcolare.")

        # Creazione grafo
        G = nx.Graph()

        # Aggiunge tutti i nodi (corridoio + macchina), conservando attributi
        for idx, row in df.iterrows():
            G.add_node(
                idx,
                x=row["X"],
                y=row["Y"],
                tag=row["Tag"],
                name=row["Entity Name"],
                size=row.get("Size", None)  # valore come "Sinistro", "Destro", "Alto", "Basso", o vuoto
            )

        # Funzione di distanza euclidea
        def distance(n1, n2):
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))

        # ====== 1) Collegamento Corridoi (MST) ======
        corr_indices = df_corridoio.index.tolist()
        G_corr = nx.Graph()
        G_corr.add_nodes_from(corr_indices)

        for i in range(len(corr_indices)):
            for j in range(i + 1, len(corr_indices)):
                n1 = corr_indices[i]
                n2 = corr_indices[j]
                dist_c = distance(n1, n2)
                G_corr.add_edge(n1, n2, weight=dist_c)

        mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')
        for (c1, c2) in mst_corridoi.edges():
            w = G_corr[c1][c2]["weight"]
            G.add_edge(c1, c2, weight=w)

        # ====== 2) Collegamento Macchine in base a 'Size', ma confrontando X,Y del corridoio ======

        def filtra_corridoi_per_size(machine_idx, corridor_indices):
            """
            Ritorna i corridoi 'validi' in base al valore di 'Size' della macchina.
            In particolare, se Size = 'Sinistro', cerchiamo i corridoi con cx < mx, ecc.
            Se la colonna 'Size' è vuota/NaN, non applichiamo filtro (tutti validi).
            """

            size_val = G.nodes[machine_idx]["size"]
            # Coordinate della macchina
            mx, my = G.nodes[machine_idx]["x"], G.nodes[machine_idx]["y"]

            # Se 'Size' è vuoto/NaN/blank => nessun filtro
            if pd.isna(size_val) or size_val.strip() == "":
                return corridor_indices

            filtered = []
            for c_idx in corridor_indices:
                cx, cy = G.nodes[c_idx]["x"], G.nodes[c_idx]["y"]

                if size_val == "Sinistro":
                    # corridor X < machine X
                    if cx < mx:
                        filtered.append(c_idx)

                elif size_val == "Destro":
                    # corridor X > machine X
                    if cx > mx:
                        filtered.append(c_idx)

                elif size_val == "Alto":
                    # corridor Y > machine Y
                    if cy > my:
                        filtered.append(c_idx)

                elif size_val == "Basso":
                    # corridor Y < machine Y
                    if cy < my:
                        filtered.append(c_idx)

                else:
                    # se Size ha un valore non previsto, non filtriamo
                    return corridor_indices

            return filtered

        # Per ogni macchina, colleghiamo al corridoio "scelto" in base alle regole
        for idx_m in df_macchina.index:
            candidati = filtra_corridoi_per_size(idx_m, corr_indices)

            # Se il filtro è vuoto (nessun corridoio soddisfa la condizione),
            # fallback: consideriamo TUTTI i corridoi
            if not candidati:
                candidati = corr_indices

            # Tra i candidati, prendi il più vicino
            nearest_dist = float("inf")
            nearest_corr = None
            for c_idx in candidati:
                d_mc = distance(idx_m, c_idx)
                if d_mc < nearest_dist:
                    nearest_dist = d_mc
                    nearest_corr = c_idx

            if nearest_corr is not None:
                # Collegamento macchina - corridoio
                G.add_edge(idx_m, nearest_corr, weight=nearest_dist)

        # Info grafo
        st.write(f"**Nodi nel grafo**: {G.number_of_nodes()}")
        st.write(f"**Archi nel grafo**: {G.number_of_edges()}")

        # ============= 3) Calcolo distanze coppie di macchine =============
        st.subheader("Distanze tra coppie di macchine (con percorso completo)")

        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) < 2:
            st.info("Meno di due macchine, nessuna coppia da calcolare.")
            return

        # Creiamo un sottografo G_paths che conterrà solo gli archi usati
        G_paths = nx.Graph()
        G_paths.add_nodes_from(G.nodes(data=True))  # Copia i nodi con attributi
        edge_usage_count = defaultdict(int)

        results = []
        pairs = itertools.combinations(machine_indices, 2)

        for (m1, m2) in pairs:
            name1 = G.nodes[m1]["name"]
            name2 = G.nodes[m2]["name"]

            # Cammino più breve (lista di nodi)
            path_nodes = nx.shortest_path(G, m1, m2, weight='weight')

            # Distanze sui segmenti
            segment_distances = []
            for i in range(len(path_nodes) - 1):
                nA = path_nodes[i]
                nB = path_nodes[i+1]
                dist_seg = G[nA][nB]['weight']
                segment_distances.append(dist_seg)

                # Aggiungiamo l'arco al sottografo, incrementando il contatore
                edge_key = tuple(sorted([nA, nB]))
                edge_usage_count[edge_key] += 1

            total_dist = sum(segment_distances)

            # Stringa del percorso
            path_list = [G.nodes[nd]["name"] for nd in path_nodes]
            path_str = " -> ".join(path_list)

            # Stringa delle distanze, es. "3.45 + 2.10 = 5.55"
            sum_str = " + ".join(f"{dist_val:.2f}" for dist_val in segment_distances)
            sum_str += f" = {total_dist:.2f}"

            results.append({
                "Coppia Macchine": f"{name1} - {name2}",
                "Percorso (macchine + corridoi)": path_str,
                "Somma distanze (stringa)": sum_str,
                "Valore complessivo": total_dist
            })

        # Ora aggiungiamo effettivamente gli archi usati in G_paths con attributi weight e count
        for (n1, n2), usage_count in edge_usage_count.items():
            dist_val = G[n1][n2]['weight']
            G_paths.add_edge(n1, n2, weight=dist_val, count=usage_count)

        # Tabella risultati
        df_results = pd.DataFrame(results).sort_values(by="Valore complessivo", ascending=True)
        st.write("Tabella dei risultati:")
        st.dataframe(df_results)

        # ========== Download Excel ==========
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_results.to_excel(writer, index=False, sheet_name="Distanze_coppie")
        excel_data = output.getvalue()

        st.download_button(
            label="Scarica risultati in Excel",
            data=excel_data,
            file_name="distanze_coppie_macchine.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # =============== 4) Visualizzazione del sottografo G_paths ===============
        st.subheader("Visualizzazione dei percorsi effettivamente usati (con count su ciascun arco)")

        if bg_image_file is not None:
            # Se abbiamo un'immagine di sfondo, la usiamo come base
            bg_image = Image.open(bg_image_file)
            x_min, x_max = df["X"].min(), df["X"].max()
            y_min, y_max = df["Y"].min(), df["Y"].max()

            if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
                st.warning("Coordinate X/Y non valide, impossibile mostrare l'immagine di sfondo.")
            else:
                fig2, ax2 = plt.subplots(figsize=(10, 8))
                ax2.imshow(
                    bg_image,
                    extent=[x_min, x_max, y_min, y_max],
                    aspect='auto',
                    origin='upper'
                )

                # Disegno SOLO gli archi del sottografo G_paths
                for (n1, n2) in G_paths.edges():
                    x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                    x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                    ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)

                    # Etichetta con il numero di utilizzi (count)
                    usage_count = G_paths[n1][n2]['count']
                    xm = (x1 + x2) / 2
                    ym = (y1 + y2) / 2
                    ax2.text(xm, ym, str(usage_count),
                             color="blue", fontsize=10,
                             ha="center", va="center",
                             bbox=dict(boxstyle="round,pad=0.3",
                                       fc="white", ec="blue", alpha=0.6))

                # Disegno i nodi
                coords_corridoio = []
                coords_macchina = []
                for nd in G_paths.nodes():
                    tag_nd = G_paths.nodes[nd]["tag"]
                    x_val = G_paths.nodes[nd]["x"]
                    y_val = G_paths.nodes[nd]["y"]
                    if pd.notna(x_val) and pd.notna(y_val):
                        if tag_nd == "Corridoio":
                            coords_corridoio.append((x_val, y_val))
                        elif tag_nd == "Macchina":
                            coords_macchina.append((x_val, y_val))

                if coords_corridoio:
                    x_c, y_c = zip(*coords_corridoio)
                    ax2.scatter(x_c, y_c, c='green', marker='o', label='Corridoio')
                if coords_macchina:
                    x_m, y_m = zip(*coords_macchina)
                    ax2.scatter(x_m, y_m, c='red', marker='s', label='Macchina')

                ax2.set_title("Sottografo dei percorsi Macchina-Macchina (count archi)")
                ax2.legend()
                st.pyplot(fig2)

        else:
            # Nessuna immagine di sfondo
            fig2, ax2 = plt.subplots(figsize=(10, 8))

            # Disegno archi del sottografo
            for (n1, n2) in G_paths.edges():
                x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)

                # Conteggio utilizzo
                usage_count = G_paths[n1][n2]['count']
                xm = (x1 + x2) / 2
                ym = (y1 + y2) / 2
                ax2.text(xm, ym, str(usage_count),
                         color="blue", fontsize=10,
                         ha="center", va="center",
                         bbox=dict(boxstyle="round,pad=0.3",
                                   fc="white", ec="blue", alpha=0.6))

            # Disegno nodi
            coords_corridoio = []
            coords_macchina = []
            for nd in G_paths.nodes():
                tag_nd = G_paths.nodes[nd]["tag"]
                x_val = G_paths.nodes[nd]["x"]
                y_val = G_paths.nodes[nd]["y"]
                if pd.notna(x_val) and pd.notna(y_val):
                    if tag_nd == "Corridoio":
                        coords_corridoio.append((x_val, y_val))
                    elif tag_nd == "Macchina":
                        coords_macchina.append((x_val, y_val))

            if coords_corridoio:
                x_c, y_c = zip(*coords_corridoio)
                ax2.scatter(x_c, y_c, c='green', marker='o', label='Corridoio')
            if coords_macchina:
                x_m, y_m = zip(*coords_macchina)
                ax2.scatter(x_m, y_m, c='red', marker='s', label='Macchina')

            ax2.set_title("Sottografo dei percorsi Macchina-Macchina (count archi)")
            ax2.legend()
            st.pyplot(fig2)

    else:
        st.write("Carica un file Excel per iniziare.")

if __name__ == "__main__":
    main()



