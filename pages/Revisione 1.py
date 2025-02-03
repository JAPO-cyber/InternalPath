import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

def main():
    st.title("Caricamento dati da Excel e immagine di sfondo (senza filtri)")

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
        # Legge il file Excel
        # Se i dati hanno la virgola come separatore decimale, decommenta decimal=',' e thousands='.'
        df = pd.read_excel(
            excel_file,
            # decimal=',',
            # thousands='.'
        )

        # Mostra tipologie delle colonne e anteprima
        st.subheader("Tipi di dati delle colonne:")
        st.write(df.dtypes)
        st.subheader("Anteprima dei dati:")
        st.dataframe(df.head())

        # Controlla che esistano le colonne X e Y
        if "X" not in df.columns or "Y" not in df.columns:
            st.error("Errore: il file Excel deve contenere colonne 'X' e 'Y'.")
            return

        # Converte "X" e "Y" in valori numerici (senza eliminare nulla)
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Apri l'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Crea il grafico
        fig, ax = plt.subplots(figsize=(8, 6))

        # Calcola i limiti per extent (potrebbero essere NaN se la colonna è vuota/illeggibile)
        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        # Se i limiti sono tutti NaN, non possiamo disegnare il grafico
        if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
            st.warning("Non è stato possibile determinare i limiti (X, Y) dal file. Controlla che i dati siano numerici.")
            return

        # Mostra l'immagine come sfondo
        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto',
            origin='upper'
        )

        # Disegna i punti (potrebbero esserci NaN in X o Y, ma matplotlib li ignora)
        ax.scatter(df["X"], df["Y"], c='red', marker='o', label='Punti Excel')

        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafico con immagine di sfondo (nessun filtro)")
        ax.legend()

        st.pyplot(fig)

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")


if __name__ == "__main__":
    main()

