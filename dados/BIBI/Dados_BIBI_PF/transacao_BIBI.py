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
        database="bibicell",
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

df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
df_vendas['total_venda'] = pd.to_numeric(df_vendas['total_venda'], errors='coerce')

# Criar a coluna Ano
df_vendas['Ano'] = df_vendas['data_venda'].dt.year

# Agregar os dados por Ano, somando o total de vendas
df_anual = df_vendas.groupby('Ano')['total_venda'].sum().reset_index()

# Calcular a evolução percentual anual (variação de um ano para o outro)
df_anual['Evolucao (%)'] = df_anual['total_venda'].pct_change() * 100

# Renomear a coluna total_venda para total_item para compatibilidade com o dashboard
df_anual.rename(columns={'total_venda': 'total_item'}, inplace=True)

# Exportar os dados para um arquivo Excel
df_anual.to_excel(os.path.join(diretorio_atual, 'faturamento_anual.xlsx'), index=False)

########################################################
# Fatuarmento Anual - Geral (Cadastrado vs Sem Cadastro)
########################################################


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
# Fatuarmento por loja por ano
########################################################

# # Definir os anos e as lojas de interesse
# anos = [2020, 2021, 2022, 2023, 2024]
# #anos = [2023, 2024]
# #lojas = [3, 4]
# lojas = [1, 2, 3, 4]

# # Para cada ano, cria um gráfico de barras agrupadas, onde cada grupo (mês)
# # tem uma barra para cada loja
# for ano in anos:
#     # Filtrar as vendas para o ano e para as lojas selecionadas
#     df_ano = df_vendas[(df_vendas['Ano'] == ano) & (df_vendas['id_loja'].isin(lojas))].copy()
    
#     # Agrupar por Mês e id_loja, somando o total_venda
#     df_mensal = df_ano.groupby(['Mês', 'id_loja'])['total_venda'].sum().reset_index()
    
#     # Criar uma tabela pivot: índice = Mês e colunas = id_loja
#     df_pivot = df_mensal.pivot(index='Mês', columns='id_loja', values='total_venda')
    
#     # Plotar o gráfico de barras agrupadas
#     plt.figure(figsize=(10, 6))
#     ax = df_pivot.plot(kind='bar', ax=plt.gca())
#     plt.title(f'Faturamento Mensal - Ano {ano}')
#     plt.xlabel('Mês')
#     plt.ylabel('Faturamento (R$)')
#     plt.xticks(rotation=0)
#     plt.grid(axis='y', linestyle='--', alpha=0.7)
#     plt.legend(title='Loja')
    
#     # Adicionar rótulos em cada barra com o valor correspondente
#     for container in ax.containers:
#         ax.bar_label(container, fmt='R$%.2f', label_type='edge')
    
#     plt.tight_layout()
#     plt.show()
