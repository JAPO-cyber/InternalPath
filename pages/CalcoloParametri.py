import streamlit as st
import pandas as pd
import numpy as np
import io

st.title("AHP per la Biodiversità")
st.write("Questa app permette di selezionare indicatori per ogni macrofamiglia e confrontarli tramite AHP.")

# 1. Creazione del DataFrame di esempio
data = [
    {'Macrofamiglia': 'Mammiferi', 'Indicatore': 'Diversità delle specie'},
    {'Macrofamiglia': 'Mammiferi', 'Indicatore': 'Abbondanza'},
    {'Macrofamiglia': 'Uccelli', 'Indicatore': 'Varietà delle specie'},
    {'Macrofamiglia': 'Uccelli', 'Indicatore': 'Numero di nidi'},
    {'Macrofamiglia': 'Rettili', 'Indicatore': 'Distribuzione geografica'},
    {'Macrofamiglia': 'Rettili', 'Indicatore': 'Percentuale specie a rischio'},
    {'Macrofamiglia': 'Anfibi', 'Indicatore': 'Popolazione stanziale'},
    {'Macrofamiglia': 'Anfibi', 'Indicatore': 'Indicatori qualità dell’acqua'},
    {'Macrofamiglia': 'Insetti', 'Indicatore': 'Indice di biodiversità'},
    {'Macrofamiglia': 'Insetti', 'Indicatore': 'Frequenza di apparizione'}
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
    # Inizializza la matrice AHP: diagonale uguale a 1
    comparison_matrix = np.ones((n, n))
    
    # Per ogni coppia (i, j) con i < j, chiedi all’utente il confronto
    for i in range(n):
        for j in range(i+1, n):
            indic_i = all_selected[i]
            indic_j = all_selected[j]
            question = (f"Confronta '{indic_i}' vs '{indic_j}':\n"
                        "Seleziona l'opzione che descrive meglio il rapporto di importanza:")
            option = st.radio(
                question,
                (
                    "Sono equamente importanti",
                    f"'{indic_i}' è poco più importante di '{indic_j}'",
                    f"'{indic_i}' è abbastanza più importante di '{indic_j}'",
                    f"'{indic_i}' è decisamente più importante di '{indic_j}'",
                    f"'{indic_i}' è assolutamente più importante di '{indic_j}'"
                ),
                key=f"{i}_{j}"
            )
            # Mappa le risposte ai valori numerici
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

    st.subheader("Matrice di confronto AHP")
    st.write(comparison_matrix)
    
    # 4. Calcolo dei pesi relativi usando il metodo degli autovalori
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

    # 5. Bottone per scaricare i dati in formato Excel
    # Salvataggio in memoria del DataFrame in un file Excel
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

    # Salvataggio del file Excel sul disco (nella stessa directory del codice)
    weights_df.to_excel('ahp_weights.xlsx', index=False)


