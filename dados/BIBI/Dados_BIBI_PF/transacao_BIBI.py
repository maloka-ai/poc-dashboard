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

    ########################################################
    # consulta da tabela loja
    ########################################################
    
    print("Consultando a tabela loja...")
    query = "SELECT * FROM maloka_core.loja"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_lojas = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_lojas)
    num_colunas = len(df_lojas.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_lojas.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_lojas.head())
    
    # Exportar para Excel
    # df_lojas.to_excel("df_lojas.xlsx", index=False)

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
df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
df_vendas['Ano'] = df_vendas['data_venda'].dt.year
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
df_anual_por_tipo.rename(columns={'S': 'Faturamento em Serviços', 'P': 'Faturamento em Produtos'}, inplace=True)

# Calcular o total para cada ano
df_anual_por_tipo['Total'] = df_anual_por_tipo.sum(axis=1)

# Calcular as porcentagens
for col in ['Faturamento em Serviços', 'Faturamento em Produtos']:
    if col in df_anual_por_tipo.columns:
        df_anual_por_tipo[f'{col} (%)'] = (df_anual_por_tipo[col] / df_anual_por_tipo['Total']) * 100

# Calcular a evolução percentual anual para cada categoria
for col in ['Faturamento em Serviços', 'Faturamento em Produtos', 'Total de Faturamento']:
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

# Contar o número de vendas distintas por ano
df_vendas_por_ano = df_vendas.groupby('Ano').size().reset_index(name='Qtd Vendas')

# Adicionar a contagem de vendas ao dataframe de análise anual
df_anual_por_tipo = df_anual_por_tipo.merge(df_vendas_por_ano, on='Ano', how='left')

# Calcular o ticket médio anual (Total Faturamento / Qtd Vendas)
df_anual_por_tipo['Ticket Médio Anual'] = df_anual_por_tipo['Total'] / df_anual_por_tipo['Qtd Vendas']

# Calcular a evolução do ticket médio anual
df_anual_por_tipo['Evolução Ticket Médio (%)'] = df_anual_por_tipo['Ticket Médio Anual'].pct_change() * 100

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
lojas_disponiveis = sorted(df_vendas['id_loja'].unique())

print(f"Gerando gráficos de faturamento para os anos: {anos_disponiveis}")
print(f"Lojas disponíveis: {lojas_disponiveis}")

# Criar um DataFrame para consolidar todos os dados
df_consolidado = pd.DataFrame()

# Para cada ano, processamos os dados e os consolidamos
for ano in anos_disponiveis:
    # Filtrar as vendas para o ano e para as lojas disponíveis
    df_ano = df_vendas[(df_vendas['Ano'] == ano) & (df_vendas['id_loja'].isin(lojas_disponiveis))].copy()
    
    # Verificar se há dados para este ano
    if df_ano.empty:
        print(f"Não há dados para o ano {ano}")
        continue
    
    # Agrupar por Mês e id_loja, somando o total_venda
    df_mensal = df_ano.groupby(['Mês', 'id_loja'])['total_venda'].sum().reset_index()
    
    # Adicionar coluna de Ano ao DataFrame
    df_mensal['Ano'] = ano
    
    # Anexar ao DataFrame consolidado
    df_consolidado = pd.concat([df_consolidado, df_mensal], ignore_index=True)
    
    # # Criar uma tabela pivot para o gráfico: índice = Mês e colunas = id_loja
    # df_pivot = df_mensal.pivot(index='Mês', columns='id_loja', values='total_venda')
    
    # # Plotar o gráfico de barras agrupadas
    # plt.figure(figsize=(12, 7))
    # ax = df_pivot.plot(kind='bar', ax=plt.gca())
    # plt.title(f'Faturamento Mensal - Ano {ano}')
    # plt.xlabel('Mês')
    # plt.ylabel('Faturamento (R$)')
    # plt.xticks(rotation=0)
    # plt.grid(axis='y', linestyle='--', alpha=0.7)
    # plt.legend(title='Loja')
    
    # # Adicionar rótulos em cada barra com o valor correspondente
    # for container in ax.containers:
    #     ax.bar_label(container, fmt='R$%.0f', fontsize=8, label_type='edge')
    
    # plt.tight_layout()
    # plt.savefig(os.path.join(diretorio_atual, f'faturamento_mensal_{ano}.png'))
    # plt.close()

# Salvar o DataFrame consolidado em um único arquivo Excel
if not df_consolidado.empty:
    excel_path = os.path.join(diretorio_atual, 'faturamento_mensal_lojas.xlsx')
    df_consolidado = df_consolidado.merge(df_lojas[['id_loja', 'nome']], on='id_loja', how='left')
    df_consolidado.to_excel(excel_path, index=False)
    print(f"Dados de faturamento consolidados salvos em: {excel_path}")
else:
    print("Não há dados para gerar o arquivo Excel consolidado.")


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
else:
    print("Não há dados para gerar análise de faturamento diário.")


########################################################
# Faturamento diário no mês atual por loja
########################################################

# Obter a data atual
data_atual = pd.Timestamp.now()
mes_atual = data_atual.month
ano_atual = data_atual.year

# Filtrar vendas apenas para o mês atual
mask_mes_atual = (df_vendas['data_venda'].dt.month == mes_atual) & (df_vendas['data_venda'].dt.year == ano_atual)
df_mes_atual = df_vendas[mask_mes_atual].copy()

if not df_mes_atual.empty:
    # Criar coluna para dia do mês
    df_mes_atual['Dia'] = df_mes_atual['data_venda'].dt.day
    
    # Agrupar por dia e loja, calculando o faturamento diário
    df_diario_loja = df_mes_atual.groupby(['id_loja', 'Dia'])['total_venda'].sum().reset_index()
    
    # Mesclar com informações das lojas para obter os nomes
    df_diario_loja = df_diario_loja.merge(df_lojas[['id_loja', 'nome']], on='id_loja', how='left')
    
    # Criar uma lista com todos os dias do mês (1 a 31)
    todos_dias = list(range(1, 32))
    
    # Criar uma versão pivotada com lojas nas linhas e dias nas colunas
    df_pivot_lojas = df_diario_loja.pivot(index='nome', columns='Dia', values='total_venda')
    
    # Garantir que todos os dias de 1 a 31 estejam presentes
    for dia in todos_dias:
        if dia not in df_pivot_lojas.columns:
            df_pivot_lojas[dia] = 0
    
    # Ordenar as colunas para que os dias apareçam em ordem crescente
    df_pivot_lojas = df_pivot_lojas[sorted(df_pivot_lojas.columns)]
    
    # Preencher valores NaN com zero
    df_pivot_lojas = df_pivot_lojas.fillna(0)
    
    # Adicionar uma coluna com o total por loja
    df_pivot_lojas['total_loja'] = df_pivot_lojas.sum(axis=1)
    
    # Ordenar o DataFrame pelo total de vendas (do maior para o menor)
    df_pivot_lojas = df_pivot_lojas.sort_values('total_loja', ascending=False)
    
    # Adicionar uma linha com o total diário (de todas as lojas juntas)
    totais_diarios = df_diario_loja.groupby('Dia')['total_venda'].sum()
    df_pivot_lojas.loc['total'] = pd.Series({dia: totais_diarios.get(dia, 0) for dia in df_pivot_lojas.columns})
    
    # Calcular o total geral (soma de todas as vendas) e adicionar na célula da última coluna da linha 'total'
    total_geral = df_diario_loja['total_venda'].sum()
    df_pivot_lojas.loc['total', 'total_loja'] = total_geral

    # Arredondar os valores para 2 casas decimais para melhor visualização
    df_pivot_lojas = df_pivot_lojas.round(2)
    
    # Salvar em Excel
    excel_path = os.path.join(diretorio_atual, f'faturamento_diario_lojas.xlsx')
    df_pivot_lojas.to_excel(excel_path)
    print(df_pivot_lojas.head())
    print(f"Dados de faturamento diário por loja salvos em: {excel_path}")
    
else:
    # Caso não existam dados para o mês atual, buscar dados do mês anterior
    mes_anterior = mes_atual - 1
    ano_anterior = ano_atual
    
    # Ajuste caso o mês atual seja janeiro
    if mes_anterior == 0:
        mes_anterior = 12
        ano_anterior = ano_atual - 1
        
    print(f"Não há dados de vendas para o mês atual ({mes_atual}/{ano_atual}). Buscando dados do mês anterior ({mes_anterior}/{ano_anterior})...")
    
    # Filtrar vendas do mês anterior
    mask_mes_anterior = (df_vendas['data_venda'].dt.month == mes_anterior) & (df_vendas['data_venda'].dt.year == ano_anterior)
    df_mes_anterior = df_vendas[mask_mes_anterior].copy()
    
    if not df_mes_anterior.empty:
        # Criar coluna para dia do mês
        df_mes_anterior['Dia'] = df_mes_anterior['data_venda'].dt.day
        
        # Agrupar por dia e loja, calculando o faturamento diário
        df_diario_loja = df_mes_anterior.groupby(['id_loja', 'Dia'])['total_venda'].sum().reset_index()
        
        # Mesclar com informações das lojas para obter os nomes
        df_diario_loja = df_diario_loja.merge(df_lojas[['id_loja', 'nome']], on='id_loja', how='left')
        
        # Criar uma lista com todos os dias do mês (1 a 31)
        todos_dias = list(range(1, 32))
        
        # Criar uma versão pivotada com lojas nas linhas e dias nas colunas
        df_pivot_lojas = df_diario_loja.pivot(index='nome', columns='Dia', values='total_venda')
        
        # Garantir que todos os dias do mês anterior estejam presentes
        for dia in todos_dias:
            if dia not in df_pivot_lojas.columns:
                df_pivot_lojas[dia] = 0
        
        # Ordenar as colunas para que os dias apareçam em ordem crescente
        df_pivot_lojas = df_pivot_lojas[sorted(df_pivot_lojas.columns)]
        
        # Preencher valores NaN com zero
        df_pivot_lojas = df_pivot_lojas.fillna(0)

        # Adicionar uma coluna com o total por loja
        df_pivot_lojas['total_loja'] = df_pivot_lojas.sum(axis=1)
        
        # Ordenar o DataFrame pelo total de vendas (do maior para o menor)
        df_pivot_lojas = df_pivot_lojas.sort_values('total_loja', ascending=False)
        
        # Adicionar uma linha com o total diário (de todas as lojas juntas)
        totais_diarios = df_diario_loja.groupby('Dia')['total_venda'].sum()
        df_pivot_lojas.loc['total'] = pd.Series({dia: totais_diarios.get(dia, 0) for dia in df_pivot_lojas.columns})
        
        # Calcular o total geral (soma de todas as vendas) e adicionar na célula da última coluna da linha 'total'
        total_geral = df_diario_loja['total_venda'].sum()
        df_pivot_lojas.loc['total', 'total_loja'] = total_geral
        
        # Arredondar os valores para 2 casas decimais para melhor visualização
        df_pivot_lojas = df_pivot_lojas.round(2)
        
        # Salvar em Excel
        excel_path = os.path.join(diretorio_atual, f'faturamento_diario_lojas.xlsx')
        df_pivot_lojas.to_excel(excel_path)
        print(f"Dados de faturamento diário por loja do mês anterior ({mes_anterior}/{ano_anterior}) salvos em: {excel_path}")
    else:
        print(f"Não há dados de vendas para o mês anterior ({mes_anterior}/{ano_anterior}).")
