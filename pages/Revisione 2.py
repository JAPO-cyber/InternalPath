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
    st.title("Grafo Corridoio-Macchina con colonna 'Size' (scelta del corridoio basata sulla direzione)")

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

        # Aggiunge tutti i nodi (corridoi e macchine) con i relativi attributi
        for idx, row in df.iterrows():
            G.add_node(
                idx,
                x=row["X"],
                y=row["Y"],
                tag=row["Tag"],
                name=row["Entity Name"],
                size=row.get("Size", None)  # Possibili valori: "Sinistro", "Destro", "Alto", "Basso" o vuoto
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

        # ====== 2) Collegamento Macchine a Corridoi ======
        def choose_corridor(machine_idx, corridor_indices):
            """
            Per una macchina data, sceglie il corridoio in base alla direzione indicata nel campo "Size".
            
            Il procedimento è il seguente:
            1. Si individua il corridoio candidato più vicino (ignorando il campo Size).
            2. In base a "Size":
               - Se "Alto": si considerano solo i corridoi con Y maggiore di quella del candidato.
               - Se "Basso": si considerano solo i corridoi con Y minore di quella del candidato.
               - Se "Sinistro": si considerano solo i corridoi con X minore di quella del candidato.
               - Se "Destro": si considerano solo i corridoi con X maggiore di quella del candidato.
            3. Tra i corridoi validi (se esistono) si sceglie quello più vicino (in distanza euclidea) alla macchina.
            4. Se nessun corridoio soddisfa la condizione, si usa il candidato iniziale.
            
            Se il campo "Size" non è specificato o è vuoto, si usa il candidato basato sulla distanza minima.
            """
            # Primo candidato: corridoio più vicino (senza considerare Size)
            candidate = min(corridor_indices, key=lambda c: distance(machine_idx, c))
            
            size_val = G.nodes[machine_idx]["size"]
            # Se Size non è specificato o vuoto, ritorna il candidato
            if pd.isna(size_val) or size_val.strip() == "":
                return candidate, distance(machine_idx, candidate)
            
            # Imposta il filtro in base al candidato
            cand_x = G.nodes[candidate]["x"]
            cand_y = G.nodes[candidate]["y"]
            
            if size_val == "Alto":
                # Considera solo corridoi con Y maggiore di quella del candidato
                valid = [c for c in corridor_indices if G.nodes[c]["y"] > cand_y]
            elif size_val == "Basso":
                # Considera solo corridoi con Y minore di quella del candidato
                valid = [c for c in corridor_indices if G.nodes[c]["y"] < cand_y]
            elif size_val == "Sinistro":
                # Considera solo corridoi con X minore di quella del candidato
                valid = [c for c in corridor_indices if G.nodes[c]["x"] < cand_x]
            elif size_val == "Destro":
                # Considera solo corridoi con X maggiore di quella del candidato
                valid = [c for c in corridor_indices if G.nodes[c]["x"] > cand_x]
            else:
                valid = corridor_indices
            
            # Se esistono corridoi che soddisfano la condizione, ne sceglie il più vicino
            if valid:
                best_corr = min(valid, key=lambda c: distance(machine_idx, c))
            else:
                best_corr = candidate
            
            return best_corr, distance(machine_idx, best_corr)

        # Per ogni macchina, collega al corridoio scelto utilizzando la funzione choose_corridor
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

        # Creiamo un sottografo G_paths che conterrà solo gli archi usati dai percorsi
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



