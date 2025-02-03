import streamlit as st
import pandas as pd
import networkx as nx
import math
import itertools
import io
from PIL import Image
import matplotlib.pyplot as plt
from collections import defaultdict

def main():
    st.title("Grafo Corridoio-Macchina – Catena con Filtraggio ad Ogni Step")

    # 1. Carica file Excel
    excel_file = st.file_uploader(
        label="Carica un file Excel (X, Y, Tag, Entity Name, Size)",
        type=["xls", "xlsx"]
    )
    
    # 2. (Opzionale) Carica immagine di sfondo
    bg_image_file = st.file_uploader(
        label="Carica un'immagine di sfondo (jpg, jpeg, png) [Opzionale]",
        type=["jpg", "jpeg", "png"]
    )
    
    if excel_file is not None:
        # Legge il DataFrame
        df = pd.read_excel(excel_file)
        st.subheader("Anteprima del DataFrame caricato")
        st.dataframe(df.head())
        
        # Verifica le colonne necessarie
        needed_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
        for c in needed_cols:
            if c not in df.columns:
                st.error(f"Colonna '{c}' mancante nel file Excel.")
                return
        
        # Converte X e Y in numerico
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
        
        # Suddivide in nodi "Corridoio" e "Macchina"
        df_corridoio = df[df["Tag"] == "Corridoio"].copy()
        df_macchina = df[df["Tag"] == "Macchina"].copy()
        if df_corridoio.empty:
            st.warning("Non ci sono corridoi: impossibile costruire il grafo completo.")
            return
        if df_macchina.empty:
            st.warning("Non ci sono macchine: non ci sono coppie da calcolare.")
            # (Se necessario, puoi comunque visualizzare solo il grafo dei corridoi)
        
        # Crea il grafo principale e aggiunge tutti i nodi
        G = nx.Graph()
        for idx, row in df.iterrows():
            G.add_node(
                idx,
                x=row["X"],
                y=row["Y"],
                tag=row["Tag"],
                name=row["Entity Name"],
                size=row.get("Size", None)
            )
        
        # Funzione per calcolare la distanza euclidea
        def distance(n1, n2):
            x1, y1 = G.nodes[n1]["x"], G.nodes[n1]["y"]
            x2, y2 = G.nodes[n2]["x"], G.nodes[n2]["y"]
            return math.dist((x1, y1), (x2, y2))
        
        # ====== 1) Collegamento Corridoi (MST) ======
        corr_indices = df_corridoio.index.tolist()
        G_corr = nx.Graph()
        G_corr.add_nodes_from(corr_indices)
        for i in range(len(corr_indices)):
            for j in range(i + 1, len(corr_indices)):
                n1 = corr_indices[i]
                n2 = corr_indices[j]
                d = distance(n1, n2)
                G_corr.add_edge(n1, n2, weight=d)
        mst_corridoi = nx.minimum_spanning_tree(G_corr, weight='weight')
        for (c1, c2) in mst_corridoi.edges():
            G.add_edge(c1, c2, weight=G_corr[c1][c2]["weight"])
        
        # ====== 2) Collegamento Macchine a Corridoi con Catena "Hard‐Filtered" ======
        def choose_corridor_chain(machine_idx, corridor_indices):
            """
            Per la macchina indicata, costruisce una catena di nodi corridoio
            in base alla direzione indicata nel campo "Size" della macchina.
            
            • Per il primo candidato, si filtrano **solamente** i nodi corridoio (non la macchina)
                che soddisfano la condizione rispetto alle coordinate della macchina.
                Ad esempio, se Size è "destro", vengono considerati solo i nodi corridoio con x > machine.x.
            
            • Una volta scelto il primo candidato, la catena viene estesa in modo iterativo:
                il prossimo candidato è scelto filtrando i nodi corridoio in base al nodo corridoio precedente.
                Ad esempio, se il primo candidato ha x = 3.46, per Size "destro" vengono considerati
                solo i nodi corridoio con x > 3.46.
            
            Ritorna la lista (catena) dei nodi corridoio selezionati.
            Se nessun nodo soddisfa il filtro per il primo candidato, ritorna una lista vuota.
            """
            size_val = G.nodes[machine_idx]["size"]
            direction = size_val.strip().lower() if isinstance(size_val, str) else ""
            machine_x = G.nodes[machine_idx]["x"]
            machine_y = G.nodes[machine_idx]["y"]
            chain = []
            
            # Per il primo candidato, filtriamo utilizzando la macchina (e non includiamo la macchina stessa)
            if direction == "destro":
                valid_first = [c for c in corridor_indices if G.nodes[c]["x"] > machine_x]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["x"])
            elif direction == "sinistro":
                valid_first = [c for c in corridor_indices if G.nodes[c]["x"] < machine_x]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["x"], reverse=True)
            elif direction == "alto":
                valid_first = [c for c in corridor_indices if G.nodes[c]["y"] > machine_y]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["y"])
            elif direction == "basso":
                valid_first = [c for c in corridor_indices if G.nodes[c]["y"] < machine_y]
                sorted_first = sorted(valid_first, key=lambda c: G.nodes[c]["y"], reverse=True)
            else:
                # Se il campo Size è vuoto, restituisci il singolo candidato (più vicino)
                candidate = min(corridor_indices, key=lambda c: distance(machine_idx, c))
                return [candidate]
            
            if not sorted_first:
                return []  # nessun nodo corridoio soddisfa il filtro rispetto alla macchina
            
            # Prendi il primo candidato dalla lista ordinata
            chain.append(sorted_first[0])
            
            # Ora, per ogni step successivo, filtra i nodi corridoio in base al nodo corridoio precedente.
            last = chain[0]
            while True:
                if direction == "destro":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["x"] > G.nodes[last]["x"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["x"])
                elif direction == "sinistro":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["x"] < G.nodes[last]["x"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["x"], reverse=True)
                elif direction == "alto":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["y"] > G.nodes[last]["y"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["y"])
                elif direction == "basso":
                    valid_next = [c for c in corridor_indices if G.nodes[c]["y"] < G.nodes[last]["y"]]
                    valid_next = sorted(valid_next, key=lambda c: G.nodes[c]["y"], reverse=True)
                else:
                    valid_next = []
                
                # Escludi i nodi già nella catena
                valid_next = [c for c in valid_next if c not in chain]
                if not valid_next:
                    break
                # Prendi il primo candidato della lista ordinata
                chain.append(valid_next[0])
                last = valid_next[0]
            return chain
        
        # Per ogni macchina, ottieni la catena filtrata e crea gli archi corrispondenti
        for idx_m in df_macchina.index:
            chain = choose_corridor_chain(idx_m, corr_indices)
            if chain:
                # Collega la macchina al primo nodo corridoio della catena
                w1 = distance(idx_m, chain[0])
                G.add_edge(idx_m, chain[0], weight=w1)
                # Collega in sequenza i nodi corridoio della catena
                for i in range(len(chain) - 1):
                    w = distance(chain[i], chain[i+1])
                    G.add_edge(chain[i], chain[i+1], weight=w)
            else:
                st.write(f"Nessun nodo corridoio soddisfa il filtro per la macchina '{G.nodes[idx_m]['name']}' con Size '{G.nodes[idx_m]['size']}'.")

        st.write(f"**Nodi nel grafo**: {G.number_of_nodes()}")
        st.write(f"**Archi nel grafo**: {G.number_of_edges()}")
        
        # ====== 3) Calcolo delle distanze tra coppie di macchine ======
        st.subheader("Distanze tra coppie di macchine (con percorso completo)")
        machine_indices = df_macchina.index.tolist()
        if len(machine_indices) < 2:
            st.info("Meno di due macchine, nessuna coppia da calcolare.")
            return
        
        G_paths = nx.Graph()
        G_paths.add_nodes_from(G.nodes(data=True))
        edge_usage_count = defaultdict(int)
        results = []
        pairs = itertools.combinations(machine_indices, 2)
        for m1, m2 in pairs:
            name1 = G.nodes[m1]["name"]
            name2 = G.nodes[m2]["name"]
            path_nodes = nx.shortest_path(G, m1, m2, weight='weight')
            segment_distances = []
            for i in range(len(path_nodes) - 1):
                nA = path_nodes[i]
                nB = path_nodes[i+1]
                d_seg = G[nA][nB]['weight']
                segment_distances.append(d_seg)
                edge_key = tuple(sorted([nA, nB]))
                edge_usage_count[edge_key] += 1
            total_dist = sum(segment_distances)
            path_list = [G.nodes[nd]["name"] for nd in path_nodes]
            path_str = " -> ".join(path_list)
            sum_str = " + ".join(f"{d_val:.2f}" for d_val in segment_distances) + f" = {total_dist:.2f}"
            results.append({
                "Coppia Macchine": f"{name1} - {name2}",
                "Percorso (macchine + corridoi)": path_str,
                "Somma distanze (stringa)": sum_str,
                "Valore complessivo": total_dist
            })
        for (n1, n2), usage_count in edge_usage_count.items():
            d_val = G[n1][n2]['weight']
            G_paths.add_edge(n1, n2, weight=d_val, count=usage_count)
        df_results = pd.DataFrame(results).sort_values(by="Valore complessivo", ascending=True)
        st.write("Tabella dei risultati:")
        st.dataframe(df_results)
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
        
        # ====== 4) Visualizzazione del sottografo G_paths ======
        st.subheader("Visualizzazione dei percorsi effettivamente usati (con count su ciascun arco)")
        if bg_image_file is not None:
            bg_image = Image.open(bg_image_file)
            x_min, x_max = df["X"].min(), df["X"].max()
            y_min, y_max = df["Y"].min(), df["Y"].max()
            if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
                st.warning("Coordinate X/Y non valide, impossibile mostrare l'immagine di sfondo.")
            else:
                fig2, ax2 = plt.subplots(figsize=(10, 8))
                ax2.imshow(bg_image, extent=[x_min, x_max, y_min, y_max],
                           aspect='auto', origin='upper')
                for (n1, n2) in G_paths.edges():
                    x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                    x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                    ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)
                    usage_count = G_paths[n1][n2]['count']
                    xm = (x1 + x2) / 2
                    ym = (y1 + y2) / 2
                    ax2.text(xm, ym, str(usage_count), color="blue", fontsize=10,
                             ha="center", va="center",
                             bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="blue", alpha=0.6))
                coords_corridoio = []
                coords_macchina = []
                for nd in G_paths.nodes():
                    tag_nd = G_paths.nodes[nd]["tag"]
                    x_val = G_paths.nodes[nd]["x"]
                    y_val = G_paths.nodes[nd]["y"]
                    if pd.notna(x_val) and pd.notna(y_val):
                        if tag_nd == "Corridoio":
                            coords_corridoio.append((x_val, y_val))
                        elif tag_nd == "Macchina":
                            coords_macchina.append((x_val, y_val))
                if coords_corridoio:
                    x_c, y_c = zip(*coords_corridoio)
                    ax2.scatter(x_c, y_c, c='green', marker='o', label='Corridoio')
                if coords_macchina:
                    x_m, y_m = zip(*coords_macchina)
                    ax2.scatter(x_m, y_m, c='red', marker='s', label='Macchina')
                ax2.set_title("Sottografo dei percorsi Macchina-Macchina (count archi)")
                ax2.legend()
                st.pyplot(fig2)
        else:
            fig2, ax2 = plt.subplots(figsize=(10, 8))
            for (n1, n2) in G_paths.edges():
                x1, y1 = G_paths.nodes[n1]["x"], G_paths.nodes[n1]["y"]
                x2, y2 = G_paths.nodes[n2]["x"], G_paths.nodes[n2]["y"]
                ax2.plot([x1, x2], [y1, y2], color='blue', linewidth=2, alpha=0.7)
                usage_count = G_paths[n1][n2]['count']
                xm = (x1 + x2) / 2
                ym = (y1 + y2) / 2
                ax2.text(xm, ym, str(usage_count), color="blue", fontsize=10,
                         ha="center", va="center",
                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="blue", alpha=0.6))
            coords_corridoio = []
            coords_macchina = []
            for nd in G_paths.nodes():
                tag_nd = G_paths.nodes[nd]["tag"]
                x_val = G_paths.nodes[nd]["x"]
                y_val = G_paths.nodes[nd]["y"]
                if pd.notna(x_val) and pd.notna(y_val):
                    if tag_nd == "Corridoio":
                        coords_corridoio.append((x_val, y_val))
                    elif tag_nd == "Macchina":
                        coords_macchina.append((x_val, y_val))
            if coords_corridoio:
                x_c, y_c = zip(*coords_corridoio)
                ax2.scatter(x_c, y_c, c='green', marker='o', label='Corridoio')
            if coords_macchina:
                x_m, y_m = zip(*coords_macchina)
                ax2.scatter(x_m, y_m, c='red', marker='s', label='Macchina')
            ax2.set_title("Sottografo dei percorsi Macchina-Macchina (count archi)")
            ax2.legend()
            st.pyplot(fig2)
    else:
        st.write("Carica un file Excel per iniziare.")

if __name__ == "__main__":
    main()


