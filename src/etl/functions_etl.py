from bs4 import BeautifulSoup
from io import BytesIO
import pandas as pd
import zipfile, tempfile, os, requests, time



def create_temp_xlsx_file(df, name_file):
    
    excel_file = BytesIO()
    with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=name_file)
    excel_file.seek(0)

    return excel_file

def etl_bilhetagem(zip_file):

    #===================
    # 01. Ler o arquivo
    #===================
    
    
    records_file = extract_records_from_zip(zip_file)
    html = BeautifulSoup(records_file, 'html.parser')
    content = html.find('div',attrs={'id':'records'}) # seleciona o corpo da página, exclui o sidebar

    #==========================================================
    # 02. Extrair os dados para listas e fazer uma STRING única
    #==========================================================
    for page_break in content.find_all('div', class_='pageBreak'):
        page_break.decompose()

    child_list = [child.text for child in content]

    lines = [line for div in child_list for line in div.split('\n') if line] # linhas do arquivo

    text_content = ''
    for line in lines:
        text_content += line

    #encontrar e extrair os blocos
    account_identifier_list = extrai_blocos_mensagens(texto=text_content, palavra_chave='Account Identifier', stop_last_keyword='Account Type')
    account_identifier = account_identifier_list[0][len('Account Identifier'):]
    generated_list = extrai_blocos_mensagens(texto=text_content, palavra_chave='Generated',stop_last_keyword='Date Range')
    generated = generated_list[0][len('Generated'):]

    messages_list = extrai_blocos_mensagens(texto=text_content, palavra_chave='MessageTimestamp', stop_last_keyword='Call Logs Definition')

    palavras_chave = ['Message','Timestamp', 'Message Id', 'Sender', 'Recipients', 'Group Id', 'Sender Ip','Sender Port', 'Sender Device', 'Type', 'Message Style', 'Message Size']
    palavras_chave_sem_group_id = [item for item in palavras_chave if item != 'Group Id']

    sub_blocos = processa_bloco(messages_list, palavras_chave,palavras_chave_sem_group_id)

    # agrupa mensagens num dataframe
    df = pd.DataFrame(sub_blocos)
    
    if 'Message' in df.columns:
        df = df.drop('Message', axis=1)
    for col in df.columns:
        df[col] = df[col].str.replace('^'+col, '', regex=True)

    try:
        # converte a coluna para string por conta da conversão em notação científica
        df['Group Id'] = df['Group Id'].astype(str)
        # substitui as células 'nan' por células vazias
        df['Group Id'] = df['Group Id'].replace('nan','')
    except:
        pass
    
    # Criação da coluna UTC-3
    df = utc_to_utc_menos_3(df, coluna='Timestamp')
    # df['Timestamp UTC-3'] = df['Timestamp'].str[:-4]
    # df['Timestamp UTC-3'] = pd.to_datetime(df['Timestamp UTC-3'], format='%Y-%m-%d %H:%M:%S')
    # df['Timestamp UTC-3'] = df['Timestamp UTC-3'] - pd.Timedelta(hours=3)
    # df['Timestamp UTC-3'] = df['Timestamp UTC-3'].astype(str) + ' UTC-3'

    #===========================
    # 04. Consulta de provedores
    #===========================
    lista_ip_sender = df['Sender Ip'].unique()

    #verifica se há IP a consultar
    if len(lista_ip_sender) > 1:
        dict_ip_provedor = consulta_ips(lista_ip_sender)
        df['Provedor'] = df['Sender Ip'].map(dict_ip_provedor)

        #alterando a ordem das colunas
        if 'Timestamp' in df.columns:
            try:
                nova_ordem = ['Timestamp', 'Timestamp UTC-3', 'Message Id', 'Sender', 'Recipients', 'Group Id', 'Sender Ip', 'Sender Port', 'Provedor', 'Sender Device', 'Type', 'Message Style', 'Message Size']
                df = df[nova_ordem]
            except:
                nova_ordem = ['Timestamp', 'Timestamp UTC-3', 'Message Id', 'Sender', 'Recipients', 'Sender Ip', 'Sender Port', 'Provedor', 'Sender Device', 'Type', 'Message Style', 'Message Size']
                df = df[nova_ordem]

    # Criação da planilha
    #df.to_excel(os.path.join(output_path,account_identifier + '_' + generated[:10] + '.xlsx'), index=False)
    name_file = account_identifier + '_' + generated[:10]

    return df, name_file


def extract_records_from_zip(file):

    # cria arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        temp_file.write(file.read())
        temp_file_path = temp_file.name

    # extrair o arquivo records
    with zipfile.ZipFile(temp_file_path, 'r') as zip_file:
        if 'records.html' in zip_file.namelist():
            # extrair o records
            with zip_file.open('records.html') as records_file:
                content = records_file.read().decode('utf-8')
                return content
    
    os.remove(temp_file_path)


def extrai_blocos_mensagens(texto, palavra_chave, stop_last_keyword):
    #encontrar todas as posições das ocorrências da palavra chave
    pos = texto.find(palavra_chave)
    stop_last = texto.find(stop_last_keyword)

    # Retorna vazio se 'stop_last_keyword' não for encontrada
    if stop_last == -1:
        stop_last = len(texto)

    posições = []
    while pos != -1:
        posições.append(pos)
        pos = texto.find(palavra_chave, pos+1)
    
    #caso não haja registros
    if not posições:
        return ['No responsive records located']

    #extrair substrings com base nas posições
    blocos = []
    for i in range(len(posições)):
        start = posições[i]
        end = posições[i+1] if i+1 < len(posições) else stop_last
        blocos.append(texto[start:end])

    return blocos


def processa_bloco(blocos, palavras_chave, palavras_chave_sem_group_id):

        def divide_bloco(bloco, palavras_chave):
            sub_blocos = {}
            for i, palavra_chave in enumerate(palavras_chave):
                start = bloco.find(palavra_chave)
                if start != -1:
                    end = bloco.find(palavras_chave[i + 1], start) if i + 1 < len(palavras_chave) else len(bloco)
                    sub_blocos[palavra_chave] = bloco[start:end].strip()
                else:
                    sub_blocos[palavra_chave] = ''
            return sub_blocos

        blocos_processados = []
        for bloco in blocos:
            if 'Group Id' in bloco:
                blocos_processados.append(divide_bloco(bloco, palavras_chave))
            else:
                blocos_processados.append(divide_bloco(bloco, palavras_chave_sem_group_id))
        return blocos_processados


def utc_to_utc_menos_3(df, coluna):
    df['Timestamp UTC-3'] = df[coluna].str[:-4]
    df['Timestamp UTC-3'] = pd.to_datetime(df['Timestamp UTC-3'], format='%Y-%m-%d %H:%M:%S')
    df['Timestamp UTC-3'] = df['Timestamp UTC-3'] - pd.Timedelta(hours=3)
    df['Timestamp UTC-3'] = df['Timestamp UTC-3'].astype(str) + ' UTC-3'
    return df


def consulta_ips(ip_list):
    url = "http://ip-api.com/batch"

    def divide_em_blocos(lista, tamanho):
        for i in range(0,len(lista),tamanho):
            yield lista[i:i+tamanho]

    dict_ip_provedor = {}
    for ip_bloco in divide_em_blocos(ip_list,100):
        data = [{'query':ip, 'fields':'isp,city'} for ip in ip_bloco]

        try:
            response = requests.post(url,json=data)
            if response.status_code == 200:
                resposta = response.json()
            else:
                resposta = 'NULL'
        except requests.exceptions.RequestException as e:
            print('Error:',e)
            resposta = 'NULL'
        
        time.sleep(1.4) # ajuste de limit rate: 45/minuto
        for i in range(0,len(data)):
            dict_ip_provedor[data[i]['query']] = f'{resposta[i]["isp"]} - {resposta[i]["city"]}'
    
    return dict_ip_provedor
