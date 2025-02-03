import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

def main():
    st.title("Caricamento dati da Excel e immagine di sfondo")

    excel_file = st.file_uploader(
        label="Scegli un file Excel",
        type=["xls", "xlsx"]
    )
    bg_image_file = st.file_uploader(
        label="Scegli un'immagine (jpg, jpeg, png)",
        type=["jpg", "jpeg", "png"]
    )

    if excel_file is not None and bg_image_file is not None:
        # Esempio: se i tuoi dati usano la virgola come separatore decimale
        # e il punto per le migliaia, abilita decimal=',' e thousands='.'
        df = pd.read_excel(
            excel_file,
            decimal=',',
            thousands='.'
        )

        # Forza la conversione delle colonne X e Y a valori numerici
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Mostra i tipi di colonna per controllo
        st.write("Tipi di dati delle colonne:", df.dtypes)

        st.write("**Anteprima dei dati**")
        st.dataframe(df.head())

        # Apri l'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Crea il grafico
        fig, ax = plt.subplots(figsize=(8, 6))

        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        # Inserisci l'immagine come sfondo
        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto',
            origin='upper'  # oppure 'lower' se preferisci invertire l'asse Y
        )

        # Traccia i punti
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

