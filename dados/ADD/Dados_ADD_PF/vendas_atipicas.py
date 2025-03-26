import pandas as pd # dataframes
import plotly.express as px
import plotly.graph_objects as go
from alimenatacao_de_dados import *
import os

def preparo_id_vendas(df):
    filtered_df = df[['quantidade', 'data_emissao', 'id_produto', 'id_cliente']]

    # Get today's date and the date one year ago
    today = pd.Timestamp.now()
    one_year_ago = today - pd.DateOffset(months=12)
    
    # Filter rows where the date is within one year before today
    filtered_df = filtered_df[(filtered_df['data_emissao'] >= one_year_ago) & (filtered_df['data_emissao'] < today)]
    
    # Display result
    filtered_df = filtered_df.sort_values(by='data_emissao')

    return filtered_df

def identificar_anomalias(df):
    # Calcular média e desvio padrão da coluna 'quantidade'
    media = df['quantidade'].mean()
    desvio_padrao = df['quantidade'].std()
    
    # Calcular Z-score
    df['z_score'] = (df['quantidade'] - media) / desvio_padrao

    # Definir o limiar para outliers (Z > 3)
    limiar = 4
    outliers = df[df['z_score'] > limiar]

    # Definir a data de 7 dias atrás
    hoje = pd.Timestamp.today()
    duas_semanas_atras = hoje - pd.DateOffset(days=15)
    
    # Filtrar outliers que ocorreram na última semana
    outliers_duas_semana = outliers[outliers['data_emissao'] >= duas_semanas_atras]
    
    return outliers_duas_semana

def identificar_produtos(df):
    ids = df['id_produto'].unique()
    anomalias = []
    
    for id in ids:
        sales = df[df['id_produto'] == id][['data_emissao', 'quantidade', 'id_cliente']]
        sales = sales.groupby(['data_emissao', 'id_cliente'], as_index=False)['quantidade'].sum()
        # Aplicar a função e identificar anomalias
        out = identificar_anomalias(sales)
    
        if len(out) > 0:
            anomalias.append((id, out))
    return anomalias

def id_vendas_atipicas(df, df_de_cli, df_de_prod, df_estoque, path, data, export=False):
    
    anomalias = identificar_produtos(df)
    
    vendas_atipicas = []
    for id, info_df in anomalias:
        
        produto = df_de_prod[df_de_prod['id_produto'] == id]['nome'].iloc[0]
        estoque = df_estoque[df_estoque['id_produto'] == id]['estoque'].iloc[0]
        critico = df_de_prod[df_de_prod['id_produto'] == id]['critico'].iloc[0]


        d1 = {'id_produto': id,
              'produto': produto,
              'estoque_atualizado': estoque,
              'critico': critico,
              'vendas_atipicas': []}


        for _, row in info_df.iterrows():
            
            id_cliente = row['id_cliente']
            cliente = df_de_cli[df_de_cli['id_cliente'] == id_cliente]['nome_cliente'].iloc[0]
            emissao = row['data_emissao']
            quantidade = row['quantidade']

            d1["vendas_atipicas"].append({
                "Dia": emissao,
                "quantidade_atipica": quantidade,
                "cliente": str(cliente)
                })
    
        vendas_atipicas.append(d1)
    df_r = pd.json_normalize(vendas_atipicas, record_path=["vendas_atipicas"], meta=["id_produto", "produto", "estoque_atualizado", "critico"])
    df_r.sort_values("Dia", inplace=True)
    df_r['Dia'] = pd.to_datetime(df_r['Dia'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    if export:   
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, f'vendas_atipicas_{data}.xlsx')
        df_r.to_excel(output_path)
        print(f"Arquivo salvo em: {output_path}")
    
    return df_r

script_dir = os.path.dirname(os.path.abspath(__file__))

df = get_df_preparo_id_vendas()
df_prod = get_produtos()
df_trat = Funcao_tratamento_base(df, df_prod)
df_de_clientes = de_para_clientes()
df_estoque = get_estoque_atualizado()[['id_produto', 'estoque', 'data_estoque_atualizado']]
df_fornecedor = get_fornecedor()

df_r = id_vendas_atipicas(df_trat, df_de_clientes, df_prod, df_estoque, script_dir, 'atual', True)
df_r = df_r.merge(df_fornecedor, how='left', on='id_produto')
df_r.rename(columns={"id_produto": 'cd_produto'}, inplace=True)
df_r.rename(columns={"nome_fornecedor": 'fornecedor'}, inplace=True)

print(df_r.columns)
print(f"Arquivo salvo com sucesso! Colunas disponíveis: {', '.join(df_r.columns)}")