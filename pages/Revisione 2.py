import streamlit as st
import pandas as pd
import math
import io
import matplotlib.pyplot as plt
from PIL import Image

def distance(xA, yA, xB, yB):
    """Distanza euclidea fra (xA,yA) e (xB,yB)."""
    return math.dist((xA, yA), (xB, yB))

def filtra_corridoi(current_corr, df_corridoi):
    """
    Legge colonna 'Size' e coordinate (X,Y) di current_corr (un record di df_corridoi).
    Se Size = 'Sinistro', ammette solo corridoi con x < x_current.
    Se Size = 'Destro',  ammette solo corridoi con x > x_current.
    Se Size = 'Alto',    ammette solo corridoi con y > y_current.
    Se Size = 'Basso',   ammette solo corridoi con y < y_current.
    Se Size è vuoto o non valido, ammette tutti i corridoi.
    """
    x_c = current_corr["X"]
    y_c = current_corr["Y"]
    size_val = current_corr["Size"]

    if not isinstance(size_val, str) or size_val.strip() == "":
        # nessun filtro
        return df_corridoi

    if size_val == "Sinistro":
        return df_corridoi[df_corridoi["X"] < x_c]
    elif size_val == "Destro":
        return df_corridoi[df_corridoi["X"] > x_c]
    elif size_val == "Alto":
        return df_corridoi[df_corridoi["Y"] > y_c]
    elif size_val == "Basso":
        return df_corridoi[df_corridoi["Y"] < y_c]
    else:
        # valore non standard => nessun filtro
        return df_corridoi

def costruisci_percorso_macchina(Mstart_idx, Mend_idx, df_macchine, df_corridoi, max_iter=50):
    """
    Costruisce un percorso step-by-step:
      1) Da MacchinaStart a Corridoio più vicino (nessun filtro).
      2) Da Corridoio C_i, in base a C_i["Size"] e (X,Y) di C_i,
         si filtrano i possibili Corridoi successivi e si sceglie il più vicino.
      3) Se non ci sono corridoi validi o conviene saltare alla MacchinaEnd,
         si conclude con la MacchinaEnd.
    Ritorna una lista di (tipo, indice, X, Y):
      es: [("Macchina", "M1", 10,10), ("Corridoio","C2",30,25), ... , ("Macchina","M2",50,50)]
    """

    path = []

    # Info di partenza
    Mstart = df_macchine.loc[Mstart_idx]
    xMstart, yMstart = Mstart["X"], Mstart["Y"]

    Mend  = df_macchine.loc[Mend_idx]
    xMend, yMend = Mend["X"], Mend["Y"]

    # 1) Corridoio più vicino alla Macchina iniziale (senza filtri)
    dist_min = float("inf")
    corr_first_idx = None
    for idxC, rowC in df_corridoi.iterrows():
        d_val = distance(xMstart, yMstart, rowC["X"], rowC["Y"])
        if d_val < dist_min:
            dist_min = d_val
            corr_first_idx = idxC

    # Se non esiste alcun corridoio, faccio un percorso diretto Mstart -> Mend
    if corr_first_idx is None:
        return [
            ("Macchina", Mstart_idx, xMstart, yMstart),
            ("Macchina", Mend_idx, xMend, yMend)
        ]

    # Inizializziamo la path
    path.append(("Macchina", Mstart_idx, xMstart, yMstart))  # Macchina iniziale
    path.append(("Corridoio", corr_first_idx,
                 df_corridoi.loc[corr_first_idx, "X"],
                 df_corridoi.loc[corr_first_idx, "Y"]))

    current_corr_idx = corr_first_idx
    visited = set([corr_first_idx])  # per evitare loop tra corridoi

    steps = 0
    while steps < max_iter:
        steps += 1

        # info corridoio attuale
        xCcurr = df_corridoi.loc[current_corr_idx, "X"]
        yCcurr = df_corridoi.loc[current_corr_idx, "Y"]

        # distanza diretta -> Macchina finale
        dist_to_end = distance(xCcurr, yCcurr, xMend, yMend)

        # filtra i corridoi successivi in base a "Size" di current_corr
        current_corr_row = df_corridoi.loc[[current_corr_idx]]  # DataFrame con 1 riga
        df_candidates = filtra_corridoi(current_corr_row.iloc[0], df_corridoi)

        # rimuovo se stesso
        if current_corr_idx in df_candidates.index:
            df_candidates = df_candidates.drop(current_corr_idx)

        # fallback se vuoto
        if df_candidates.empty:
            df_candidates = df_corridoi.drop(current_corr_idx)

        # Trovo il corridoio più vicino (fra i candidati) che non sia già visitato
        best_dist = float("inf")
        best_idx = None
        for idxCand, rowCand in df_candidates.iterrows():
            if idxCand in visited:
                continue
            d_val = distance(xCcurr, yCcurr, rowCand["X"], rowCand["Y"])
            if d_val < best_dist:
                best_dist = d_val
                best_idx = idxCand

        # Se non ho trovato un corridoio nuovo, oppure conviene passare alla MacchinaEnd
        if best_idx is None or dist_to_end < best_dist:
            # Salto a MacchinaEnd
            path.append(("Macchina", Mend_idx, xMend, yMend))
            return path

        # Altrimenti, salto a best_idx
        path.append(("Corridoio", best_idx,
                     df_corridoi.loc[best_idx, "X"],
                     df_corridoi.loc[best_idx, "Y"]))
        visited.add(best_idx)
        current_corr_idx = best_idx

    # Se arrivo qui perché ho superato max_iter, comunque concludo
    path.append(("Macchina", Mend_idx, xMend, yMend))
    return path


# ================== APP STREAMLIT ==================
def main():
    st.title("Percorso Macchina -> Corridoio multipli (con Size) -> Macchina Finale")

    excel_file = st.file_uploader("Carica un file Excel (X, Y, Tag=Macchina/Corridoio, Size)", type=["xls","xlsx"])
    bg_image_file = st.file_uploader("Carica immagine di sfondo (opzionale)", type=["jpg","jpeg","png"])

    if excel_file is None:
        st.write("Carica un file Excel per continuare.")
        return

    df = pd.read_excel(excel_file)

    # Controlli base
    needed_cols = ["X", "Y", "Tag", "Entity Name", "Size"]
    for c in needed_cols:
        if c not in df.columns:
            st.error(f"Manca la colonna '{c}' nel file Excel.")
            return

    # Converti X,Y in numerico
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

    # Suddividi macchine e corridoi
    df_macchine = df[df["Tag"] == "Macchina"].copy()
    df_corridoi = df[df["Tag"] == "Corridoio"].copy()

    if df_macchine.empty:
        st.warning("Non ci sono Macchine nel file. Impossibile procedere.")
        return
    if df_corridoi.empty:
        st.warning("Non ci sono Corridoi nel file. Percorso 'step' non realizzabile.")
        return

    # Scelta Macchina Start e Macchina End da combo box
    machine_options = df_macchine.index.tolist()
    st.subheader("Seleziona Macchina Iniziale e Macchina Finale")
    Mstart_idx = st.selectbox("Macchina Iniziale", options=machine_options)
    Mend_idx   = st.selectbox("Macchina Finale",  options=machine_options)

    if st.button("Calcola Percorso"):
        percorso = costruisci_percorso_macchina(Mstart_idx, Mend_idx, df_macchine, df_corridoi, max_iter=50)
        
        st.subheader("Percorso Trovato:")
        # Mostriamo in tabella i nodi attraversati e (facoltativo) la distanza "segmento per segmento"
        rows = []
        total_dist = 0.0
        for i in range(len(percorso)):
            typ, idx, x_val, y_val = percorso[i]
            if i == 0:
                dist_seg = 0.0
            else:
                # Distanza dal nodo precedente
                x_prev, y_prev = percorso[i-1][2], percorso[i-1][3]
                dist_seg = distance(x_prev, y_prev, x_val, y_val)
            total_dist += dist_seg
            # Se "Entity Name" esiste, recuperiamolo dal df
            if typ == "Macchina":
                name = df_macchine.loc[idx, "Entity Name"]
            else:
                name = df_corridoi.loc[idx, "Entity Name"]
            rows.append({
                "Tipo": typ,
                "Indice": idx,
                "Nome": name,
                "X": x_val,
                "Y": y_val,
                "Distanza Step": f"{dist_seg:.2f}"
            })

        df_path = pd.DataFrame(rows)
        st.dataframe(df_path)
        st.write(f"**Distanza totale**: {total_dist:.2f}")

        # Disegno su mappa
        if bg_image_file is not None:
            bg_image = Image.open(bg_image_file)
            x_min, x_max = df["X"].min(), df["X"].max()
            y_min, y_max = df["Y"].min(), df["Y"].max()

            fig, ax = plt.subplots(figsize=(8,6))
            ax.imshow(
                bg_image,
                extent=[x_min, x_max, y_min, y_max],
                aspect='auto',
                origin='upper'
            )
            # Disegno corridoi (punti verdi)
            ax.scatter(df_corridoi["X"], df_corridoi["Y"], c='green', marker='o', label='Corridoio')
            # Disegno macchine (punti rossi)
            ax.scatter(df_macchine["X"], df_macchine["Y"], c='red', marker='s', label='Macchina')

            # Ora disegno il percorso come linee con step
            xs = [p[2] for p in percorso]
            ys = [p[3] for p in percorso]
            ax.plot(xs, ys, color='blue', linewidth=2, marker='o', markersize=4)

            ax.set_title("Percorso Step-by-Step (con Corridoi Size)")
            ax.legend()
            st.pyplot(fig)

        else:
            # Nessuna immagine di sfondo: disegno almeno i punti
            fig, ax = plt.subplots(figsize=(8,6))
            # Corridoi
            ax.scatter(df_corridoi["X"], df_corridoi["Y"], c='green', marker='o', label='Corridoio')
            # Macchine
            ax.scatter(df_macchine["X"], df_macchine["Y"], c='red', marker='s', label='Macchina')

            # Percorso
            xs = [p[2] for p in percorso]
            ys = [p[3] for p in percorso]
            ax.plot(xs, ys, color='blue', linewidth=2, marker='o', markersize=4)

            ax.set_title("Percorso Step-by-Step (con Corridoi Size)")
            ax.legend()
            st.pyplot(fig)

if __name__ == "__main__":
    main()



