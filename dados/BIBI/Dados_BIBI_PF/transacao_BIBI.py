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

# Primeiro, vamos preparar os dados de venda_itens
df_venda_itens['tipo'] = df_venda_itens['tipo'].fillna('N/A')  # Tratando possíveis valores nulos

# Mesclar df_vendas com df_venda_itens para obter as informações de tipo
# Precisamos primeiro adicionar a data e o ano às vendas de itens
df_venda_itens_com_data = df_venda_itens.merge(
    df_vendas[['id_venda', 'data_venda']], 
    on='id_venda', 
    how='left'
)

# Converter data_venda para datetime e criar coluna Ano
df_venda_itens_com_data['data_venda'] = pd.to_datetime(df_venda_itens_com_data['data_venda'])
df_venda_itens_com_data['Ano'] = df_venda_itens_com_data['data_venda'].dt.year

# Certifique-se de que total_item seja numérico
df_venda_itens_com_data['total_item'] = pd.to_numeric(df_venda_itens_com_data['total_item'], errors='coerce')

# Agrupar por Ano e tipo (Serviço ou Produto)
df_anual_por_tipo = df_venda_itens_com_data.groupby(['Ano', 'tipo'])['total_item'].sum().unstack(fill_value=0)

# Verificar se as colunas 'S' e 'P' existem, senão criar
if 'S' not in df_anual_por_tipo.columns:
    df_anual_por_tipo['S'] = 0
if 'P' not in df_anual_por_tipo.columns:
    df_anual_por_tipo['P'] = 0

# Renomear as colunas para melhor clareza
df_anual_por_tipo.rename(columns={'S': 'Serviços', 'P': 'Produtos'}, inplace=True)

# Calcular o total para cada ano
df_anual_por_tipo['Total'] = df_anual_por_tipo.sum(axis=1)

# Calcular as porcentagens
for col in ['Serviços', 'Produtos']:
    if col in df_anual_por_tipo.columns:
        df_anual_por_tipo[f'{col} (%)'] = (df_anual_por_tipo[col] / df_anual_por_tipo['Total']) * 100

# Calcular a evolução percentual anual para cada categoria
for col in ['Serviços', 'Produtos', 'Total']:
    if col in df_anual_por_tipo.columns:
        df_anual_por_tipo[f'Evolução {col} (%)'] = df_anual_por_tipo[col].pct_change() * 100

# Adicionar contagem de vendas por tipo de produto (quantidade de itens)
df_contagem_por_tipo = df_venda_itens_com_data.groupby(['Ano', 'tipo']).size().unstack(fill_value=0)

# Verificar se as colunas 'S' e 'P' existem, senão criar
if 'S' not in df_contagem_por_tipo.columns:
    df_contagem_por_tipo['S'] = 0
if 'P' not in df_contagem_por_tipo.columns:
    df_contagem_por_tipo['P'] = 0

# Renomear as colunas para melhor clareza
df_contagem_por_tipo.rename(columns={'S': 'Qtd Serviços', 'P': 'Qtd Produtos'}, inplace=True)

# Resetar o índice para incluir 'Ano' como uma coluna
df_anual_por_tipo.reset_index(inplace=True)

# Adicionar as contagens ao dataframe de faturamento
df_anual_por_tipo = df_anual_por_tipo.merge(df_contagem_por_tipo, on='Ano', how='left')

# Calcular o total de itens por ano
df_anual_por_tipo['Total Itens'] = df_anual_por_tipo[['Qtd Serviços', 'Qtd Produtos']].sum(axis=1)


# Exportar os dados para um arquivo Excel
df_anual_por_tipo.to_excel(os.path.join(diretorio_atual, 'faturamento_anual.xlsx'), index=False)
print(df_anual_por_tipo.head())

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
# Faturamento por loja por ano
########################################################

anos_disponiveis = sorted(df_vendas['Ano'].unique())
lojas_disponiveis = sorted(df_vendas['id_loja_fisica'].unique())

print(f"Gerando gráficos de faturamento para os anos: {anos_disponiveis}")
print(f"Lojas disponíveis: {lojas_disponiveis}")

# Criar um DataFrame para consolidar todos os dados
df_consolidado = pd.DataFrame()

# Para cada ano, processamos os dados e os consolidamos
for ano in anos_disponiveis:
    # Filtrar as vendas para o ano e para as lojas disponíveis
    df_ano = df_vendas[(df_vendas['Ano'] == ano) & (df_vendas['id_loja_fisica'].isin(lojas_disponiveis))].copy()
    
    # Verificar se há dados para este ano
    if df_ano.empty:
        print(f"Não há dados para o ano {ano}")
        continue
    
    # Agrupar por Mês e id_loja, somando o total_venda
    df_mensal = df_ano.groupby(['Mês', 'id_loja_fisica'])['total_venda'].sum().reset_index()
    
    # Adicionar coluna de Ano ao DataFrame
    df_mensal['Ano'] = ano
    
    # Anexar ao DataFrame consolidado
    df_consolidado = pd.concat([df_consolidado, df_mensal], ignore_index=True)
    
    # Criar uma tabela pivot para o gráfico: índice = Mês e colunas = id_loja
    df_pivot = df_mensal.pivot(index='Mês', columns='id_loja_fisica', values='total_venda')
    
    # Plotar o gráfico de barras agrupadas
    plt.figure(figsize=(12, 7))
    ax = df_pivot.plot(kind='bar', ax=plt.gca())
    plt.title(f'Faturamento Mensal - Ano {ano}')
    plt.xlabel('Mês')
    plt.ylabel('Faturamento (R$)')
    plt.xticks(rotation=0)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Loja')
    
    # Adicionar rótulos em cada barra com o valor correspondente
    for container in ax.containers:
        ax.bar_label(container, fmt='R$%.0f', fontsize=8, label_type='edge')
    
    plt.tight_layout()
    plt.savefig(os.path.join(diretorio_atual, f'faturamento_mensal_{ano}.png'))
    plt.close()

# Salvar o DataFrame consolidado em um único arquivo Excel
if not df_consolidado.empty:
    excel_path = os.path.join(diretorio_atual, 'faturamento_mensal_lojas.xlsx')
    df_consolidado.to_excel(excel_path, index=False)
    print(f"Dados de faturamento consolidados salvos em: {excel_path}")
else:
    print("Não há dados para gerar o arquivo Excel consolidado.")
