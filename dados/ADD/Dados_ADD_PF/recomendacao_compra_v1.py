import pandas as pd
from datetime import datetime
import psycopg2
import os
import re
import dotenv
import warnings
from datetime import date

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# Carrega variáveis de ambiente
dotenv.load_dotenv()

def conectar_banco():
    """Estabelece conexão com o banco de dados PostgreSQL."""
    try:
        print("Conectando ao banco de dados PostgreSQL...")
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database="add",
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT")
        )
        print("Conexão estabelecida com sucesso!")
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        print("\nVerifique se:")
        print("1. O PostgreSQL está rodando")
        print("2. O banco de dados existe")
        print("3. As credenciais de conexão estão corretas")
        return None

def obter_dados_base(conn):
    """Obtém os dados necessários para análise de recomendação de compra."""
    print("Obtendo dados para análise de recomendação de compra...")
    
    # Vendas e itens de venda
    query_vendas = """
        SELECT v.id_venda, v.id_cliente, v.data_venda, v.total_venda
        FROM maloka_core.venda v
    """
    df_vendas = pd.read_sql(query_vendas, conn)
    df_vendas.to_csv('vendas.csv', index=False)  # Exportar para CSV para verificação
    
    query_venda_itens = """
        SELECT id_venda, id_produto, quantidade, preco_bruto, total_item
        FROM maloka_core.venda_item
    """
    df_venda_itens = pd.read_sql(query_venda_itens, conn)
    df_venda_itens.to_csv('venda_itens.csv', index=False)  # Exportar para CSV para verificação
    
    # Produtos
    query_produtos = """
        SELECT id_produto, nome, preco_custo, id_categoria
        FROM maloka_core.produto
    """
    df_produtos = pd.read_sql(query_produtos, conn)
    df_produtos.to_csv('produtos.csv', index=False)  # Exportar para CSV para verificação
    
    # Fornecedores
    query_fornecedores = """
        SELECT id_fornecedor, nome as nome_fornecedor, cpf_cnpj
        FROM maloka_core.fornecedor
    """
    df_fornecedores = pd.read_sql(query_fornecedores, conn)
    df_fornecedores.to_csv('fornecedores.csv', index=False)  # Exportar para CSV para verificação
    
    # Estoque atualizado
    query_estoque = """
        SELECT DISTINCT ON (id_produto) 
            id_produto, 
            estoque_depois as estoque, 
            data_movimento as data_estoque_atualizado
        FROM maloka_core.estoque_movimento 
        ORDER BY id_produto, data_movimento DESC
    """
    df_estoque = pd.read_sql(query_estoque, conn)
    df_estoque.to_csv('estoque.csv', index=False)  # Exportar para CSV para verificação
    
    # Histórico de movimentações (para aquisições)
    query_historico = """
        SELECT 
            id_estoque_movimento,
            id_produto,
            data_movimento,
            tipo,
            quantidade,
            descricao
        FROM maloka_core.estoque_movimento
        WHERE tipo = 'E'
        ORDER BY id_produto, data_movimento DESC
    """
    df_historico = pd.read_sql(query_historico, conn)
    df_historico.to_csv('historico.csv', index=False)  # Exportar para CSV para verificação
    
    # Relacionamento produto-fornecedor
    query_produto_fornecedor = """
        SELECT p.id_produto, f.id_fornecedor, f.nome as nome_fornecedor
        FROM maloka_core.produto p
        JOIN maloka_core.fornecedor f ON p.id_fornecedor = f.id_fornecedor
    """
    df_produto_fornecedor = pd.read_sql(query_produto_fornecedor, conn)
    
    print("Dados obtidos com sucesso!")
    
    return df_vendas, df_venda_itens, df_produtos, df_fornecedores, df_estoque, df_historico, df_produto_fornecedor

def preparar_dados_vendas(df_vendas, df_venda_itens, df_produtos):
    """Prepara os dados de vendas para análise."""
    print("Preparando dados de vendas...")
    
    # Converter tipos
    df_vendas['id_venda'] = df_vendas['id_venda'].astype(str)
    df_venda_itens['id_venda'] = df_venda_itens['id_venda'].astype(str)
    
    # Mesclar vendas e itens
    df = df_venda_itens.merge(df_vendas, on='id_venda', how='left')
    
    # Converter data_venda para datetime
    df['data_venda'] = pd.to_datetime(df['data_venda'])
    
    # Adicionar componentes de data
    df['ano'] = df['data_venda'].dt.year
    df['mes'] = df['data_venda'].dt.month
    df['ano_mes'] = df['data_venda'].dt.strftime('%Y_%m')
    
    return df

def calcular_vendas_mensais(df):
    """Calcula as vendas mensais por produto."""
    print("Calculando vendas mensais por produto...")
    
    # Pivot para obter vendas por produto e mês
    df_pivot = df.pivot_table(
        values='quantidade',
        index='id_produto',
        columns='ano_mes',
        aggfunc='sum',
        fill_value=0
    )
    
    # Resetar índice para ter id_produto como coluna
    df_pivot.reset_index(inplace=True)
    
    return df_pivot

def extract_custo(desc):
    """Extrai valor de custo da descrição."""
    if pd.isna(desc):
        return 0
        
    if 'Preço de Custo Médio' in desc:
        result = desc.split('Preço de Custo Médio')[1].split('|')[0].replace(')', "").strip()
    elif 'Preço de Custo (Médio)' in desc:
        result = desc.split('Preço de Custo (Médio')[1].split('|')[0].replace(')', "").strip()
    else:
        return 0
        
    # Limpar o texto para extrair apenas o valor numérico
    result = result.replace('R$', '').strip()
    result = result.replace('.', '').replace(',', '.').strip()
    
    try:
        return float(result)
    except:
        return 0

def extract_fornecedor(desc):
    """Extrai nome do fornecedor da descrição."""
    if pd.isna(desc):
        return 0
        
    match = re.search(r'aquisição|aquisicao', desc, re.IGNORECASE)  # Case-insensitive match
    if match: 
        x = desc[match.end():].split('\n')[0]  # Extract text after the matched word
        clean_text = re.sub(r'\([^)]*$', '', x).strip()  # Removes anything from '(' to end if no ')'
        clean_text = re.sub(r'\([^)]*\)', '', clean_text).strip()  # Removes normal '(...)' cases
        return clean_text
    return 0

def processar_historico_entrada(df_historico):
    """Processa o histórico de entradas para cada produto."""
    print("Processando histórico de entradas...")
    
    # Filtrar apenas movimentos de aquisição
    df_aquisicoes = df_historico[df_historico["descricao"].str.contains("aquisicao|aquisição", case=False, na=False)]
    
    # Extrair custo e fornecedor das descrições
    df_aquisicoes["custo"] = df_aquisicoes["descricao"].apply(extract_custo)
    df_aquisicoes["fornecedor"] = df_aquisicoes["descricao"].apply(extract_fornecedor)
    
    # Adicionar ranking de transação (1 = mais recente)
    df_aquisicoes["rank"] = df_aquisicoes.groupby("id_produto")["data_movimento"].rank(method="first", ascending=False)
    
    # Filtrar apenas as 3 entradas mais recentes por produto
    df_aquisicoes = df_aquisicoes[df_aquisicoes["rank"] <= 3]
    
    # Converter para formato wide com pivot
    df_pivot = df_aquisicoes.pivot(
        index="id_produto", 
        columns="rank", 
        values=["data_movimento", "quantidade", "custo", "fornecedor"]
    )
    
    # Simplificar nomes das colunas
    df_pivot.columns = [f"{col[0]}_{int(col[1])}" for col in df_pivot.columns]
    
    # Resetar índice
    df_pivot.reset_index(inplace=True)
    
    return df_pivot

def calcular_metricas_estoque(df_vendas_mensais, df_estoque, df_pivot_historico):
    """Calcula métricas de estoque e recomendações de compra."""
    print("Calculando métricas de estoque e recomendações...")
    
    # Mesclar dados de vendas e estoque
    df_completo = df_vendas_mensais.merge(df_estoque, on='id_produto', how='inner')
    
    # Obter meses mais recentes (últimos 3)
    colunas_numericas = [col for col in df_completo.columns if '_' in col]
    colunas_numericas.sort(reverse=True)
    ultimos_meses = colunas_numericas[:3] if len(colunas_numericas) >= 3 else colunas_numericas
    
    # Calcular média dos últimos 3 meses
    if len(ultimos_meses) > 0:
        df_completo['Media_3M'] = df_completo[ultimos_meses].mean(axis=1)
    else:
        df_completo['Media_3M'] = 0
    
    # Calcular cobertura (meses)
    df_completo['Cobertura'] = df_completo['estoque'] / df_completo['Media_3M']
    
    # Calcular sugestão para 3 meses
    df_completo['Sug_3M'] = (3 * df_completo['Media_3M']) - df_completo['estoque']
    
    # Calcular sugestão para 1 mês (baseado no último mês)
    if len(ultimos_meses) > 0:
        df_completo['Sug_1M'] = df_completo[ultimos_meses[0]] - df_completo['estoque']
    else:
        df_completo['Sug_1M'] = 0
    
    # Mesclar com histórico de entradas
    if df_pivot_historico is not None:
        df_completo = df_completo.merge(df_pivot_historico, on='id_produto', how='left')
    
    return df_completo

def adicionar_dados_ultima_venda(conn, df_analise):
    """Adiciona informações da última venda de cada produto."""
    print("Adicionando dados da última venda...")
    
    query = """
    SELECT
        id_produto,
        MAX(data_movimento) AS data_ultima_venda
    FROM maloka_core.estoque_movimento
    WHERE tipo = 'S'
    GROUP BY id_produto
    """
    
    df_ultima_venda = pd.read_sql(query, conn)
    df_ultima_venda['data_ultima_venda'] = pd.to_datetime(df_ultima_venda['data_ultima_venda']).dt.date
    
    # Realizar merge
    df_analise = df_analise.merge(df_ultima_venda, on='id_produto', how='left')
    
    # Calcular dias desde a última venda
    data_hoje = date.today()
    df_analise['dias_desde_ultima_venda'] = df_analise['data_ultima_venda'].apply(
        lambda x: (data_hoje - x).days if not pd.isna(x) else None
    )
    
    # Identificar produtos sem vendas recentes
    df_analise['sem_venda_recente'] = df_analise['dias_desde_ultima_venda'].apply(
        lambda x: 'Sim' if pd.isna(x) or x > 180 else 'Não'
    )
    
    return df_analise

def adicionar_dados_produto(df_analise, df_produtos, df_produto_fornecedor):
    """Adiciona informações de produtos e fornecedores."""
    print("Adicionando informações de produtos e fornecedores...")
    
    # Mesclar com dados de produtos
    df_analise = df_analise.merge(df_produtos, on='id_produto', how='left')
    
    # Mesclar com dados de fornecedores
    df_analise = df_analise.merge(df_produto_fornecedor, on='id_produto', how='left')
    
    return df_analise

def preparar_dataframe_final(df_analise):
    """Prepara o DataFrame final com as colunas necessárias e renomeadas."""
    print("Preparando DataFrame final...")
    
    # Selecionar e renomear colunas
    colunas_numericas = [col for col in df_analise.columns if '_' in col and col.split('_')[0].isdigit()]
    colunas_numericas.sort()
    
    # Lista de todas as colunas na ordem desejada
    colunas_finais = [
        'id_produto', 'nome', 
        *colunas_numericas,  # Colunas de vendas mensais
        'nome_fornecedor', 'estoque', 'data_estoque_atualizado', 
        'Media_3M', 'Cobertura', 'Sug_3M', 'Sug_1M',
        'data_movimento_1', 'quantidade_1', 'custo_1', 'fornecedor_1',
        'data_movimento_2', 'quantidade_2', 'custo_2', 'fornecedor_2',
        'data_movimento_3', 'quantidade_3', 'custo_3', 'fornecedor_3',
        'data_ultima_venda', 'dias_desde_ultima_venda', 'sem_venda_recente'
    ]
    
    # Filtrar apenas colunas existentes
    colunas_existentes = [col for col in colunas_finais if col in df_analise.columns]
    df_final = df_analise[colunas_existentes].copy()
    
    # Renomear colunas
    mapeamento_colunas = {
        'id_produto': 'cd_produto',
        'nome': 'desc_produto',
        'estoque': 'estoque_atualizado',
        'Media_3M': 'Media 3M',
        'Cobertura': 'Cobertura',
        'Sug_3M': 'Sug 3M',
        'Sug_1M': 'Sug 1M',
        'data_movimento_1': 'Data1',
        'data_movimento_2': 'Data2',
        'data_movimento_3': 'Data3',
        'quantidade_1': 'Quantidade1',
        'quantidade_2': 'Quantidade2',
        'quantidade_3': 'Quantidade3',
        'custo_1': 'custo1',
        'custo_2': 'custo2',
        'custo_3': 'custo3',
        'fornecedor_1': 'Fornecedor1',
        'fornecedor_2': 'Fornecedor2',
        'fornecedor_3': 'Fornecedor3'
    }
    
    # Aplicar renomeação de colunas
    for coluna_antiga, coluna_nova in mapeamento_colunas.items():
        if coluna_antiga in df_final.columns:
            df_final.rename(columns={coluna_antiga: coluna_nova}, inplace=True)
    
    return df_final

def analisar_criticidade_estoque(df):
    """Analisa a criticidade dos níveis de estoque."""
    print("Analisando criticidade dos níveis de estoque...")
    
    # Converter colunas numéricas
    for col in ['estoque_atualizado', 'Media 3M', 'Cobertura', 'Sug 3M', 'Sug 1M']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Processar coluna de custo
    if 'custo1' in df.columns:
        # Criar uma nova coluna para os cálculos, preservando a original
        df['custo1_calc'] = df['custo1'].copy()
        
        # Se for string com formatação de moeda
        if df['custo1_calc'].dtype == object:
            # Remover caracteres não numéricos e substituir vírgula por ponto
            df['custo1_calc'] = df['custo1_calc'].astype(str).str.replace('R$', '', regex=False) \
                                           .str.replace(' ', '', regex=False) \
                                           .str.replace('.', '', regex=False) \
                                           .str.replace(',', '.', regex=False)
        
        df['custo1_calc'] = pd.to_numeric(df['custo1_calc'], errors='coerce')

    # Calcular percentual de cobertura
    if 'Media 3M' in df.columns and df['Media 3M'].sum() > 0:  # Verificar se há vendas
        df['percentual_cobertura'] = (df['Cobertura'] * 100).round(1)
        
        # Definir categorias de criticidade
        df['criticidade'] = pd.cut(
            df['percentual_cobertura'],
            bins=[-float('inf'), 30, 50, 80, 100, float('inf')],
            labels=['Crítico', 'Muito Baixo', 'Baixo', 'Adequado', 'Excesso']
        )
    else:
        df['percentual_cobertura'] = None
        df['criticidade'] = 'Sem movimento'
    
    return df

def exportar_para_excel(df, nome_arquivo=None):
    """Exporta os resultados para Excel."""
    if df.empty:
        print("DataFrame vazio. Nada para exportar.")
        return
        
    # Gerar nome de arquivo com timestamp atual se não for especificado
    if nome_arquivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f'recomendacao_de_compra_{timestamp}.xlsx'
    
    # Obter diretório do script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_completo = os.path.join(script_dir, nome_arquivo)
    
    try:
        # Exportar para Excel
        df.to_excel(caminho_completo, index=False)
        print(f"Arquivo salvo em: {caminho_completo}")
        print(f"Total de {len(df)} produtos analisados")
    except Exception as e:
        print(f"Erro ao exportar arquivo: {e}")
        
        # Tentar salvar no diretório atual como último recurso
        try:
            fallback_path = nome_arquivo
            df.to_excel(fallback_path, index=False)
            print(f"Arquivo salvo como {fallback_path} após falha")
        except Exception as inner_e:
            print(f"Falha final ao tentar salvar: {inner_e}")

if __name__ == "__main__":
    # Estabelecer conexão com banco de dados
    conn = conectar_banco()
    if conn is None:
        exit(1)
        
    try:
        # Obter dados base
        df_vendas, df_venda_itens, df_produtos, df_fornecedores, df_estoque, df_historico, df_produto_fornecedor = obter_dados_base(conn)
        
        # Preparar dados de vendas
        df_vendas_preparado = preparar_dados_vendas(df_vendas, df_venda_itens, df_produtos)
        
        # Calcular vendas mensais
        df_vendas_mensais = calcular_vendas_mensais(df_vendas_preparado)
        
        # Processar histórico de entradas
        df_pivot_historico = processar_historico_entrada(df_historico)
        
        # Calcular métricas de estoque
        df_metricas = calcular_metricas_estoque(df_vendas_mensais, df_estoque, df_pivot_historico)
        
        # Adicionar dados da última venda
        df_metricas = adicionar_dados_ultima_venda(conn, df_metricas)
        
        # Adicionar dados de produtos e fornecedores
        df_metricas = adicionar_dados_produto(df_metricas, df_produtos, df_produto_fornecedor)
        
        # Preparar DataFrame final
        df_final = preparar_dataframe_final(df_metricas)
        
        # Analisar criticidade
        df_final = analisar_criticidade_estoque(df_final)
        
        # Ordenar por sugestão de compra
        df_final = df_final.sort_values(by='Sug 3M', ascending=False)
        
        # Exportar resultados
        data_atual = datetime.now().strftime("%Y%m%d")
        exportar_para_excel(df_final, f'recomendacao_de_compra_{data_atual}.xlsx')
        
        print("Análise de recomendação de compra concluída!")
        
    except Exception as e:
        print(f"Erro durante a análise: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Fechar conexão com banco de dados
        if conn:
            conn.close()
            print("Conexão com banco de dados encerrada.")