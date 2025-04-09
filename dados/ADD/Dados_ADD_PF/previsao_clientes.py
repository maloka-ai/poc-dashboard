import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import psycopg2
import dotenv
from tqdm import tqdm

def classificar_padrao_compra(df_cliente):
    """
    Analisa o padrão de compras e classifica em categorias pré-definidas.
    Requer no mínimo 6 pedidos para fazer a análise.
    """
    # Verificar número mínimo de pedidos
    total_pedidos = len(df_cliente)
    if total_pedidos < 6:
        return "Histórico insuficiente (menos de 6 pedidos)"
   
    # Ordenar por data
    df_cliente = df_cliente.sort_values('data_emissao')
   
    # Calcular dias entre compras
    df_cliente['dias_ate_proxima'] = df_cliente['data_emissao'].shift(-1) - df_cliente['data_emissao']
    df_cliente['dias_ate_proxima'] = df_cliente['dias_ate_proxima'].dt.days
   
    # Calcular métricas
    media_dias = df_cliente['dias_ate_proxima'].mean()
    mediana_dias = df_cliente['dias_ate_proxima'].median()
   
    # Calcular compras por dia da semana
    compras_por_dia = df_cliente['data_emissao'].dt.dayofweek.value_counts()
    dias_uteis_com_compra = compras_por_dia[compras_por_dia.index < 5].count()
   
    # Calcular período total
    periodo_total_dias = (df_cliente['data_emissao'].max() - df_cliente['data_emissao'].min()).days
    if periodo_total_dias < 30:
        return "Histórico insuficiente (período menor que 30 dias)"
   
    # Calcular média de compras por semana
    compras_por_semana = (total_pedidos * 7) / periodo_total_dias
   
    # Calcular regularidade (desvio padrão dos intervalos)
    regularidade = df_cliente['dias_ate_proxima'].std()
   
    # Classificação baseada nas métricas calculadas
    if compras_por_semana >= 4 and dias_uteis_com_compra >= 4:
        padrao = "diário - todos os dias úteis"
    elif compras_por_semana >= 3:
        padrao = "3x por semana"
    elif compras_por_semana >= 2:
        padrao = "2x por semana"
    elif compras_por_semana >= 0.8:
        padrao = "1x por semana"
    elif media_dias <= 20:
        padrao = "2x por quinzena"
    elif media_dias <= 35:
        if regularidade <= 7:
            padrao = "1x por quinzena"
        else:
            padrao = "1x por mês"
    elif media_dias <= 75:
        padrao = "1x a cada 2 meses"
    elif media_dias <= 105:
        padrao = "1x a cada 3 meses"
    elif media_dias <= 135:
        padrao = "1x a cada 4 meses"
    elif media_dias <= 165:
        padrao = "1x a cada 5 meses"
    elif media_dias <= 195:
        padrao = "1x a cada 6 meses"
    else:
        padrao = f"1x a cada {round(media_dias/30)} meses"

    # Adicionar informações sobre regularidade
    if regularidade < media_dias * 0.2:
        consistencia = "muito regular"
    elif regularidade < media_dias * 0.4:
        consistencia = "regular"
    else:
        consistencia = "irregular"
   
    # Verificar se há preferência por quinzena específica
    compras_q1 = df_cliente[df_cliente['data_emissao'].dt.day <= 15].shape[0]
    compras_q2 = df_cliente[df_cliente['data_emissao'].dt.day > 15].shape[0]
   
    if abs(compras_q1 - compras_q2) > total_pedidos * 0.3:
        quinzena_preferida = " (preferencialmente na " + ("1ª" if compras_q1 > compras_q2 else "2ª") + " quinzena)"
    else:
        quinzena_preferida = ""
   
    return f"{padrao} - {consistencia}{quinzena_preferida}"

def analisar_cliente(df_cliente):
    """Analisa o padrão de compras de um único cliente."""
    # Total de pedidos
    total_pedidos = len(df_cliente)
   
    # Adicionar colunas de ano, mês e quinzena
    df_cliente['ano'] = df_cliente['data_emissao'].dt.year
    df_cliente['mes'] = df_cliente['data_emissao'].dt.month
    df_cliente['quinzena'] = df_cliente['data_emissao'].apply(lambda x: 1 if x.day <= 15 else 2)
   
    # Criar identificador único para cada quinzena
    df_cliente['quinzena_id'] = df_cliente['data_emissao'].dt.to_period('M').astype(str) + '_Q' + df_cliente['quinzena'].astype(str)
   
    # Agrupar por quinzena
    compras_quinzena = df_cliente.groupby('quinzena_id').size().reset_index()
    compras_quinzena.columns = ['quinzena_id', 'quantidade_compras']
    compras_quinzena['comprou'] = 1
   
    # Criar DataFrame com todas as quinzenas no período
    data_inicial = df_cliente['data_emissao'].min()
    data_final = df_cliente['data_emissao'].max()
   
    # Criar range de datas
    datas_range = pd.date_range(start=data_inicial, end=data_final, freq='MS')
    todas_quinzenas = []
   
    for data in datas_range:
        ano_mes = data.strftime('%Y-%m')
        todas_quinzenas.append(f'{ano_mes}_Q1')
        todas_quinzenas.append(f'{ano_mes}_Q2')
   
    df_todas_quinzenas = pd.DataFrame({'quinzena_id': todas_quinzenas})
   
    # Merge para incluir quinzenas sem compras
    df_quinzenal = pd.merge(df_todas_quinzenas, compras_quinzena[['quinzena_id', 'comprou']],
                           on='quinzena_id', how='left')
    df_quinzenal['comprou'] = df_quinzenal['comprou'].fillna(0)
   
    # Análise de padrões
    total_quinzenas = len(df_quinzenal)
    if total_quinzenas < 6:  # Mínimo de 3 meses de histórico
        return None
       
    # Calcular probabilidades
    ultimos_6m = df_quinzenal.tail(12)  # 12 quinzenas = 6 meses
    q1_recente = ultimos_6m[ultimos_6m['quinzena_id'].str.contains('_Q1')]['comprou'].mean()
    q2_recente = ultimos_6m[ultimos_6m['quinzena_id'].str.contains('_Q2')]['comprou'].mean()
   
    return {
        'q1_prob': q1_recente,
        'q2_prob': q2_recente,
        'ultima_data': pd.to_datetime(df_quinzenal['quinzena_id'].iloc[-1].split('_')[0]),
        'total_compras': total_pedidos,
        'regularidade': max(q1_recente, q2_recente)
    }

# ----------------------------------------------------
# 1. Leitura dos dados AWS
# ----------------------------------------------------

# Nome do arquivo com timestamp para evitar sobrescrever arquivos anteriores
dotenv.load_dotenv()
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("DB_HOST"),
        database="add",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS")
    )
    
    print("Conexão estabelecida com sucesso!")
    
    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela vendas...")
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
    
    # Exportar para Excel
    #df_vendas.to_excel("df_vendas.xlsx", index=False)

    ########################################################
    # consulta da tabela clientes
    ########################################################
    
    # Consultar a tabela clientes
    print("Consultando a tabela clientes...")
    query = "SELECT * FROM clientes"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_clientes_info = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_clientes_info)
    num_colunas = len(df_clientes_info.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_clientes_info.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_clientes_info.head())
    
    # Exportar para Excel
    #df_clientes.to_excel("df_clientes.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados 'add' existe")
    print("3. As credenciais de conexão estão corretas")

# ----------------------------------------------------
# 2. Processamento dos dados
# ----------------------------------------------------
# Converter a coluna 'data_emissao' para datetime
df_vendas['data_emissao'] = pd.to_datetime(df_vendas['data_emissao'])
df_vendas = df_vendas[df_vendas['status'].str.startswith('Pedido')]

# Identificar clientes com pelo menos 6 compras
contagem_compras = df_vendas.groupby('id_cliente').size()
clientes_validos = contagem_compras[contagem_compras >= 6].index

# Processar clientes
print("Iniciando análise de clientes...")
print(f"Total de clientes na base: {len(df_vendas['id_cliente'].unique())}")
print(f"Clientes com 6 ou mais pedidos: {len(clientes_validos)}")

resultados = []
padroes_clientes = {}

for cliente_id in tqdm(clientes_validos):
    df_cliente = df_vendas[df_vendas['id_cliente'] == cliente_id].copy()
   
    # Classificar padrão de compra
    padrao = classificar_padrao_compra(df_cliente)
    padroes_clientes[cliente_id] = padrao
   
    # Análise de quinzenas
    analise = analisar_cliente(df_cliente)
   
    if analise is not None:
        proximas_quinzenas = []
        ultima_data = analise['ultima_data']
       
        for i in range(1, 7):
            mes = ultima_data + pd.DateOffset(months=i)
            ano_mes = mes.strftime('%Y-%m')
           
            proximas_quinzenas.extend([
                {
                    'cliente_id': cliente_id,
                    'quinzena': f"{ano_mes}_Q1",
                    'probabilidade': analise['q1_prob'],
                    'total_compras_historico': analise['total_compras'],
                    'regularidade': analise['regularidade'],
                    'padrao_compra': padrao
                },
                {
                    'cliente_id': cliente_id,
                    'quinzena': f"{ano_mes}_Q2",
                    'probabilidade': analise['q2_prob'],
                    'total_compras_historico': analise['total_compras'],
                    'regularidade': analise['regularidade'],
                    'padrao_compra': padrao
                }
            ])
       
        resultados.extend(proximas_quinzenas)

# Criar DataFrame com resultados
df_resultados = pd.DataFrame(resultados)
df_resultados = df_resultados.sort_values(['cliente_id', 'quinzena'])
df_resultados['probabilidade'] = df_resultados['probabilidade'].fillna(0)

# Gerar Excel
print("\nGerando arquivo Excel...")
# Obter o diretório do script atual
script_dir = os.path.dirname(os.path.abspath(__file__))
# Definir o caminho completo do arquivo no mesmo diretório do script
nome_arquivo = os.path.join(script_dir, f'previsao_retorno.xlsx')


with pd.ExcelWriter(nome_arquivo, engine='xlsxwriter') as writer:
    # # Primeira aba: Previsões detalhadas
    # df_resultados.to_excel(writer, sheet_name='Previsoes_Detalhadas', index=False)
   
    # Segunda aba: Resumo por cliente
    # Criar DataFrame com últimas compras
    ultimas_compras = df_vendas.groupby('id_cliente')['data_emissao'].max().reset_index()
    ultimas_compras.columns = ['cliente_id', 'ultima_compra']
    
    # Calcular próxima compra baseada no padrão
    def estimar_proxima_compra(padrao, ultima_data):
        # Verificar se está inativo (mais de 6 meses sem comprar)
        hoje = pd.Timestamp.now()
        meses_sem_compra = (hoje - ultima_data).days / 30  # aproximação de meses
       
        if meses_sem_compra > 6:
            return "INATIVO"
           
        padrao = padrao.lower()
        if 'diário' in padrao:
            return ultima_data + pd.Timedelta(days=1)
        elif '3x por semana' in padrao:
            return ultima_data + pd.Timedelta(days=2)
        elif '2x por semana' in padrao:
            return ultima_data + pd.Timedelta(days=3)
        elif '1x por semana' in padrao:
            return ultima_data + pd.Timedelta(days=7)
        elif '2x por quinzena' in padrao:
            return ultima_data + pd.Timedelta(days=15)
        elif '1x por quinzena' in padrao:
            return ultima_data + pd.Timedelta(days=15)
        elif '1x por mês' in padrao:
            return ultima_data + pd.DateOffset(months=1)
        elif 'cada 2 meses' in padrao:
            return ultima_data + pd.DateOffset(months=2)
        elif 'cada 3 meses' in padrao:
            return ultima_data + pd.DateOffset(months=3)
        elif 'cada 4 meses' in padrao:
            return ultima_data + pd.DateOffset(months=4)
        elif 'cada 5 meses' in padrao:
            return ultima_data + pd.DateOffset(months=5)
        elif 'cada 6 meses' in padrao:
            return ultima_data + pd.DateOffset(months=6)
        else:
            # Extrair número de meses do padrão se for maior que 6 meses
            import re
            match = re.search(r'cada (\d+) meses', padrao)
            if match:
                meses = int(match.group(1))
                if meses > 6:  # Se o padrão indica intervalo maior que 6 meses
                    return "INATIVO"
                return ultima_data + pd.DateOffset(months=meses)
            return "INATIVO"
   
    # Calcular situação do cliente
    def determinar_situacao(ultima_compra, proxima_compra):
        if proxima_compra == "INATIVO":
            meses_sem_compra = (pd.Timestamp.now() - ultima_compra).days / 30
            return f"INATIVO - {meses_sem_compra:.1f} meses sem comprar"
        return "ATIVO"
   
    resumo_cliente = df_resultados.groupby('cliente_id').agg({
        'probabilidade': ['mean', 'min', 'max'],
        'total_compras_historico': 'first',
        'regularidade': 'first',
        'padrao_compra': 'first'
    }).reset_index()
   
    resumo_cliente.columns = ['cliente_id', 'prob_media', 'prob_minima', 'prob_maxima',
                            'total_compras_historico', 'regularidade', 'padrao_compra']
   
    # Adicionar última compra
    resumo_cliente = pd.merge(resumo_cliente, ultimas_compras, on='cliente_id', how='left')
   
    # Adicionar previsão da próxima compra
    resumo_cliente['proxima_compra'] = resumo_cliente.apply(
        lambda x: estimar_proxima_compra(x['padrao_compra'], x['ultima_compra']),
        axis=1
    )
   
    # Adicionar situação do cliente
    resumo_cliente['situacao'] = resumo_cliente.apply(
        lambda x: determinar_situacao(x['ultima_compra'], x['proxima_compra']),
        axis=1
    )
    resumo_cliente.rename(columns={'cliente_id': 'id_cliente'}, inplace=True)
    resumo_cliente = pd.merge(resumo_cliente, df_clientes_info[['id_cliente', 'nome_cliente']], on='id_cliente', how='left')
    cols_to_round = ['prob_media', 'prob_minima', 'prob_maxima', 'regularidade']
    for col in cols_to_round:
        if col in resumo_cliente.columns:
            resumo_cliente[col] = resumo_cliente[col].round(2)

    resumo_cliente.to_excel(writer, sheet_name='Resumo_por_Cliente', index=False)
    print(resumo_cliente.columns)
    print(resumo_cliente.head())
   
    # Terceira aba: Distribuição de padrões
    # dist_padroes = pd.DataFrame(resumo_cliente['padrao_compra'].value_counts()).reset_index()
    # dist_padroes.columns = ['Padrão de Compra', 'Quantidade de Clientes']
    # dist_padroes['Percentual'] = (dist_padroes['Quantidade de Clientes'] / dist_padroes['Quantidade de Clientes'].sum()) * 100
   
    # dist_padroes.to_excel(writer, sheet_name='Distribuicao_Padroes', index=False)
   
    # Formatação
    workbook = writer.book
    percent_format = workbook.add_format({'num_format': '0.0%'})
   
    # # Formatar aba de previsões
    # worksheet = writer.sheets['Previsoes_Detalhadas']
    # worksheet.set_column('D:D', 12, percent_format)
    # worksheet.set_column('F:F', 50)  # Coluna do padrão de compra
   
    # Formatar aba de resumo
    worksheet = writer.sheets['Resumo_por_Cliente']
    worksheet.set_column('B:D', 12, percent_format)
    worksheet.set_column('F:F', 12, percent_format)
    worksheet.set_column('G:G', 50)  # Coluna do padrão de compra
    worksheet.set_column('J:J', 30)  # Coluna de situação
   
    # Formato para datas
    date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
    worksheet.set_column('H:I', 12, date_format)  # Colunas de data
   
    # Formatos condicionais para situação
    inativo_format = workbook.add_format({'bg_color': '#FFC7CE',  # Rosa claro
                                       'font_color': '#9C0006'})  # Vermelho escuro
    ativo_format = workbook.add_format({'bg_color': '#C6EFCE',    # Verde claro
                                     'font_color': '#006100'})   # Verde escuro
   
    # Aplicar formato condicional na coluna de situação
    worksheet.conditional_format('J2:J1048576', {'type': 'text',
                                               'criteria': 'containing',
                                               'value': 'INATIVO',
                                               'format': inativo_format})
   
    worksheet.conditional_format('J2:J1048576', {'type': 'text',
                                               'criteria': 'containing',
                                               'value': 'ATIVO',
                                               'format': ativo_format})
   
    # # Formatar aba de distribuição
    # worksheet = writer.sheets['Distribuicao_Padroes']
    
    # worksheet.set_column('A:A', 50)  # Coluna do padrão
    # worksheet.set_column('C:C', 12, workbook.add_format({'num_format': '0.0"%"'}))  # Formato percentual com símbolo %
   
    # # Adicionar total
    # total_row = len(dist_padroes) + 1
    # worksheet.write(total_row, 0, 'TOTAL')
    # worksheet.write_formula(total_row, 1, f'=SUM(B2:B{total_row})')
    # worksheet.write_formula(total_row, 2, '100,0%')

print(f"\nArquivo gerado com sucesso: {nome_arquivo}")
# print("\nResumo das abas:")
# print("1. Previsoes_Detalhadas: Probabilidade de compra por quinzena para cada cliente")
print("Resumo_por_Cliente: Estatísticas agregadas por cliente")
# print("3. Distribuicao_Padroes: Distribuição dos diferentes padrões de compra encontrados")