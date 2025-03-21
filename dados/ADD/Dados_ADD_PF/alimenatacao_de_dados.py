import pandas as pd
from sqlalchemy import create_engine

# Database connection string
db_url = "postgresql+psycopg2://adduser:addpassword@add.cwlsoqygi6rc.us-east-1.rds.amazonaws.com/add"
engine = create_engine(db_url)

def get_df_preparo_id_vendas():
    # SQL Query
    query_vendas = "SELECT id_venda, data_emissao, id_cliente, status FROM vendas"
    query_venda_itens = "SELECT id_venda, id_produto, quantidade FROM venda_itens"

    # Load into DataFrame
    df_vendas = pd.read_sql(query_vendas, engine)
    df_venda_itens = pd.read_sql(query_venda_itens, engine)

    df = df_venda_itens.merge(df_vendas, on='id_venda', how='left')

    # Display DataFrame
    return df

def de_para_clientes():
    query = "SELECT id_cliente, nome_cliente FROM clientes"
    df = pd.read_sql(query, engine)
    return df

def get_produtos():
    query = "SELECT id_produto, nome, critico FROM produtos"
    df = pd.read_sql(query, engine)
    return df

def get_estoque_atualizado():
    query = "SELECT DISTINCT ON (id_produto) * FROM estoquemovimentos ORDER BY id_produto, data_movimento DESC;"
    df = pd.read_sql(query, engine)
    df = df.rename(columns={'depois': 'estoque', 'data_movimento': 'data_estoque_atualizado'})
    df['data_estoque_atualizado'] = df['data_estoque_atualizado'].dt.date
    return df

def get_fornecedor():
    query = "SELECT id_produto, nome_fornecedor FROM fornecedor"
    df = pd.read_sql(query, engine)
    return df

def get_historico_entrada():
    query = '''

    
    SELECT 
        id_movimento,
        id_produto,
        data_movimento,
        tipo_movimento,
        quantidade,
        antes,
        depois,
        descricao
        
        FROM estoquemovimentos
        WHERE tipo_movimento = 'entrada'
        ORDER BY id_produto, data_movimento DESC;
    
    '''

    df = pd.read_sql(query, engine)[['id_produto', 'data_movimento', 'quantidade', 'descricao']]
    df['data_movimento'] = df['data_movimento'].dt.date

    return df