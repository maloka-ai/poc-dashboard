from datetime import datetime
import pandas as pd
import dotenv
import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import warnings
import psycopg2

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

dotenv.load_dotenv()
# Nome do arquivo com timestamp para evitar sobrescrever arquivos anteriores
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# Configuração da conexão
try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("DB_HOST"),
        database="add",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS"),
        port= os.getenv("DB_PORT")
    )
    
    print("Conexão estabelecida com sucesso!")
    
    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela vendas...")
    query = "SELECT * FROM maloka_core.venda"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_vendas = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_vendas)
    num_colunas = len(df_vendas.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_vendas.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_vendas.head())
    
    # Exportar para Excel
    # df_vendas.to_excel("df_vendas.xlsx", index=False)

    ########################################################
    # consulta da tabela clientes
    ########################################################

    print("Consultando a tabela cliente...")
    query = "SELECT * FROM maloka_core.cliente"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_clientes = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_vendas)
    num_colunas = len(df_clientes.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_clientes.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_clientes.head())

    # df_clientes.to_excel("df_clientes.xlsx", index=False)

    ########################################################
    # consulta da tabela venda_itens
    ########################################################
    
    print("Consultando a tabela venda_item...")
    query = "SELECT * FROM maloka_core.venda_item"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_venda_itens = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_venda_itens)
    num_colunas = len(df_venda_itens.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_venda_itens.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_venda_itens.head())
    
    # Exportar para Excel
    # df_venda_itens.to_excel("df_venda_itens.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")

########################################################
# Crescimento Anual de vendas 
########################################################

# Converter data_venda para datetime e criar coluna Ano
df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
df_vendas['Ano'] = df_vendas['data_venda'].dt.year

# Certifique-se de que total_venda seja numérico
df_vendas['total_venda'] = pd.to_numeric(df_vendas['total_venda'], errors='coerce')

# Agrupar por Ano para obter o faturamento total anual (sem distinção de tipo)
df_anual = df_vendas.groupby(['Ano'])['total_venda'].sum().reset_index()
df_anual.rename(columns={'total_venda': 'Total'}, inplace=True)

# Calcular a evolução percentual anual
df_anual['Evolução Total (%)'] = df_anual['Total'].pct_change() * 100

# Adicionar contagem de vendas (quantidade de itens)
df_contagem = df_vendas.groupby(['Ano']).size().reset_index(name='Qtd Produtos')

# Adicionar as contagens ao dataframe de faturamento
df_anual = df_anual.merge(df_contagem, on='Ano', how='left')

# Contar o número de vendas distintas por ano
df_vendas_por_ano = df_vendas.groupby('Ano').size().reset_index(name='Qtd Vendas')

# Adicionar a contagem de vendas ao dataframe de análise anual
df_anual = df_anual.merge(df_vendas_por_ano, on='Ano', how='left')

#Calculo do ticket médio
df_anual['Ticket Médio Anual'] = df_anual['Total'] / df_anual['Qtd Vendas']

#Evolução do ticket médio
df_anual['Evolução Ticket Médio (%)'] = df_anual['Ticket Médio Anual'].pct_change() * 100

# Exportar os dados para um arquivo Excel
df_anual.to_excel(os.path.join(diretorio_atual, 'faturamento_anual.xlsx'), index=False)
print(df_anual.head())

########################################################
# Fatuarmento Anual - Geral (Cadastrado vs Sem Cadastro)
########################################################

# Criar a coluna Ano
df_vendas['Ano'] = df_vendas['data_venda'].dt.year

# Mesclar df_vendas com df_clientes para trazer a coluna 'tipo_cliente'
df_vendas_com_tipo = df_vendas.merge(df_clientes[['id_cliente', 'tipo']], on='id_cliente', how='left')

# Classificamos corretamente baseado no tipo do cliente
df_vendas_com_tipo['grupo_cliente'] = df_vendas_com_tipo['tipo'].apply(
    lambda tipo: 'Cadastrado' if tipo in ['F', 'J'] else 'Sem Cadastro'
)

# Agregar os dados por Ano e grupo de cliente
df_ano_group = df_vendas_com_tipo.groupby(['Ano', 'grupo_cliente'])['total_venda'].sum().unstack(fill_value=0)

# Resetar o índice para incluir 'Ano' como uma coluna no arquivo exportado
df_ano_group.reset_index(inplace=True)

# Exportar os dados para um arquivo Excel
df_ano_group.to_excel(os.path.join(diretorio_atual, 'faturamento_anual_geral.xlsx'), index=False)

########################################################
# Fatuarmento mensal por ano
########################################################

df_vendas['Mês'] = df_vendas['data_venda'].dt.month
# Agrupar por Ano e Mês somando o total_item
df_pivot = df_vendas.groupby(['Ano', 'Mês'])['total_venda'].sum().reset_index()
df_pivot = df_pivot.pivot(index='Mês', columns='Ano', values='total_venda')
df_pivot.reset_index(inplace=True)
df_pivot.to_excel(os.path.join(diretorio_atual, 'faturamento_mensal.xlsx'), index=False)

########################################################
# Faturamento diário no mês atual e 3 meses anteriores
########################################################

# Obter a data atual
data_atual = pd.Timestamp.now()
mes_atual = data_atual.month
ano_atual = data_atual.year

# Criar uma lista para armazenar os DataFrames de cada mês
dfs_mensais = []

# Processar mês atual e 3 meses anteriores
for i in range(4):
    # Calcular o mês e ano de referência
    mes_ref = mes_atual - i
    ano_ref = ano_atual
    
    # Ajustar o ano se necessário (quando o mês for negativo)
    if mes_ref <= 0:
        mes_ref += 12
        ano_ref -= 1
    
    # Filtrar os dados para o mês e ano em questão
    mask = (df_vendas['data_venda'].dt.month == mes_ref) & (df_vendas['data_venda'].dt.year == ano_ref)
    df_mes = df_vendas[mask].copy()
    
    # Se não houver dados, continuar para o próximo mês
    if df_mes.empty:
        print(f"Não há dados para {mes_ref}/{ano_ref}")
        continue
    
    # Criar coluna para dia do mês
    df_mes['Dia'] = df_mes['data_venda'].dt.day
    
    # Agrupar por dia e calcular o faturamento diário
    df_diario = df_mes.groupby('Dia')['total_venda'].sum().reset_index()
    
    # Adicionar colunas de mês e ano
    df_diario['Mês'] = mes_ref
    df_diario['Ano'] = ano_ref
    df_diario['Período'] = f"{mes_ref:02d}/{ano_ref}"
    
    # Adicionar à lista de DataFrames
    dfs_mensais.append(df_diario)

# Combinar todos os DataFrames
if dfs_mensais:
    df_faturamento_diario = pd.concat(dfs_mensais, ignore_index=True)
    
    # Salvar em Excel
    excel_path = os.path.join(diretorio_atual, 'faturamento_diario.xlsx')
    df_faturamento_diario.to_excel(excel_path, index=False)
    print(f"Dados de faturamento diário salvos em: {excel_path}")
    print(df_faturamento_diario.head(15))
else:
    print("Não há dados para gerar análise de faturamento diário.")
