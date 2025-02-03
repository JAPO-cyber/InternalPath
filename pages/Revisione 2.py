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
    st.title("Distanze tra coppie di macchine, visualizzazione percorsi e conteggio utilizzi archi")

    # 1. Caricamento file Excel
    excel_file = st.file_uploader(
        label="Carica un file Excel (X, Y, Tag, Entity Name)",
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
        needed_cols = ["X", "Y", "Tag", "Entity Name"]
        for c in needed_cols:
            if c not in df.columns:
                st.error(f"Colonna '{c}' mancante nel file Excel.")
                return

        # Pulizia rapida: se trovi ' m' in X/Y, rimuovi e converti in numerico
        df["X"] = df["X"].apply(lambda v: None if isinstance(v, str) and ' m' in v else v)
        df["Y"] = df["Y"].apply(lambda v: None if isinstance(v, str) and ' m' in v else v)
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Suddividi corridoi e macchine
        df_corridoio = df[df["Tag"] == "Corridoio"].copy()
        df_macchina = df[df["Tag"] == "Macchina"].copy()

        if df_corridoio.empty:
            st.warning("Non ci sono corridoi; impossibile costruire il grafo completo.")
            return
        if df_macchina.empty:
            st.warning("Non ci sono macchine; non ci sono coppie da calcolare.")

        # =============== COSTRUZIONE GRAFO COMPLETO ===============
        G = nx.Graph()

        # Aggiungi tutti i punti come nodi
        for idx, row in df.iterrows():
            G.add_node(idx,
                       x=row["X"],
                       y=row["Y"],
                       tag=row["Tag"],
                       name=row["Entity Name"])

        def distance(n1, n2):
            """Distanza euclidea tra nodi n1, n2 del grafo."""
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))

        # 1) Collegamento Corridoi (MST)
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

        # 2) Collegamento Macchine -> Corridoio più vicino
        for idx_m, row_m in df_macchina.iterrows():
            nearest_c = None
            nearest_d = float('inf')
            for idx_c in corr_indices:
                d_mc = distance(idx_m, idx_c)
                if d_mc < nearest_d:
                    nearest_d = d_mc
                    nearest_c = idx_c
            if nearest_c is not None:
                G.add_edge(idx_m, nearest_c, weight=nearest_d)

        st.write(f"**Nodi nel grafo**: {G.number_of_nodes()}")
        st.write(f"**Archi nel grafo**: {G.number_of_edges()}")

        # =============== CALCOLO DISTANZE COPPIE ===============
        st.subheader("Distanze tra coppie di macchine (con percorso completo)")

        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) < 2:
            st.info("Meno di due macchine, nessuna coppia da calcolare.")
            return

        # Creiamo un sottografo con tutti i nodi (per mantenere attributi x, y, name, tag)
        # In cui aggiungeremo solo gli archi usati nei percorsi
        G_paths = nx.Graph()
        G_paths.add_nodes_from(G.nodes(data=True))

        # Dizionario per contare l'utilizzo di ogni arco (edge) nei percorsi
        edge_usage_count = defaultdict(int)

        results = []
        pairs = itertools.combinations(machine_indices, 2)

        for (m1, m2) in pairs:
            name1 = G.nodes[m1]["name"]
            name2 = G.nodes[m2]["name"]

            # 1) Troviamo il path effettivo (lista di nodi)
            path_nodes = nx.shortest_path(G, m1, m2, weight='weight')

            # 2) Calcola le distanze "segmento per segmento"
            segment_distances = []
            for i in range(len(path_nodes) - 1):
                nA = path_nodes[i]
                nB = path_nodes[i + 1]
                dist_seg = G[nA][nB]['weight']
                segment_distances.append(dist_seg)

                # A) Creiamo una rappresentazione ordinata dell'arco
                #    (così (nA,nB) e (nB,nA) vengono contati come lo stesso arco)
                edge_key = tuple(sorted([nA, nB]))
                edge_usage_count[edge_key] += 1

            # 3) Somma totale
            total_dist = sum(segment_distances)

            # 4) Stringa del percorso
            path_list = [G.nodes[nd]["name"] for nd in path_nodes]
            path_str = " -> ".join(path_list)

            # 5) Stringa delle distanze
            sum_str = " + ".join(f"{dist_val:.2f}" for dist_val in segment_distances)
            sum_str += f" = {total_dist:.2f}"

            results.append({
                "Coppia Macchine": f"{name1} - {name2}",
                "Percorso (macchine + corridoi)": path_str,
                "Somma distanze (stringa)": sum_str,
                "Valore complessivo": total_dist
            })

        # Ora, aggiungiamo effettivamente gli archi al G_paths, assegnandogli l'attributo 'count'
        for (n1, n2), usage_count in edge_usage_count.items():
            dist_val = G[n1][n2]['weight']
            G_paths.add_edge(n1, n2, weight=dist_val, count=usage_count)

        # -- Creiamo il DataFrame dei risultati e lo ordiniamo
        df_results = pd.DataFrame(results).sort_values(by="Valore complessivo", ascending=True)

        st.write("Tabella dei risultati:")
        st.dataframe(df_results)

        # ========== Bottone per scaricare l'Excel ==========
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

        # =============== VISUALIZZAZIONE SOLO DEI PERCORSI TROVATI ===============
        st.subheader("Visualizzazione SOLO dei percorsi (con count utilizzo archi)")

        # Se abbiamo un'immagine di sfondo
        if bg_image_file is not None:
            bg_image = Image.open(bg_image_file)
            x_min, x_max = df["X"].min(), df["X"].max()
            y_min, y_max = df["Y"].min(), df["Y"].max()

            if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
                st.warning("Coordinate X e/o Y non valide, impossibile mostrare l'immagine di sfondo.")
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

                    # Mostriamo il numero di utilizzi (count) a metà dell'arco
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
                    tag = G_paths.nodes[nd]["tag"]
                    x_val = G_paths.nodes[nd]["x"]
                    y_val = G_paths.nodes[nd]["y"]
                    if pd.notna(x_val) and pd.notna(y_val):
                        if tag == "Corridoio":
                            coords_corridoio.append((x_val, y_val))
                        elif tag == "Macchina":
                            coords_macchina.append((x_val, y_val))

                # Scatter corridoi (verde)
                if coords_corridoio:
                    x_c, y_c = zip(*coords_corridoio)
                    ax2.scatter(x_c, y_c, c='green', marker='o', label='Corridoio')
                # Scatter macchine (rosso)
                if coords_macchina:
                    x_m, y_m = zip(*coords_macchina)
                    ax2.scatter(x_m, y_m, c='red', marker='s', label='Macchina')

                ax2.set_title("Sottografo dei percorsi (Macchina - Macchina) con count utilizzo archi")
                ax2.legend()
                st.pyplot(fig2)
        else:
            # Se non c'è immagine di sfondo, visualizziamo comunque il sottografo G_paths
            fig2, ax2 = plt.subplots(figsize=(10, 8))

            # Disegno SOLO gli archi di G_paths
            for (n1, n2) in G_paths.edges():
                x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)

                # Numero di utilizzi
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
                tag = G_paths.nodes[nd]["tag"]
                x_val = G_paths.nodes[nd]["x"]
                y_val = G_paths.nodes[nd]["y"]
                if pd.notna(x_val) and pd.notna(y_val):
                    if tag == "Corridoio":
                        coords_corridoio.append((x_val, y_val))
                    elif tag == "Macchina":
                        coords_macchina.append((x_val, y_val))

            # Scatter corridoi (verde)
            if coords_corridoio:
                x_c, y_c = zip(*coords_corridoio)
                ax2.scatter(x_c, y_c, c='green', marker='o', label='Corridoio')
            # Scatter macchine (rosso)
            if coords_macchina:
                x_m, y_m = zip(*coords_macchina)
                ax2.scatter(x_m, y_m, c='red', marker='s', label='Macchina')

            ax2.set_title("Sottografo dei percorsi (Macchina - Macchina) con count utilizzo archi")
            ax2.legend()
            st.pyplot(fig2)

    else:
        st.write("Carica un file Excel per iniziare.")

if __name__ == "__main__":
    main()


