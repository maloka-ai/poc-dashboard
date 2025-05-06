import pandas as pd
import psycopg2
import dotenv
import os
import numpy as np
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dotenv.load_dotenv()
caminho_arquivo_completo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analise_curva_cobertura.xlsx")

try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("DB_HOST"),
        database="bibicell",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS"),
        port= os.getenv("DB_PORT"),
    )
    
    print("Conexão estabelecida com sucesso!")

    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela VENDAS...")
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
    
    # EXPORTAR EXCEL
    # df_vendas.to_excel("df_vendas.xlsx", index=False)
    
    ########################################################
    # consulta da tabela vendas_itens
    ########################################################
    
    print("Consultando a tabela VENDA_ITENS...")
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
    
    # EXPORTAR EXCEL
    # df_venda_itens.to_excel("df_venda_itens.xlsx", index=False)

    ########################################################
    # consulta da tabela estoque_movimentos
    ########################################################
    
    # Consultar a tabela estoque_movimentos
    print("Consultando a tabela ESTOQUE_MOVIMENTOS...")
    query = "SELECT * FROM maloka_core.estoque_movimento"

    # Carregar os dados diretamente em um DataFrame do pandas
    df_estoque_movi = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_estoque_movi)
    num_colunas = len(df_estoque_movi.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_estoque_movi.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_estoque_movi.head())
    
    # EXPORTAR EXCEL
    # df_estoque_movi.to_excel("df_estoque_movimentos.xlsx", index=False)

    ########################################################
    # consulta da tabela estoque
    ########################################################
    
    # Consultar a tabela estoque
    print("Consultando a tabela ESTOQUE...")
    query = "SELECT * FROM maloka_core.historico_estoque"

    # Carregar os dados diretamente em um DataFrame do pandas
    df_estoque = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_estoque)
    num_colunas = len(df_estoque.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_estoque.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_estoque.head())
    
    # EXPORTAR EXCEL
    # df_estoque.to_excel("df_estoque.xlsx", index=False)

    ########################################################
    # consulta da tabela produtos
    ########################################################
    
    # Consultar a tabela produtos
    print("Consultando a tabela PRODUTOS...")
    query = "SELECT * FROM maloka_core.produto"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_produtos = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_produtos)
    num_colunas = len(df_produtos.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_produtos.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_produtos.head())
    
    # EXPORTAR EXCEL
    # df_produtos.to_excel("df_produtos.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")

# Criar tabela de estoque geral consolidado por SKU
print("Preparando tabela de estoque geral consolidado...")

# Criar tabela de estoque geral consolidado por SKU
print("Preparando tabela de estoque geral consolidado...")

# 1. Primeiro, obter o estoque mais recente para cada combinação de produto e loja
estoque_mais_recente = df_estoque.sort_values('data_estoque', ascending=False)
estoque_mais_recente = estoque_mais_recente.drop_duplicates(subset=['id_produto', 'id_loja'], keep='first')

# 2. Agora agrupar por produto, somando os valores únicos (mais recentes) de cada loja
estoque_consolidado = estoque_mais_recente.groupby('id_produto').agg({
    'estoque': 'sum',                # Soma do estoque mais recente de todas as lojas
    'data_estoque': 'max',           # Data mais recente de atualização
    'id_loja': 'count'               # Quantidade de lojas com este produto
}).reset_index()

#Adicionar informações do produto
estoque_final = pd.merge(
    estoque_consolidado,
    df_produtos[['id_produto', 'nome']],
    on='id_produto',
    how='left'
)

# 3. Renomear colunas para melhor compreensão
estoque_final = estoque_final.rename(columns={
    'id_produto': 'SKU',
    'estoque': 'Estoque Total',
    'data_estoque': 'Data Atualização',
    'id_loja': 'Qtd Lojas',
    'nome': 'Descrição do Produto'
})

# 4. Reorganizar colunas
estoque_final = estoque_final[[
    'SKU', 
    'Descrição do Produto', 
    'Estoque Total', 
    'Data Atualização', 
    'Qtd Lojas'
]]

# 5. Ordenar do menor para o maior estoque para destacar produtos críticos
estoque_final = estoque_final.sort_values('Estoque Total')

# 6. Exibir informações da tabela
print(f"\nTabela de Estoque Consolidado por Produto - {len(estoque_final)} produtos")
print(estoque_final.head(10))

# 7. Salvar em Excel
# caminho_arquivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "estoque_geral_consolidado.xlsx")
# estoque_final.to_excel(caminho_arquivo, index=False)
# print(f"\nTabela exportada para: {caminho_arquivo}")

# 8. Análise do status de estoque
print("\n=== RESUMO DA SITUAÇÃO DE ESTOQUE ===")

# Contagem de SKUs por status de estoque
estoque_negativo = (estoque_final['Estoque Total'] < 0).sum()
estoque_zerado = (estoque_final['Estoque Total'] == 0).sum()
estoque_positivo = (estoque_final['Estoque Total'] > 0).sum()

# Percentuais
total_skus = len(estoque_final)
pct_negativo = (estoque_negativo / total_skus) * 100
pct_zerado = (estoque_zerado / total_skus) * 100
pct_positivo = (estoque_positivo / total_skus) * 100

# Imprimir resultados
print(f"Total de SKUs: {total_skus}")
print(f"- SKUs com estoque negativo: {estoque_negativo} ({pct_negativo:.1f}%)")
print(f"- SKUs com estoque zerado: {estoque_zerado} ({pct_zerado:.1f}%)")
print(f"- SKUs com estoque positivo: {estoque_positivo} ({pct_positivo:.1f}%)")


# 9. Análise de vendas por período (30, 60, 90 dias e 1 ano)
print("\n=== ANÁLISE DE VENDAS POR PERÍODO ===")

# Preparar os dados de vendas
print("Preparando análise de vendas por SKU em diferentes períodos...")

# Converter coluna de data para datetime se ainda não estiver
if not pd.api.types.is_datetime64_any_dtype(df_vendas['data_venda']):
    df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])

# Juntar as tabelas de vendas e itens de venda
df_venda_itens_pedido = pd.merge(
    df_venda_itens,
    df_vendas[['id_venda', 'data_venda']],
    on='id_venda',
    how='left'
)

# Data atual para calcular os períodos
data_atual = datetime.now()

# Definir os períodos de análise
periodos = {
    'ultimos_30_dias': data_atual - timedelta(days=30),
    'ultimos_60_dias': data_atual - timedelta(days=60),
    'ultimos_90_dias': data_atual - timedelta(days=90),
    'ultimo_ano': data_atual - timedelta(days=365)
}

# Criar DataFrames para cada período
vendas_por_periodo = {}
valores_por_periodo = {}  # Novo dicionário para armazenar valores vendidos

for periodo_nome, data_inicio in periodos.items():
    # Filtrar vendas do período
    vendas_periodo = df_venda_itens_pedido[df_venda_itens_pedido['data_venda'] >= data_inicio]
    
    # Agrupar por produto e somar quantidades
    vendas_agrupadas = vendas_periodo.groupby('id_produto')['quantidade'].sum().reset_index()
    vendas_agrupadas.rename(columns={'quantidade': f'vendas_{periodo_nome}'}, inplace=True)
    
    # Agrupar por produto e somar valores vendidos
    valores_agrupados = vendas_periodo.groupby('id_produto')['total_item'].sum().reset_index()
    valores_agrupados.rename(columns={'total_item': f'valor_{periodo_nome}'}, inplace=True)
    
    # Armazenar nos dicionários
    vendas_por_periodo[periodo_nome] = vendas_agrupadas
    valores_por_periodo[periodo_nome] = valores_agrupados

# Adicionar as vendas por período ao DataFrame de estoque
estoque_com_vendas = estoque_final.copy()

# Mesclar com as vendas e valores de cada período
for periodo_nome, df_vendas_periodo in vendas_por_periodo.items():
    estoque_com_vendas = pd.merge(
        estoque_com_vendas,
        df_vendas_periodo,
        left_on='SKU',
        right_on='id_produto',
        how='left'
    )
    
    # Mesclar com os valores vendidos
    estoque_com_vendas = pd.merge(
        estoque_com_vendas,
        valores_por_periodo[periodo_nome],
        left_on='SKU',
        right_on='id_produto',
        how='left'
    )
    
    # Remover colunas id_produto redundantes
    if 'id_produto_x' in estoque_com_vendas.columns:
        estoque_com_vendas.drop('id_produto_x', axis=1, inplace=True)
    if 'id_produto_y' in estoque_com_vendas.columns:
        estoque_com_vendas.drop('id_produto_y', axis=1, inplace=True)
    if 'id_produto' in estoque_com_vendas.columns:
        estoque_com_vendas.drop('id_produto', axis=1, inplace=True)

# Preencher valores nulos com zero (produtos sem vendas no período)
for periodo_nome in periodos.keys():
    estoque_com_vendas[f'vendas_{periodo_nome}'] = estoque_com_vendas[f'vendas_{periodo_nome}'].fillna(0).astype(int)
    estoque_com_vendas[f'valor_{periodo_nome}'] = estoque_com_vendas[f'valor_{periodo_nome}'].fillna(0).astype(float)

# 10. Identificar produtos mais vendidos em cada período
print("\nTop 5 produtos mais vendidos por período:")
for periodo_nome in periodos.keys():
    coluna_vendas = f'vendas_{periodo_nome}'
    top_produtos = estoque_com_vendas.nlargest(5, coluna_vendas)
    print(f"\n{periodo_nome.replace('_', ' ').title()}:")
    for idx, row in top_produtos.iterrows():
        print(f"- SKU {int(row['SKU'])}: {row['Descrição do Produto'][:50]} - {int(row[coluna_vendas]):,} unidades")

# Mostrar resumo dos valores vendidos nos últimos 30 dias
print("\nResumo dos valores vendidos nos últimos 30 dias:")
valor_total_30dias = estoque_com_vendas['valor_ultimos_30_dias'].sum()
produtos_com_vendas_30dias = (estoque_com_vendas['vendas_ultimos_30_dias'] > 0).sum()
print(f"- Valor total vendido: R$ {valor_total_30dias:,.2f}")
print(f"- Produtos vendidos: {produtos_com_vendas_30dias} SKUs")
print(f"- Ticket médio por produto: R$ {(valor_total_30dias/produtos_com_vendas_30dias if produtos_com_vendas_30dias > 0 else 0):,.2f}")


# 11. Adicionar situação do produto
print("\nClassificando produtos por situação...")
# Preencher valores nulos com zero (produtos sem vendas no período)
for periodo_nome in periodos.keys():
    estoque_com_vendas[f'vendas_{periodo_nome}'] = estoque_com_vendas[f'vendas_{periodo_nome}'].fillna(0).astype(int)

# Consulta SQL para buscar a data da última venda de cada produto
query_ultima_venda = """
SELECT vi.id_produto, MAX(v.data_venda) as ultima_venda
FROM maloka_core.venda_item vi
JOIN maloka_core.venda v ON vi.id_venda = v.id_venda
GROUP BY vi.id_produto
"""

# Consulta SQL para buscar a primeira data de venda de cada produto (histórico anterior a 1 ano)
query_vendas_historicas = """
SELECT vi.id_produto, MIN(v.data_venda) as primeira_venda
FROM maloka_core.venda_item vi
JOIN maloka_core.venda v ON vi.id_venda = v.id_venda
WHERE v.data_venda < %s
GROUP BY vi.id_produto
"""


# Executar consulta para obter produtos com vendas anteriores a 1 ano
conn = psycopg2.connect(
    host= os.getenv("DB_HOST"),
    database="bibicell",
    user= os.getenv("DB_USER"),
    password= os.getenv("DB_PASS"),
    port= os.getenv("DB_PORT"),
)
cursor = conn.cursor()

# Buscar a data da última venda de cada produto
print("Consultando a data da última venda de cada produto...")
cursor.execute(query_ultima_venda)
ultimas_vendas = {row[0]: row[1] for row in cursor.fetchall()}

# Buscar dados para classificação de produtos com histórico antigo
data_um_ano_atras = data_atual - timedelta(days=365)
cursor.execute(query_vendas_historicas, (data_um_ano_atras,))
vendas_historicas = {row[0]: row[1] for row in cursor.fetchall()}

conn.close()

# Adicionar coluna de vendas históricas ao DataFrame principal
estoque_com_vendas['Tem Vendas > 1 ano'] = estoque_com_vendas['SKU'].apply(
    lambda sku: "Sim" if sku in vendas_historicas else "Não"
)

# Adicionar coluna com a data da última venda
estoque_com_vendas['Data Última Venda'] = estoque_com_vendas['SKU'].apply(
    lambda sku: ultimas_vendas.get(sku, None)
)

# Calcular recência (dias desde a última venda)
estoque_com_vendas['Recência (dias)'] = estoque_com_vendas['Data Última Venda'].apply(
    lambda data: (data_atual - data).days if pd.notnull(data) else None
)

# Resumo dos produtos com vendas históricas
produtos_com_vendas_historicas = estoque_com_vendas['Tem Vendas > 1 ano'].value_counts()
print("\n=== PRODUTOS COM HISTÓRICO DE VENDAS ===")
for status, count in produtos_com_vendas_historicas.items():
    percentual = (count / total_skus) * 100
    print(f"- {status}: {count:,} produtos ({percentual:.1f}%)")

# Resumo de recência
produtos_com_venda = estoque_com_vendas['Recência (dias)'].notna().sum()
print(f"\nProdutos com histórico de vendas: {produtos_com_venda} ({produtos_com_venda/total_skus*100:.1f}% do total)")

# Criar função para classificar situação
def classificar_situacao_produto(row):
    # Verificar se teve venda no último ano
    sem_venda_ano = row['vendas_ultimo_ano'] == 0
    
    # Verificar se estoque é zero
    estoque_zero = row['Estoque Total'] == 0
    
    # Verificar se tem vendas históricas (mais de um ano)
    tem_vendas_historicas = row['Tem Vendas > 1 ano'] == "Sim"
    
    # Verificar se nunca teve venda (nenhuma recência registrada)
    nunca_teve_venda = pd.isnull(row['Recência (dias)'])

    # Se nunca teve venda (novo produto)
    if nunca_teve_venda:
        if row['Estoque Total'] > 0:
            return "Novo(sem Venda com Saldo)"
        else:
            return "Novo(sem Venda sem Saldo)"
    
    # Se não teve venda no último ano, mas teve anteriormente
    elif sem_venda_ano:
        if tem_vendas_historicas:
            # Produto com vendas históricas (mais de um ano)
            if estoque_zero:
                return "Inativo (Histórico)"
            else:
                return "Inativo com Saldo (Histórico)"
        else:
            # Produto sem vendas históricas antigas
            if estoque_zero:
                return "Inativo"
            else:
                return "Inativo com Saldo"
    else:
        # Teve vendas no último ano
        if row['Estoque Total'] > 0:
            return "Ativo"
        else:
            return "Ativo sem Estoque"

# Aplicar a classificação
estoque_com_vendas['Situação do Produto'] = estoque_com_vendas.apply(classificar_situacao_produto, axis=1)

# Resumo da situação dos produtos
situacao_counts = estoque_com_vendas['Situação do Produto'].value_counts()
print("\n=== SITUAÇÃO DOS PRODUTOS ===")
for situacao, count in situacao_counts.items():
    percentual = (count / total_skus) * 100
    print(f"- {situacao}: {count:,} produtos ({percentual:.1f}%)")

# Resumo de vendas
print("\nResumo de vendas por período:")
for periodo_nome in periodos.keys():
    coluna_vendas = f'vendas_{periodo_nome}'
    coluna_valores = f'valor_{periodo_nome}'
    total_vendas = estoque_com_vendas[coluna_vendas].sum()
    total_valores = estoque_com_vendas[coluna_valores].sum()
    produtos_vendidos = (estoque_com_vendas[coluna_vendas] > 0).sum()
    print(f"- {periodo_nome.replace('_', ' ').title()}: {total_vendas:,} unidades vendidas em {produtos_vendidos:,} SKUs, valor total: R$ {total_valores:,.2f}")


# 12. Análise de Curva ABC para produtos vendidos nos últimos 90 dias
print("\n=== ANÁLISE DE CURVA ABC (ÚLTIMOS 90 DIAS) ===")
# Filtrar apenas os produtos com vendas nos últimos 90 dias
produtos_com_vendas = estoque_com_vendas[estoque_com_vendas['vendas_ultimos_90_dias'] > 0].copy()

if len(produtos_com_vendas) > 0:
    # Calcular a participação de cada produto no valor total das vendas
    valor_total = produtos_com_vendas['valor_ultimos_90_dias'].sum()
    produtos_com_vendas['participacao'] = produtos_com_vendas['valor_ultimos_90_dias'] / valor_total * 100
    
    # Ordenar por valor de venda decrescente
    produtos_com_vendas = produtos_com_vendas.sort_values('valor_ultimos_90_dias', ascending=False)
    
    # Calcular a participação acumulada
    produtos_com_vendas['participacao_acumulada'] = produtos_com_vendas['participacao'].cumsum()
    
    # Definir as classes ABC
    produtos_com_vendas['curva_abc'] = 'C'
    produtos_com_vendas.loc[produtos_com_vendas['participacao_acumulada'] <= 80, 'curva_abc'] = 'A'
    produtos_com_vendas.loc[(produtos_com_vendas['participacao_acumulada'] > 80) & 
                           (produtos_com_vendas['participacao_acumulada'] <= 95), 'curva_abc'] = 'B'
    
    # Adicionar a classificação ao DataFrame original
    estoque_com_vendas['Curva ABC'] = None
    for idx, row in produtos_com_vendas.iterrows():
        estoque_com_vendas.loc[estoque_com_vendas['SKU'] == row['SKU'], 'Curva ABC'] = row['curva_abc']
    
    # Substituir None por 'Sem Venda' para produtos sem vendas nos últimos 90 dias
    estoque_com_vendas['Curva ABC'] = estoque_com_vendas['Curva ABC'].fillna('Sem Venda')
    
    # Resumo detalhado da classificação ABC
    curva_counts = produtos_com_vendas['curva_abc'].value_counts().sort_index()
    total_produtos_com_vendas = len(produtos_com_vendas)
    
    print("\n=== DETALHAMENTO DA CURVA ABC ===")
    print(f"Total de produtos com vendas nos últimos 90 dias: {total_produtos_com_vendas}")
    
    # Calcular totais por curva
    for curva in ['A', 'B', 'C']:
        if curva in curva_counts:
            count = curva_counts[curva]
            pct_produtos = (count / total_produtos_com_vendas) * 100
            
            # Calcular valor total para esta curva
            valor_curva = produtos_com_vendas[produtos_com_vendas['curva_abc'] == curva]['valor_ultimos_90_dias'].sum()
            pct_valor = (valor_curva / valor_total) * 100
            
            # Calcular estoque médio para esta curva
            estoque_medio = produtos_com_vendas[produtos_com_vendas['curva_abc'] == curva]['Estoque Total'].mean()
            
            print(f"\nCurva {curva}:")
            print(f"- Quantidade de produtos: {count} ({pct_produtos:.1f}% dos produtos com vendas)")
            print(f"- Valor total vendido: R$ {valor_curva:,.2f} ({pct_valor:.1f}% do faturamento)")
            print(f"- Estoque médio atual: {estoque_medio:.1f} unidades por produto")
            
            # Adicionar informação de cobertura de estoque (dias)
            vendas_diarias = produtos_com_vendas[produtos_com_vendas['curva_abc'] == curva]['vendas_ultimos_90_dias'].sum() / 90
            estoque_total_curva = produtos_com_vendas[produtos_com_vendas['curva_abc'] == curva]['Estoque Total'].sum()
            if vendas_diarias > 0:
                cobertura = estoque_total_curva / vendas_diarias
                print(f"- Cobertura média de estoque: {cobertura:.1f} dias")
    
    # Análise de valor por curva
    print("\nDistribuição do valor vendido por Curva ABC (últimos 90 dias):")
    curva_valores = estoque_com_vendas.groupby('Curva ABC')['valor_ultimos_90_dias'].sum()
    for curva, valor in curva_valores.items():
        if valor_total > 0:
            percentual = (valor / valor_total) * 100
            print(f"- Curva {curva}: R$ {valor:,.2f} ({percentual:.1f}%)")
        else:
            print(f"- Curva {curva}: R$ {valor:,.2f} (0.0%)")

else:
    print("Não foram encontrados produtos com vendas nos últimos 90 dias.")
    estoque_com_vendas['Curva ABC'] = 'Sem Venda'

# 13. Análise de cobertura de estoque para produtos ativos
print("\n=== ANÁLISE DE COBERTURA DE ESTOQUE PARA PRODUTOS ATIVOS ===")

# Filtrar apenas produtos ativos
produtos_ativos = estoque_com_vendas[estoque_com_vendas['Situação do Produto'] == 'Ativo'].copy()

# Calcular a cobertura de estoque (em dias) com base nas vendas dos últimos 90 dias
produtos_ativos['vendas_diarias'] = produtos_ativos['vendas_ultimos_90_dias'] / 90
produtos_ativos['cobertura_estoque_dias'] = 0  # Valor padrão

# Evitar divisão por zero
mask = produtos_ativos['vendas_diarias'] > 0
produtos_ativos.loc[mask, 'cobertura_estoque_dias'] = (
    produtos_ativos.loc[mask, 'Estoque Total'] / produtos_ativos.loc[mask, 'vendas_diarias']
)

# Copiar os valores calculados para o DataFrame principal
estoque_com_vendas['Vendas Diárias'] = 0
estoque_com_vendas['Cobertura Estoque (dias)'] = 0

for idx, row in produtos_ativos.iterrows():
    estoque_com_vendas.loc[estoque_com_vendas['SKU'] == row['SKU'], 'Vendas Diárias'] = row['vendas_diarias']
    estoque_com_vendas.loc[estoque_com_vendas['SKU'] == row['SKU'], 'Cobertura Estoque (dias)'] = row['cobertura_estoque_dias']

# Estatísticas da cobertura de estoque
cobertura_stats = produtos_ativos['cobertura_estoque_dias'].describe()

print(f"Total de produtos ativos analisados: {len(produtos_ativos)}")
print("\nEstatísticas de cobertura de estoque (em dias):")
print(f"- Média: {cobertura_stats['mean']:.1f}")
print(f"- Mediana: {cobertura_stats['50%']:.1f}")
print(f"- Mínimo: {cobertura_stats['min']:.1f}")
print(f"- Máximo: {cobertura_stats['max']:.1f}")

# Distribuição da cobertura de estoque
print("\nDistribuição da cobertura de estoque:")
bins = [0, 15, 30, 60, 90, 180, float('inf')]
labels = ['1-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', '91-180 dias', 'Mais de 180 dias']
produtos_ativos['faixa_cobertura'] = pd.cut(produtos_ativos['cobertura_estoque_dias'], bins=bins, labels=labels)
cobertura_dist = produtos_ativos['faixa_cobertura'].value_counts().sort_index()

for faixa, count in cobertura_dist.items():
    pct = (count / len(produtos_ativos)) * 100
    print(f"- {faixa}: {count} produtos ({pct:.1f}%)")

# Adicionar análise por curva ABC
print("\nCobertura média por curva ABC (produtos ativos):")
for curva in ['A', 'B', 'C']:
    produtos_curva = produtos_ativos[produtos_ativos['Curva ABC'] == curva]
    if len(produtos_curva) > 0:
        cobertura_media = produtos_curva['cobertura_estoque_dias'].mean()
        print(f"- Curva {curva}: {cobertura_media:.1f} dias")

# Identificar produtos críticos (cobertura inferior a 15 dias)
produtos_criticos = produtos_ativos[produtos_ativos['cobertura_estoque_dias'] < 15].sort_values('cobertura_estoque_dias')
print(f"\nProdutos ativos com cobertura crítica (menos de 15 dias): {len(produtos_criticos)}")

if len(produtos_criticos) > 0:
    print("\nTop 10 produtos críticos que precisam de reposição urgente:")
    for idx, row in produtos_criticos.head(10).iterrows():
        print(f"- SKU {int(row['SKU'])}: {row['Descrição do Produto'][:50]} - Cobertura: {row['cobertura_estoque_dias']:.1f} dias")

#############################################################################
### Exportar o DataFrame completo com múltiplas abas organizadas por tema ###
#############################################################################

print("\nCriando planilha organizada com múltiplas abas por tema...")

with pd.ExcelWriter(caminho_arquivo_completo, engine='openpyxl', mode='w') as writer:
    # Aba 1: Dados completos
    estoque_com_vendas.to_excel(writer, sheet_name='Análise Completa', index=False)
    
    # Aba 2: Resumo da situação de estoque
    df_estoque_resumo = pd.DataFrame([
        ["Total de SKUs", total_skus, ""],
        ["SKUs com estoque negativo", estoque_negativo, f"{pct_negativo:.1f}%"],
        ["SKUs com estoque zerado", estoque_zerado, f"{pct_zerado:.1f}%"],
        ["SKUs com estoque positivo", estoque_positivo, f"{pct_positivo:.1f}%"],
    ], columns=["Métrica", "Valor", "Percentual"])
    df_estoque_resumo.to_excel(writer, sheet_name='Situação do Estoque', index=False)
    
    # Aba 3: Resumo de vendas por período
    vendas_periodo_data = []
    for periodo_nome in periodos.keys():
        coluna_vendas = f'vendas_{periodo_nome}'
        coluna_valores = f'valor_{periodo_nome}'
        total_vendas = estoque_com_vendas[coluna_vendas].sum()
        total_valores = estoque_com_vendas[coluna_valores].sum()
        produtos_vendidos = (estoque_com_vendas[coluna_vendas] > 0).sum()
        periodo_formatado = periodo_nome.replace('_', ' ').title()
        vendas_periodo_data.append([
            periodo_formatado,
            f"{total_vendas:,}",
            f"{produtos_vendidos:,}",
            f"{total_valores:.2f}"
        ])
    df_vendas_periodo = pd.DataFrame(
        vendas_periodo_data, 
        columns=["Período", "Unidades Vendidas", "SKUs com Venda", "Valor Total (R$)"]
    )
    df_vendas_periodo.to_excel(writer, sheet_name='Vendas por Período', index=False)
    
    # Aba 4: Resumo dos produtos com histórico de vendas
    historico_data = []
    for status, count in produtos_com_vendas_historicas.items():
        percentual = (count / total_skus) * 100
        historico_data.append([status, count, f"{percentual:.1f}%"])
    df_historico = pd.DataFrame(historico_data, columns=["Status", "Quantidade", "Percentual"])
    df_historico.to_excel(writer, sheet_name='Historico de Vendas > 1 ano', index=False)
    
    # Aba 5: Resumo da situação dos produtos
    situacao_data = []
    for situacao, count in situacao_counts.items():
        percentual = (count / total_skus) * 100
        situacao_data.append([situacao, count, f"{percentual:.1f}%"])
    df_situacao = pd.DataFrame(situacao_data, columns=["Situação", "Quantidade", "Percentual"])
    df_situacao.to_excel(writer, sheet_name='Situação dos Produtos', index=False)
    
    # Aba 6: Detalhamento da Curva ABC
    abc_data = []
    abc_data.append(["Total de produtos com vendas (90 dias)", total_produtos_com_vendas, "", "", ""])
    abc_data.append(["", "", "", "", ""])  # Linha em branco
    abc_data.append(["Curva", "Quantidade", "% dos Produtos", "Valor (R$)", "% do Faturamento"])
    
    for curva in ['A', 'B', 'C']:
        if curva in curva_counts:
            count = curva_counts[curva]
            pct_produtos = (count / total_produtos_com_vendas) * 100
            valor_curva = produtos_com_vendas[produtos_com_vendas['curva_abc'] == curva]['valor_ultimos_90_dias'].sum()
            pct_valor = (valor_curva / valor_total) * 100
            abc_data.append([
                curva, 
                count, 
                f"{pct_produtos:.1f}%", 
                f"{valor_curva:.2f}", 
                f"{pct_valor:.1f}%"
            ])
    
    df_abc = pd.DataFrame(abc_data, columns=["Curva ABC", "Quantidade", "% Produtos", "Valor (R$)", "% Faturamento"])
    df_abc.to_excel(writer, sheet_name='Curva ABC', index=False)
    
    # Aba 7: Cobertura de estoque para produtos ativos
    cobertura_data = []
    cobertura_data.append(["Total de produtos ativos analisados", len(produtos_ativos)])
    cobertura_data.append(["", ""])  # Linha em branco
    cobertura_data.append(["Estatística", "Valor (dias)"])
    cobertura_data.append(["Média", f"{cobertura_stats['mean']:.1f}"])
    cobertura_data.append(["Mediana", f"{cobertura_stats['50%']:.1f}"])
    cobertura_data.append(["Mínimo", f"{cobertura_stats['min']:.1f}"])
    cobertura_data.append(["Máximo", f"{cobertura_stats['max']:.1f}"])
    cobertura_data.append(["", ""])  # Linha em branco
    cobertura_data.append(["Distribuição por faixa", ""])
    cobertura_data.append(["", ""])  # Linha em branco
    cobertura_data.append(["Faixa", "Quantidade", "Percentual"])
    
    for faixa, count in cobertura_dist.items():
        pct = (count / len(produtos_ativos)) * 100
        cobertura_data.append([faixa, count, f"{pct:.1f}%"])
    
    cobertura_data.append(["", "", ""])  # Linha em branco
    cobertura_data.append(["Cobertura por curva", "", ""])
    
    for curva in ['A', 'B', 'C']:
        produtos_curva = produtos_ativos[produtos_ativos['Curva ABC'] == curva]
        if len(produtos_curva) > 0:
            cobertura_media = produtos_curva['cobertura_estoque_dias'].mean()
            cobertura_data.append([f"Curva {curva}", f"{cobertura_media:.1f} dias", ""])
            
    df_cobertura = pd.DataFrame(cobertura_data)
    df_cobertura.to_excel(writer, sheet_name='Cobertura de Estoque', index=False, header=False)
    
    # Aba 8: Produtos críticos (cobertura < 15 dias)
    if len(produtos_criticos) > 0:
        produtos_criticos_export = produtos_criticos[[
            'SKU', 'Descrição do Produto', 'Estoque Total', 'vendas_ultimos_90_dias', 
            'cobertura_estoque_dias', 'Curva ABC'
        ]].copy()
        
        produtos_criticos_export = produtos_criticos_export.rename(columns={
            'vendas_ultimos_90_dias': 'Vendas (90 dias)',
            'cobertura_estoque_dias': 'Cobertura (dias)'
        })
        
        produtos_criticos_export.to_excel(writer, sheet_name='Produtos Críticos', index=False)
    else:
        pd.DataFrame({"Mensagem": ["Não há produtos críticos identificados"]}).to_excel(
            writer, sheet_name='Produtos Críticos', index=False
        )

print(f"\nTabela exportada com sucesso para: {caminho_arquivo_completo}")
print("Foram criadas 8 abas organizadas por tema para facilitar a análise.")