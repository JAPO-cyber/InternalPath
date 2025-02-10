import streamlit as st

# Definizione del contenuto del file CSV (in formato testo)
csv_content = """X,Y,Tag,Entity Name,Size
10,10,Macchina,M1,
20,10,Corridoio,Corridoio1,destro
30,10,Corridoio,Corridoio2,destro
40,10,Macchina,M2,
10,20,Macchina,M3,
10,30,Corridoio,Corridoio3,alto
10,40,Macchina,M4,
30,30,Corridoio,Corridoio4,sinistro
40,40,Macchina,M5,
"""

st.title("Download CSV di Input")

st.write("Clicca sul pulsante qui sotto per scaricare il file CSV di input con tutte le caratteristiche richieste:")

# Pulsante di download: quando cliccato, il file CSV verrà scaricato
st.download_button(
    label="Scarica CSV di input",
    data=csv_content,
    file_name="input.csv",
    mime="text/csv"
)
