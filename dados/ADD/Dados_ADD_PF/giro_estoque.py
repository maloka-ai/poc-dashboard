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
dotenv.load_dotenv()

try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("DB_HOST"),
        dbname="add_v1",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS"),
        port= os.getenv("DB_PORT"),
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
    
    # EXPORTAR EXCEL
    # df_vendas.to_excel("df_vendas.xlsx", index=False)
    
    ########################################################
    # consulta da tabela vendas_itens
    ########################################################
    
    print("Consultando a tabela VENDA_ITENS...")
    query = "SELECT * FROM vendasitens"
    
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
    
    # EXPORTAR EXCEL
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

############################################################
#Pre-processamento dos dados
############################################################
df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])

# Fazer um merge para obter apenas os itens de venda relacionados aos pedidos
df_venda_itens_pedido = pd.merge(
    df_venda_itens,
    df_vendas,
    on='id_venda',
    how='inner'
).merge(
    df_produtos[['id_produto', 'nome']],
    on='id_produto',
    how='left'
)
print("Merge realizado com sucesso! VENDA_ITENS_PEDIDO")
print(df_venda_itens_pedido.columns)
print(df_venda_itens_pedido.head())

# df_venda_itens_pedido.to_excel("df_venda_itens_pedido.xlsx", index=False)
df_venda_itens_pedido['data_venda'] = pd.to_datetime(df_venda_itens_pedido['data_venda'])

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
    df_venda_itens_pedido['data_venda'] = pd.to_datetime(df_venda_itens_pedido['data_venda'])
    
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
    df_vendas_periodo = df_venda_itens_pedido[df_venda_itens_pedido['data_venda'] >= data_inicio].copy()
    
    print("\n=== PRÉ-ANÁLISE DE GIRO DE ESTOQUE ===")
    print(f"Período de análise: {data_inicio.strftime('%d/%m/%Y')} até {data_atual.strftime('%d/%m/%Y')}")
    print(f"Total de movimentos de estoque no período: {len(df_estoque_periodo)}")
    print(f"Total de itens vendidos no período: {len(df_vendas_periodo)}")
    
    # 1. Calcular estoque atual por produto (último registro)
    estoque_atual = df_estoque.sort_values(['id_produto', 'data_movimento'], ascending=[True, False])
    estoque_atual = estoque_atual.drop_duplicates('id_produto', keep='first')[['id_produto', 'estoque_depois']]
    estoque_atual.rename(columns={'estoque_depois': 'estoque_atual'}, inplace=True)
    
    # 2. Calcular estoque médio por produto no período
    print("Calculando estoque médio diário...")

    # a. Determinar o estoque inicial para o período de análise
    # Pegar o último movimento ANTES do início do período para cada produto
    estoque_antes_periodo = df_estoque[df_estoque['data_movimento'] < data_inicio].sort_values('data_movimento')
    estoque_inicial_periodo = estoque_antes_periodo.drop_duplicates('id_produto', keep='last')[['id_produto', 'estoque_depois']]
    estoque_inicial_periodo = estoque_inicial_periodo.rename(columns={'estoque_depois': 'saldo_diario'})

    # b. Selecionar movimentos DENTRO do período
    movimentos_no_periodo = df_estoque_periodo[['id_produto', 'data_movimento', 'estoque_depois']].copy()
    movimentos_no_periodo = movimentos_no_periodo.rename(columns={'data_movimento': 'data', 'estoque_depois': 'saldo_diario'})

    # c. Criar scaffold (todas as combinações de produto x dia no período)
    todos_produtos = df_estoque['id_produto'].unique() # Usar todos os produtos com qualquer histórico
    datas_periodo = pd.date_range(start=data_inicio, end=data_atual, freq='D')
    idx = pd.MultiIndex.from_product([todos_produtos, datas_periodo], names=['id_produto', 'data'])
    df_scaffold = pd.DataFrame(index=idx).reset_index()

    # d. Mapear o estoque inicial para o scaffold (para preencher dias antes do primeiro movimento no período)
    df_scaffold = pd.merge(df_scaffold, estoque_inicial_periodo.rename(columns={'saldo_diario': 'saldo_inicial'}), on='id_produto', how='left')

    # e. Mapear os movimentos do período para o scaffold (sobrescreverá o saldo inicial nos dias de movimento)
    # Usamos merge para trazer o saldo do dia, se houver movimento.
    df_scaffold = pd.merge(df_scaffold, movimentos_no_periodo, on=['id_produto', 'data'], how='left')

    # f. Determinar o saldo diário final
    # Se houve movimento no dia ('saldo_diario' não é NaN), use-o. Caso contrário, use o 'saldo_inicial'.
    df_scaffold['saldo_calculado'] = df_scaffold['saldo_diario'].combine_first(df_scaffold['saldo_inicial'])

    # g. Propagar o último saldo conhecido para frente (forward fill) dentro de cada grupo de produto
    df_scaffold = df_scaffold.sort_values(['id_produto', 'data'])
    # Crucial: O fillna(0) antes do ffill garante que produtos que surgiram DO NADA antes do período comecem com 0.
    # O ffill propaga o último saldo conhecido.
    # O fillna(0) DEPOIS do ffill trata produtos que podem ter sido criados DENTRO do período (começando com NaN).
    df_scaffold['saldo_calculado'] = df_scaffold.groupby('id_produto')['saldo_calculado'].fillna(0).ffill().fillna(0)

    # h. Calcular a média do saldo diário por produto
    estoque_medio_df = df_scaffold.groupby('id_produto')['saldo_calculado'].mean().reset_index()
    estoque_medio_df.rename(columns={'saldo_calculado': 'estoque_medio'}, inplace=True)

    # Limpeza de memória (opcional, mas bom para DataFrames grandes)
    del estoque_antes_periodo, estoque_inicial_periodo, movimentos_no_periodo
    del df_scaffold
    print("Cálculo do estoque médio diário concluído.")
    
    # 3. Calcular quantidade total vendida por produto no período
    # Somando diretamente da tabela de vendas itens
    vendas_por_produto = df_vendas_periodo.groupby('id_produto')['quantidade'].sum().reset_index()
    vendas_por_produto.rename(columns={'quantidade': 'quantidade_vendida'}, inplace=True)
    
    # 4. Calcular valor total vendido por produto
    valor_vendido = df_vendas_periodo.groupby('id_produto').apply(
        lambda x: (x['quantidade'] * x['preco_bruto']).sum()
    ).reset_index(name='valor_vendido')
    
    # 5. Calcular movimento de saída pelo estoque (como alternativa/confirmação)
    saidas_estoque = df_estoque_periodo[df_estoque_periodo['tipo'] == 'S'].groupby('id_produto')['quantidade'].sum().reset_index()
    saidas_estoque.rename(columns={'quantidade': 'saidas_estoque'}, inplace=True)
    
    # 6. Integrar dados do DataFrame de produtos
    produtos_info = df_produtos[['id_produto', 'nome']].copy()
    
    # 7. Mesclar todos os dados coletados
    analise_base = estoque_atual.merge(estoque_medio_df, on='id_produto', how='outer')
    analise_base = analise_base.merge(vendas_por_produto, on='id_produto', how='outer')
    analise_base = analise_base.merge(valor_vendido, on='id_produto', how='outer')
    analise_base = analise_base.merge(saidas_estoque, on='id_produto', how='outer')
    analise_base = analise_base.merge(produtos_info, on='id_produto', how='left')

    # Preencher NaNs no estoque_medio para produtos sem histórico de estoque no período, se necessário
    # Se um produto existe mas nunca teve estoque, a média será NaN. Podemos definir como 0.
    analise_base['estoque_medio'] = analise_base['estoque_medio'].fillna(0)
    
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
    
    # 11. Classificação ABC apenas para produtos com movimentação no último mês
    
    # Definir período de um mês
    data_inicio_mes = data_atual - timedelta(days=30)

    # Filtrar vendas do último mês
    df_vendas_ultimo_mes = df_venda_itens_pedido[df_venda_itens_pedido['data_venda'] >= data_inicio_mes].copy()
    
    # Criar um DataFrame com IDs de produtos que tiveram movimentação no último mês
    produtos_com_movimentacao = df_vendas_ultimo_mes['id_produto'].unique()
    
    # Identificar produtos com movimentação no último mês
    analise_base['movimentou_ultimo_mes'] = analise_base['id_produto'].isin(produtos_com_movimentacao)
    
    # Filtrar apenas produtos com movimentação no último mês para classificação ABC
    produtos_movimentados = analise_base[analise_base['movimentou_ultimo_mes']].copy()
    
    # Ordenar por valor vendido para classificação ABC
    produtos_movimentados = produtos_movimentados.sort_values('valor_vendido', ascending=False).reset_index(drop=True)
    
    # Calcular valor acumulado e percentual acumulado para classificação ABC
    produtos_movimentados['valor_acumulado'] = produtos_movimentados['valor_vendido'].cumsum()
    produtos_movimentados['percentual_acumulado'] = produtos_movimentados['valor_acumulado'] / produtos_movimentados['valor_vendido'].sum() * 100
    
    # Definir limites para classificação ABC (apenas para produtos com movimentação)
    total_produtos_movimentados = len(produtos_movimentados)
    limite_a = int(total_produtos_movimentados * 0.2)  # 20% dos produtos
    limite_b = int(total_produtos_movimentados * 0.5)  # 50% dos produtos (20% + 30%)
    
    # Função para classificação ABC
    def classificar_abc_por_quantidade(posicao, limite_a, limite_b):
        if posicao < limite_a:
            return 'A'
        elif posicao < limite_b:
            return 'B'
        else:
            return 'C'
    
    # Aplicar classificação ABC apenas para produtos com movimentação
    produtos_movimentados['classe_abc'] = produtos_movimentados.index.map(
        lambda x: classificar_abc_por_quantidade(x, limite_a, limite_b)
    )
    
    # Criar um mapeamento de id_produto para classe_abc
    mapeamento_abc = dict(zip(produtos_movimentados['id_produto'], produtos_movimentados['classe_abc']))
    
    # Aplicar classificação na análise base (produtos sem movimentação ficam vazios)
    analise_base['classe_abc'] = analise_base['id_produto'].map(
        lambda x: mapeamento_abc.get(x, '') if x in mapeamento_abc else ''
    )

    # 12. Identificar produtos críticos e com estoque negativo
    analise_base['estoque_negativo'] = analise_base['estoque_atual'] < 0
    
    # 13. Adicionar flag para produtos críticos com baixo estoque
    analise_base['alerta_estoque'] = (analise_base['estoque_atual'] <= 0)
    
    # 14. Calcular taxa de crescimento de vendas (se tivermos dados históricos suficientes)
    if periodo in ['anual', 'semestral']:
        # Dividir o período em duas partes iguais
        meio_periodo = data_inicio + (data_atual - data_inicio) / 2
        
        # Vendas na primeira metade
        vendas_primeira_metade = df_vendas_periodo[df_vendas_periodo['data_venda'] < meio_periodo]
        vendas_primeira = vendas_primeira_metade.groupby('id_produto')['quantidade'].sum().reset_index()
        vendas_primeira.rename(columns={'quantidade': 'vendas_periodo1'}, inplace=True)
        
        # Vendas na segunda metade
        vendas_segunda_metade = df_vendas_periodo[df_vendas_periodo['data_venda'] >= meio_periodo]
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
    
    # 15. Ordenar por classificação ABC (A, B, C primeiro) e giro
    analise_base['ordem_abc'] = analise_base['classe_abc'].map({'A': 1, 'B': 2, 'C': 3, '': 4})
    analise_final = analise_base.sort_values(['ordem_abc', 'giro_quantidade_anualizado'], 
                                           ascending=[True, False]).reset_index(drop=True)
    analise_final.drop('ordem_abc', axis=1, inplace=True)
    
    # Indicadores gerais
    print("\n=== INDICADORES GERAIS DE GIRO DE ESTOQUE ===")
    print(f"Giro médio: {analise_final['giro_quantidade_anualizado'].mean():.2f}")
    print(f"Cobertura média (dias): {analise_final['cobertura_dias'].median():.2f}")
    print(f"Produtos com estoque negativo: {analise_final['estoque_negativo'].sum()}")
    print(f"Produtos críticos com alerta: {analise_final['alerta_estoque'].sum()}")

    print("\n=== DISTRIBUIÇÃO POR CLASSIFICAÇÃO DE GIRO ===")
    print(analise_final['classificacao_giro'].value_counts())

    print("\n=== PRODUTOS COM MOVIMENTAÇÃO NO ÚLTIMO MÊS ===")
    print(f"Período de análise da curva ABC: {data_inicio_mes.strftime('%d/%m/%Y')} até {data_atual.strftime('%d/%m/%Y')}")
    print(f"Total de produtos com movimentação: {analise_final['movimentou_ultimo_mes'].sum()}")
    print(f"Total de produtos sem movimentação: {len(analise_final) - analise_final['movimentou_ultimo_mes'].sum()}")   
    
    print("\n=== DISTRIBUIÇÃO POR CLASSE ABC ===")
    print(analise_final['classe_abc'].value_counts(dropna=False))
    
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
    
    ########################################################
    # Gráfico distribuição de Giro
    ########################################################
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
    # plt.savefig(f'distribuicao_giro.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    ########################################################
    # Gráfico distribuição de Cobertura
    ########################################################
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
    # plt.savefig(f'distribuicao_cobertura.png', dpi=300)
    plt.close()
    
    ########################################################
    # Gráfico ABC vs Giro
    ########################################################
    plt.figure(figsize=(12, 8))
    
    # Criar tabela de contingência
    cross_table = pd.crosstab(analise_giro['classe_abc'], analise_giro['classificacao_giro'])
    
    # Plotar heatmap
    sns.heatmap(cross_table, annot=True, cmap='YlGnBu', fmt='d', cbar_kws={'label': 'Número de Produtos'})
    
    plt.title('Relação entre Classe ABC e Classificação de Giro', fontsize=14)
    plt.xlabel('Classificação de Giro', fontsize=12)
    plt.ylabel('Classe ABC', fontsize=12)
    
    plt.tight_layout()
    # plt.savefig(f'abc_vs_giro.png', dpi=300)
    plt.close()

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
    recomendacoes = analise_giro[['id_produto', 
        'nome', 
        'classe_abc', 
        'classificacao_giro', 
        'giro_quantidade_anualizado', 
        'estoque_atual', 
        'cobertura_dias',
        'estoque_negativo', 
        'alerta_estoque'
    ]].copy()
    
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

# Exportar resultados
# Obter o diretório do script atual
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# Construir os caminhos completos para os arquivos de saída
caminho_analise = os.path.join(diretorio_atual, "analise_giro_completa.xlsx")
caminho_recomendacoes = os.path.join(diretorio_atual, "recomendacoes_giro_estoque.xlsx")

# Exportar os arquivos para o diretório do script
print(f"Exportando análise para: {caminho_analise}")
analise.to_excel(caminho_analise, index=False)

print(f"Exportando recomendações para: {caminho_recomendacoes}")
recomendacoes.to_excel(caminho_recomendacoes, index=False)

print("Exportação concluída com sucesso!")
