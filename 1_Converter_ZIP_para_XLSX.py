import os
import streamlit as st

from src.etl.functions_etl import etl_bilhetagem, create_temp_xlsx_file



current_dir = os.getcwd()

# Configurações da página no Streamlit
st.set_page_config(page_title="Análise de Bilhetagem", page_icon = f'{current_dir}/src/media/icone.png')

st.title("Converter Arquivos ZIP para XLSX")

# Instruções para o usuário
st.write("""
Este aplicativo permite que você faça o upload de arquivos `.zip` contendo os dados de bilhetagem diários. 
Os arquivos serão descompactados e convertidos em um arquivo `.xlsx`. 
""")

if 'arquivos_convertidos' not in st.session_state:
    st.session_state.arquivos_convertidos = {}

# Seção de upload
uploaded_files = st.file_uploader("Faça upload de um arquivo .zip:", type=["zip"], accept_multiple_files=True)

if uploaded_files:
    st.info("Extraindo arquivos...")
    col1, col2, col3 = st.columns([2, 2, 1])  # Ajustando proporções das colunas
    col1.write("📂 **Arquivo Original**")
    col2.write("📑 **Arquivo Convertido (.xlsx)**")
    col3.write("📥 **Download**")

    st.markdown("---")


    try:
        # Extrair arquivos do .zip
        for idx, uploaded_file in enumerate(uploaded_files):
            if uploaded_file.name in st.session_state.arquivos_convertidos:
                name_file, excel_file = st.session_state.arquivos_convertidos[uploaded_file.name]
            else:
                df, name_file = etl_bilhetagem(uploaded_file)

                excel_file = create_temp_xlsx_file(df, name_file)

                # Salvar no session_state para evitar reconversão
                st.session_state.arquivos_convertidos[uploaded_file.name] = (name_file, excel_file)

            # Criar uma linha com nome do arquivo e botão de download
            col1, col2, col3 = st.columns([2, 2, 1])

            col1.text(uploaded_file.name)  # Nome do arquivo original

            col2.text(name_file)  # Nome do arquivo convertido
            
            col3.download_button(
                    label="Download",
                    data=excel_file,
                    file_name=f"{name_file}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f'download_{idx}'
                )
            
            st.markdown("---")  # Linha horizontal abaixo do cabeçalho

    except Exception as e:
        st.error(f"Ocorreu um erro durante o processamento: {e}")

