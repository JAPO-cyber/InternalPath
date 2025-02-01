import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

st.title("Pagina 2: Output della Configurazione dei Percorsi")

# Verifica se i risultati sono presenti nello stato della sessione
if "computed_results" not in st.session_state:
    st.error("Non sono disponibili risultati. Assicurati di aver eseguito la Pagina 1 per calcolare i percorsi.")
else:
    results = st.session_state["computed_results"]

    # Visualizza una tabella riassuntiva dei percorsi
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

    # Funzione per disegnare il grafo (questa funzione è una copia della definizione usata in Pagina 1)
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
        # Disegna le etichette degli archi (opzionale)
        edge_labels = nx.get_edge_attributes(G, 'weight')
        edge_labels = {edge: f"{weight:.2f}" for edge, weight in edge_labels.items()}
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax)
        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.axis('equal')
        ax.grid(True)
        ax.set_title("Grafo: Macchine e Corridoi")
        return fig

    # Visualizza il grafo
    st.subheader("Grafico del Grafo")
    G = results["graph"]
    fig_graph = disegna_grafo(G)
    st.pyplot(fig_graph)

    # Pulsante per scaricare il file Excel con i collegamenti
    st.subheader("Download del File Excel")
    st.download_button(
        label="Scarica file Excel con i collegamenti",
        data=results["excel_data"],
        file_name="machine_connections.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

