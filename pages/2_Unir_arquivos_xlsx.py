import streamlit as st
import pandas as pd
import os

from src.utils import create_temp_xlsx_file


st.title("Unir Arquivos XLSX")

# Upload de arquivos XLSX
uploaded_files = st.file_uploader("Faça upload de arquivos .xlsx para unir:", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:
    st.info("Processando arquivos...")

    try:
        dfs = []
        filename = uploaded_files[0].name
        alvo = os.path.splitext(filename)[0]
        name_alvo = alvo.split('_')[0][1:]
        filename = uploaded_files[0].name
        
        for uploaded_file in uploaded_files:
            
            alvo = os.path.splitext(filename)[0]
            alvo = alvo.split('_')[0][1:]
            if alvo == name_alvo:
                df = pd.read_excel(uploaded_file)
                if 'Group Id' in df.columns:
                    df['Group Id'] = df['Group Id'].astype(str).fillna('')
                #dfs = pd.concat([dfs, df], ignore_index=True)
                dfs.append(df)
            else:
                st.error(f"Insira planilhas do mesmo alvo")

        if dfs:
            df_final = pd.concat(dfs, ignore_index=True)
            excel_file = create_temp_xlsx_file(df_final, f'{name_alvo}')

            col1, col2 = st.columns([1, 1])

            with col1:
                st.success("Arquivos unificados com sucesso!")

            with col2:
                st.download_button(
                    label="Download Arquivo Unificado",
                    data=excel_file,
                    file_name=f"{name_alvo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    except Exception as e:
        st.error(f"Ocorreu um erro ao unir os arquivos: {e}")