import streamlit as st
import pandas as pd
import numpy as np
import io

st.title("AHP per la Biodiversità")
st.write("Questa app permette di selezionare indicatori per ogni macrofamiglia e confrontarli tramite AHP.")

# 0. Caricamento opzionale del dataframe da file Excel
uploaded_file = st.file_uploader("Carica un file Excel con i dati (opzionale)", type=["xlsx"])
if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("File caricato con successo!")
    except Exception as e:
        st.error("Errore nel caricamento del file: " + str(e))
        df = None
if uploaded_file is None or df is None:
    # 1. Creazione del DataFrame di default
    data = [
        {'Macrofamiglia': 'Da definire', 'Indicatore': 'Biodiversità'},
        {'Macrofamiglia': 'Da definire', 'Indicatore': 'Copertura vegetale'},
        {'Macrofamiglia': 'Da definire', 'Indicatore': 'Permeabilità'},
        {'Macrofamiglia': 'Da definire', 'Indicatore': 'Servizi'},
        {'Macrofamiglia': 'Da definire', 'Indicatore': 'Tutela'}
    ]
    df = pd.DataFrame(data)

st.subheader("Dati di base")
st.dataframe(df)

# 2. Selezione degli indicatori per ogni macrofamiglia
macrofamiglie = df['Macrofamiglia'].unique()
selected_indicators = {}

st.subheader("Selezione degli indicatori per ogni macrofamiglia")
for macro in macrofamiglie:
    indicators = df[df['Macrofamiglia'] == macro]['Indicatore'].tolist()
    selected = st.multiselect(f"Seleziona indicatori per {macro}:", indicators, default=indicators)
    selected_indicators[macro] = selected

# Combina tutti gli indicatori selezionati (evitando duplicati)
all_selected = list({indic for sublist in selected_indicators.values() for indic in sublist})
st.write("Indicatori selezionati:", all_selected)

# 3. Confronto AHP tra indicatori (se ne sono stati selezionati almeno 2)
if len(all_selected) > 1:
    st.header("Confronto AHP")
    n = len(all_selected)
    # Inizializza la matrice AHP con la diagonale uguale a 1
    comparison_matrix = np.ones((n, n))
    
    # Creiamo un form per raccogliere le risposte
    with st.form("ahp_form"):
        responses = {}
        st.write("Per ciascuna coppia, espandi la sezione e seleziona il rapporto di importanza.")
        for i in range(n):
            for j in range(i+1, n):
                indic_i = all_selected[i]
                indic_j = all_selected[j]
                with st.expander(f"Confronta '{indic_i}' vs '{indic_j}'", expanded=False):
                    option = st.radio(
                        "Seleziona l'opzione che descrive meglio il rapporto di importanza:",
                        (
                            "Sono equamente importanti",
                            f"'{indic_i}' è poco più importante di '{indic_j}'",
                            f"'{indic_i}' è abbastanza più importante di '{indic_j}'",
                            f"'{indic_i}' è decisamente più importante di '{indic_j}'",
                            f"'{indic_i}' è assolutamente più importante di '{indic_j}'"
                        ),
                        index=0,
                        key=f"{i}_{j}"
                    )
                    responses[f"{i}_{j}"] = option
        submit = st.form_submit_button("Calcola Pesi")
    
    if submit:
        # Costruzione della matrice di confronto AHP basata sulle risposte
        for i in range(n):
            for j in range(i+1, n):
                option = responses[f"{i}_{j}"]
                if option == "Sono equamente importanti":
                    value = 1
                elif "poco più importante" in option:
                    value = 3
                elif "abbastanza più importante" in option:
                    value = 5
                elif "decisamente più importante" in option:
                    value = 7
                elif "assolutamente più importante" in option:
                    value = 9
                else:
                    value = 1
                comparison_matrix[i, j] = value
                comparison_matrix[j, i] = 1 / value
        
        # Creazione di un DataFrame per la matrice con etichette su righe e colonne
        matrix_df = pd.DataFrame(comparison_matrix, index=all_selected, columns=all_selected)
        st.subheader("Matrice di confronto AHP")
        st.dataframe(matrix_df)
        
        # 4. Calcolo dei pesi relativi tramite il metodo degli autovalori
        eigenvalues, eigenvectors = np.linalg.eig(comparison_matrix)
        max_index = np.argmax(eigenvalues.real)
        weights = eigenvectors[:, max_index].real
        weights = weights / np.sum(weights)  # normalizza i pesi
        
        weights_df = pd.DataFrame({
            'Indicatore': all_selected,
            'Peso Relativo': weights
        })
        st.subheader("Pesi relativi calcolati")
        st.dataframe(weights_df)
        
        # 5. Creazione del file Excel per il download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            weights_df.to_excel(writer, index=False, sheet_name='AHP_Weights')
        excel_data = output.getvalue()
        
        st.download_button(
            label="Scarica i dati AHP (Excel)",
            data=excel_data,
            file_name="ahp_weights.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Salvataggio locale del file Excel
        weights_df.to_excel('ahp_weights.xlsx', index=False)



