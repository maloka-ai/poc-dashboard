import pandas as pd
from sqlalchemy import create_engine

# Database connection string
db_url = "postgresql+psycopg2://adduser:maloka2025@maloka-application-db.cwlsoqygi6rc.us-east-1.rds.amazonaws.com:5432/add_v1"
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
    
    Table_filtro = Table[((Table["status"] == "pedido") | 
                         (Table["status"] == "Pedido/Concluído") | 
                         (Table["status"] == "Pedido/Pago") | 
                         (Table["status"] == "Pedido/Entregue") | 
                         (Table["status"] == "Pedido/Pendente") | 
                         (Table["status"] == "Pedido/Faturado")) & 
                         (Table["data_venda_Ano"] != "2020")]

    # Join tabela + DE_PARA
    Table_join = Table_filtro.merge(df_de, how = "left", on="id_produto")

    return Table_join

def get_df_preparo_id_vendas():
    # SQL Query
    query_vendas = "SELECT id_venda, data_venda, id_cliente, status FROM vendas"
    query_venda_itens = "SELECT id_venda, id_produto, quantidade FROM vendasitens"

    # Load into DataFrame
    df_vendas = pd.read_sql(query_vendas, engine)
    df_venda_itens = pd.read_sql(query_venda_itens, engine)

    df = df_venda_itens.merge(df_vendas, on='id_venda', how='left')

    # Display DataFrame
    return df

def de_para_clientes():
    query = "SELECT id_cliente, nome FROM clientes"
    df = pd.read_sql(query, engine)

    df.rename(columns={'nome': 'nome_cliente'}, inplace=True)
    return df

def get_produtos():
    query = "SELECT id_produto, nome, prazo_reposicao_dias, estoque_atual FROM produtos"
    df = pd.read_sql(query, engine)

    # Criando a segunda coluna critico se o valor de prazo_reposicao_dias for >= 40, caso contrário False
    df['critico'] = df['prazo_reposicao_dias'] >= 40

    return df

def get_estoque_atualizado():
    query = "SELECT DISTINCT ON (id_produto) * FROM estoquemovimentos ORDER BY id_produto, data_movimento DESC;"
    df = pd.read_sql(query, engine)
    df = df.rename(columns={'estoque_depois': 'estoque', 'data_movimento': 'data_estoque_atualizado'})
    df['data_estoque_atualizado'] = df['data_estoque_atualizado'].dt.date
    return df


def get_historico_entrada():
    query = '''

    
    SELECT 
        id_movimento,
        id_produto,
        data_movimento,
        tipo,
        quantidade,
        estoque_antes,
        estoque_depois,
        descricao
        
        FROM estoquemovimentos
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
        FROM estoquemovimentos
        WHERE tipo_movimento = 'S'
        GROUP BY id_produto;
    '''

    df = pd.read_sql(query, engine)
    df['data_ultima_venda'] = df['data_ultima_venda'].dt.date
    
    return df