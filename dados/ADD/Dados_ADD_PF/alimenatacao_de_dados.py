import pandas as pd
from sqlalchemy import create_engine

# Database connection string
db_url = "postgresql+psycopg2://adduser:maloka2025@maloka-application-db.cwlsoqygi6rc.us-east-1.rds.amazonaws.com:5432/add"
engine = create_engine(db_url)

def Trat_coluna_date(Dataframe, Data_name, formato_data_ingles = True):

    Table = Dataframe.copy()
    Table[Data_name]  = pd.to_datetime(Table[Data_name], yearfirst = formato_data_ingles)
    Table["Date_aux"] = pd.to_datetime(Table[Data_name], yearfirst = formato_data_ingles)

    # Criacao das colunas auxiliares de datas
    Table[str(Data_name) + "_Ano"] = Table["Date_aux"].dt.year.astype(str)
    Table["Mes"]                   = Table["Date_aux"].dt.month.astype(str).str.zfill(2)
    Table["Semana"]                = Table["Date_aux"].dt.isocalendar().week.astype(str).str.zfill(2)
    Table.loc[Table["Mes"].isin(["01","02","03"]), "Tri"] = "1ºTri"
    Table.loc[Table["Mes"].isin(["04","05","06"]), "Tri"] = "2ºTri"
    Table.loc[Table["Mes"].isin(["07","08","09"]), "Tri"] = "3ºTri"
    Table.loc[Table["Mes"].isin(["10","11","12"]), "Tri"] = "4ºTri"
    Table.loc[Table["Mes"].isin(["01","02","03","04","05","06"]), "Sem"] = "1ºSem"
    Table.loc[Table["Mes"].isin(["07","08","09","10","11","12"]), "Sem"] = "2ºSem"
    for data in ["Sem", "Tri", "Mes", "Semana"]:
        Table[str(Data_name) + "_Ano_" + data] = Table[str(Data_name) + "_Ano"] + "_" + Table[data]
    # Deletar algumas colunas
    Table.drop(["Sem", "Tri","Mes","Semana","Date_aux"], axis=1, inplace = True)
    return Table

#||====================================||
#           FUNCAO - Arrumar Base
#||====================================||
def Funcao_tratamento_base(Dataframe, Dataframe_de_para):

    Table = Dataframe.copy()
    df_de = Dataframe_de_para.copy()
    #||====================================||
    #           Tratamento da base
    #||====================================||

    # Criar colunas de data
    Table = Trat_coluna_date(Table, "data_venda")
    
    #Para que serve este data_venda_ano diferente de 2020?
    Table_filtro = Table[(Table["data_venda_Ano"] != "2020")]

    Table_filtro['id_produto'] = Table_filtro['id_produto'].astype(str)
    df_de['id_produto'] = df_de['id_produto'].astype(str)

    # Join tabela + DE_PARA
    Table_join = Table_filtro.merge(df_de, how = "left", on="id_produto")

    print("PASSEI no Funcao_tratamento_base")
    print(Table_join.head())
    return Table_join

def get_df_preparo_id_vendas():
    # SQL Query
    query_vendas = "SELECT id_venda, data_venda, id_cliente, status FROM maloka_core.venda"
    query_venda_itens = "SELECT id_venda, id_produto, quantidade FROM venda_itens"

    # Load into DataFrame
    df_vendas = pd.read_sql(query_vendas, engine)
    df_venda_itens = pd.read_sql(query_venda_itens, engine)

    df_vendas['id_venda'] = df_vendas['id_venda'].astype(str)
    df_venda_itens['id_venda'] = df_venda_itens['id_venda'].astype(str)

    df = df_venda_itens.merge(df_vendas, on='id_venda', how='left')

    # Display DataFrame
    return df

def de_para_clientes():
    query = "SELECT id_cliente, nome FROM maloka_core.cliente"
    df = pd.read_sql(query, engine)
    print("PASSEI no de_para_clientes")
    print(df.head())
    return df

def get_produtos():
    # Não temos mais o critico, tenho a reposição em dias 
    query = "SELECT id_produto, nome FROM maloka_core.produto"
    df = pd.read_sql(query, engine)
    print("PASSEI no get_produtos")
    print(df.head())
    return df

def get_compra():
    query = '''
    SELECT 
        id_compra,
        id_fornecedor,
        data_compra 
    FROM maloka_core.compra
    ORDER BY id_compra, data_compra DESC;
    '''

    df = pd.read_sql(query, engine)
    df['data_compra'] = df['data_compra'].dt.date
    print("PASSEI no get_compra")
    print(df.head())
    return df

def get_compra_itens():
    query = '''
    SELECT 
        id_compra,
        id_produto 
    FROM maloka_core.compra_item;
    '''

    df = pd.read_sql(query, engine)
    print("PASSEI no get_compra_itens")
    print(df.head())
    return df

def get_estoque_atualizado():
    query = "SELECT DISTINCT ON (id_produto) * FROM maloka_core.estoque_movimento ORDER BY id_produto, data_movimento DESC;"
    df = pd.read_sql(query, engine)
    df = df.rename(columns={'estoque_depois': 'estoque', 'data_movimento': 'data_estoque_atualizado'})
    df['data_estoque_atualizado'] = df['data_estoque_atualizado'].dt.date
    print("PASSEI no get_estoque_atualizado")
    print(df.head())
    return df

def get_fornecedor():
    query = "SELECT id_fornecedor, nome FROM maloka_core.fornecedor"
    df = pd.read_sql(query, engine)
    print("PASSEI no get_fornecedor")
    print(df.head())
    return df

def get_historico_entrada():
    query = '''

    
    SELECT 
        id_movimento,
        id_produto,
        data_movimento,
        tipo,
        quantidade,
        data_antes,
        data_depois,
        descricao
        
        FROM maloka_core.estoque_movimento
        WHERE tipo = 'E'
        ORDER BY id_produto, data_movimento DESC;
    
    '''

    df = pd.read_sql(query, engine)[['id_produto', 'data_movimento', 'quantidade', 'descricao']]
    df['data_movimento'] = df['data_movimento'].dt.date

    return df

def get_ultima_venda():
    query = '''

    SELECT
        id_produto,
        MAX(data_movimento) AS data_ultima_venda
        FROM maloka_core.estoque_movimento
        WHERE tipo_movimento = 'S'
        GROUP BY id_produto;
    '''

    df = pd.read_sql(query, engine)
    df['data_ultima_venda'] = df['data_ultima_venda'].dt.date
    print("PASSEI no get_ultima_venda")
    print(df.head())  # Debugging line to check the DataFrame content
    return df