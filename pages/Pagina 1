import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

def main():
    st.title("Caricamento dati da Excel e immagine di sfondo")

    # Caricamento del file Excel
    st.subheader("1. Carica il file Excel")
    excel_file = st.file_uploader(
        label="Scegli un file Excel",
        type=["xls", "xlsx"]
    )

    # Caricamento dell'immagine di sfondo
    st.subheader("2. Carica l'immagine di sfondo")
    bg_image_file = st.file_uploader(
        label="Scegli un'immagine (jpg, jpeg, png)",
        type=["jpg", "jpeg", "png"]
    )

    if excel_file is not None and bg_image_file is not None:
        # Leggi dati da Excel
        df = pd.read_excel(excel_file)

        # Converte X e Y in valori numerici
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Elimina eventuali righe che hanno NaN in X o Y
        df.dropna(subset=["X", "Y"], inplace=True)

        # Ordina il DataFrame in base alla colonna X
        df.sort_values(by="X", inplace=True)

        st.write("**Anteprima dei dati**")
        st.dataframe(df.head())  # Mostra le prime righe

        # Apri l'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Crea figura e assi per il grafico
        fig, ax = plt.subplots(figsize=(8, 6))

        # Calcola i limiti
        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        # Mostra immagine di sfondo (extent definisce l'area in coordinate)
        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto'
        )

        # Aggiunge i punti come scatter
        ax.scatter(df["X"], df["Y"], c='red', marker='o', label='Punti Excel')

        # Assi e titolo
        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafico con immagine di sfondo (ordinato per X)")

        ax.legend()

        st.pyplot(fig)

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")


if __name__ == "__main__":
    main()

