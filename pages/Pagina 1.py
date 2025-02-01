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
    machine_ids = [m.id for m in results["macchine"]]
    
    orders = []
    # Genera 50 ordini con almeno 3 macchine per ordine (da 3 a 5)
    for i in range(1, 51):
        n = random.randint(3, 5)
        selected = random.sample(machine_ids, n)
        breakdown_list = []
        total_distance = 0
        for j in range(len(selected) - 1):
            try:
                d = nx.dijkstra_path_length(G, selected[j], selected[j+1], weight='weight')
            except nx.NetworkXNoPath:
                d = float('inf')
            total_distance += d
            breakdown_list.append(f"{d:.2f}")
        orders.append({
            "Ordine": f"Ordine {i}",
            "Path": " -> ".join(selected),
            "Breakdown": " + ".join(breakdown_list),
            "Distance (m)": round(total_distance, 2)
        })
    
    df_orders = pd.DataFrame(orders)
    st.dataframe(df_orders)
    
    st.download_button(
        label="Scarica Ordini di Processo (CSV)",
        data=df_orders.to_csv(index=False),
        file_name="ordini_di_processo.csv",
        mime="text/csv"
    )
    
    # --- Nuova Sezione: Grafico Frequenze degli Archi Utilizzati negli Ordini ---
    st.subheader("Grafico Frequenze degli Archi Utilizzati negli Ordini")
    # Calcola la frequenza di utilizzo di ciascun arco nei percorsi degli ordini
    edge_freq = {}
    for order in orders:
        path_nodes = order["Path"].split(" -> ")
        for i in range(len(path_nodes) - 1):
            edge = (path_nodes[i], path_nodes[i+1])
            edge_freq[edge] = edge_freq.get(edge, 0) + 1

    # Crea un grafo per le frequenze (utilizziamo un grafo diretto)
    freq_graph = nx.DiGraph()
    for (src, dst), freq in edge_freq.items():
        freq_graph.add_edge(src, dst, frequency=freq)
    # Imposta le posizioni usando quelle dei nodi presenti nel grafo G (assumiamo che le macchine siano in G)
    pos_freq = {}
    for node in freq_graph.nodes():
        if node in G.nodes():
            punto = G.nodes[node]['punto']
            pos_freq[node] = (punto.x, punto.y)
        else:
            pos_freq[node] = (0, 0)  # fallback

    fig_freq, ax_freq = plt.subplots(figsize=(8, 6))
    # Disegna i nodi
    nx.draw_networkx_nodes(freq_graph, pos_freq, node_color='red', node_size=600, ax=ax_freq)
    # Imposta lo spessore degli archi in base alla frequenza (scalando il valore, ad esempio, moltiplicando per 1.5)
    edge_widths = [freq_graph[u][v]['frequency'] * 1.5 for u, v in freq_graph.edges()]
    nx.draw_networkx_edges(freq_graph, pos_freq, ax=ax_freq, width=edge_widths, arrowstyle='->', arrowsize=15)
    nx.draw_networkx_labels(freq_graph, pos_freq, ax=ax_freq)
    # Disegna le etichette degli archi con il valore della frequenza
    edge_labels = {(u, v): freq_graph[u][v]['frequency'] for u, v in freq_graph.edges()}
    nx.draw_networkx_edge_labels(freq_graph, pos_freq, edge_labels=edge_labels, ax=ax_freq)
    
    ax_freq.set_title("Frequenza di utilizzo degli archi negli ordini")
    ax_freq.set_xlabel("Coordinata X")
    ax_freq.set_ylabel("Coordinata Y")
    ax_freq.axis('equal')
    ax_freq.grid(True)
    st.pyplot(fig_freq)
    
    # Salva i risultati nello stato della sessione per renderli accessibili in altre pagine
    st.session_state["computed_results"] = {
        "percorsi_macchine": results["percorsi_macchine"],
        "excel_data": results["excel_data"],
        "graph": G,
        "macchine": results["macchine"],
        "corridoi": results["corridoi"],
        "orders": orders,
        "edge_frequency": edge_freq
    }


