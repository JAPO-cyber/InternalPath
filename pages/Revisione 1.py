import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
import io

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

    # Elaborazione dopo aver caricato entrambi
    if excel_file is not None and bg_image_file is not None:
        # Leggi dati da Excel
        # Assicurati che le colonne richieste esistano nel foglio
        df = pd.read_excel(excel_file)

        st.write("**Anteprima dei dati**")
        st.dataframe(df.head())  # Mostra le prime righe

        # Con Pil apriamo l'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Prepariamo la figura e gli assi per il grafico
        fig, ax = plt.subplots(figsize=(8, 6))

        # Inseriamo l'immagine come sfondo.
        # extent definisce l'area (in coordinate x e y) che l'immagine occuperà.
        # Per semplicità, imposteremo:
        #   xmin = min(X), xmax = max(X)
        #   ymin = min(Y), ymax = max(Y)
        # oppure valori costanti se preferiamo uno scaling fisso.
        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto'
        )

        # Ora aggiungiamo i punti in base alle coordinate (X, Y)
        ax.scatter(df["X"], df["Y"], c='red', marker='o', label='Punti Excel')

        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafico con immagine di sfondo")

        ax.legend()

        st.pyplot(fig)

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")


if __name__ == "__main__":
    main()
