import pandas as pd
from alimenatacao_de_dados import *
import os

def preparo_id_vendas(df):
    filtered_df = df[['quantidade', 'data_venda', 'id_produto', 'id_cliente']]

    # Get today's date and the date one year ago
    today = pd.Timestamp.now()
    one_year_ago = today - pd.DateOffset(months=12)
    
    # Filter rows where the date is within one year before today
    filtered_df = filtered_df[(filtered_df['data_venda'] >= one_year_ago) & (filtered_df['data_venda'] < today)]
    
    # Display result
    filtered_df = filtered_df.sort_values(by='data_venda')

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

    # Definir a data de 15 dias atrás
    hoje = pd.Timestamp.today()
    duas_semanas_atras = hoje - pd.DateOffset(days=15)
    
    # Filtrar outliers que ocorreram na última semana
    outliers_duas_semana = outliers[outliers['data_venda'] >= duas_semanas_atras]
    
    return outliers_duas_semana

def identificar_produtos(df):
    ids = df['id_produto'].unique()
    anomalias = []
    
    for id in ids:
        sales = df[df['id_produto'] == id][['data_venda', 'quantidade', 'id_cliente']]
        sales = sales.groupby(['data_venda', 'id_cliente'], as_index=False)['quantidade'].sum()
        # Aplicar a função e identificar anomalias
        out = identificar_anomalias(sales)
    
        if len(out) > 0:
            print(f"*** Anomalias encontradas para produto {id}: {len(out)} ***")
            anomalias.append((id, out))
    print(f"Total de produtos com anomalias: {len(anomalias)}")
    return anomalias

def id_vendas_atipicas(df, df_de_cli, df_de_prod, df_estoque, path, data, export=False):
    
    anomalias = identificar_produtos(df)
    
    vendas_atipicas = []
    for id, info_df in anomalias:
        
        produto = df_de_prod[df_de_prod['id_produto'] == id]['nome'].iloc[0]
        estoque = df_estoque[df_estoque['id_produto'] == id]['estoque'].iloc[0]
        # critico = df_de_prod[df_de_prod['id_produto'] == id]['prazo_reposicao_dias'].iloc[0]


        d1 = {'id_produto': id,
              'produto': produto,
              'estoque_atualizado': estoque,
            #   'critico': critico,
              'vendas_atipicas': []}


        for _, row in info_df.iterrows():
            
            id_cliente = row['id_cliente']
            cliente = df_de_cli[df_de_cli['id_cliente'] == id_cliente]['nome'].iloc[0]
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
        # Passar critico para o dataframe
        df_r = pd.json_normalize(vendas_atipicas, record_path=["vendas_atipicas"], meta=["id_produto", "produto", "estoque_atualizado"])
        df_r.sort_values("Dia", inplace=True)
        df_r['Dia'] = pd.to_datetime(df_r['Dia'], errors='coerce').dt.strftime('%Y-%m-%d')
        
        if export:   
            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, f'vendas_atipicas_{data}.xlsx')
            df_r.to_excel(output_path)
            print(f"Arquivo salvo em: {output_path}")
    else:
        # Criar um DataFrame vazio com as colunas esperadas
        df_r = pd.DataFrame(columns=["Dia", "quantidade_atipica", "cliente", "id_produto", "produto", "estoque_atualizado"])
        if export:
            print("Nenhuma venda atípica foi encontrada para exportar.")
    
    return df_r

script_dir = os.path.dirname(os.path.abspath(__file__))

df = get_df_preparo_id_vendas()
df_prod = get_produtos()
df_trat = Funcao_tratamento_base(df, df_prod)
df_de_clientes = de_para_clientes()
df_estoque = get_estoque_atualizado()[['id_produto', 'estoque', 'data_estoque_atualizado']]
# df_fornecedor = get_fornecedor()
# df_compra = get_compra()
# df_compra_item = get_compra_itens()

# Primeiro, obtemos o DataFrame de vendas atípicas
df_r = id_vendas_atipicas(df_trat, df_de_clientes, df_prod, df_estoque, script_dir, 'atual', True)

if not df_r.empty:
    # # Fazemos o merge primeiro com compra_item para obter id_compra
    # df_r = df_r.merge(df_compra_item, how='left', on='id_produto')
    
    # # Depois com compra para obter id_fornecedor
    # df_r = df_r.merge(df_compra, how='left', on='id_compra')
    
    # # Por fim, com fornecedor usando id_fornecedor
    # df_r = df_r.merge(df_fornecedor, how='left', on='id_fornecedor')
    
    # Renomeamos as colunas conforme necessário
    df_r.rename(columns={"id_produto": 'cd_produto'}, inplace=True)
    # df_r.rename(columns={"nome": 'fornecedor'}, inplace=True)

    print(df_r.columns)
    print(f"Arquivo salvo com sucesso! Colunas disponíveis: {', '.join(df_r.columns)}")
else:
    print("Não foram encontradas vendas atípicas para processar.")