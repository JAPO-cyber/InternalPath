import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import random

st.title("Pagina 2: Output della Configurazione dei Percorsi e Ordini di Processo")

# Verifica se i risultati sono presenti nello stato della sessione
if "computed_results" not in st.session_state:
    st.error("Non sono disponibili risultati. Assicurati di aver eseguito la Pagina 1 per calcolare i percorsi.")
else:
    results = st.session_state["computed_results"]

    # --- Sezione: Tabella Riassuntiva dei Percorsi ---
    st.subheader("Percorsi minimi fra macchine")
    # Costruiamo un dataframe dai risultati
    rows = []
    for (m1, m2), info in results["percorsi_macchine"].items():
        rows.append({
            "Machine1": m1,
            "Machine2": m2,
            "Path": " -> ".join(info["path"]) if info["path"] is not None else None,
            "Distance": info["distance"]
        })
    df_paths = pd.DataFrame(rows)
    st.dataframe(df_paths)

    # --- Sezione: Visualizzazione del Grafo ---
    st.subheader("Grafico del Grafo")
    G = results["graph"]
    # Funzione per disegnare il grafo (copia dalla Pagina 1)
    def disegna_grafo(G):
        pos = {}
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            punto = G.nodes[node]['punto']
            pos[node] = (punto.x, punto.y)
            if punto.categoria == "macchina":
                node_colors.append('red')
                node_sizes.append(600)
            else:
                node_colors.append('blue')
                node_sizes.append(300)
        fig, ax = plt.subplots(figsize=(8, 6))
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=node_sizes, font_weight='bold', ax=ax)
        edge_labels = nx.get_edge_attributes(G, 'weight')
        edge_labels = {edge: f"{weight:.2f}" for edge, weight in edge_labels.items()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.axis('equal')
        ax.grid(True)
        ax.set_title("Grafo: Macchine e Corridoi")
        return fig

    fig_graph = disegna_grafo(G)
    st.pyplot(fig_graph)

    # --- Sezione: Download del File Excel con i Collegamenti ---
    st.subheader("Download del File Excel con i Collegamenti")
    st.download_button(
        label="Scarica file Excel con i collegamenti",
        data=results["excel_data"],
        file_name="machine_connections.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- Sezione: Generazione degli Ordini di Processo ---
    st.subheader("Ordini di Processo")
    # Estrae gli ID delle macchine dai risultati (assumiamo che "macchine" sia una lista di oggetti Punto)
    machine_ids = [m.id for m in results["macchine"]]
    
    orders = []
    # Genera 50 ordini con almeno 3 macchine per ordine (scegliendo casualmente tra quelli disponibili)
    for i in range(1, 51):
        n = random.randint(3, 5)  # numero casuale di macchine per l'ordine (da 3 a 5)
        selected = random.sample(machine_ids, n)
        orders.append({
            "Ordine": f"Ordine {i}",
            "Path": " -> ".join(selected)
        })
    
    df_orders = pd.DataFrame(orders)
    st.dataframe(df_orders)
    
    st.download_button(
        label="Scarica Ordini di Processo (CSV)",
        data=df_orders.to_csv(index=False),
        file_name="ordini_di_processo.csv",
        mime="text/csv"
    )

