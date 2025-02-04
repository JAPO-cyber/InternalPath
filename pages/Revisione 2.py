import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import matplotlib.pyplot as plt

def main():
    st.title("Grafo Corridoio-Macchina – Visualizzazione e Forzatura")

    # 1. Caricamento del file Excel
    excel_file = st.file_uploader(
        "Carica file Excel (X, Y, Tag, Entity Name, Size)",
        type=["xls", "xlsx"]
    )
    if not excel_file:
        return

    df = pd.read_excel(excel_file)
    st.subheader("Anteprima del DataFrame")
    st.dataframe(df.head())

    # 2. Verifica delle colonne necessarie
    required_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
    for col in required_cols:
        if col not in df.columns:
            st.error(f"Colonna '{col}' mancante nel file Excel.")
            return

    # Conversione delle coordinate in numerico
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    # Separiamo corridoi e macchine
    df_corridor = df[df["Tag"] == "Corridoio"].copy()
    df_machine = df[df["Tag"] == "Macchina"].copy()

    if df_corridor.empty:
        st.warning("Nessun corridoio presente. Impossibile costruire il grafo.")
        return
    if df_machine.empty:
        st.warning("Nessuna macchina presente. Nessun percorso da calcolare.")

    # 3. Costruzione del grafo diretto
    DG = nx.DiGraph()
    for idx, row in df.iterrows():
        size_val = str(row.get("Size", "")).strip().lower()
        DG.add_node(idx,
                    x=row["X"],
                    y=row["Y"],
                    tag=row["Tag"],
                    name=row["Entity Name"],
                    size=size_val)

    # Lista degli indici dei corridoi
    corridor_nodes = list(df_corridor.index)

    # 4. Funzioni ausiliarie

    def euclidean(i, j):
        x1, y1 = DG.nodes[i]["x"], DG.nodes[i]["y"]
        x2, y2 = DG.nodes[j]["x"], DG.nodes[j]["y"]
        return math.dist((x1, y1), (x2, y2))

    def is_valid_direction(i, j, direction):
        x1, y1 = DG.nodes[i]["x"], DG.nodes[i]["y"]
        x2, y2 = DG.nodes[j]["x"], DG.nodes[j]["y"]
        if direction == "destro":
            return x2 > x1
        elif direction == "sinistro":
            return x2 < x1
        elif direction == "alto":
            return y2 > y1
        elif direction == "basso":
            return y2 < y1
        else:
            return False

    def get_forced_candidate(i):
        direction = DG.nodes[i]["size"]
        if direction not in {"destro", "sinistro", "alto", "basso"}:
            return None
        # Seleziona tra gli altri corridoi (diversi da i) quelli che soddisfano il vincolo
        candidates = [j for j in corridor_nodes if j != i and is_valid_direction(i, j, direction)]
        if not candidates:
            return None
        # Restituisce il candidato con distanza minima
        return min(candidates, key=lambda j: euclidean(i, j))

    # 5. Aggiunta degli archi forzati per i corridoi con vincolo
    forced_factor = 0.001  # Il peso degli archi forzati viene abbassato per essere preferito
    forced_edges = {}
    for i in corridor_nodes:
        direction = DG.nodes[i]["size"]
        if direction in {"destro", "sinistro", "alto", "basso"}:
            candidate = get_forced_candidate(i)
            if candidate is not None:
                forced_edges[i] = candidate
                weight = euclidean(i, candidate) * forced_factor
                DG.add_edge(i, candidate, weight=weight, forced=True)

    # 6. Aggiunta degli archi di fallback
    # Regola: se il nodo sorgente è un corridoio con arco forzato, non aggiungiamo archi fallback verso altri corridoi.
    all_nodes = list(DG.nodes())
    for i in all_nodes:
        for j in all_nodes:
            if i == j:
                continue
            if DG.nodes[i]["tag"] == "Corridoio" and i in forced_edges and DG.nodes[j]["tag"] == "Corridoio":
                continue
            if not DG.has_edge(i, j):
                DG.add_edge(i, j, weight=euclidean(i, j), forced=False)

    # 7. Visualizzazione del grafo completo
    st.subheader("Visualizzazione del Grafo Completo")
    fig, ax = plt.subplots(figsize=(10, 8))
    pos = {n: (DG.nodes[n]["x"], DG.nodes[n]["y"]) for n in DG.nodes()}
    # Disegna tutti i nodi
    nx.draw_networkx_nodes(DG, pos, node_color='lightblue', ax=ax, node_size=300)
    nx.draw_networkx_labels(DG, pos, ax=ax, font_size=8)
    # Disegna gli archi forzati (in verde) e gli altri (in rosso, con trasparenza)
    forced_edges_list = [(u, v) for u, v in DG.edges() if DG[u][v].get("forced", False)]
    nx.draw_networkx_edges(DG, pos, edgelist=forced_edges_list, ax=ax, edge_color='green', width=2, label="Forzato")
    fallback_edges_list = [(u, v) for u, v in DG.edges() if not DG[u][v].get("forced", False)]
    nx.draw_networkx_edges(DG, pos, edgelist=fallback_edges_list, ax=ax, edge_color='red', width=1, alpha=0.3, label="Fallback")
    ax.set_title("Grafo Completo")
    st.pyplot(fig)

    # 8. Calcolo e visualizzazione dei percorsi tra macchine
    st.subheader("Percorsi tra Macchine (Percorso più breve)")
    machine_nodes = list(df_machine.index)
    if len(machine_nodes) < 2:
        st.info("Non ci sono abbastanza macchine per calcolare un percorso.")
        return

    for m1, m2 in itertools.combinations(machine_nodes, 2):
        try:
            path_nodes = nx.shortest_path(DG, source=m1, target=m2, weight="weight")
            # Visualizzazione testuale del percorso
            percorso_testuale = " -> ".join(DG.nodes[n]["name"] for n in path_nodes)
            st.write(f"Percorso da {DG.nodes[m1]['name']} a {DG.nodes[m2]['name']}:")
            st.write(percorso_testuale)
            
            # Visualizzazione grafica del percorso (sovrapposto al grafo completo)
            fig, ax = plt.subplots(figsize=(10, 8))
            nx.draw_networkx_nodes(DG, pos, node_color='lightgray', ax=ax, node_size=300)
            nx.draw_networkx_labels(DG, pos, ax=ax, font_size=8)
            # Disegniamo il percorso evidenziato in blu
            path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
            nx.draw_networkx_edges(DG, pos, edgelist=path_edges, ax=ax, edge_color='blue', width=3)
            ax.set_title(f"Percorso: {DG.nodes[m1]['name']} -> {DG.nodes[m2]['name']}")
            st.pyplot(fig)
        except nx.NetworkXNoPath:
            st.write(f"Nessun percorso trovato tra {DG.nodes[m1]['name']} e {DG.nodes[m2]['name']}.")

if __name__ == "__main__":
    main()





