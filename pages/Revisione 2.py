import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import io
from PIL import Image
import matplotlib.pyplot as plt

def main():
    st.title("Distanze tra coppie di macchine: percorso completo con start, corridoi e end")

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

        # Pulizia rapida: se trovi ' m' in X/Y, rimuovi e converti
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

        # =============== COSTRUZIONE GRAFO ===============
        G = nx.Graph()

        # Aggiunge tutti i punti come nodi
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

        # =============== VISUALIZZAZIONE OPZIONALE ===============
        if bg_image_file is not None:
            bg_image = Image.open(bg_image_file)
            x_min, x_max = df["X"].min(), df["X"].max()
            y_min, y_max = df["Y"].min(), df["Y"].max()

            if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
                st.warning("Coordinate X e/o Y non valide, impossibile mostrare l'immagine di sfondo.")
            else:
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.imshow(
                    bg_image,
                    extent=[x_min, x_max, y_min, y_max],
                    aspect='auto',
                    origin='upper'
                )
                # Disegno archi (blu)
                for (n1, n2) in G.edges():
                    x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
                    x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
                    ax.plot([x1, x2], [y1, y2], color='blue', linewidth=1, alpha=0.5)

                # Disegno punti: Corridoio in verde, Macchina in rosso
                ax.scatter(df_corridoio["X"], df_corridoio["Y"], c='green', marker='o', label='Corridoio')
                ax.scatter(df_macchina["X"], df_macchina["Y"], c='red', marker='s', label='Macchina')
                ax.set_title("Visualizzazione del grafo (con sfondo)")
                ax.legend()
                st.pyplot(fig)

        # =============== CALCOLO DISTANZE COPPIE (SENZA ORDINE) ===============
        st.subheader("Distanze tra coppie di macchine (con percorso completo nel dettaglio)")

        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) < 2:
            st.info("Meno di due macchine, nessuna coppia da calcolare.")
            return

        pairs = itertools.combinations(machine_indices, 2)
        results = []

        for (m1, m2) in pairs:
            name1 = G.nodes[m1]["name"]
            name2 = G.nodes[m2]["name"]

            # Troviamo il path effettivo (lista di nodi)
            path_nodes = nx.shortest_path(G, m1, m2, weight='weight')

            # Calcola le distanze "segmento per segmento"
            segment_distances = []
            for i in range(len(path_nodes) - 1):
                nA = path_nodes[i]
                nB = path_nodes[i+1]
                dist_seg = G[nA][nB]['weight']
                segment_distances.append(dist_seg)

            # Somma totale
            total_dist = sum(segment_distances)

            # Costruiamo una stringa con TUTTI i nodi (macchina iniziale, eventuali corridoi, macchina finale)
            path_list = [G.nodes[nd]["name"] for nd in path_nodes]
            # Esempio: "MacchinaA -> Corr1 -> Corr2 -> MacchinaB"
            path_str = " -> ".join(path_list)

            # Creiamo la stringa dei segmenti con '+' in mezzo
            # Esempio: "3.45 + 2.10 + 5.00 = 10.55"
            sum_str = " + ".join(f"{dist_val:.2f}" for dist_val in segment_distances)
            sum_str += f" = {total_dist:.2f}"

            results.append({
                "Coppia Macchine": f"{name1} - {name2}",
                # Seconda colonna: percorso completo (inizio, corridoi, fine)
                "Percorso (macchine + corridoi)": path_str,
                # Terza colonna: somma delle distanze con stringa
                "Somma distanze (stringa)": sum_str,
                # Quarta colonna: valore numerico totale
                "Valore complessivo": total_dist
            })

        # Convertiamo in DataFrame e mostriamo
        df_results = pd.DataFrame(results)
        # Ordiniamo per "Valore complessivo"
        df_results = df_results.sort_values(by="Valore complessivo", ascending=True)

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
    else:
        st.write("Carica un file Excel per iniziare.")

if __name__ == "__main__":
    main()


