import streamlit as st
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import random
from datetime import datetime, timedelta

st.title("Pagina 2: Output della Configurazione dei Percorsi, Ordini e Frequenze dei Corridoi")

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

    # --- Sezione: Visualizzazione del Grafo Completo ---
    st.subheader("Grafico del Grafo Completo")
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
    # Definisci l'intervallo di date per generare date casuali
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    delta_days = (end_date - start_date).days

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
        # Genera una data casuale nell'intervallo
        random_days = random.randint(0, delta_days)
        order_date = start_date + timedelta(days=random_days)
        orders.append({
            "Ordine": f"Ordine {i}",
            "Date": order_date.strftime("%Y-%m-%d"),
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
    
    # --- Sezione: Filtro per Data con Tasto "Annulla Filtro" ---
    st.subheader("Filtro Ordini per Data")
    default_range = [start_date.date(), end_date.date()]
    selected_range = st.date_input("Seleziona intervallo di date", default_range)
    # Pulsante per annullare il filtro
    if st.button("Annulla Filtro"):
        df_filtered = df_orders.copy()
    else:
        if isinstance(selected_range, (tuple, list)):
            filter_start, filter_end = selected_range
        else:
            filter_start = filter_end = selected_range
        df_orders["Date"] = pd.to_datetime(df_orders["Date"])
        df_filtered = df_orders[(df_orders["Date"] >= pd.to_datetime(filter_start)) & (df_orders["Date"] <= pd.to_datetime(filter_end))]
    st.write("Ordini filtrati:")
    st.dataframe(df_filtered)
    
    # --- Sezione: Grafico Frequenze degli Archi Utilizzati tra Punti Corridoio (solo per ordini filtrati) ---
    st.subheader("Grafico Frequenze: Solo Punti Corridoio (Ordini Filtrati)")
    corridor_ids = {c.id for c in results["corridoi"]}
    edge_freq_corridor = {}
    for _, order in df_filtered.iterrows():
        path_nodes = order["Path"].split(" -> ")
        for i in range(len(path_nodes) - 1):
            if path_nodes[i] in corridor_ids and path_nodes[i+1] in corridor_ids:
                edge = (path_nodes[i], path_nodes[i+1])
                edge_freq_corridor[edge] = edge_freq_corridor.get(edge, 0) + 1

    freq_graph = nx.DiGraph()
    for node in G.nodes():
        if node in corridor_ids:
            freq_graph.add_node(node, punto=G.nodes[node]['punto'])
    for (src, dst), freq in edge_freq_corridor.items():
        if src in freq_graph.nodes() and dst in freq_graph.nodes():
            freq_graph.add_edge(src, dst, frequency=freq)
    pos_freq = {node: (G.nodes[node]['punto'].x, G.nodes[node]['punto'].y) for node in freq_graph.nodes()}
    
    fig_freq, ax_freq = plt.subplots(figsize=(8, 6))
    nx.draw_networkx_nodes(freq_graph, pos_freq, node_color='blue', node_size=400, ax=ax_freq)
    edge_widths = [freq_graph[u][v]['frequency'] * 1.5 for u, v in freq_graph.edges()]
    nx.draw_networkx_edges(freq_graph, pos_freq, ax=ax_freq, width=edge_widths, arrowstyle='->', arrowsize=15)
    nx.draw_networkx_labels(freq_graph, pos_freq, ax=ax_freq)
    edge_labels = {(u, v): freq_graph[u][v]['frequency'] for u, v in freq_graph.edges()}
    nx.draw_networkx_edge_labels(freq_graph, pos_freq, edge_labels=edge_labels, ax=ax_freq)
    
    ax_freq.set_title("Frequenza utilizzo degli archi (solo corridoi) [Ordini filtrati]")
    ax_freq.set_xlabel("Coordinata X")
    ax_freq.set_ylabel("Coordinata Y")
    ax_freq.axis('equal')
    ax_freq.grid(True)
    st.pyplot(fig_freq)
    
    # Salva i risultati aggiornati nello stato della sessione
    st.session_state["computed_results"] = {
        "percorsi_macchine": results["percorsi_macchine"],
        "excel_data": results["excel_data"],
        "graph": G,
        "macchine": results["macchine"],
        "corridoi": results["corridoi"],
        "orders": orders,
        "edge_frequency": edge_freq_corridor
    }


