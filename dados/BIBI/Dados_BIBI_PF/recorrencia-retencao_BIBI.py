import pandas as pd
import psycopg2
import dotenv
import os
from datetime import datetime

dotenv.load_dotenv()
# Nome do arquivo com timestamp para evitar sobrescrever arquivos anteriores
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

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
    #df_vendas.to_excel("df_vendas.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")

###############################################################
#Análise de Recorrência Mensal
###############################################################

# Criar um DataFrame com mês e cliente
df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
monthly_customers = df_vendas.groupby([df_vendas['data_venda'].dt.strftime('%Y-%m'), 'id_cliente']).size().reset_index()
monthly_customers.columns = ['yearmonth', 'id_cliente', 'count']

# Criar um pivot para facilitar a comparação entre meses
customer_matrix = monthly_customers.pivot_table(
    index='id_cliente',
    columns='yearmonth',
    values='count',
    fill_value=0
).astype(bool).astype(int)

# Calcular retenção
retention_rates = []
months = sorted(customer_matrix.columns)

for i in range(1, len(months)):
    prev_month = months[i-1]
    current_month = months[i]
    
    # Total de clientes no mês anterior
    prev_customers = customer_matrix[prev_month].sum()
    
    # Clientes que permaneceram
    retained = ((customer_matrix[prev_month] == 1) & (customer_matrix[current_month] == 1)).sum()
    
    # Calcular taxa
    retention_rate = (retained / prev_customers * 100) if prev_customers > 0 else 0
    
    retention_rates.append({
        'yearmonth': current_month,
        'retained_customers': retained,
        'prev_total_customers': prev_customers,
        'retention_rate': retention_rate
    })

retention_metrics = pd.DataFrame(retention_rates)

# Salvar resultados
retention_metrics.to_excel(os.path.join(diretorio_atual, 'metricas_recorrencia_mensal.xlsx'), index=False)
print(f"\nResultados salvos em {os.path.join(diretorio_atual, 'metricas_recorrencia_mensal.xlsx')}")

# Imprimir métricas
print("\nMétricas de Recorrência:")
print(retention_metrics.to_string(index=False))

# Estatísticas resumidas
print("\nEstatísticas de Recorrência:")
print(f"Taxa média de retenção: {retention_metrics['retention_rate'].mean():.1f}%")
print(f"Taxa máxima de retenção: {retention_metrics['retention_rate'].max():.1f}%")
print(f"Taxa mínima de retenção: {retention_metrics['retention_rate'].min():.1f}%")

###############################################################
#Análise de Recorrência Trimestral
###############################################################

# Criar trimestre para cada compra
df_vendas['trimestre'] = df_vendas['data_venda'].dt.to_period('Q')

# Criar DataFrame de clientes por trimestre
quarterly_customers = df_vendas.groupby(['trimestre', 'id_cliente']).size().reset_index()
quarterly_customers.columns = ['trimestre', 'id_cliente', 'count']

# Criar pivot para análise trimestral
customer_matrix = quarterly_customers.pivot_table(
    index='id_cliente',
    columns='trimestre',
    values='count',
    fill_value=0
).astype(bool).astype(int)

# Calcular recorrência trimestral
quarterly_metrics = []
quarters = sorted(customer_matrix.columns)

for i in range(1, len(quarters)):
    current_quarter = quarters[i]
    prev_quarter = quarters[i-1]
    
    # Total de clientes no trimestre anterior
    prev_customers = customer_matrix[prev_quarter].sum()
    
    # Clientes que voltaram
    returning = ((customer_matrix[prev_quarter] == 1) & (customer_matrix[current_quarter] == 1)).sum()
    
    # Novos clientes (não compraram no trimestre anterior)
    new_customers = (customer_matrix[current_quarter] & ~customer_matrix[prev_quarter]).sum()
    
    # Total de clientes no trimestre atual
    total_customers = customer_matrix[current_quarter].sum()
    
    # Calcular taxas
    recurrence_rate = (returning / prev_customers * 100) if prev_customers > 0 else 0
    
    quarterly_metrics.append({
        'trimestre': str(current_quarter),  # Convertendo para string
        'trimestre_obj': current_quarter,   # Mantendo o objeto período para ordenação
        'total_customers': total_customers,
        'returning_customers': returning,
        'new_customers': new_customers,
        'recurrence_rate': recurrence_rate
    })

quarterly_df = pd.DataFrame(quarterly_metrics)
quarterly_df = quarterly_df.sort_values('trimestre_obj')  # Ordenar pelos trimestres


# Salvar resultados
quarterly_df.to_excel(os.path.join(diretorio_atual, 'metricas_recorrencia_trimestral.xlsx'), index=False)
print(f"\nResultados salvos em {os.path.join(diretorio_atual, 'metricas_recorrencia_trimestral.xlsx')}")

# Imprimir métricas (removendo a coluna trimestre_obj para melhor visualização)
print("\nMétricas Trimestrais:")
print(quarterly_df.drop('trimestre_obj', axis=1).to_string(index=False))

# Estatísticas resumidas
print("\nEstatísticas de Recorrência Trimestral:")
print(f"Taxa média de recorrência: {quarterly_df['recurrence_rate'].mean():.1f}%")
print(f"Taxa máxima de recorrência: {quarterly_df['recurrence_rate'].max():.1f}%")
print(f"Taxa mínima de recorrência: {quarterly_df['recurrence_rate'].min():.1f}%")
print(f"\nMédia de novos clientes por trimestre: {quarterly_df['new_customers'].mean():.0f}")
print(f"Média de clientes recorrentes por trimestre: {quarterly_df['returning_customers'].mean():.0f}")

###############################################################
#Análise de Recorrência Anual
###############################################################

# Criar ano para cada compra
df_vendas['ano'] = df_vendas['data_venda'].dt.to_period('Y')

# Criar DataFrame de clientes por ano
annual_customers = df_vendas.groupby(['ano', 'id_cliente']).size().reset_index()
annual_customers.columns = ['ano', 'id_cliente', 'count']

# Criar pivot para análise anual
customer_matrix = annual_customers.pivot_table(
    index='id_cliente',
    columns='ano',
    values='count',
    fill_value=0
).astype(bool).astype(int)

# Calcular métricas anuais
annual_metrics = []
years = sorted(customer_matrix.columns)

for i in range(1, len(years)):
    current_year = years[i]
    prev_year = years[i-1]
    
    # Total de clientes no ano anterior
    prev_customers = customer_matrix[prev_year].sum()
    
    # Clientes que voltaram
    returning = ((customer_matrix[prev_year] == 1) & (customer_matrix[current_year] == 1)).sum()
    
    # Novos clientes (não compraram no ano anterior)
    new_customers = (customer_matrix[current_year] & ~customer_matrix[prev_year]).sum()
    
    # Total de clientes no ano atual
    total_customers = customer_matrix[current_year].sum()
    
    # Calcular taxas
    retention_rate = (returning / prev_customers * 100) if prev_customers > 0 else 0
    new_rate = (new_customers / total_customers * 100) if total_customers > 0 else 0
    returning_rate = (returning / total_customers * 100) if total_customers > 0 else 0
    
    annual_metrics.append({
        'ano': str(current_year),
        'ano_obj': current_year,
        'total_customers': total_customers,
        'returning_customers': returning,
        'new_customers': new_customers,
        'retention_rate': retention_rate,  # Taxa de retenção em relação ao ano anterior
        'new_rate': new_rate,  # % de novos clientes no total
        'returning_rate': returning_rate  # % de clientes recorrentes no total
    })

annual_df = pd.DataFrame(annual_metrics)
annual_df = annual_df.sort_values('ano_obj')

# Salvar resultados
annual_df.to_excel(os.path.join(diretorio_atual, 'metricas_recorrencia_anual.xlsx'), index=False)
print(f"\nResultados salvos em {os.path.join(diretorio_atual, 'metricas_recorrencia_anual.xlsx')}")

# Imprimir estatísticas
print("\nMétricas Anuais:")
print(annual_df.drop('ano_obj', axis=1).to_string(index=False))

print("\nEstatísticas de Recorrência Anual:")
print(f"Taxa média de retenção: {annual_df['retention_rate'].mean():.1f}%")
print(f"Taxa média de novos clientes: {annual_df['new_rate'].mean():.1f}%")
print(f"Taxa média de recorrentes: {annual_df['returning_rate'].mean():.1f}%")


###############################################################
#Análise de Retenção Anual
###############################################################

# ---- Análise de Cohort: Agrupando Clientes em Coortes Anuais com Base na Primeira Compra ----

# Utilizaremos a base de dados df_vendas que já possui a coluna 'data_venda' no formato datetime.
# Cada pedido será associado a um período anual, e cada cliente receberá a coorte (ano) de sua primeira compra.

# 1. Definir o período do pedido como ano
df_vendas['order_period'] = df_vendas['data_venda'].dt.to_period('Y')

# 2. Para cada cliente, identificar a data da primeira compra e definir sua coorte anual
first_purchase = df_vendas.groupby('id_cliente')['data_venda'].min().reset_index()
first_purchase.columns = ['id_cliente', 'first_purchase_date']
first_purchase['cohort_year'] = first_purchase['first_purchase_date'].dt.to_period('Y')

# 3. Mesclar a informação da coorte (ano da primeira compra) de volta à base de pedidos
df_vendas = pd.merge(df_vendas, first_purchase[['id_cliente', 'cohort_year']], on='id_cliente')

# 4. Calcular o índice do período (em anos) para cada pedido: quantos anos se passaram desde a coorte
df_vendas['period_index'] = (df_vendas['order_period'] - df_vendas['cohort_year']).apply(lambda x: x.n)

# 5. Agregar os dados para contar o número de clientes únicos por coorte e por período
cohort_data = df_vendas.groupby(['cohort_year', 'period_index'])['id_cliente'].nunique().reset_index()
cohort_data.rename(columns={'id_cliente': 'num_customers'}, inplace=True)

# 6. Obter o tamanho inicial de cada coorte (ou seja, o número de clientes no período 0)
cohort_sizes = cohort_data[cohort_data['period_index'] == 0][['cohort_year', 'num_customers']]
cohort_sizes.rename(columns={'num_customers': 'cohort_size'}, inplace=True)

# 7. Mesclar o tamanho da coorte com os dados agregados
cohort_data = pd.merge(cohort_data, cohort_sizes, on='cohort_year')

# 8. Calcular a taxa de retenção para cada coorte e período:
#    Taxa de Retenção = Número de clientes ativos no período / Tamanho inicial da coorte
cohort_data['retention_rate'] = cohort_data['num_customers'] / cohort_data['cohort_size']

# 9. Criar uma tabela dinâmica (pivot table) para visualizar a retenção ao longo dos anos
cohort_pivot = cohort_data.pivot(index='cohort_year', columns='period_index', values='retention_rate')

# Exibir a tabela de retenção
cohort_data.to_excel(os.path.join(diretorio_atual, 'metricas_retencao_anual.xlsx'), index=False)
print(f"\nTabela de retenção salva em {os.path.join(diretorio_atual, 'metricas_retencao_anual.xlsx')}")
