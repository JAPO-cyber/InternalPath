import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image

def main():
    st.title("Caricamento dati da Excel e immagine di sfondo (sostituzione ' m' con null)")

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
        # Se hai bisogno di gestire separatori decimali/migliaia, decommenta e imposta.
        df = pd.read_excel(
            excel_file,
            # decimal=',',    # se i decimali nel tuo file Excel usano la virgola
            # thousands='.'   # se usi il punto per le migliaia
        )

        # Mostra tipologie delle colonne e anteprima (prima di modifiche)
        st.subheader("Tipi di dati delle colonne (prima delle modifiche):")
        st.write(df.dtypes)
        st.subheader("Anteprima dei dati (prima delle modifiche):")
        st.dataframe(df.head())

        # Assicuriamoci che esistano le colonne "X" e "Y"
        if "X" not in df.columns or "Y" not in df.columns:
            st.error("Errore: il file Excel deve contenere colonne 'X' e 'Y'.")
            return

        # --- SOSTITUZIONE ' m' CON VALORE NULL (None) PRIMA DELLA CONVERSIONE ---
        # Se troviamo la sottostringa " m" in una cella di X o Y, sostituiamo con None.
        df["X"] = df["X"].apply(lambda v: None if isinstance(v, str) and ' m' in v else v)
        df["Y"] = df["Y"].apply(lambda v: None if isinstance(v, str) and ' m' in v else v)
        # ------------------------------------------------------------------------

        # Converte "X" e "Y" in valori numerici (i None diventeranno NaN)
        df["X"] = pd.to_numeric(df["X"], errors="coerce")
        df["Y"] = pd.to_numeric(df["Y"], errors="coerce")

        # Mostra i dati dopo la sostituzione e la conversione
        st.subheader("Tipi di dati delle colonne (dopo le modifiche):")
        st.write(df.dtypes)
        st.subheader("Anteprima dei dati (dopo le modifiche):")
        st.dataframe(df.head())

        # Apri l'immagine di sfondo
        bg_image = Image.open(bg_image_file)

        # Crea il grafico
        fig, ax = plt.subplots(figsize=(8, 6))

        # Calcola i limiti per extent (potrebbero essere NaN se tutte le celle sono invalide)
        x_min, x_max = df["X"].min(), df["X"].max()
        y_min, y_max = df["Y"].min(), df["Y"].max()

        if pd.isna(x_min) or pd.isna(x_max) or pd.isna(y_min) or pd.isna(y_max):
            st.warning("Non è stato possibile determinare i limiti (X, Y). Verifica che i dati siano numerici.")
            return

        # Mostra l'immagine come sfondo
        ax.imshow(
            bg_image,
            extent=[x_min, x_max, y_min, y_max],
            aspect='auto',
            origin='upper'
        )

        # Disegna i punti (Matplotlib ignora automaticamente le righe con NaN)
        ax.scatter(df["X"], df["Y"], c='red', marker='o', label='Punti Excel')

        ax.set_xlabel("Coordinata X")
        ax.set_ylabel("Coordinata Y")
        ax.set_title("Grafico con immagine di sfondo (sostituzione ' m' con null)")
        ax.legend()

        st.pyplot(fig)

    else:
        st.write("Carica sia il file Excel che l'immagine di sfondo per continuare.")

if __name__ == "__main__":
    main()


