from datetime import datetime, timedelta
import pandas as pd
import dotenv
import os
import warnings
import psycopg2
import numpy as np

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
    
    print("Consultando a tabela VENDAS...")
    query = """
    SELECT id_venda, id_cliente, data_venda, total_venda
    FROM maloka_core.venda
    """
    
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
    # df_vendas.to_excel("df_vendas_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela venda_itens
    ########################################################
    
    print("Consultando a tabela VENDA_ITEM...")
    query = """
    SELECT id_venda_item, id_venda, id_produto, quantidade, total_item
    FROM maloka_core.venda_item
    """
    
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
    # df_venda_itens.to_excel("df_venda_itens_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela produto
    ########################################################
    
    print("Consultando a tabela PRODUTO...")
    query = """
    SELECT id_produto, nome AS nome_produto, id_categoria, preco_custo
    FROM maloka_core.produto
    """
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_produto = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_produto)
    num_colunas = len(df_produto.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_produto.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_produto.head())
    
    # Exportar para Excel
    # df_produto.to_excel("df_produto_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela compra
    ########################################################
    
    print("Consultando a tabela COMPRA...")
    query = """
    SELECT id_compra, id_fornecedor, data_compra, total_compra
    FROM maloka_core.compra
    """
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_compra = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_compra)
    num_colunas = len(df_compra.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_compra.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_compra.head())
    
    # Exportar para Excel
    # df_compra.to_excel("df_compra_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela compra
    ########################################################
    
    print("Consultando a tabela COMPRA_ITEM...")
    query = "SELECT * FROM maloka_core.compra_item"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_compra_item = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_compra_item)
    num_colunas = len(df_compra_item.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_compra_item.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_compra_item.head())
    
    # Exportar para Excel
    # df_compra_item.to_excel("df_compra_item_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela fornecedor
    ########################################################
    
    print("Consultando a tabela FORNECEDOR...")
    query = """
    SELECT id_fornecedor, cpf_cnpj, nome AS nome_fornecedor
    FROM maloka_core.fornecedor
    """
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_fornecedor = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_fornecedor)
    num_colunas = len(df_fornecedor.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_fornecedor.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_fornecedor.head())
    
    # Exportar para Excel
    # df_fornecedor.to_excel("df_fornecedor_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela estoque_movimento
    ########################################################
    
    print("Consultando a tabela ESTOQUE_MOVIMENTO...")
    query = """
    SELECT id_estoque_movimento, id_produto, quantidade, data_movimento, tipo, estoque_depois
    FROM maloka_core.estoque_movimento
    """
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_estoque_movimento = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_estoque_movimento)
    num_colunas = len(df_estoque_movimento.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_estoque_movimento.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_estoque_movimento.head())
    
    # Exportar para Excel
    # df_estoque_movimento.to_excel("df_estoque_movimento_BD.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")

print("\n# Iniciando análise para recomendação de compras...")

# Processando os dados para análise
try:
    # Converter data_venda para datetime
    df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
    
    # Mesclar vendas e itens de venda
    df_vendas_completo = df_vendas.merge(
        df_venda_itens, 
        on='id_venda', 
        how='left'
    )
    
    # Adicionar informações do produto
    df_vendas_completo = df_vendas_completo.merge(
        df_produto[['id_produto', 'nome_produto', 'preco_custo']],
        on='id_produto',
        how='left'
    )
    
    print(f"Dados de vendas processados: {len(df_vendas_completo)} registros")
    
    # Calcular data atual e período de análise
    data_atual = datetime.now()
    periodo_12_meses = data_atual - timedelta(days=364)
    
    # Filtrar vendas dos últimos 12 meses
    df_vendas_1ano = df_vendas_completo[df_vendas_completo['data_venda'] >= periodo_12_meses].copy()
    
    print(f"Vendas no último ano: {len(df_vendas_1ano)} registros")
    
    #Calcular diretamente com dados do último ano (12 meses)
    vendas_mensais_12m = df_vendas_1ano.groupby('id_produto').agg(
        quantidade_total_12m=('quantidade', 'sum'),
        valor_total_12m=('total_item', 'sum'),
        transacoes_12m=('id_venda', 'nunique')
    ).reset_index()
    
    # Calcular média mensal (dividindo por 12 meses)
    vendas_mensais_12m['media_12m_qtd'] = vendas_mensais_12m['quantidade_total_12m'] / 12
    vendas_mensais_12m['media_mensal_valor'] = vendas_mensais_12m['valor_total_12m'] / 12

    # Adicionar análise de consumo mês a mês no último ano
    print("Calculando consumo mês a mês no último ano...")
    
    # Extrair mês e ano de cada venda
    df_vendas_1ano['mes_ano'] = df_vendas_1ano['data_venda'].dt.strftime('%Y-%m')
    # df_vendas_1ano.to_excel("df_vendas_1ano.xlsx", index=False)

    # Criar tabela pivô com o consumo mensal por produto
    consumo_mensal = df_vendas_1ano.pivot_table(
        index='id_produto',
        columns='mes_ano',
        values='quantidade',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    
    # Obter lista de todos os meses no período analisado (em ordem cronológica)
    meses_ordenados = sorted(df_vendas_1ano['mes_ano'].unique())

    print("\nMeses incluídos na análise de consumo:")
    print(', '.join(meses_ordenados))
    
    # Renomear colunas para incluir prefixo 'qtd_'
    colunas_renomeadas = {mes: f'qtd_vendas_{mes}' for mes in meses_ordenados}
    consumo_mensal = consumo_mensal.rename(columns=colunas_renomeadas)
    
    print(f"Consumo mensal calculado para {len(consumo_mensal)} produtos ao longo de {len(meses_ordenados)} meses")
    # Calcular a média de vendas mensais por produto, mas apenas para produtos vendidos no último ano
    produtos_vendidos_ultimo_ano = df_vendas_1ano['id_produto'].unique()

    # Obter estoque atual por produto
    df_estoque_atual = df_estoque_movimento.sort_values('data_movimento', ascending=False)
    df_estoque_atual = df_estoque_atual.drop_duplicates(subset=['id_produto'])
    df_estoque_atual = df_estoque_atual[['id_produto', 'estoque_depois', 'data_movimento']]
    df_estoque_atual = df_estoque_atual.rename(columns={'estoque_depois': 'estoque_atual', 
                                                      'data_movimento': 'data_ultima_movimentacao'})
    
    # Combinar médias de vendas com estoque atual
    df_recomendacao = vendas_mensais_12m.merge(
        df_estoque_atual,
        on='id_produto',
        how='left'
    )
    
    # Adicionar informações do produto
    df_recomendacao = df_recomendacao.merge(
        df_produto[['id_produto', 'nome_produto', 'preco_custo']],
        on='id_produto',
        how='left'
    )
    
    # Calcular métricas de recomendação
    df_recomendacao['estoque_atual'] = df_recomendacao['estoque_atual'].fillna(0)
    df_recomendacao['cobertura_meses'] = df_recomendacao.apply(
        lambda x: 0 if x['estoque_atual'] <= 0 else 
                (x['estoque_atual'] / x['media_12m_qtd'] if x['media_12m_qtd'] > 0 else float('inf')),
        axis=1
    )
    
    # Calcular sugestão de compra para 3 meses de estoque
    df_recomendacao['sugestao_3m'] = df_recomendacao.apply(
        lambda x: 0 if x['media_12m_qtd'] <= 0 else (
            # Para estoque negativo: 3 meses de estoque + compensação do negativo
            (3 * x['media_12m_qtd'] - x['estoque_atual']) if x['estoque_atual'] < 0 
            # Para estoque positivo: complemento até 3 meses, se necessário
            else max(0, 3 * x['media_12m_qtd'] - x['estoque_atual'])
        ),
        axis=1
    )
    
    # Arredondar sugestão para cima (não queremos frações de produtos)
    df_recomendacao['sugestao_3m'] = np.ceil(df_recomendacao['sugestao_3m'])
    
    # Calcular sugestão de compra para 1 mês de estoque
    df_recomendacao['sugestao_1m'] = df_recomendacao.apply(
        lambda x: 0 if x['media_12m_qtd'] <= 0 else (
            # Para estoque negativo: 1 mês de estoque + compensação do negativo
            (1 * x['media_12m_qtd'] - x['estoque_atual']) if x['estoque_atual'] < 0 
            # Para estoque positivo: complemento até 1 mês, se necessário
            else max(0, 1 * x['media_12m_qtd'] - x['estoque_atual'])
        ),
        axis=1
    )
    
    # Arredondar sugestão para cima (não queremos frações de produtos)
    df_recomendacao['sugestao_1m'] = np.ceil(df_recomendacao['sugestao_1m'])
    
    # Calcular valor estimado da compra sugerida
    df_recomendacao['valor_estimado_compra_3m'] = df_recomendacao['sugestao_3m'] * df_recomendacao['preco_custo']
    df_recomendacao['valor_estimado_compra_1m'] = df_recomendacao['sugestao_1m'] * df_recomendacao['preco_custo']
    
    # Classificar criticidade do estoque
    def classificar_criticidade(cobertura):
        if cobertura < 0.3:  # Menos de 30%
            return "CRÍTICO"
        elif cobertura < 0.5:  # Entre 30% e 50%
            return "MUITO BAIXO"
        elif cobertura < 0.8:  # Entre 50% e 80%
            return "BAIXO"
        elif cobertura <= 1.0:  # Entre 80% e 100%
            return "ADEQUADO"
        else:  # Acima de 100%
            return "EXCESSO"
    
    df_recomendacao['criticidade'] = df_recomendacao['cobertura_meses'].apply(classificar_criticidade)

    # Obter as últimas 3 compras para cada produto (última, penúltima e antepenúltima)
    print("Processando histórico de compras para obter últimas 3 aquisições...")
    df_historico_compras = df_compra_item.merge(df_compra, on='id_compra', how='left')
    df_historico_compras = df_historico_compras.sort_values(['id_produto', 'data_compra'], ascending=[True, False])

    # Função para extrair as 3 compras mais recentes por produto
    ultimas_compras_dict = {}
    penultimas_compras_dict = {}
    antepenultimas_compras_dict = {}

    for produto_id in df_historico_compras['id_produto'].unique():
        # Filtrar compras deste produto e ordená-las por data (mais recente primeiro)
        compras_produto = df_historico_compras[df_historico_compras['id_produto'] == produto_id]
        compras_produto = compras_produto.sort_values('data_compra', ascending=False)
        
        # Adicionar última compra
        if len(compras_produto) >= 1:
            ultima = compras_produto.iloc[0]
            ultimas_compras_dict[produto_id] = {
                'id_fornecedor': ultima['id_fornecedor'],
                'preco_bruto': ultima['preco_bruto'],
                'data_compra': ultima['data_compra'],
                'quantidade': ultima['quantidade']
            }
        
        # Adicionar penúltima compra
        if len(compras_produto) >= 2:
            penultima = compras_produto.iloc[1]
            penultimas_compras_dict[produto_id] = {
                'id_fornecedor': penultima['id_fornecedor'],
                'preco_bruto': penultima['preco_bruto'],
                'data_compra': penultima['data_compra'],
                'quantidade': penultima['quantidade']
            }
        
        # Adicionar antepenúltima compra
        if len(compras_produto) >= 3:
            antepenultima = compras_produto.iloc[2]
            antepenultimas_compras_dict[produto_id] = {
                'id_fornecedor': antepenultima['id_fornecedor'],
                'preco_bruto': antepenultima['preco_bruto'],
                'data_compra': antepenultima['data_compra'],
                'quantidade': antepenultima['quantidade']
            }

    # Converter dicionários para DataFrames
    df_ultima_compra = pd.DataFrame.from_dict(ultimas_compras_dict, orient='index').reset_index()
    if not df_ultima_compra.empty:
        df_ultima_compra.rename(columns={
            'index': 'id_produto',
            'preco_bruto': 'ultimo_preco_compra',
            'data_compra': 'data_ultima_compra',
            'quantidade': 'ultima_qtd_comprada'
        }, inplace=True)

    df_penultima_compra = pd.DataFrame.from_dict(penultimas_compras_dict, orient='index').reset_index()
    if not df_penultima_compra.empty:
        df_penultima_compra.rename(columns={
            'index': 'id_produto',
            'preco_bruto': 'penultimo_preco_compra',
            'data_compra': 'data_penultima_compra',
            'quantidade': 'penultima_qtd_comprada'
        }, inplace=True)

    df_antepenultima_compra = pd.DataFrame.from_dict(antepenultimas_compras_dict, orient='index').reset_index()
    if not df_antepenultima_compra.empty:
        df_antepenultima_compra.rename(columns={
            'index': 'id_produto',
            'preco_bruto': 'antepenultimo_preco_compra',
            'data_compra': 'data_antepenultima_compra',
            'quantidade': 'antepenultima_qtd_comprada'
        }, inplace=True)

    # Adicionar informações de fornecedor para cada compra
    if not df_ultima_compra.empty:
        df_ultima_compra = df_ultima_compra.merge(
            df_fornecedor[['id_fornecedor', 'nome_fornecedor']],
            on='id_fornecedor',
            how='left'
        )
        df_ultima_compra.rename(columns={'nome_fornecedor': 'ultimo_fornecedor'}, inplace=True)

    if not df_penultima_compra.empty:
        df_penultima_compra = df_penultima_compra.merge(
            df_fornecedor[['id_fornecedor', 'nome_fornecedor']],
            on='id_fornecedor',
            how='left'
        )
        df_penultima_compra.rename(columns={'nome_fornecedor': 'penultimo_fornecedor'}, inplace=True)

    if not df_antepenultima_compra.empty:
        df_antepenultima_compra = df_antepenultima_compra.merge(
            df_fornecedor[['id_fornecedor', 'nome_fornecedor']],
            on='id_fornecedor',
            how='left'
        )
        df_antepenultima_compra.rename(columns={'nome_fornecedor': 'antepenultimo_fornecedor'}, inplace=True)

    # Adicionar informações das compras ao dataframe de recomendação
    colunas_ultima = ['id_produto', 'ultimo_preco_compra', 'data_ultima_compra', 'ultimo_fornecedor', 'ultima_qtd_comprada']
    colunas_penultima = ['id_produto', 'penultimo_preco_compra', 'data_penultima_compra', 'penultimo_fornecedor', 'penultima_qtd_comprada']
    colunas_antepenultima = ['id_produto', 'antepenultimo_preco_compra', 'data_antepenultima_compra', 'antepenultimo_fornecedor', 'antepenultima_qtd_comprada']

    if not df_ultima_compra.empty:
        df_recomendacao = df_recomendacao.merge(
            df_ultima_compra[colunas_ultima],
            on='id_produto',
            how='left'
        )

    if not df_penultima_compra.empty:
        df_recomendacao = df_recomendacao.merge(
            df_penultima_compra[colunas_penultima],
            on='id_produto',
            how='left'
        )

    if not df_antepenultima_compra.empty:
        df_recomendacao = df_recomendacao.merge(
            df_antepenultima_compra[colunas_antepenultima],
            on='id_produto',
            how='left'
        )

    # Adicionar consumo mensal do último ano
    df_recomendacao = df_recomendacao.merge(
        consumo_mensal,
        on='id_produto',
        how='left'
    )
    
    # Preencher valores nulos do consumo mensal com zero
    colunas_consumo = [col for col in df_recomendacao.columns if col.startswith('qtd_vendas_')]
    df_recomendacao[colunas_consumo] = df_recomendacao[colunas_consumo].fillna(0)

    # Calcular média móvel de 3 meses (3M) para cada produto
    print("Calculando média móvel de 3 meses (media_3m)...")
    
    # Ordenar meses cronologicamente
    meses_ordenados_decrescente = sorted(meses_ordenados, reverse=False)
    
    # Se tivermos pelo menos 3 meses de dados
    if len(meses_ordenados_decrescente) >= 3:
        # Pegar os 3 últimos meses
        ultimos_3_meses = meses_ordenados_decrescente[-3:]
        print(f"Calculando média móvel com base nos meses: {', '.join(ultimos_3_meses)}")
        
        # Calcular média dos últimos 3 meses
        df_recomendacao['media_3m'] = 0  # Inicializar coluna
        
        for produto_idx in df_recomendacao.index:
            soma_3_meses = 0
            for mes in ultimos_3_meses:
                coluna = f'qtd_vendas_{mes}'
                if coluna in df_recomendacao.columns:
                    soma_3_meses += df_recomendacao.at[produto_idx, coluna]
            
            # Calcular média dos últimos 3 meses
            df_recomendacao.at[produto_idx, 'media_3m'] = soma_3_meses / len(ultimos_3_meses)
        
        # Arredondar para 2 casas decimais
        df_recomendacao['media_3m'] = df_recomendacao['media_3m'].round(2)
    else:
        # Se não tivermos pelo menos 3 meses, usar a média mensal geral
        print("Não há dados suficientes para calcular média móvel de 3 meses. Usando média mensal geral.")
        df_recomendacao['media_3m'] = df_recomendacao['media_12m_qtd']

    print("Histórico de compras processado com sucesso!")
    
    # Ordenar por criticidade e valor de venda
    ordem_criticidade = {
        "CRÍTICO": 1,
        "MUITO BAIXO": 2,
        "BAIXO": 3,
        "ADEQUADO": 4,
        "EXCESSO": 5
    }

    df_recomendacao['ordem_criticidade'] = df_recomendacao['criticidade'].map(ordem_criticidade)
    df_recomendacao = df_recomendacao.sort_values(['ordem_criticidade'], ascending=[True])
    
    # Obter colunas de consumo mensal
    colunas_consumo = [col for col in df_recomendacao.columns if col.startswith('qtd_vendas_')]
    
    # Selecionar e reorganizar colunas para o relatório final
    colunas_finais = [
        'id_produto', 
        'nome_produto', 
        'estoque_atual', 
        'media_12m_qtd',
        'media_3m',
        'cobertura_meses', 
        'criticidade', 
        'sugestao_1m',
        'valor_estimado_compra_1m',
        'sugestao_3m',
        'valor_estimado_compra_3m',
        # Última compra
        'ultimo_preco_compra',
        'ultima_qtd_comprada',
        'ultimo_fornecedor', 
        'data_ultima_compra',
        # Penúltima compra
        'penultimo_preco_compra',
        'penultima_qtd_comprada',
        'penultimo_fornecedor',
        'data_penultima_compra',
        # Antepenúltima compra
        'antepenultimo_preco_compra',
        'antepenultima_qtd_comprada',
        'antepenultimo_fornecedor',
        'data_antepenultima_compra',
        # Outras informações
        'data_ultima_movimentacao',
        'transacoes_12m', 
        'quantidade_total_12m', 
        'valor_total_12m'
    ]

    # Adicionar colunas de consumo mensal à lista de colunas finais
    colunas_finais.extend(sorted(colunas_consumo))
    
    # Manter apenas as colunas que existem
    colunas_existentes = [col for col in colunas_finais if col in df_recomendacao.columns]
    df_recomendacao_final = df_recomendacao[colunas_existentes].copy()
    
    # Formatar valores decimais
    for col in ['media_12m_qtd', 'media_3m', 'cobertura_meses', 'valor_estimado_compra_3m', 'valor_estimado_compra_1m']:
        if col in df_recomendacao_final.columns:
            df_recomendacao_final[col] = df_recomendacao_final[col].round(2)
    
    # Exportar para CSV
    nome_arquivo = f"metricas_de_compra.csv"
    caminho_arquivo = os.path.join(diretorio_atual, nome_arquivo)
    df_recomendacao_final.to_csv(caminho_arquivo, index=False)
    
    print(f"\nAnálise concluída com sucesso!")
    print(f"Foram analisados {len(df_recomendacao_final)} produtos.")
    
    # Mostrar resumo por criticidade
    resumo_criticidade = df_recomendacao_final['criticidade'].value_counts().to_dict()
    print("\nResumo por criticidade:")
    for nivel, quantidade in sorted(resumo_criticidade.items(), key=lambda x: ordem_criticidade.get(x[0], 999)):
        print(f"- {nivel}: {quantidade} produtos")

except Exception as e:
    print(f"\nErro durante a análise de recomendação: {e}")
    import traceback
    traceback.print_exc()
