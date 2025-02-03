import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from PIL import Image
import math
import itertools
import io

def main():
    st.title("Grafo Corridoio-Macchina: combinazioni macchine e percorsi più brevi")

    # 1. Caricamento file Excel
    excel_file = st.file_uploader(
        label="Scegli un file Excel",
        type=["xls", "xlsx"]
    )

    # 2. Caricamento dell'immagine di sfondo
    bg_image_file = st.file_uploader(
        label="Scegli un'immagine (jpg, jpeg, png)",
        type=["jpg", "jpeg", "png"]
    )

    if excel_file is not None and bg_image_file is not None:
        # Legge il file Excel
        df = pd.read_excel(
            excel_file,
            # decimal=',',    # se i decimali nel tuo file Excel usano la virgola
            # thousands='.'   # se usi il punto per le migliaia
        )

        # Mostra tipologie delle colonne e anteprima
        st.subheader("Tipi di dati delle colonne (prima delle modifiche):")
        st.write(df.dtypes)
        st.subheader("Anteprima dei dati (prima delle modifiche):")
        st.dataframe(df.head())

        # Assicuriamoci che esistano le colonne X, Y, Tag e Entity Name
        required_cols = ["X", "Y", "Tag", "Entity Name"]
        for col in required_cols:
            if col not in df.columns:
                st.error(f"Errore: il file Excel deve contenere la colonna '{col}'.")
                return

        # Esempio di pulizia: sostituiamo ' m' con None in X/Y
        df["X"] = df["X"].apply(lambda v: None if isinstance(v, str) and ' m' in v else v)
        df["Y"] = df["Y"].apply(lambda v: None if isinstance(v, str) and ' m' in v else v)

        # Converte X e Y in valori numerici
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Mostra i dati dopo la sostituzione e la conversione
        st.subheader("Tipi di dati delle colonne (dopo le modifiche):")
        st.write(df.dtypes)
        st.subheader("Anteprima dei dati (dopo le modifiche):")
        st.dataframe(df.head())

        # Suddividiamo tra corridoio e macchina
        df_corridoio = df[df["Tag"] == "Corridoio"].copy()
        df_macchina = df[df["Tag"] == "Macchina"].copy()

        if df_corridoio.empty:
            st.warning("Nessun punto Corridoio trovato. Impossibile costruire il grafo dei corridoi.")
            return

        # ---- COSTRUZIONE GRAFO ----
        G = nx.Graph()

        # Aggiunge tutti i nodi al grafo (sia corridoio che macchina)
        # Usando l'indice del DataFrame come 'id' del nodo
        for idx, row in df.iterrows():
            x_val = row["X"]
            y_val = row["Y"]
            tag_val = row["Tag"]
            name_val = row["Entity Name"]
            G.add_node(idx, x=x_val, y=y_val, tag=tag_val, name=name_val)

        def distance(n1, n2):
            """Distanza euclidea fra due nodi nel grafo."""
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))

        # --- Colleghiamo i Corridoi con un MST ---
        G_corr = nx.Graph()
        corridoio_indices = df_corridoio.index.tolist()
        for idx_c in corridoio_indices:
            G_corr.add_node(idx_c)

        # Crea archi completi tra i corridoi, con peso = distanza
        for i in range(len(corridoio_indices)):
            for j in range(i + 1, len(corridoio_indices)):
                n1 = corridoio_indices[i]
                n2 = corridoio_indices[j]
                dist = distance(n1, n2)
                G_corr.add_edge(n1, n2, weight=dist)

        # Calcola MST del sottografo dei corridoi
        mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')

        # Aggiunge gli archi del MST al grafo principale G
        for (n1, n2) in mst_corridoi.edges():
            w = G_corr[n1][n2]["weight"]
            G.add_edge(n1, n2, weight=w)

        # --- Colleghiamo ogni Macchina al Corridoio più vicino ---
        for idx_m, row_m in df_macchina.iterrows():
            nearest_corr = None
            nearest_dist = float("inf")
            for idx_c in corridoio_indices:
                dist_mc = distance(idx_m, idx_c)
                if dist_mc < nearest_dist:
                    nearest_dist = dist_mc
                    nearest_corr = idx_c
            if nearest_corr is not None:
                G.add_edge(idx_m, nearest_corr, weight=nearest_dist)

        # ---- INFO GRAFO ----
        st.subheader("Grafo creato:")
        st.write(f"Nodi totali: {G.number_of_nodes()}")
        st.write(f"Archi totali: {G.number_of_edges()}")

        # ---- VISUALIZZAZIONE BASE ----
        # (Facoltativa, come da esempio precedente: disegno sfondo e punti)
        bg_image = Image.open(bg_image_file)
        fig, ax = plt.subplots(figsize=(10, 8))

        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
            st.warning("Non è stato possibile determinare i limiti (X, Y). Verifica che i dati siano numerici.")
            return

        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto',
            origin='upper'
        )

        # Disegniamo gli archi (in blu)
        for (n1, n2) in G.edges():
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            ax.plot([x1, x2], [y1, y2], color='blue', linewidth=1, alpha=0.5)

        # Disegna i punti Corridoio (verde)
        ax.scatter(df_corridoio["X"], df_corridoio["Y"], c='green', marker='o', label='Corridoio')
        # Disegna i punti Macchina (rosso)
        ax.scatter(df_macchina["X"], df_macchina["Y"], c='red', marker='s', label='Macchina')

        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafo Corridoio-Macchina (Visualizzazione Base)")
        ax.legend()

        st.pyplot(fig)

        # =============== NUOVA PARTE: TUTTE LE COMBINAZIONI MACCHINE ===============
        st.subheader("Calcolo di tutte le permutazioni (ordini) delle macchine")

        # Indici (o ID) delle macchine nel DataFrame
        machine_indices = df_macchina.index.tolist()

        if len(machine_indices) == 0:
            st.warning("Non ci sono macchine; impossibile creare percorsi.")
            return

        # Generiamo tutte le permutazioni (ordini) delle macchine
        perms = itertools.permutations(machine_indices, len(machine_indices))

        results = []
        for perm in perms:
            # perm è una tupla di indici (es. (2, 5, 10) ) corrispondenti a Macchine
            route_names = []
            route_distances = []  # distanza tra macchine consecutive
            total_dist = 0.0

            # Calcoliamo i "leg" (sotto-percorsi) tra una macchina e la successiva
            for i in range(len(perm) - 1):
                m1 = perm[i]
                m2 = perm[i + 1]
                # Calcola la distanza minima su G
                dist_leg = nx.shortest_path_length(G, m1, m2, weight='weight')
                route_distances.append(dist_leg)
                total_dist += dist_leg

            # Creiamo una stringa "MacchinaA -> MacchinaB -> ..."
            # usando il nome 'Entity Name' dal DataFrame
            route_names = [df.loc[idx_m, "Entity Name"] for idx_m in perm]
            route_str = " -> ".join(str(name) for name in route_names)

            # Creiamo la stringa delle distanze "d1 + d2 + ... = TOT"
            sum_str = " + ".join(f"{dist:.2f}" for dist in route_distances)
            sum_str += f" = {total_dist:.2f}"

            results.append({
                "Percorso": route_str,
                "Somma valori (stringa)": sum_str,
                "Valore complessivo": total_dist
            })

        # Convertiamo i risultati in DataFrame
        df_results = pd.DataFrame(results)

        # Mostra a schermo i risultati (ATTENZIONE: può essere molto lungo!)
        st.write("Tabella dei percorsi e distanze:")
        st.dataframe(df_results)

        # ============ BOTTONE PER SCARICARE IL RISULTATO IN EXCEL ============
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_results.to_excel(writer, index=False, sheet_name="Percorsi_Macchine")
        excel_data = output.getvalue()

        st.download_button(
            label="Scarica risultati in Excel",
            data=excel_data,
            file_name="percorsi_macchine.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")

if __name__ == "__main__":
    main()





