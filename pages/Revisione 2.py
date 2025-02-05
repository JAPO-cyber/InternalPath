def display_graph(G, pos, corridors, machines):
    """
    Visualizza il grafo con i nodi etichettati e colori distinti:
      - Corridoi: blu chiaro (skyblue)
      - Macchine: verde chiaro (lightgreen)
    """
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Disegna gli archi con un'opacità ridotta
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.5)
    
    # Disegna i nodi, distinguendo corridoi e macchine
    nx.draw_networkx_nodes(G, pos, nodelist=corridors, node_color="skyblue", label="Corridoio", node_size=100, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=machines, node_color="lightgreen", label="Macchina", node_size=100, ax=ax)
    
    # Aggiungi le etichette dei nodi (ad esempio, mostrando l'Entity Name o l'ID)
    labels = {node: f"{G.nodes[node]['entity_name']}\n(ID: {node})" for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8, ax=ax)
    
    ax.set_title("Grafico dei Nodi")
    ax.legend()
    ax.axis("off")
    st.pyplot(fig)

# ... (il resto del tuo codice)

def main():
    st.title("Collegamento Macchine Tramite Corridoi – Percorsi")

    # 1. Caricamento del file Excel
    excel_file = st.file_uploader("Carica file Excel (X, Y, Tag, Entity Name, Size)", type=["xls", "xlsx"])
    if not excel_file:
        st.info("Carica un file Excel per iniziare.")
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

    # Conversione in numerico delle coordinate
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    # Separiamo i nodi in base al Tag
    df_corridor = df[df["Tag"] == "Corridoio"].copy()
    df_machine = df[df["Tag"] == "Macchina"].copy()

    if df_corridor.empty:
        st.warning("Nessun corridoio presente. Impossibile costruire il grafo.")
        return
    if df_machine.empty:
        st.warning("Nessuna macchina presente.")
        return

    # Uniamo i dati in un unico DataFrame
    df_all = pd.concat([df_corridor, df_machine])

    # 3. Costruzione del grafo
    st.subheader("Costruzione del grafo")
    max_distance = st.slider("Distanza massima per collegare i nodi", min_value=1.0, max_value=500.0, value=50.0,
                             help="Due nodi vengono collegati se la distanza euclidea è ≤ a questo valore.")
    G = nx.Graph()

    # Aggiungiamo i nodi con i relativi attributi (utilizziamo l'indice del DataFrame come ID)
    for idx, row in df_all.iterrows():
        G.add_node(idx, 
                   x=row["X"], 
                   y=row["Y"], 
                   tag=row["Tag"], 
                   entity_name=row["Entity Name"], 
                   size=row["Size"])

    # Aggiungiamo gli archi: solo se la distanza ≤ max_distance e se almeno uno dei due nodi è un Corridoio.
    nodes = list(G.nodes(data=True))
    for (i, data_i), (j, data_j) in itertools.combinations(nodes, 2):
        dist = math.dist((data_i["x"], data_i["y"]), (data_j["x"], data_j["y"]))
        if dist <= max_distance:
            if data_i["tag"] == "Corridoio" or data_j["tag"] == "Corridoio":
                G.add_edge(i, j, weight=dist)

    st.write("Numero totale di nodi:", G.number_of_nodes())
    st.write("Numero totale di archi:", G.number_of_edges())

    # Preparo la posizione dei nodi per la visualizzazione
    pos = {node: (data["x"], data["y"]) for node, data in G.nodes(data=True)}
    corridors = [n for n, d in G.nodes(data=True) if d["tag"] == "Corridoio"]
    machines = [n for n, d in G.nodes(data=True) if d["tag"] == "Macchina"]

    # 4. Visualizzazione del grafo dei nodi
    st.subheader("Grafico dei Nodi")
    display_graph(G, pos, corridors, machines)

    # ... (il resto del codice per il calcolo dei percorsi)
    # ad esempio: selezione macchine, calcolo percorsi, etc.

if __name__ == "__main__":
    main()






