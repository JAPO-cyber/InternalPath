import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from PIL import Image
import math

def main():
    st.title("Caricamento dati da Excel + Costruzione Grafo Corridoio-Macchina con etichette")

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

        # 1) Crea un grafo iniziale vuoto
        G = nx.Graph()

        # 2) Aggiunge i nodi (tutti i punti: corridoi e macchine)
        #    Usando l'indice del DataFrame come 'id' del nodo
        for idx, row in df.iterrows():
            x_val = row["X"]
            y_val = row["Y"]
            tag_val = row["Tag"]
            name_val = row["Entity Name"]
            G.add_node(idx, x=x_val, y=y_val, tag=tag_val, name=name_val)

        # Funzione per calcolare la distanza euclidea tra due nodi nel grafo
        def distance(n1, n2):
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))

        # 3) Connettiamo i punti corridoio tra loro (MST sui Corridoi)
        G_corr = nx.Graph()
        corridoio_indices = df_corridoio.index.tolist()

        # Aggiunge i nodi (solo corridoio) al G_corr
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

        # 4) Connettiamo ogni macchina al corridoio più vicino
        for idx_m, row_m in df_macchina.iterrows():
            nearest_corr = None
            nearest_dist = float("inf")
            for idx_c, row_c in df_corridoio.iterrows():
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

        # ---- VISUALIZZAZIONE ----

        # Apri l'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Crea il grafico
        fig, ax = plt.subplots(figsize=(10, 8))

        # Limiti grafico (in base a min/max di tutti i punti)
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

        # Disegniamo gli archi del grafo
        # e posizioniamo la distanza sugli archi se entrambi i nodi sono Corridoio
        for (n1, n2) in G.edges():
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            ax.plot([x1, x2], [y1, y2], color='blue', linewidth=1, alpha=0.5)

            # Se entrambi sono corridoi, scriviamo la distanza a metà
            if G.nodes[n1]["tag"] == "Corridoio" and G.nodes[n2]["tag"] == "Corridoio":
                dist_val = G[n1][n2]["weight"]  # peso dell'arco
                xm, ym = (x1 + x2) / 2, (y1 + y2) / 2
                ax.text(xm, ym, f"{dist_val:.2f}", color='blue', fontsize=8,
                        ha='center', va='center', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))

        # Disegna i punti Corridoio (in verde)
        ax.scatter(df_corridoio["X"], df_corridoio["Y"], c='green', marker='o', label='Corridoio')

        # Disegna i punti Macchina (in rosso)
        ax.scatter(df_macchina["X"], df_macchina["Y"], c='red', marker='s', label='Macchina')

        # Aggiunge il nome sui punti Macchina (colonna 'Entity Name')
        for idx_m, row_m in df_macchina.iterrows():
            x_m = row_m["X"]
            y_m = row_m["Y"]
            name_m = row_m["Entity Name"]
            if pd.notna(x_m) and pd.notna(y_m):
                ax.text(x_m, y_m, str(name_m), color='black', fontsize=8,
                        ha='left', va='bottom',
                        bbox=dict(boxstyle="round,pad=0.1", fc="yellow", ec="black", alpha=0.5))

        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafo Corridoio-Macchina con nomi Macchine e distanze Corridoi")
        ax.legend()

        st.pyplot(fig)

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")

if __name__ == "__main__":
    main()




