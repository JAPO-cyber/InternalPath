import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import matplotlib.pyplot as plt

def main():
    st.title("Grafo Corridoio-Macchina – Percorso Forzato Ristrutturato")
    
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

    # Conversione delle coordinate in valori numerici
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
    
    # 3. Costruiamo il grafo diretto
    DG = nx.DiGraph()
    
    # Aggiunta dei nodi con i relativi attributi. Per "Size" usiamo il valore in minuscolo e senza spazi.
    for idx, row in df.iterrows():
        size_val = str(row.get("Size", "")).strip().lower()
        DG.add_node(
            idx,
            x=row["X"],
            y=row["Y"],
            tag=row["Tag"],
            name=row["Entity Name"],
            size=size_val
        )
    
    # Lista degli indici dei corridoi
    corridor_nodes = list(df_corridor.index)
    
    # 4. Funzioni di utilità
    
    # Calcola la distanza euclidea tra il nodo i e il nodo j
    def euclidean(i, j):
        x1, y1 = DG.nodes[i]["x"], DG.nodes[i]["y"]
        x2, y2 = DG.nodes[j]["x"], DG.nodes[j]["y"]
        return math.dist((x1, y1), (x2, y2))
    
    # Verifica se il nodo j è nella direzione richiesta a partire dal nodo i
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
            return False  # non è una direzione forzata
    
    # Per un nodo corridoio i, restituisce il candidato (tra gli altri corridoi) che soddisfa il vincolo direzionale
    def get_forced_candidate(i):
        direction = DG.nodes[i]["size"]
        if direction not in {"destro", "sinistro", "alto", "basso"}:
            return None
        # Seleziona i candidati (esclude se stesso)
        candidates = [j for j in corridor_nodes if j != i and is_valid_direction(i, j, direction)]
        if not candidates:
            return None
        # Sceglie il candidato con la distanza euclidea minima
        return min(candidates, key=lambda j: euclidean(i, j))
    
    # 5. Aggiunta degli archi forzati (solo per corridoi con direzione impostata)
    forced_factor = 0.001  # fattore per ridurre artificialmente il peso degli archi forzati
    forced_edges = {}      # memorizziamo {nodo: candidato} per debug/eventuale analisi
    for i in corridor_nodes:
        direction = DG.nodes[i]["size"]
        if direction in {"destro", "sinistro", "alto", "basso"}:
            candidate = get_forced_candidate(i)
            if candidate is not None:
                forced_edges[i] = candidate
                weight = euclidean(i, candidate) * forced_factor
                DG.add_edge(i, candidate, weight=weight, forced=True)
    
    # 6. Aggiunta degli archi di fallback (non forzati)
    # Per garantire la connessione tra i nodi:
    # - Se il nodo sorgente è un corridoio con direzione forzata, *non* aggiungiamo archi verso altri corridoi (fallback)
    # - In tutti gli altri casi (corridoio senza vincolo, macchina, o collegamenti macchina-corridoio) li aggiungiamo.
    all_nodes = list(DG.nodes())
    for i in all_nodes:
        for j in all_nodes:
            if i == j:
                continue
            # Se il nodo sorgente è un corridoio forzato e il target è un corridoio, non aggiungiamo arco fallback
            if DG.nodes[i]["tag"] == "Corridoio" and i in forced_edges and DG.nodes[j]["tag"] == "Corridoio":
                continue
            # Se non esiste già un arco (ad es. forzato) da i a j, aggiungiamo il fallback
            if not DG.has_edge(i, j):
                DG.add_edge(i, j, weight=euclidean(i, j), forced=False)
    
    # 7. Calcolo e visualizzazione dei percorsi tra macchine
    st.subheader("Percorsi tra macchine (con forzatura nei corridoi)")
    machine_nodes = list(df_machine.index)
    if len(machine_nodes) < 2:
        st.info("Non ci sono abbastanza macchine per calcolare i percorsi.")
        return
    
    for m1, m2 in itertools.combinations(machine_nodes, 2):
        try:
            path_nodes = nx.shortest_path(DG, source=m1, target=m2, weight="weight")
            path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))
            
            # Visualizzazione del percorso
            fig, ax = plt.subplots(figsize=(10, 8))
            # Disegno dei nodi lungo il percorso
            for n in path_nodes:
                x, y = DG.nodes[n]["x"], DG.nodes[n]["y"]
                ax.scatter(x, y, color='blue')
                ax.text(x, y, DG.nodes[n]["name"], fontsize=9)
            
            # Disegno degli archi: quelli forzati vengono evidenziati in verde
            for (u, v) in path_edges:
                x1, y1 = DG.nodes[u]["x"], DG.nodes[u]["y"]
                x2, y2 = DG.nodes[v]["x"], DG.nodes[v]["y"]
                if DG[u][v].get("forced", False):
                    ax.plot([x1, x2], [y1, y2], color='green', linewidth=3, label="Forzato")
                else:
                    ax.plot([x1, x2], [y1, y2], color='red', linewidth=2)
            
            ax.set_title(f"Percorso: {DG.nodes[m1]['name']} -> {DG.nodes[m2]['name']}")
            st.pyplot(fig)
        except nx.NetworkXNoPath:
            st.write(f"Nessun percorso trovato tra {DG.nodes[m1]['name']} e {DG.nodes[m2]['name']}")
    
if __name__ == "__main__":
    main()





