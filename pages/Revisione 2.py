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
    st.title("Grafo Corridoio-Macchina con colonna 'Size' (percorso diretto basato su direzione)")

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

        # Verifica la presenza delle colonne necessarie
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

        # Creazione grafo principale
        G = nx.Graph()

        # Aggiunge tutti i nodi (corridoio e macchina) con i relativi attributi
        for idx, row in df.iterrows():
            G.add_node(
                idx,
                x=row["X"],
                y=row["Y"],
                tag=row["Tag"],
                name=row["Entity Name"],
                size=row.get("Size", None)  # Valori possibili: "Sinistro", "Destro", "Alto", "Basso", o vuoto
            )

        # Funzione per calcolare la distanza euclidea tra due nodi
        def distance(n1, n2):
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))

        # ====== 1) Collegamento Corridoi (MST) ======
        corr_indices = df_corridoio.index.tolist()
        G_corr = nx.Graph()
        G_corr.add_nodes_from(corr_indices)

        # Aggiunge tutti i possibili archi tra corridoi con il peso dato dalla distanza
        for i in range(len(corr_indices)):
            for j in range(i + 1, len(corr_indices)):
                n1 = corr_indices[i]
                n2 = corr_indices[j]
                d = distance(n1, n2)
                G_corr.add_edge(n1, n2, weight=d)

        # Calcola il Minimum Spanning Tree (MST) dei corridoi
        mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')
        for (c1, c2) in mst_corridoi.edges():
            w = G_corr[c1][c2]["weight"]
            G.add_edge(c1, c2, weight=w)

        # ====== 2) Collegamento Macchine a Corridoi (usando la direzione specificata in Size) ======

        def filtra_corridoi_per_size(machine_idx, corridor_indices):
            """
            Ritorna i corridoi 'validi' in base al valore di 'Size' della macchina.
            Se Size = 'Sinistro', ritorna i corridoi con X < machine.X, ecc.
            Se Size è vuoto/NaN, non si applica il filtro (tutti validi).
            """
            size_val = G.nodes[machine_idx]["size"]
            mx, my = G.nodes[machine_idx]["x"], G.nodes[machine_idx]["y"]

            if pd.isna(size_val) or size_val.strip() == "":
                return corridor_indices

            filtered = []
            for c_idx in corridor_indices:
                cx, cy = G.nodes[c_idx]["x"], G.nodes[c_idx]["y"]

                if size_val == "Sinistro" and cx < mx:
                    filtered.append(c_idx)
                elif size_val == "Destro" and cx > mx:
                    filtered.append(c_idx)
                elif size_val == "Alto" and cy > my:
                    filtered.append(c_idx)
                elif size_val == "Basso" and cy < my:
                    filtered.append(c_idx)
            return filtered

        def choose_corridor(machine_idx, corridor_indices):
            """
            Se per la macchina (machine_idx) è specificata una direzione (Size),
            sceglie il corridoio che massimizza lo scostamento nella direzione desiderata.
            In caso di Size non specificato (o se nessun corridoio soddisfa la condizione),
            sceglie il corridoio con distanza euclidea minima.
            Ritorna una tupla (corridor_idx, distanza).
            """
            size_val = G.nodes[machine_idx]["size"]

            # Se Size non è specificato, usa il criterio della distanza minima
            if pd.isna(size_val) or size_val.strip() == "":
                best_corr = None
                best_dist = float("inf")
                for c in corridor_indices:
                    d = distance(machine_idx, c)
                    if d < best_dist:
                        best_dist = d
                        best_corr = c
                return best_corr, best_dist

            # Applica il filtro direzionale
            candidates = filtra_corridoi_per_size(machine_idx, corridor_indices)
            # Se non ci sono candidati, si usa il fallback: tutti i corridoi
            if not candidates:
                candidates = corridor_indices

            # Se la direzione è specificata, scegli in base allo scostamento
            if size_val == "Sinistro":
                best_corr = None
                best_value = -float("inf")
                for c in candidates:
                    diff = G.nodes[machine_idx]["x"] - G.nodes[c]["x"]  # Positivo se c è a sinistra
                    if diff > best_value:
                        best_value = diff
                        best_corr = c
            elif size_val == "Destro":
                best_corr = None
                best_value = -float("inf")
                for c in candidates:
                    diff = G.nodes[c]["x"] - G.nodes[machine_idx]["x"]  # Positivo se c è a destra
                    if diff > best_value:
                        best_value = diff
                        best_corr = c
            elif size_val == "Alto":
                best_corr = None
                best_value = -float("inf")
                for c in candidates:
                    diff = G.nodes[c]["y"] - G.nodes[machine_idx]["y"]  # Positivo se c è sopra
                    if diff > best_value:
                        best_value = diff
                        best_corr = c
            elif size_val == "Basso":
                best_corr = None
                best_value = -float("inf")
                for c in candidates:
                    diff = G.nodes[machine_idx]["y"] - G.nodes[c]["y"]  # Positivo se c è sotto
                    if diff > best_value:
                        best_value = diff
                        best_corr = c
            else:
                # In caso di valore inatteso, si usa il criterio distanza minima
                best_corr = None
                best_dist = float("inf")
                for c in candidates:
                    d = distance(machine_idx, c)
                    if d < best_dist:
                        best_dist = d
                        best_corr = c
                return best_corr, best_dist

            # Calcola la distanza per completezza (utile anche per il weight dell'arco)
            best_dist = distance(machine_idx, best_corr)
            return best_corr, best_dist

        # Per ogni macchina, collega al corridoio scelto usando la funzione sopra
        for idx_m in df_macchina.index:
            best_corr, best_dist = choose_corridor(idx_m, corr_indices)
            if best_corr is not None:
                G.add_edge(idx_m, best_corr, weight=best_dist)

        st.write(f"**Nodi nel grafo**: {G.number_of_nodes()}")
        st.write(f"**Archi nel grafo**: {G.number_of_edges()}")

        # ============= 3) Calcolo distanze tra coppie di macchine =============
        st.subheader("Distanze tra coppie di macchine (con percorso completo)")

        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) < 2:
            st.info("Meno di due macchine, nessuna coppia da calcolare.")
            return

        # Creiamo un sottografo G_paths che conterrà solo gli archi utilizzati dai percorsi
        G_paths = nx.Graph()
        G_paths.add_nodes_from(G.nodes(data=True))
        edge_usage_count = defaultdict(int)

        results = []
        pairs = itertools.combinations(machine_indices, 2)

        for m1, m2 in pairs:
            name1 = G.nodes[m1]["name"]
            name2 = G.nodes[m2]["name"]

            # Calcola il cammino più breve (lista di nodi)
            path_nodes = nx.shortest_path(G, m1, m2, weight='weight')

            # Calcola le distanze dei segmenti e incrementa il contatore per ogni arco usato
            segment_distances = []
            for i in range(len(path_nodes) - 1):
                nA = path_nodes[i]
                nB = path_nodes[i+1]
                d_seg = G[nA][nB]['weight']
                segment_distances.append(d_seg)

                edge_key = tuple(sorted([nA, nB]))
                edge_usage_count[edge_key] += 1

            total_dist = sum(segment_distances)

            # Crea le stringhe di percorso e delle distanze
            path_list = [G.nodes[nd]["name"] for nd in path_nodes]
            path_str = " -> ".join(path_list)
            sum_str = " + ".join(f"{d_val:.2f}" for d_val in segment_distances) + f" = {total_dist:.2f}"

            results.append({
                "Coppia Macchine": f"{name1} - {name2}",
                "Percorso (macchine + corridoi)": path_str,
                "Somma distanze (stringa)": sum_str,
                "Valore complessivo": total_dist
            })

        # Aggiunge gli archi usati con il conteggio delle occorrenze al sottografo G_paths
        for (n1, n2), usage_count in edge_usage_count.items():
            d_val = G[n1][n2]['weight']
            G_paths.add_edge(n1, n2, weight=d_val, count=usage_count)

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
            # Se è stata caricata un'immagine di sfondo, la usiamo come base
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

                # Disegna gli archi del sottografo G_paths
                for (n1, n2) in G_paths.edges():
                    x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                    x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                    ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)

                    usage_count = G_paths[n1][n2]['count']
                    xm = (x1 + x2) / 2
                    ym = (y1 + y2) / 2
                    ax2.text(xm, ym, str(usage_count),
                             color="blue", fontsize=10,
                             ha="center", va="center",
                             bbox=dict(boxstyle="round,pad=0.3",
                                       fc="white", ec="blue", alpha=0.6))

                # Disegna i nodi
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
            # Senza immagine di sfondo
            fig2, ax2 = plt.subplots(figsize=(10, 8))

            for (n1, n2) in G_paths.edges():
                x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)

                usage_count = G_paths[n1][n2]['count']
                xm = (x1 + x2) / 2
                ym = (y1 + y2) / 2
                ax2.text(xm, ym, str(usage_count),
                         color="blue", fontsize=10,
                         ha="center", va="center",
                         bbox=dict(boxstyle="round,pad=0.3",
                                   fc="white", ec="blue", alpha=0.6))

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


