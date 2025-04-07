from matplotlib.ticker import FuncFormatter
import pandas as pd
import psycopg2
import dotenv
import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from sklearn.metrics import silhouette_score
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("hostAWS"),
        database="add",
        user= os.getenv("userADD"),
        password= os.getenv("addPass")
    )
    
    print("Conexão estabelecida com sucesso!")

    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela VENDAS...")
    query = "SELECT * FROM vendas"
    
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
    # consulta da tabela vendas_itens
    ########################################################
    
    print("Consultando a tabela VENDA_ITENS...")
    query = "SELECT * FROM venda_itens"
    
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
    # consulta da tabela estoque
    ########################################################
    
    # Consultar a tabela estoque
    print("Consultando a tabela ESTOQUE...")
    query = "SELECT * FROM estoquemovimentos"
    # query = "SELECT DISTINCT ON (id_produto) * FROM estoquemovimentos ORDER BY id_produto, data_movimento DESC;"
    
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
    
    # Exportar para Excel
    df_estoque.to_excel("df_estoque.xlsx", index=False)

    ########################################################
    # consulta da tabela produtos
    ########################################################
    
    # Consultar a tabela produtos
    print("Consultando a tabela PRODUTOS...")
    query = "SELECT * FROM produtos"
    
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
    
    # Exportar para Excel
    # df_produtos.to_excel("df_produtos.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados 'add' existe")
    print("3. As credenciais de conexão estão corretas")

############################################################
#Pre-processamento dos dados
############################################################
df_vendas['data_emissao'] = pd.to_datetime(df_vendas['data_emissao'])

# Filtrar o DataFrame de vendas para manter apenas registros com status começando com 'Pedido'
df_vendas_pedido = df_vendas[df_vendas['status'].str.startswith('Pedido')]

# Fazer um merge para obter apenas os itens de venda relacionados aos pedidos
df_venda_itens_pedido = pd.merge(
    df_venda_itens,
    df_vendas_pedido,
    on='id_venda',
    how='inner'
).merge(
    df_produtos[['id_produto', 'nome', 'critico']],
    on='id_produto',
    how='left'
)
print("Merge realizado com sucesso! VENDA_ITENS_PEDIDO")
print(df_venda_itens_pedido.columns)
print(df_venda_itens_pedido.head())
# df_venda_itens_pedido.to_excel("df_venda_itens_pedido.xlsx", index=False)
df_venda_itens_pedido['data_emissao'] = pd.to_datetime(df_venda_itens_pedido['data_emissao'])
df_venda_itens_pedido['data_faturamento'] = pd.to_datetime(df_venda_itens_pedido['data_faturamento'])


def analisar_giro_estoque_melhorado(df_venda_itens_pedido, df_estoque, df_produtos, periodo='anual', dias_personalizados=None):
    """
    Realiza análise completa de giro de estoque com base nos dados disponíveis
    
    Args:
        df_venda_itens_pedido: DataFrame com dados de itens de venda em pedidos
        df_estoque: DataFrame com dados do estoque
        df_produtos: DataFrame com dados dos produtos
        periodo: String indicando o período para análise ('anual', 'semestral', 'trimestral', 'mensal', 'diario')
        dias_personalizados: Número de dias para análise personalizada quando periodo='diario'
    
    Returns:
        DataFrame com a análise de giro de estoque e dataframes auxiliares para análises adicionais
    """
    print(f"Iniciando análise completa de giro de estoque para o período {periodo}...")
    
    # Converter datas
    df_estoque['data_movimento'] = pd.to_datetime(df_estoque['data_movimento'])
    df_venda_itens_pedido['data_emissao'] = pd.to_datetime(df_venda_itens_pedido['data_emissao'])
    
    # Definir período de análise
    data_atual = datetime.now()
    
    if periodo == 'anual':
        data_inicio = data_atual - timedelta(days=365)
    elif periodo == 'semestral':
        data_inicio = data_atual - timedelta(days=180)
    elif periodo == 'trimestral':
        data_inicio = data_atual - timedelta(days=90)
    elif periodo == 'mensal':
        data_inicio = data_atual - timedelta(days=30)
    elif periodo == 'diario':
        # Se dias_personalizados for fornecido, use-o; caso contrário, use 1 dia como padrão
        dias = dias_personalizados if dias_personalizados is not None else 1
        data_inicio = data_atual - timedelta(days=dias)
    else:
        data_inicio = data_atual - timedelta(days=365)  # Default para anual
    
    # Filtrar dados pelo período
    df_estoque_periodo = df_estoque[df_estoque['data_movimento'] >= data_inicio].copy()
    df_vendas_periodo = df_venda_itens_pedido[df_venda_itens_pedido['data_emissao'] >= data_inicio].copy()
    
    print(f"Período de análise: {data_inicio.strftime('%d/%m/%Y')} até {data_atual.strftime('%d/%m/%Y')}")
    print(f"Total de movimentos de estoque no período: {len(df_estoque_periodo)}")
    print(f"Total de itens vendidos no período: {len(df_vendas_periodo)}")
    
    # 1. Calcular estoque atual por produto (último registro)
    estoque_atual = df_estoque.sort_values(['id_produto', 'data_movimento'], ascending=[True, False])
    estoque_atual = estoque_atual.drop_duplicates('id_produto', keep='first')[['id_produto', 'depois']]
    estoque_atual.rename(columns={'depois': 'estoque_atual'}, inplace=True)
    
    # 2. Calcular estoque médio por produto no período
    # Obter primeiro e último movimento de cada produto no período
    primeiro_movimento = df_estoque_periodo.sort_values(['id_produto', 'data_movimento'])
    primeiro_movimento = primeiro_movimento.drop_duplicates('id_produto', keep='first')[['id_produto', 'antes']]
    primeiro_movimento.rename(columns={'antes': 'estoque_inicial'}, inplace=True)
    
    ultimo_movimento = df_estoque_periodo.sort_values(['id_produto', 'data_movimento'], ascending=[True, False])
    ultimo_movimento = ultimo_movimento.drop_duplicates('id_produto', keep='first')[['id_produto', 'depois']]
    ultimo_movimento.rename(columns={'depois': 'estoque_final'}, inplace=True)
    
    # Mesclar para calcular estoque médio
    estoque_medio = pd.merge(primeiro_movimento, ultimo_movimento, on='id_produto', how='outer')
    estoque_medio['estoque_medio'] = (estoque_medio['estoque_inicial'].fillna(0) + estoque_medio['estoque_final'].fillna(0)) / 2
    
    # 3. Calcular quantidade total vendida por produto no período
    # Somando diretamente da tabela de vendas itens
    vendas_por_produto = df_vendas_periodo.groupby('id_produto')['quantidade'].sum().reset_index()
    vendas_por_produto.rename(columns={'quantidade': 'quantidade_vendida'}, inplace=True)
    
    # 4. Calcular valor total vendido por produto
    valor_vendido = df_vendas_periodo.groupby('id_produto').apply(
        lambda x: (x['quantidade'] * x['valor_unitario']).sum()
    ).reset_index(name='valor_vendido')
    
    # 5. Calcular movimento de saída pelo estoque (como alternativa/confirmação)
    saidas_estoque = df_estoque_periodo[df_estoque_periodo['tipo_movimento'] == 'saída'].groupby('id_produto')['quantidade'].sum().reset_index()
    saidas_estoque.rename(columns={'quantidade': 'saidas_estoque'}, inplace=True)
    
    # 6. Integrar dados do DataFrame de produtos
    produtos_info = df_produtos[['id_produto', 'nome', 'critico']].copy()
    
    # 7. Mesclar todos os dados coletados
    analise_base = estoque_atual.merge(estoque_medio, on='id_produto', how='outer')
    analise_base = analise_base.merge(vendas_por_produto, on='id_produto', how='outer')
    analise_base = analise_base.merge(valor_vendido, on='id_produto', how='outer')
    analise_base = analise_base.merge(saidas_estoque, on='id_produto', how='outer')
    analise_base = analise_base.merge(produtos_info, on='id_produto', how='left')
    
    # 8. Calcular métricas de giro de estoque
    analise_base['quantidade_vendida'] = analise_base['quantidade_vendida'].fillna(0)
    analise_base['valor_vendido'] = analise_base['valor_vendido'].fillna(0)
    analise_base['saidas_estoque'] = analise_base['saidas_estoque'].fillna(0)
    
    # Calcular giro com base na quantidade vendida e estoque médio
    analise_base['giro_quantidade'] = analise_base['quantidade_vendida'] / analise_base['estoque_medio'].where(analise_base['estoque_medio'] > 0, np.nan)
    
    # Ajustar o fator de anualização com base no período
    if periodo == 'mensal':
        analise_base['giro_quantidade_anualizado'] = analise_base['giro_quantidade'] * 12
    elif periodo == 'trimestral':
        analise_base['giro_quantidade_anualizado'] = analise_base['giro_quantidade'] * 4
    elif periodo == 'semestral':
        analise_base['giro_quantidade_anualizado'] = analise_base['giro_quantidade'] * 2
    elif periodo == 'diario':
        # Para análise diária, anualizar multiplicando pelo número de dias em um ano
        dias_no_periodo = dias_personalizados if dias_personalizados is not None else 1
        fator_anual = 365 / dias_no_periodo
        analise_base['giro_quantidade_anualizado'] = analise_base['giro_quantidade'] * fator_anual
    else:
        analise_base['giro_quantidade_anualizado'] = analise_base['giro_quantidade']
    
    # 9. Calcular dias de estoque (cobertura)
    dias_periodo = (data_atual - data_inicio).days
    analise_base['dias_vendendo'] = dias_periodo
    
    # Calcular média diária de vendas
    analise_base['media_diaria_vendas'] = analise_base['quantidade_vendida'] / dias_periodo
    
    # Calcular cobertura de estoque em dias
    analise_base['cobertura_dias'] = analise_base['estoque_atual'] / analise_base['media_diaria_vendas'].where(analise_base['media_diaria_vendas'] > 0, np.nan)
    
    # 10. Classificar produtos por giro
    def classificar_giro(giro):
        if pd.isna(giro):
            return "Sem movimento"
        elif giro > 6:
            return "Giro muito alto"
        elif giro > 4:
            return "Giro alto"
        elif giro > 2:
            return "Giro médio"
        elif giro > 1:
            return "Giro baixo"
        else:
            return "Giro muito baixo"
    
    analise_base['classificacao_giro'] = analise_base['giro_quantidade_anualizado'].apply(classificar_giro)
    
    # 11. Classificação ABC por valor
    analise_base = analise_base.sort_values('valor_vendido', ascending=False).reset_index(drop=True)
    analise_base['valor_acumulado'] = analise_base['valor_vendido'].cumsum()
    analise_base['percentual_acumulado'] = analise_base['valor_acumulado'] / analise_base['valor_vendido'].sum() * 100
    
    def classificar_abc(percentual):
        if percentual <= 80:
            return 'A'
        elif percentual <= 95:
            return 'B'
        else:
            return 'C'
    
    analise_base['classe_abc'] = analise_base['percentual_acumulado'].apply(classificar_abc)
    
    # 12. Identificar produtos críticos e com estoque negativo
    analise_base['estoque_negativo'] = analise_base['estoque_atual'] < 0
    
    # 13. Adicionar flag para produtos críticos com baixo estoque
    analise_base['alerta_estoque'] = (analise_base['estoque_atual'] <= 0) & (analise_base['critico'] == True)
    
    # 14. Calcular taxa de crescimento de vendas (se tivermos dados históricos suficientes)
    if periodo in ['anual', 'semestral']:
        # Dividir o período em duas partes iguais
        meio_periodo = data_inicio + (data_atual - data_inicio) / 2
        
        # Vendas na primeira metade
        vendas_primeira_metade = df_vendas_periodo[df_vendas_periodo['data_emissao'] < meio_periodo]
        vendas_primeira = vendas_primeira_metade.groupby('id_produto')['quantidade'].sum().reset_index()
        vendas_primeira.rename(columns={'quantidade': 'vendas_periodo1'}, inplace=True)
        
        # Vendas na segunda metade
        vendas_segunda_metade = df_vendas_periodo[df_vendas_periodo['data_emissao'] >= meio_periodo]
        vendas_segunda = vendas_segunda_metade.groupby('id_produto')['quantidade'].sum().reset_index()
        vendas_segunda.rename(columns={'quantidade': 'vendas_periodo2'}, inplace=True)
        
        # Mesclar com a análise base
        analise_base = analise_base.merge(vendas_primeira, on='id_produto', how='left')
        analise_base = analise_base.merge(vendas_segunda, on='id_produto', how='left')
        
        # Preencher NaN com zeros
        analise_base['vendas_periodo1'] = analise_base['vendas_periodo1'].fillna(0)
        analise_base['vendas_periodo2'] = analise_base['vendas_periodo2'].fillna(0)
        
        # Calcular taxa de crescimento
        def calcular_crescimento(row):
            if row['vendas_periodo1'] == 0:
                if row['vendas_periodo2'] > 0:
                    return float('inf')  # Crescimento infinito (de 0 para algo)
                else:
                    return 0  # Sem crescimento
            else:
                return ((row['vendas_periodo2'] - row['vendas_periodo1']) / row['vendas_periodo1']) * 100
        
        analise_base['taxa_crescimento'] = analise_base.apply(calcular_crescimento, axis=1)
        
        # Classificar tendência
        def classificar_tendencia(taxa):
            if pd.isna(taxa) or taxa == 0:
                return "Estável"
            elif taxa == float('inf'):
                return "Novo produto"
            elif taxa > 50:
                return "Crescimento forte"
            elif taxa > 20:
                return "Crescimento moderado"
            elif taxa > 5:
                return "Crescimento leve"
            elif taxa > -5:
                return "Estável"
            elif taxa > -20:
                return "Queda leve"
            elif taxa > -50:
                return "Queda moderada"
            else:
                return "Queda forte"
        
        analise_base['tendencia'] = analise_base['taxa_crescimento'].apply(classificar_tendencia)
    
    # 15. Ordenar por giro e valor
    analise_final = analise_base.sort_values(['classe_abc', 'giro_quantidade_anualizado'], 
                                             ascending=[True, False]).reset_index(drop=True)
    
    # Indicadores gerais
    print("\n=== INDICADORES GERAIS DE GIRO DE ESTOQUE ===")
    print(f"Giro médio: {analise_final['giro_quantidade_anualizado'].mean():.2f}")
    print(f"Cobertura média (dias): {analise_final['cobertura_dias'].median():.2f}")
    print(f"Produtos com estoque negativo: {analise_final['estoque_negativo'].sum()}")
    print(f"Produtos críticos com alerta: {analise_final['alerta_estoque'].sum()}")
    
    print("\n=== DISTRIBUIÇÃO POR CLASSE ABC ===")
    print(analise_final['classe_abc'].value_counts())
    
    print("\n=== DISTRIBUIÇÃO POR CLASSIFICAÇÃO DE GIRO ===")
    print(analise_final['classificacao_giro'].value_counts())
    
    # Criar também DataFrames filtrados para facilitar análises específicas
    top_giro = analise_final.nlargest(20, 'giro_quantidade_anualizado')
    sem_giro = analise_final[analise_final['quantidade_vendida'] == 0]
    estoque_negativo = analise_final[analise_final['estoque_negativo'] == True]
    alertas_criticos = analise_final[analise_final['alerta_estoque'] == True]
    
    return analise_final, top_giro, sem_giro, estoque_negativo, alertas_criticos

def visualizar_giro_estoque_melhorado(analise_giro, top_giro, sem_giro, estoque_negativo, alertas_criticos):
    """
    Gera visualizações completas para análise de giro de estoque
    
    Args:
        analise_giro: DataFrame principal com a análise de giro de estoque
        top_giro: DataFrame com produtos de maior giro
        sem_giro: DataFrame com produtos sem giro
        estoque_negativo: DataFrame com produtos com estoque negativo
        alertas_criticos: DataFrame com alertas de produtos críticos
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    diretorio_saida = f'analise_giro'
    
    # Configurar o estilo
    sns.set(style="whitegrid")
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 10
    
    # 1. Distribuição de produtos por classificação de giro
    fig, ax = plt.subplots(figsize=(12, 6))
    cores = sns.color_palette('viridis', n_colors=6)
    classificacao_counts = analise_giro['classificacao_giro'].value_counts()
    explode = [0.1 if x == classificacao_counts.index[0] else 0 for x in classificacao_counts.index]
    
    wedges, texts, autotexts = ax.pie(
        classificacao_counts, 
        labels=classificacao_counts.index, 
        autopct='%1.1f%%', 
        colors=cores, 
        startangle=90, 
        explode=explode,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1}
    )
    
    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_weight('bold')
    
    ax.set_title('Distribuição de Produtos por Classificação de Giro', fontsize=14, pad=20)
    ax.axis('equal')
    
    # Adicionar legenda com valores absolutos
    labels = [f'{idx} ({val} produtos)' for idx, val in zip(classificacao_counts.index, classificacao_counts.values)]
    ax.legend(wedges, labels, title="Classificação", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    
    plt.tight_layout()
    plt.savefig(f'distribuicao_giro.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Top 10 produtos com maior giro (com nomes dos produtos)
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Ordenar e limitar para os 10 principais
    top10 = top_giro.nlargest(10, 'giro_quantidade_anualizado').copy()
    
    # Criar labels com nome e ID do produto
    top10['label'] = top10.apply(lambda x: f"{x['nome'][:15]}... ({x['id_produto']})" 
                             if len(str(x['nome'])) > 15 
                             else f"{x['nome']} ({x['id_produto']})", axis=1)
    
    # Plotar o gráfico
    bars = sns.barplot(x='giro_quantidade_anualizado', y='label', data=top10, palette='viridis')
    
    # Adicionar valores nas barras
    for i, p in enumerate(bars.patches):
        width = p.get_width()
        plt.text(width + 0.3, p.get_y() + p.get_height()/2, f'{width:.1f}', ha='left', va='center')
    
    plt.title('Top 10 Produtos com Maior Giro (Anualizado)', fontsize=14)
    plt.xlabel('Índice de Giro Anualizado', fontsize=12)
    plt.ylabel('Produto', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'top10_giro.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Gráfico de dispersão: Giro de Estoque vs. Valor Vendido com classes ABC
    plt.figure(figsize=(14, 10))
    
    # Filtrar apenas produtos com movimento
    produtos_com_movimento = analise_giro[analise_giro['quantidade_vendida'] > 0].copy()
    
    # Definir cores por classe ABC
    cores_abc = {'A': '#1f77b4', 'B': '#ff7f0e', 'C': '#2ca02c'}
    
    # Criar o gráfico de dispersão
    scatter = sns.scatterplot(
        x='valor_vendido', 
        y='giro_quantidade_anualizado', 
        hue='classe_abc', 
        size='quantidade_vendida',
        sizes=(50, 400),
        alpha=0.7,
        palette=cores_abc,
        data=produtos_com_movimento
    )
    
    # Ajustar o formato dos eixos
    plt.xscale('log')
    formatter = FuncFormatter(lambda x, _: f'R${x:,.0f}' if x >= 1000 else f'R${x:.2f}')
    plt.gca().xaxis.set_major_formatter(formatter)
    
    # Adicionar linhas de referência
    plt.axhline(y=4, color='red', linestyle='--', alpha=0.3, label='Giro Alto (>4)')
    plt.axhline(y=2, color='orange', linestyle='--', alpha=0.3, label='Giro Médio (>2)')
    plt.axhline(y=1, color='blue', linestyle='--', alpha=0.3, label='Giro Baixo (>1)')
    
    # Configuração do gráfico
    plt.title('Relação entre Giro de Estoque e Valor Vendido (com Classificação ABC)', fontsize=14)
    plt.xlabel('Valor Vendido (R$) - Escala Logarítmica', fontsize=12)
    plt.ylabel('Giro de Estoque (Anualizado)', fontsize=12)
    plt.legend(title='Classe ABC', fontsize=10)
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'giro_vs_valor.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. Distribuição de produtos por cobertura de estoque (histograma)
    plt.figure(figsize=(14, 8))
    
    # Filtrar produtos com cobertura calculável e limitar para melhor visualização
    df_cobertura = analise_giro[(analise_giro['cobertura_dias'].notnull()) & 
                               (analise_giro['cobertura_dias'] <= 365)].copy()
    
    # Plotar histograma
    sns.histplot(df_cobertura['cobertura_dias'], bins=30, kde=True)
    
    # Adicionar linhas de referência
    plt.axvline(x=30, color='red', linestyle='--', alpha=0.7, label='1 mês')
    plt.axvline(x=90, color='orange', linestyle='--', alpha=0.7, label='3 meses')
    plt.axvline(x=180, color='green', linestyle='--', alpha=0.7, label='6 meses')
    
    plt.title('Distribuição de Produtos por Cobertura de Estoque', fontsize=14)
    plt.xlabel('Cobertura de Estoque (Dias)', fontsize=12)
    plt.ylabel('Número de Produtos', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'distribuicao_cobertura.png', dpi=300)
    plt.close()
    
    # 5. Mapa de calor: Relação entre Classe ABC e Classificação de Giro
    plt.figure(figsize=(12, 8))
    
    # Criar tabela de contingência
    cross_table = pd.crosstab(analise_giro['classe_abc'], analise_giro['classificacao_giro'])
    
    # Plotar heatmap
    sns.heatmap(cross_table, annot=True, cmap='YlGnBu', fmt='d', cbar_kws={'label': 'Número de Produtos'})
    
    plt.title('Relação entre Classe ABC e Classificação de Giro', fontsize=14)
    plt.xlabel('Classificação de Giro', fontsize=12)
    plt.ylabel('Classe ABC', fontsize=12)
    
    plt.tight_layout()
    plt.savefig(f'abc_vs_giro.png', dpi=300)
    plt.close()
    
    # 6. Gráfico de alertas críticos
    if len(alertas_criticos) > 0:
        plt.figure(figsize=(14, max(6, len(alertas_criticos) * 0.4)))
        
        # Ordenar por classe ABC e depois pelo estoque atual
        alertas_ordenados = alertas_criticos.sort_values(['classe_abc', 'estoque_atual'])
        
        # Criar rótulos para o eixo y
        alertas_ordenados['label'] = alertas_ordenados.apply(
            lambda x: f"{x['nome'][:20]}... ({x['id_produto']})" if len(str(x['nome'])) > 20 
            else f"{x['nome']} ({x['id_produto']})", axis=1
        )
        
        # Definir cores por classe ABC
        cores = alertas_ordenados['classe_abc'].map({'A': '#d62728', 'B': '#ff7f0e', 'C': '#2ca02c'})
        
        # Plotar gráfico de barras horizontais
        bars = plt.barh(alertas_ordenados['label'], alertas_ordenados['estoque_atual'], color=cores, alpha=0.7)
        
        # Adicionar valores nas barras
        for i, p in enumerate(bars):
            width = p.get_width()
            plt.text(width - 0.3 if width < 0 else 0.3, 
                    p.get_y() + p.get_height()/2, 
                    f'{width:.0f}', 
                    ha='right' if width < 0 else 'left', 
                    va='center',
                    color='white' if width < 0 else 'black',
                    fontweight='bold')
        
        plt.axvline(x=0, color='black', linestyle='-', alpha=0.7)
        plt.title('Produtos Críticos com Alerta de Estoque', fontsize=14)
        plt.xlabel('Estoque Atual', fontsize=12)
        plt.grid(True, alpha=0.3)
        
        # Adicionar legenda para classes ABC
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#d62728', markersize=10, label='Classe A'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#ff7f0e', markersize=10, label='Classe B'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#2ca02c', markersize=10, label='Classe C')
        ]
        plt.legend(handles=legend_elements, loc='best')
        
        plt.tight_layout()
        plt.savefig(f'alertas_criticos.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    return

def recomendar_acoes(analise_giro, top_giro, sem_giro, estoque_negativo, alertas_criticos):
    """
    Gera recomendações de ações com base na análise de giro de estoque
    
    Args:
        analise_giro: DataFrame principal com a análise de giro de estoque
        top_giro: DataFrame com produtos de maior giro
        sem_giro: DataFrame com produtos sem giro
        estoque_negativo: DataFrame com produtos com estoque negativo
        alertas_criticos: DataFrame com alertas de produtos críticos
    
    Returns:
        DataFrame com recomendações de ações para cada produto
    """
    # Criar DataFrame para recomendações
    recomendacoes = analise_giro[['id_produto', 'nome', 'classe_abc', 'classificacao_giro', 
                                 'giro_quantidade_anualizado', 'estoque_atual', 'cobertura_dias',
                                 'estoque_negativo', 'alerta_estoque']].copy()
    
    # Definir recomendações com base na classe ABC e giro
    def definir_recomendacao(row):
        recomendacoes = []
        
        # Verificar estoque negativo (prioridade máxima)
        if row['estoque_negativo']:
            recomendacoes.append("URGENTE: Corrigir estoque negativo. Verificar divergências no inventário ou registro de vendas.")
        
        # Verificar alertas críticos
        if row['alerta_estoque']:
            recomendacoes.append("CRÍTICO: Repor estoque imediatamente. Produto crítico com estoque insuficiente.")
        
        # Recomendações baseadas na combinação de classe ABC e giro
        if row['classe_abc'] == 'A':
            if row['classificacao_giro'] in ['Giro muito alto', 'Giro alto']:
                recomendacoes.append("Bom giro, mas classe C: Considerar simplificar gestão ou reduzir variedade.")
            elif row['classificacao_giro'] in ['Giro médio', 'Giro baixo', 'Giro muito baixo']:
                recomendacoes.append("Avaliar descontinuidade ou promoção para redução de estoque.")
            else:  # Sem movimento
                recomendacoes.append("Considerar eliminação do estoque via promoções ou descarte.")
        
        # Recomendações baseadas na cobertura
        if pd.notnull(row['cobertura_dias']):
            if row['cobertura_dias'] > 180:
                recomendacoes.append(f"Estoque elevado: {row['cobertura_dias']:.0f} dias de cobertura. Reduzir compras.")
            elif row['cobertura_dias'] < 7 and row['classe_abc'] in ['A', 'B'] and not row['estoque_negativo']:
                recomendacoes.append(f"Estoque crítico: Apenas {row['cobertura_dias']:.0f} dias de cobertura. Repor com urgência.")
        
        return "; ".join(recomendacoes)
    
    # Aplicar função para gerar recomendações
    recomendacoes['acoes_recomendadas'] = recomendacoes.apply(definir_recomendacao, axis=1)
    
    # Ordenar por prioridade
    recomendacoes['prioridade'] = 0
    recomendacoes.loc[recomendacoes['estoque_negativo'], 'prioridade'] = 3
    recomendacoes.loc[recomendacoes['alerta_estoque'], 'prioridade'] = 2
    recomendacoes.loc[(recomendacoes['classe_abc'] == 'A') & (recomendacoes['classificacao_giro'].isin(['Giro muito alto', 'Giro alto'])), 'prioridade'] = 1
    
    # Ordenar o DataFrame
    recomendacoes_ordenadas = recomendacoes.sort_values(['prioridade', 'classe_abc', 'giro_quantidade_anualizado'], 
                                                       ascending=[False, True, False]).reset_index(drop=True)
    
    return recomendacoes_ordenadas


# Executar a análise melhorada
analise, top_giro, sem_giro, estoque_negativo, alertas_criticos = analisar_giro_estoque_melhorado(
    df_venda_itens_pedido, df_estoque, df_produtos, periodo='anual')
# # Para análise de um único dia:
# analise_diaria, top_giro, sem_giro, estoque_negativo, alertas_criticos = analisar_giro_estoque_melhorado(
#     df_venda_itens_pedido, df_estoque, df_produtos, periodo='diario')

# # Para análise personalizada dos últimos 7 dias:
# analise_semanal, top_giro, sem_giro, estoque_negativo, alertas_criticos = analisar_giro_estoque_melhorado(
#     df_venda_itens_pedido, df_estoque, df_produtos, periodo='diario', dias_personalizados=7)

# Visualizar os resultados
visualizar_giro_estoque_melhorado(analise, top_giro, sem_giro, estoque_negativo, alertas_criticos)

# Gerar recomendações
recomendacoes = recomendar_acoes(analise, top_giro, sem_giro, estoque_negativo, alertas_criticos)

# Exportar resultados (opcional)
analise.to_excel("analise_giro_completa.xlsx", index=False)
recomendacoes.to_excel("recomendacoes_giro_estoque.xlsx", index=False)
