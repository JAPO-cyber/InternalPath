import itertools
import networkx as nx
import pandas as pd
import math

def calcola_coppie_macchine(G, df, df_macchina, output_excel_file="distanze_coppie_macchine.xlsx"):
    """
    Dato un grafo G (networkx) con attributi:
      G.edges[u, v]['weight'] = distanza
    e i DataFrame df (completo) e df_macchina (solo righe con Tag='Macchina'),
    produce tutte le combinazioni (coppie) di macchine ignorando l'ordine
    e calcola la distanza del percorso più breve su G.
    
    Parametri:
    - G: grafo NetworkX con nodi corrispondenti a corridoi/macchine
         e archi con 'weight' come distanza
    - df: DataFrame completo (contiene colonna "Entity Name")
    - df_macchina: DataFrame filtrato (Tag == 'Macchina')
    - output_excel_file: nome del file Excel di output

    Ritorna:
    - df_results: DataFrame con colonne:
        1) "Coppia" (stringa: "Macchina1 - Macchina2")
        2) "Distanza" (float, distanza del cammino più breve)
    """
    machine_indices = df_macchina.index.tolist()

    # Se non ci sono macchine, non facciamo nulla
    if len(machine_indices) < 2:
        print("Ci sono meno di due macchine; impossibile calcolare coppie.")
        return pd.DataFrame()

    # Generiamo tutte le combinazioni di 2 macchine (ignorando l'ordine)
    pairs = itertools.combinations(machine_indices, 2)

    results = []
    for (m1, m2) in pairs:
        # Calcoliamo la distanza del percorso più breve nel grafo
        dist = nx.shortest_path_length(G, source=m1, target=m2, weight='weight')

        name1 = df.loc[m1, "Entity Name"]
        name2 = df.loc[m2, "Entity Name"]

        results.append({
            "Coppia": f"{name1} - {name2}",
            "Distanza": dist
        })

    # Creiamo un DataFrame con i risultati
    df_results = pd.DataFrame(results).sort_values("Distanza", ascending=True)

    # Salviamo i risultati in un file Excel
    df_results.to_excel(output_excel_file, index=False)
    print(f"Risultati salvati in {output_excel_file}")

    return df_results

# ========== ESEMPIO DI UTILIZZO ==========

if __name__ == "__main__":
    # Supponendo che tu abbia già:
    # 1) Creato il grafo G con tutti i nodi e archi (collegando corridoi e macchine).
    # 2) Un DataFrame df con TUTTI i punti (colonna "Entity Name", "Tag", ecc.).
    # 3) Un DataFrame df_macchina = df[df["Tag"] == "Macchina"].
    # (Questa parte dipende dal tuo codice precedente di costruzione MST e collegamenti).

    G = nx.Graph()
    df = pd.DataFrame()
    df_macchina = pd.DataFrame()

    # Qui dovresti riempire G, df, df_macchina come vuoi.
    # Dopodiché:
    df_result = calcola_coppie_macchine(G, df, df_macchina, "distanze_coppie_macchine.xlsx")

    print("Distanze calcolate:")
    print(df_result)
