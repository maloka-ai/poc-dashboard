import pandas as pd
import psycopg2
import dotenv
import os
import numpy as np
import warnings
from lifetimes import BetaGeoFitter
from datetime import datetime

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
    # consulta da tabela cliente pessoa física
    ########################################################

    print("Consultando a tabela cliente...")
    query = "SELECT * FROM maloka_core.cliente_pessoa_fisica"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_clientes_PF = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_vendas)
    num_colunas = len(df_clientes_PF.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_clientes_PF.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_clientes_PF.head())

    # df_clientes_PF.to_excel("df_clientes_PF.xlsx", index=False)

    ########################################################
    # consulta da tabela cliente pessoa jurídica
    ########################################################

    print("Consultando a tabela cliente...")
    query = "SELECT * FROM maloka_core.cliente_pessoa_juridica"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_clientes_PJ = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_vendas)
    num_colunas = len(df_clientes_PJ.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_clientes_PJ.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_clientes_PJ.head())

    # df_clientes_PF.to_excel("df_clientes_PJ.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")

##########################################################
# Filtrar apenas os clientes PF
##########################################################

df_vendas = df_vendas.merge(df_clientes[['id_cliente', 'tipo']], on='id_cliente', how='left')
df_vendas = df_vendas[df_vendas['tipo'] == 'F']

unique_clientes = df_vendas['id_cliente'].nunique()
print(f"Número de Clientes PF: {unique_clientes}")

##########################################################
# Calcular as métricas RFMA
##########################################################

# Recency: Número de dias desde a última compra
data_referencia = df_vendas['data_venda'].max()
recency = df_vendas.groupby('id_cliente')['data_venda'].max().apply(lambda x: (data_referencia - x).days)

# Frequency: Número de pedidos únicos por cliente
frequency = df_vendas.groupby('id_cliente')['id_venda'].nunique()

# Monetary: Valor total gasto
monetary = df_vendas.groupby('id_cliente')['total_venda'].sum()

# Age (Antiguidade): Dias desde a primeira compra
age = df_vendas.groupby('id_cliente')['data_venda'].min().apply(lambda x: (data_referencia - x).days)

# Combinar métricas em um único DataFrame
rfma = pd.DataFrame({
    'Recency': recency,
    'Frequency': frequency,
    'Monetary': monetary,
    'Age': age
})

# Resetar o índice para ter id_cliente como coluna
rfma = rfma.reset_index()

# Adicionar algumas verificações
print("\nEstatísticas das métricas RFMA:")
print("\nRecency (dias):")
print(rfma['Recency'].describe())
print("\nFrequency (número de pedidos):")
print(rfma['Frequency'].describe())
print("\nMonetary (valor total):")
print(rfma['Monetary'].describe())
print("\nAge (dias desde primeira compra):")
print(rfma['Age'].describe())

#Salvar o resultado em um arquivo CSV
# rfma.to_csv('RFMA_por_cliente.csv', index=False)

# Exibir o DataFrame RFMA
print("\nPrimeiras linhas do RFMA:")
print(rfma.head())

# Verificações adicionais
print("\nContagens de controle:")
print(f"Número total de clientes: {len(rfma)}")

# Verificação adicional para Age
print("\nVerificação de coerência:")
print("Clientes com Age menor que Recency:", len(rfma[rfma['Age'] < rfma['Recency']]))

##############################################################
#RFMA -Análise de clientes por Decis
###############################################################

# Converter as colunas para float (caso estejam em decimal.Decimal)
for col in ['Recency', 'Frequency', 'Monetary', 'Age']:
    rfma[col] = rfma[col].astype(float)

# Criar decis para cada métrica RFMA
# Primeiro vamos obter os bins para cada métrica
_, r_bins = pd.qcut(rfma['Recency'], q=10, duplicates='drop', retbins=True)
_, f_bins = pd.qcut(rfma['Frequency'], q=10, duplicates='drop', retbins=True)
_, m_bins = pd.qcut(rfma['Monetary'], q=10, duplicates='drop', retbins=True)
_, a_bins = pd.qcut(rfma['Age'], q=10, duplicates='drop', retbins=True)

# Agora criar os labels com o número correto de categorias
r_labels = list(range(len(r_bins)-1, 0, -1))  # Ordem inversa para Recency
f_labels = list(range(1, len(f_bins)))  # Ordem normal para os demais
m_labels = list(range(1, len(m_bins)))
a_labels = list(range(1, len(a_bins)))

# Aplicar os decis
rfma['R_decil'] = pd.qcut(rfma['Recency'], q=10, labels=r_labels, duplicates='drop')
rfma['F_decil'] = pd.qcut(rfma['Frequency'], q=10, labels=f_labels, duplicates='drop')
rfma['M_decil'] = pd.qcut(rfma['Monetary'], q=10, labels=m_labels, duplicates='drop')
rfma['A_decil'] = pd.qcut(rfma['Age'], q=10, labels=a_labels, duplicates='drop')

# Criar ranges para visualização
r_bins = pd.qcut(rfma['Recency'], q=10, duplicates="drop", retbins=True)[1]
rfma['R_range'] = pd.cut(
    rfma['Recency'], 
    bins=r_bins, 
    labels=[f"{r_bins[i]:.1f}-{r_bins[i+1]:.1f}" for i in range(len(r_bins)-1)], 
    include_lowest=True
)

f_bins = pd.qcut(rfma['Frequency'], q=10, duplicates="drop", retbins=True)[1]
rfma['F_range'] = pd.cut(
    rfma['Frequency'], 
    bins=f_bins, 
    labels=[f"{f_bins[i]:.1f}-{f_bins[i+1]:.1f}" for i in range(len(f_bins)-1)], 
    include_lowest=True
)

m_bins = pd.qcut(rfma['Monetary'], q=10, duplicates="drop", retbins=True)[1]
rfma['M_range'] = pd.cut(
    rfma['Monetary'], 
    bins=m_bins, 
    labels=[f"{m_bins[i]:.1f}-{m_bins[i+1]:.1f}" for i in range(len(m_bins)-1)], 
    include_lowest=True
)

a_bins = pd.qcut(rfma['Age'], q=10, duplicates="drop", retbins=True)[1]
rfma['A_range'] = pd.cut(
    rfma['Age'], 
    bins=a_bins, 
    labels=[f"{a_bins[i]:.1f}-{a_bins[i+1]:.1f}" for i in range(len(a_bins)-1)], 
    include_lowest=True
)

# Imprimir exemplo dos primeiros registros com os decis
print("\nExemplo dos primeiros registros com decis:")
print(rfma[['Recency', 'R_decil', 'Frequency', 'F_decil', 
            'Monetary', 'M_decil', 'Age', 'A_decil']].head())


################################################################
# RFMA - Segmentação baseada em Regras
################################################################

def segment_customers(df):
    """
    Segmenta clientes com base em regras atualizadas, de acordo com a análise da distribuição por faixa.
    
    Parâmetros:
    - Recency: dias desde a última compra
    - Age: dias desde a primeira compra (antiguidade)
    - Frequency: número de compras
    - Monetary: valor médio das compras
    """
    # Criar cópia do dataframe
    df_seg = df.copy()
    
    # Definir condições de forma mutuamente exclusiva

    cond_novos = (df_seg['Recency'] <= 30) & (df_seg['Age'] <= 30) # compraram no mês anterior
    
    cond_campeoes = (df_seg['Recency'] <= 180) & \
                    (df_seg['Frequency'] >= 3) & (df_seg['M_decil'] == 10) # clientes que compraram nos últimos 6 meses e possuem valor monetário muito acima da média
                    
    cond_fieis_baixo_valor = (df_seg['Recency'] <= 365) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 3) & (df_seg['M_decil'] <= 7) # clientes há mais de 2 anos que compraram no último ano e possuem valor monetário menor ou igual a média
    
    cond_fieis_alto_valor = (df_seg['Recency'] <= 365) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 3) & (df_seg['M_decil'] > 7) # clientes há mais de 2 anos que compraram no último ano e possuem valor monetário abaixo da média
                 
    cond_recentes_alto = (df_seg['Recency'] <= 365) & \
                         (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] >= 6) # clientes que compraram nos últimos 6 meses, com idade de 1 ano e possui valor monetário acima da média
                         
    cond_recentes_baixo = (df_seg['Recency'] <= 365) & \
                          (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] < 6) # clientes que compraram nos últimos 6 meses, com idade de 1 ano e possui valor monetário menor ou igual da média
    
    # Clientes menos ativos
    cond_sumidos = (df_seg['Recency'] >= 365) & (df_seg['Recency'] < 730) # última compra entre 1 a 2 anos
    cond_inativos = (df_seg['Recency'] >= 730) # sem comprar faz 2 anos
    
    # Lista de condições e respectivos rótulos
    conditions = [
        cond_novos,
        cond_campeoes,
        cond_fieis_baixo_valor,
        cond_fieis_alto_valor,
        cond_recentes_alto,
        cond_recentes_baixo,
        cond_sumidos,
        cond_inativos
    ]
    
    labels = [
        'Novos',
        'Campeões',
        'Fiéis Baixo Valor',
        'Fiéis Alto Valor',
        'Recentes Alto Valor',
        'Recentes Baixo Valor',
        'Sumidos',
        'Inativos'
    ]
    
    # Aplicar segmentação
    df_seg['Segmento'] = np.select(conditions, labels, default='Não Classificado')
    
    # Definir cores para cada segmento
    cores_segmento = {
        'Novos': '#2ecc71',              # Verde
        'Campeões': '#9b59b6',           # Roxo
        'Fiéis Baixo Valor': '#e74c3c',  # Vermelho
        'Fiéis Alto Valor' : '#e7443c',  
        'Recentes Alto Valor': '#f1c40f', # Amarelo
        'Recentes Baixo Valor': '#3498db',# Azul
        'Sumidos': '#1abc9c',             # Turquesa
        'Inativos': '#e67e22'             # Laranja
    }
    
    # Agregar dados para análise dos segmentos
    analise_segmentos = df_seg.groupby('Segmento').agg({
        'id_cliente': 'count',
        'Recency': 'mean',
        'Frequency': 'mean',
        'Monetary': 'mean',
        'Age': 'mean'
    }).round(2)
    
    analise_segmentos.columns = [
        'Quantidade Clientes',
        'Média Recency (dias)',
        'Média Frequency',
        'Média Monetary (R$)',
        'Média Age (dias)'
    ]
    
    # Ordenar por quantidade de clientes
    analise_segmentos = analise_segmentos.sort_values('Quantidade Clientes', ascending=False)
    
    return df_seg, analise_segmentos

# Usar a função
rfma_segmentado, analise = segment_customers(rfma)

# Salvar resultados
# rfma_segmentado.to_excel('rfma_segmentado_regras.xlsx', index=False)
# print("\nResultados salvos em 'rfma_segmentado_regras.xlsx'")

# Exibir análise
print("\nAnálise Detalhada por Segmento:")
print("=" * 120)
print(analise)

################################################################
# Preparando dados para Dashboard da BIBI
################################################################

rfma_segmentado = rfma_segmentado.merge(df_clientes_PF[['id_cliente', 'cpf']], on='id_cliente', how='left')
rfma_segmentado = rfma_segmentado.merge(df_clientes_PJ[['id_cliente', 'cnpj']], on='id_cliente', how='left')
rfma_segmentado = rfma_segmentado.merge(df_clientes[['id_cliente', 'nome', 'email', 'telefone']], on='id_cliente', how='left')
print(rfma_segmentado.columns)
#Arquivo usado para o dash de segmentação
rfma_segmentado.to_csv(os.path.join(diretorio_atual, f"analytics_cliente_BIBI_PF.csv"), index=False)

################################################################
# Previsão de compra para 30 dias
################################################################

# Pré-processamento para o modelo BG/NBD
rfma = rfma_segmentado.copy()

# Limpeza e tratamento dos dados
rfma = rfma[rfma['Frequency'] > 3]

# Ajustar os valores para evitar problemas numéricos
rfma['frequency_adjusted'] = rfma['Frequency'] - 1
rfma['recency_bg'] = (rfma['Age'] - rfma['Recency']).clip(lower=1)  # Garantir valores positivos
rfma['T'] = rfma['Age'].clip(lower=1)  # Garantir valores positivos

# Remover outliers extremos
for col in ['frequency_adjusted', 'recency_bg', 'T']:
    Q1 = rfma[col].quantile(0.01)
    Q3 = rfma[col].quantile(0.99)
    IQR = Q3 - Q1
    rfma = rfma[
        (rfma[col] >= Q1 - 1.5 * IQR) &
        (rfma[col] <= Q3 + 1.5 * IQR)
    ]

# Ajuste do Modelo BG/NBD com parâmetros para melhor convergência
bgf = BetaGeoFitter(penalizer_coef=0.01)  # Aumentar penalizador
bgf.fit(
    rfma['frequency_adjusted'],
    rfma['recency_bg'],
    rfma['T'],
    iterative_fitting=2,          # Reduzir número de iterações
    tol=1e-4,                     # Aumentar tolerância
    initial_params=None,          # Permitir estimativa automática
    verbose=True                  # Mostrar progresso
)

# Calcular previsões para 30 dias
rfma['predicted_purchases_30d'] = bgf.conditional_expected_number_of_purchases_up_to_time(
    30,
    rfma['frequency_adjusted'],
    rfma['recency_bg'],
    rfma['T']
)

# Remover previsões extremas ou inválidas
rfma = rfma[rfma['predicted_purchases_30d'].between(
    rfma['predicted_purchases_30d'].quantile(0.01),
    rfma['predicted_purchases_30d'].quantile(0.99)
)]

# Imprimir parâmetros do modelo
print("\nParâmetros do Modelo:")
print(bgf)
print("\nEstatísticas das Previsões:")
print(rfma['predicted_purchases_30d'].describe())

# Definir limiar usando método mais robusto
limiar = rfma['predicted_purchases_30d'].median() + \
         rfma['predicted_purchases_30d'].std() * 0.01

# Classificar clientes
rfma['categoria_previsao'] = np.where(
    rfma['predicted_purchases_30d'] >= limiar,
    'Alta Probabilidade de Compra',
    'Baixa Probabilidade de Compra'
)
# Análise por categoria
print("\nAnálise por Categoria de Previsão:")
analise_categoria = rfma.groupby('categoria_previsao').agg({
    'Frequency': ['mean', 'median', 'count'],
    'Recency': ['mean', 'median'],
    'Monetary': ['mean', 'median'],
    'predicted_purchases_30d': ['mean', 'median', 'min', 'max']
}).round(2)

print(analise_categoria)

# Validação das previsões
print("\nValidação do Modelo:")
print(f"Média de transações previstas: {rfma['predicted_purchases_30d'].mean():.2f}")
print(f"Mediana de transações previstas: {rfma['predicted_purchases_30d'].median():.2f}")
print(f"% de clientes com alta probabilidade: {(rfma['categoria_previsao'] == 'Alta Probabilidade de Compra').mean()*100:.1f}%")

# Salvar resultados
rfma.to_excel(os.path.join(diretorio_atual, f"rfma_previsoes_ajustado.xlsx"), index=False)
print("\nResultados salvos em 'rfma_previsoes_ajustado.xlsx'")