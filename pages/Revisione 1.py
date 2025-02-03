import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

def main():
    st.title("Caricamento dati da Excel, filtro e grafico con immagine di sfondo")

    # 1. Caricamento file Excel
    excel_file = st.file_uploader(
        label="Scegli un file Excel",
        type=["xls", "xlsx"]
    )

    # 2. Caricamento dell'immagine di sfondo
    bg_image_file = st.file_uploader(
        label="Scegli un'immagine (jpg, jpeg, png)",
        type=["jpg", "jpeg", "png"]
    )

    if excel_file is not None and bg_image_file is not None:
        # Leggi i dati da Excel
        # Se usi virgola come decimale e punto come separatore migliaia, decommenta decimal=',' e thousands='.'
        df = pd.read_excel(
            excel_file,
            # decimal=',',   # decommenta se i decimali sono scritti con la virgola
            # thousands='.'  # decommenta se i separatori di migliaia sono i punti
        )

        # Mostra tipologie delle colonne e anteprima
        st.subheader("Tipi di dati delle colonne:")
        st.write(df.dtypes)
        st.subheader("Anteprima dei dati:")
        st.dataframe(df.head())

        # Assicurati che esistano le colonne "X" e "Y"
        if "X" not in df.columns or "Y" not in df.columns:
            st.error("Errore: il file Excel deve contenere colonne 'X' e 'Y'.")
            return

        # 3. Converte "X" e "Y" in valori numerici
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Elimina righe con NaN in X o Y
        df.dropna(subset=["X", "Y"], inplace=True)

        # Se vuoi filtrare su un range di valori per X e Y, ad esempio:
        # (Decommenta e imposta i range che ti servono)
        # df = df[(df["X"] >= 0) & (df["X"] <= 1000)]
        # df = df[(df["Y"] >= 0) & (df["Y"] <= 1000)]

        # Se dopo i filtri non restano righe, avvisa e interrompi
        if df.empty:
            st.warning("Nessun dato valido da visualizzare dopo il filtro.")
            return

        # 4. Apertura dell'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Creazione del grafico
        fig, ax = plt.subplots(figsize=(8, 6))

        # Calcoliamo i limiti per extent (per sovrapporre l'immagine)
        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        # Mostra l'immagine come sfondo
        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto',    # oppure 'equal' se vuoi mantenere il rapporto originale
            origin='upper'    # usa 'lower' se vuoi invertire l'asse Y
        )

        # Disegna i punti
        ax.scatter(df["X"], df["Y"], c='red', marker='o', label='Punti Excel')

        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafico con immagine di sfondo e filtro dati")
        ax.legend()

        st.pyplot(fig)

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")

if __name__ == "__main__":
    main()

