import pandas as pd # dataframes
import numpy as np # arrays
import datetime, os, re, math
from alimenatacao_de_dados import *

#||====================================||
#           FUNCAO - Analise por Tempo
#||====================================||
def Funcao_Analise(Dataframe, column_name):

    Table   = Dataframe.copy()
    # De_para = Table[["id_produto", "cd_produto","desc_produto", "emissao", "preco_custo"]].drop_duplicates()
    De_para = Table[["id_produto" ,"nome"]].drop_duplicates()

    lista_tempo  = ["data_venda_Ano","data_venda_Ano_Sem","data_venda_Ano_Tri","data_venda_Ano_Mes","data_venda_Ano_Semana"]
    list1 = []
    list2 = []


    for data in lista_tempo:
    
        #||====================================||
        #           Visao por Produto
        #||====================================||
        analise1 = pd.pivot_table(Table,
                                values =column_name,
                                index  ="id_produto",
                                columns=data,
                                aggfunc='sum',
                                fill_value=0,
                                dropna=False).reset_index()
        # Analise + De_para
        analise1 = De_para.merge(analise1, how = "right", left_on = ["id_produto"], right_on = ["id_produto"])
        # Tratamento do nome da coluna
        # analise  = analise.rename({"index":data},axis=1)
        analise1 = analise1.rename({"index":data},axis=1)
        # list1.append(analise)
        list2.append(analise1)
    
    print("Função Análise concluída !"), 
    return list2[3] 

# Custom function to calculate the mean
def conditional_mean(row):
    values = [row[df1.columns[-10]], row[df1.columns[-11]], row[df1.columns[-12]]]
    count = 3 
    if 0 in values:
        for i in values:
            if i == 0:
                count -= 1 # Divide by 3 normally, or by 2 if any value is 0
        if count == 0:
            return 0
    return sum(values) / count


def extract_custo(desc):
    if 'Preço de Custo Médio' in desc:
        return desc.split('Preço de Custo Médio')[1].split('|')[0].replace(')', "")
    elif 'Preço de Custo (Médio)' in desc:
        return desc.split('Preço de Custo (Médio')[1].split('|')[0].replace(')', "")
    return 0

        
def extract_fornecedor(desc):
    match = re.search(r'aquisição|aquisicao', desc, re.IGNORECASE)  # Case-insensitive match
    if match: 
        x = desc[match.end():].split('\n')[0]  # Extract text after the matched word
        clean_text = re.sub(r'\([^)]*$', '', x).strip()  # Removes anything from '(' to end if no ')'
        clean_text = re.sub(r'\([^)]*\)', '', clean_text).strip()  # Removes normal '(...)' cases
        return clean_text
    return 0
      

#||====================================||
#               PARAMETROS
#||====================================||


df = get_df_preparo_id_vendas()
df_de = get_produtos()
df_estoque = get_estoque_atualizado()

df_trat = Funcao_tratamento_base(df, df_de)
Nome_analise = "quantidade"
df1 = Funcao_Analise(df_trat, Nome_analise)

# Filter necessary columns and drop NaNs in one step
df1 = df1.filter(regex="2024_|2025_|produto|custo|emissao|fornecedor").dropna(subset=["id_produto"])

# Merge with stock data
df1 = df1.merge(df_estoque, how="inner", on="id_produto").rename(columns={"estoque": f"estoque_atualizado"})


# Compute required columns efficiently
df1["Media 3M"]  = df1.apply(conditional_mean, axis=1)  # Use map() instead of apply() if possible
df1["Cobertura"] = df1[f"estoque_atualizado"] / df1["Media 3M"]

# Get the last relevant column dynamically to avoid hardcoded indices
df1["Sug 3M"] = (3 * df1["Media 3M"]) - df1['estoque_atualizado']
print(df1.columns)

ultimo_mes = df1.columns[-13]
df1["Sug 1M"] = (df1[ultimo_mes]) - df1['estoque_atualizado']

# Final filtering step
df1 = df1[df1[f"estoque_atualizado"] > 0]

df_historico_entrada = get_historico_entrada()

df_historico_entrada = df_historico_entrada[df_historico_entrada["descricao"].str.contains("aquisicao|aquisição", case=False, na=False)]

df_historico_entrada["rank"] = df_historico_entrada.groupby("id_produto")["data_movimento"].rank(method="first", ascending=False)

df_historico_entrada["custo"] = df_historico_entrada["descricao"].apply(extract_custo)
df_historico_entrada['Fornecedor'] = df_historico_entrada['descricao'].apply(extract_fornecedor)


df_pivot = df_historico_entrada.pivot(index="id_produto", columns="rank", values=["data_movimento", "quantidade", 'custo', 'Fornecedor'])


df_pivot.columns = [f"{col[0]}_{int(col[1])}" for col in df_pivot.columns]
df_pivot.reset_index(inplace=True)
column_order = ["id_produto"] + sorted(
    [col for col in df_pivot.columns if col not in ["id_produto"]],
    key=lambda x: int(x[-1])  # Ordenar por número (1, 2, 3)
)

df_pivot = df_pivot[column_order]

# Step 4: Merge with df_products
df_pivot.columns = ["".join(map(str, col)) for col in df_pivot.columns]  # Converts multi-index to flat column names
df_merged = df1.merge(df_pivot, on="id_produto", how="left").sort_values(by='Sug 3M', ascending=False)
df_merged = df_merged.fillna('0')
df_merged = df_merged.astype(str)
df_de = df_de.astype(str)
df_merged = df_merged.merge(df_de, on="id_produto", how="left")

df_merged = df_merged[['id_produto', 'nome', 'critico', '2024_01', '2024_02', '2024_03', '2024_04',
       '2024_05', '2024_06', '2024_07', '2024_08', '2024_09', '2024_10',
       '2024_11', '2024_12', '2025_01', '2025_02', '2025_03', 'estoque_atualizado', 'data_estoque_atualizado', 'Media 3M', 'Cobertura', 'Sug 3M', 'Sug 1M', 'data_movimento_1',
       'quantidade_1', 'custo_1', 'Fornecedor_1', 'data_movimento_2', 'quantidade_2',
       'custo_2','Fornecedor_2', 'data_movimento_3', 'quantidade_3', 'custo_3', 'Fornecedor_3']]

df_merged.rename(columns={"id_produto": 'cd_produto'}, inplace=True)
df_merged.rename(columns={"nome": 'desc_produto'}, inplace=True)
df_merged.rename(columns={"nome_fornecedor": 'fornecedor'}, inplace=True)
df_merged.rename(columns={"data_movimento_1": 'Data1'}, inplace=True)
df_merged.rename(columns={"data_movimento_2": 'Data2'}, inplace=True)
df_merged.rename(columns={"data_movimento_3": 'Data3'}, inplace=True)
df_merged.rename(columns={"quantidade_1": 'Quantidade1'}, inplace=True)
df_merged.rename(columns={"quantidade_2": 'Quantidade2'}, inplace=True)
df_merged.rename(columns={"quantidade_3": 'Quantidade3'}, inplace=True)
df_merged.rename(columns={"custo_1": 'custo1'}, inplace=True)
df_merged.rename(columns={"custo_2": 'custo2'}, inplace=True)
df_merged.rename(columns={"custo_3": 'custo3'}, inplace=True)
df_merged.rename(columns={"Fornecedor_1": 'Fornecedor1'}, inplace=True)
df_merged.rename(columns={"Fornecedor_2": 'Fornecedor2'}, inplace=True)
df_merged.rename(columns={"Fornecedor_3": 'Fornecedor3'}, inplace=True)

df_merged.to_excel('recomendacao_de_compra2.xlsx')



# def analisar_estoque():
#     df = df_merged
    
#     # Verificar e limpar os dados
#     print(f"Total de produtos carregados: {len(df)}")
#     print(f"Colunas disponíveis: {', '.join(df.columns.tolist())}")
    
#     # Mapeamento das colunas específicas para os nomes padronizados que usaremos na análise
#     mapeamento_colunas = {
#         'cd_produto': 'cd_produto',
#         'desc_produto': 'desc_produto',
#         'estoque_atualizado': 'estoque_atualizado',  # Estoque atual
#         'Media 3M': 'media_3m',               # Média de consumo trimestral
#         'Cobertura': 'cobertura',             # Cobertura em meses
#         'Sug 3M': 'sugestao_3m',              # Sugestão para 3 meses
#         'Sug 1M': 'sugestao_1m',              # Sugestão para 1 mês
#         'custo1': 'custo1'                    # Custo unitário da última compra
#     }
    
#     # Verificar quais colunas esperadas estão presentes
#     colunas_faltantes = [col for col in mapeamento_colunas.keys() if col not in df.columns]
    
#     if colunas_faltantes:
#         print(f"AVISO: As seguintes colunas esperadas não foram encontradas: {colunas_faltantes}")
        
#         # Verificar se existem colunas similares que podemos usar
#         for col_faltante in colunas_faltantes.copy():
#             # Verificar se alguma coluna contém o nome da coluna faltante
#             colunas_similares = [col for col in df.columns if col_faltante.lower() in col.lower()]
#             if colunas_similares:
#                 print(f"  Usando '{colunas_similares[0]}' como substituto para '{col_faltante}'")
#                 df[col_faltante] = df[colunas_similares[0]]
#                 colunas_faltantes.remove(col_faltante)
    
#     # Verificar se ainda existem colunas faltantes críticas
#     colunas_criticas = ['estoque_atualizado', 'Media 3M']
#     colunas_criticas_faltantes = [col for col in colunas_criticas if col not in df.columns]
    
#     if colunas_criticas_faltantes:
#         print("ERRO: Não foi possível encontrar colunas essenciais para a análise.")
#         return None
    
#     # Converter colunas numéricas
#     for col in ['estoque_atualizado', 'Media 3M', 'Cobertura', 'Sug 3M', 'Sug 1M']:
#         if col in df.columns:
#             df[col] = pd.to_numeric(df[col], errors='coerce')
            
#     if 'custo1' in df.columns:
        
#         # Criar uma nova coluna para os cálculos, preservando a original
#         df['custo1_calc'] = df['custo1'].copy()
        
#         # Se for string com formatação de moeda
#         if df['custo1_calc'].dtype == object:
#             # Remover caracteres não numéricos (R$, espaços, etc) e substituir vírgula por ponto
#             df['custo1_calc'] = df['custo1_calc'].astype(str).str.replace('R$', '', regex=False) \
#                                                .str.replace(' ', '', regex=False) \
#                                                .str.replace('.', '', regex=False) \
#                                                .str.replace(',', '.', regex=False)
        
#         df['custo1_calc'] = pd.to_numeric(df['custo1_calc'], errors='coerce')

    
#     # Remover linhas com valores NaN nas colunas essenciais
#     df_limpo = df.dropna(subset=[col for col in colunas_criticas if col in df.columns])
#     if len(df_limpo) < len(df):
#         print(f"AVISO: {len(df) - len(df_limpo)} linhas removidas devido a valores ausentes.")
    
#     df = df_limpo
    
#     # Calcular percentual de cobertura se 'Cobertura' não estiver disponível
#     if 'Cobertura' not in df.columns:
#         if 'estoque_atualizado' in df.columns and 'Media 3M' in df.columns:
#             df['percentual_cobertura'] = (df['estoque_atualizado'] / df['Media 3M'] * 100).round(1)
#             print("Percentual de cobertura calculado a partir do estoque atual e média 3M")
#     else:
#         # Usar a coluna 'Cobertura' para calcular o percentual (assumindo que Cobertura está em meses)
#         df['percentual_cobertura'] = (df['Cobertura'] * 100).round(1)
#         print("Percentual de cobertura calculado a partir da coluna Cobertura")
    
#     # Definir categorias de criticidade
#     df['criticidade'] = pd.cut(
#         df['percentual_cobertura'],
#         bins=[-float('inf'), 30, 50, 80, 100, float('inf')],
#         labels=['Crítico', 'Muito Baixo', 'Baixo', 'Adequado', 'Excesso']
#     )

#     exportar_excel_para_dashboard(df)
    
#     return df

# def exportar_excel_para_dashboard(df, pasta_destino=None, arquivo_saida="relatorio_produtos.xlsx"):
#     """
#     Exporta os dados processados para um arquivo Excel estruturado que pode ser 
#     utilizado como fonte de dados para um dashboard.
    
#     Args:
#         df (pandas.DataFrame): DataFrame com os dados processados
#         pasta_destino (str): Pasta onde o arquivo será salvo
#         arquivo_saida (str): Nome do arquivo Excel de saída
#     """
    
#     # Se pasta_destino for None, usar o diretório do script atual
#     if pasta_destino is None:
#         # Obter o caminho absoluto do diretório do script
#         pasta_destino = os.path.dirname(os.path.abspath(__file__))
#         print(f"Usando pasta do script: {pasta_destino}")
    
#     # Verificar se a pasta existe, se não, criar
#     if not os.path.exists(pasta_destino):
#         try:
#             os.makedirs(pasta_destino)
#             print(f"Pasta de destino criada: {pasta_destino}")
#         except Exception as e:
#             print(f"Erro ao criar pasta de destino: {e}")
#             # Fallback para o diretório atual do processo
#             pasta_destino = os.getcwd()
#             print(f"Usando diretório atual como fallback: {pasta_destino}")
    
#     # Construir caminho completo
#     caminho_completo = os.path.join(pasta_destino, arquivo_saida)
    
#     print(f"Preparando Excel para dashboard: {caminho_completo}")
    
#     # 1. Dados completos com todas as métricas calculadas
#     df_completo = df.copy()
    
#     # # 2. Resumo de criticidade (para gráfico de barras e pizza)
#     # contagem_criticidade = df['criticidade'].value_counts().sort_index()
#     # df_criticidade = pd.DataFrame({
#     #     'nivel_criticidade': contagem_criticidade.index,
#     #     'quantidade': contagem_criticidade.values,
#     #     'percentual': (contagem_criticidade.values / len(df) * 100).round(1)
#     # })
    
#     # # 3. Dados para gráfico de dispersão
#     # df_dispersao = df[['cd_produto', 'desc_produto', 'estoque_atualizado', 'Media 3M', 
#     #                   'percentual_cobertura', 'criticidade']].copy()
    
#     # # 4. Top 20 produtos mais críticos
#     # df_top20_criticos = df.sort_values('percentual_cobertura').head(20)
    
#     # # 5. Resumo de valores por criticidade (se disponível)
#     # if 'valor_estimado_1m' in df.columns:
#     #     resumo_valores = df.groupby('criticidade')['valor_estimado_1m'].sum().reset_index()
#     #     resumo_valores['percentual'] = (resumo_valores['valor_estimado_1m'] / resumo_valores['valor_estimado_1m'].sum() * 100).round(1)
#     # else:
#     #     resumo_valores = pd.DataFrame(columns=['criticidade', 'valor_estimado_1m', 'percentual'])

#      # Adicionar coluna de recência (última venda)
#     try:
#         # Obter os dados da última venda
#         df_ultima_venda = get_ultima_venda()
        
#         # Se já existe a coluna id_produto, renomeie temporariamente
#         if 'id_produto' in df_completo.columns:
#             df_completo = df_completo.rename(columns={'id_produto': 'id_produto_original'})
        
#         # Realizar o merge
#         df_completo = df_completo.merge(
#             df_ultima_venda[['id_produto', 'data_ultima_venda']], 
#             left_on='cd_produto', 
#             right_on='id_produto', 
#             how='left'
#         )
        
#         # Calcular a recência em dias
#         data_hoje = datetime.datetime.now().date()
        
#         # Garantir que a coluna 'data_ultima_venda' seja do tipo datetime
#         df_completo['data_ultima_venda'] = pd.to_datetime(df_completo['data_ultima_venda'], errors='coerce').dt.date
        
#         # Calcular a diferença em dias
#         df_completo['dias_desde_ultima_venda'] = df_completo['data_ultima_venda'].apply(
#             lambda x: (data_hoje - x).days if pd.notna(x) and isinstance(x, datetime.date) else None
#         )
        
#         # Manter a data da última venda como recência para acompanhamento
#         df_completo['recencia'] = df_completo['data_ultima_venda']
        
#         # Adicionar coluna que indica se o produto não tem vendas recentes (mais de 180 dias)
#         df_completo['sem_venda_recente'] = df_completo['dias_desde_ultima_venda'].apply(
#             lambda x: 'Sim' if pd.isna(x) or x > 180 else 'Não'
#         )
        
#         # Manter a coluna id_produto_original se existia antes
#         if 'id_produto_original' in df_completo.columns:
#             df_completo = df_completo.drop('id_produto', axis=1, errors='ignore')
#             df_completo = df_completo.rename(columns={'id_produto_original': 'id_produto'})
        
#         # Substituir valores nulos por valor padrão
#         df_completo['dias_desde_ultima_venda'] = df_completo['dias_desde_ultima_venda'].fillna(-1)  # -1 indica que nunca foi vendido
        
#         print("Merge com data de última venda realizado com sucesso.")
#         print(f"Cálculo de recência em dias concluído: {sum(~pd.isna(df_completo['recencia']))} produtos com vendas registradas.")
#     except Exception as e:
#         print(f"Erro ao adicionar recência dos produtos: {e}")
#         # Garantir que as colunas existam mesmo em caso de erro
#         if 'recencia' not in df_completo.columns:
#             df_completo['recencia'] = None
#         if 'dias_desde_ultima_venda' not in df_completo.columns:
#             df_completo['dias_desde_ultima_venda'] = -1
#         if 'sem_venda_recente' not in df_completo.columns:
#             df_completo['sem_venda_recente'] = 'Sem dados'

#     try:
#         # Recuperar o histórico completo de entradas
#         df_historico_completo = get_historico_entrada()
        
#         # Filtrar apenas movimentos de aquisição
#         df_historico_compras = df_historico_completo[
#             df_historico_completo["descricao"].str.contains("aquisicao|aquisição", case=False, na=False)
#         ]
        
#         # Para cada produto, encontrar a data mais antiga (primeira compra)
#         df_primeira_compra = df_historico_compras.groupby('id_produto')['data_movimento'].min().reset_index()
#         df_primeira_compra.rename(columns={'data_movimento': 'antiguidade', 'id_produto': 'cd_produto'}, inplace=True)
        
#         # Adicionar a informação de antiguidade ao dataframe principal
#         df_completo = df_completo.merge(df_primeira_compra, on='cd_produto', how='left')
        
#         # Substituir valores nulos por '0'
#         df_completo['antiguidade'] = df_completo['antiguidade'].fillna('0')
        
#         print("Dados de antiguidade calculados com sucesso.")
#     except Exception as e:
#         print(f"Erro ao calcular antiguidade: {e}")
#         # Se falhar, criar coluna com valores '0'
#         df_completo['antiguidade'] = '0'
#         print("Usando valor padrão '0' para a coluna de antiguidade.")

#     try:
#         with pd.ExcelWriter(caminho_completo, engine='xlsxwriter') as writer:
#             # Adicionar cada DataFrame como uma aba
#             df_completo.to_excel(writer, sheet_name='Dados_Completos', index=False)
#             # df_criticidade.to_excel(writer, sheet_name='Resumo_Criticidade', index=False)
#             # df_dispersao.to_excel(writer, sheet_name='Dados_Dispersao', index=False)
#             # df_top20_criticos.to_excel(writer, sheet_name='Top20_Criticos', index=False)
            
#             # if not resumo_valores.empty:
#             #     resumo_valores.to_excel(writer, sheet_name='Resumo_Valores', index=False)
        
#         print(f"Arquivo Excel '{caminho_completo}' criado com sucesso!")
#     except Exception as e:
#         print(f"Erro ao salvar arquivo Excel: {e}")
#         # Tentar salvar no diretório atual como último recurso
#         try:
#             fallback_path = arquivo_saida
#             df_completo.to_excel(fallback_path, index=False)
#             print(f"Arquivo salvo como {fallback_path} após falha")
#         except Exception as inner_e:
#             print(f"Falha final ao tentar salvar: {inner_e}")
    
#     print("\nEstrutura do arquivo:")
#     print("- Dados_Completos: Todos os dados com métricas calculadas")
#     print(df_completo.columns)
#     # print("- Resumo_Criticidade: Contagens por nível de criticidade")
#     # print("- Dados_Dispersao: Dados para o gráfico de dispersão")
#     # print("- Top20_Criticos: Os 20 produtos mais críticos")
    
#     # if not resumo_valores.empty:
#     #     print("- Resumo_Valores: Valores de compra estimados por criticidade")

# if __name__ == "__main__":
#     try:
#         print(f"Executando script a partir de: {os.path.abspath(__file__)}")
#         df_resultado = analisar_estoque()
#         if df_resultado is not None:
#             print("\nAnálise concluída com sucesso!")
#     except Exception as e:
#         print(f"Erro durante a análise: {e}")