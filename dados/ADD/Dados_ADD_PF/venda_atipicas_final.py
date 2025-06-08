import pandas as pd
from datetime import datetime
import psycopg2
import os
import dotenv
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

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
    """Obtém os dados necessários para análise de vendas atípicas."""
    # Vendas e itens de venda
    query_vendas = """
        SELECT v.id_venda, v.data_venda, v.id_cliente, v.status 
        FROM maloka_core.venda v
    """
    df_vendas = pd.read_sql(query_vendas, conn)
    
    query_venda_itens = """
        SELECT id_venda, id_produto, quantidade 
        FROM maloka_core.venda_item
    """
    df_venda_itens = pd.read_sql(query_venda_itens, conn)
    
    # Clientes
    query_clientes = """
        SELECT id_cliente, nome
        FROM maloka_core.cliente
    """
    df_clientes = pd.read_sql(query_clientes, conn)
    
    # Produtos
    query_produtos = """
        SELECT id_produto, nome
        FROM maloka_core.produto
    """
    df_produtos = pd.read_sql(query_produtos, conn)
    
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
    
    return df_vendas, df_venda_itens, df_clientes, df_produtos, df_estoque

def preparar_dados_vendas(df_vendas, df_venda_itens):
    """Prepara e filtra os dados de vendas."""
    # Converter tipos
    df_vendas['id_venda'] = df_vendas['id_venda'].astype(str)
    df_venda_itens['id_venda'] = df_venda_itens['id_venda'].astype(str)
    
    # Mesclar vendas e itens
    df_combinado = df_venda_itens.merge(df_vendas, on='id_venda', how='left')
    
    # Filtrar colunas relevantes
    filtered_df = df_combinado[['id_venda', 'quantidade', 'data_venda', 'id_produto', 'id_cliente']]
    
    # Filtrar vendas do último ano
    today = pd.Timestamp.now()
    one_year_ago = today - pd.DateOffset(months=12)
    filtered_df = filtered_df[(filtered_df['data_venda'] >= one_year_ago) & (filtered_df['data_venda'] < today)]
    
    # Converter data_venda para datetime
    filtered_df['data_venda'] = pd.to_datetime(filtered_df['data_venda'])
    
    # Ordenar por data
    filtered_df = filtered_df.sort_values(by='data_venda')
    
    return filtered_df

def identificar_anomalias(df):
    """Identifica vendas anômalas com base em z-score."""
    # Calcular média e desvio padrão da coluna 'quantidade'
    media = df['quantidade'].mean()
    desvio_padrao = df['quantidade'].std()
    
    # Se o desvio padrão for zero ou NaN, não há variação para calcular anomalias
    if desvio_padrao == 0 or pd.isna(desvio_padrao):
        return pd.DataFrame()  # Retorna DataFrame vazio
    
    # Calcular Z-score
    df['z_score'] = (df['quantidade'] - media) / desvio_padrao

    # Definir o limiar para outliers (Z > 3)
    limiar = 4
    outliers = df[df['z_score'] > limiar]

    # Definir a data de 15 dias atrás
    hoje = pd.Timestamp.today()
    duas_semanas_atras = hoje - pd.DateOffset(days=15)
    
    # Filtrar outliers que ocorreram nas últimas duas semanas
    outliers_duas_semana = outliers[outliers['data_venda'] >= duas_semanas_atras]
    
    return outliers_duas_semana

def identificar_produtos_anomalos(df):
    """Identifica produtos com vendas anômalas."""
    ids = df['id_produto'].unique()
    anomalias = []
    
    for id in ids:
        # Filtrar vendas do produto
        sales = df[df['id_produto'] == id][['data_venda', 'quantidade', 'id_cliente', 'id_venda']]
        
        # Agrupar por data e cliente
        sales = sales.groupby(['data_venda', 'id_cliente', 'id_venda'], as_index=False)['quantidade'].sum()
        
        # Aplicar a função e identificar anomalias
        out = identificar_anomalias(sales)
    
        if len(out) > 0:
            print(f"*** Anomalias encontradas para produto {id}: {len(out)} ***")
            anomalias.append((id, out))
            
    print(f"Total de produtos com anomalias: {len(anomalias)}")
    return anomalias

def gerar_relatorio_vendas_atipicas(anomalias, df_produtos, df_clientes, df_estoque):
    """Gera relatório de vendas atípicas."""
    vendas_atipicas = []
    
    for id, info_df in anomalias:
        # Obter informações do produto
        produto_info = df_produtos[df_produtos['id_produto'] == id]
        if produto_info.empty:
            print(f"Produto ID {id} não encontrado no cadastro")
            continue
            
        produto = produto_info['nome'].iloc[0]
        
        # Obter estoque atual
        estoque_info = df_estoque[df_estoque['id_produto'] == id]
        estoque = estoque_info['estoque'].iloc[0] if not estoque_info.empty else 0

        # Criar dicionário para o produto
        d1 = {
            'id_produto': id,
            'produto': produto,
            'estoque_atualizado': estoque,
            'vendas_atipicas': []
        }

        # Adicionar detalhes das vendas atípicas
        for _, row in info_df.iterrows():
            id_cliente = row['id_cliente']
            
            # Obter informações do cliente
            cliente_info = df_clientes[df_clientes['id_cliente'] == id_cliente]
            cliente = cliente_info['nome'].iloc[0] if not cliente_info.empty else "Cliente não identificado"
            
            emissao = row['data_venda']
            quantidade = row['quantidade']

            d1["vendas_atipicas"].append({
                "Dia": emissao,
                "quantidade_atipica": quantidade,
                "cliente": str(cliente)
            })
    
        vendas_atipicas.append(d1)

    # Verificar se há anomalias antes de criar o DataFrame
    if len(vendas_atipicas) > 0:
        # Criar DataFrame normalizado dos resultados
        df_r = pd.json_normalize(vendas_atipicas, record_path=["vendas_atipicas"], meta=["id_produto", "produto", "estoque_atualizado"])
        df_r.sort_values("Dia", inplace=True)
        df_r['Dia'] = pd.to_datetime(df_r['Dia'], errors='coerce').dt.strftime('%Y-%m-%d')
        
    else:
        # Criar um DataFrame vazio com as colunas esperadas
        df_r = pd.DataFrame(columns=["Dia", "id_venda", "quantidade_atipica", "cliente", "id_produto", "produto", "estoque_atualizado"])
    
    return df_r

def exportar_resultados(df, nome_arquivo=None):
    """Exporta os resultados para arquivo Excel."""
    if df.empty:
        print("Nenhuma venda atípica foi encontrada para exportar.")
        return
        
    # Gerar nome de arquivo com timestamp atual se não for especificado
    if nome_arquivo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f'vendas_atipicas_{timestamp}.xlsx'
    
    # Obter diretório do script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_completo = os.path.join(script_dir, nome_arquivo)
    
    try:
        # Exportar para Excel
        df.to_excel(caminho_completo, index=False)
        print(f"Arquivo salvo em: {caminho_completo}")
        print(f"Colunas disponíveis: {', '.join(df.columns)}")
    except Exception as e:
        print(f"Erro ao exportar arquivo: {e}")

if __name__ == "__main__":
    # Estabelecer conexão com banco de dados
    conn = conectar_banco()
    if conn is None:
        exit(1)
        
    try:
        print("Obtendo dados base para análise...")
        df_vendas, df_venda_itens, df_clientes, df_produtos, df_estoque = obter_dados_base(conn)
        
        print("Preparando dados de vendas...")
        df_vendas_preparado = preparar_dados_vendas(df_vendas, df_venda_itens)
        
        print("Identificando produtos com vendas atípicas...")
        anomalias = identificar_produtos_anomalos(df_vendas_preparado)
        
        print("Gerando relatório de vendas atípicas...")
        df_resultados = gerar_relatorio_vendas_atipicas(anomalias, df_produtos, df_clientes, df_estoque)
        
        print("Exportando resultados...")
        exportar_resultados(df_resultados, f'vendas_atipicas_v1.xlsx')
        
        print("Análise completa!")
        
    except Exception as e:
        print(f"Erro durante a análise: {e}")
        
    finally:
        # Fechar conexão com banco de dados
        if conn:
            conn.close()
            print("Conexão com banco de dados encerrada.")