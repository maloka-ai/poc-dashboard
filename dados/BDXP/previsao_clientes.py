import os
import pandas as pd
from datetime import datetime
import psycopg2
import dotenv
from tqdm import tqdm

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
        database="demonstracao",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS")
    )
    
    print("Conexão estabelecida com sucesso!")
    
    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela vendas...")
    query = "SELECT * FROM maloka_core.venda"
    
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
    query = "SELECT * FROM maloka_core.cliente"
    
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
# Converter a coluna 'data_venda' para datetime
df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])

# Identificar clientes com pelo menos 6 compras
contagem_compras = df_vendas.groupby('id_cliente').size()
clientes_validos = contagem_compras[contagem_compras >= 6].index

# Processar clientes
print("Iniciando análise de clientes...")
print(f"Total de clientes na base: {len(df_vendas['id_cliente'].unique())}")
print(f"Clientes com 6 ou mais pedidos: {len(clientes_validos)}")

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
    df_cliente = df_cliente.sort_values('data_venda')
   
    # Calcular dias entre compras
    df_cliente['dias_ate_proxima'] = df_cliente['data_venda'].shift(-1) - df_cliente['data_venda']
    df_cliente['dias_ate_proxima'] = df_cliente['dias_ate_proxima'].dt.days
   
    # Calcular métricas
    media_dias = df_cliente['dias_ate_proxima'].mean()
    mediana_dias = df_cliente['dias_ate_proxima'].median()
   
    # Calcular compras por dia da semana
    compras_por_dia = df_cliente['data_venda'].dt.dayofweek.value_counts()
    dias_uteis_com_compra = compras_por_dia[compras_por_dia.index < 5].count()
   
    # Calcular período total
    periodo_total_dias = (df_cliente['data_venda'].max() - df_cliente['data_venda'].min()).days
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
    compras_q1 = df_cliente[df_cliente['data_venda'].dt.day <= 15].shape[0]
    compras_q2 = df_cliente[df_cliente['data_venda'].dt.day > 15].shape[0]
   
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
    df_cliente['ano'] = df_cliente['data_venda'].dt.year
    df_cliente['mes'] = df_cliente['data_venda'].dt.month
    df_cliente['quinzena'] = df_cliente['data_venda'].apply(lambda x: 1 if x.day <= 15 else 2)
   
    # Criar identificador único para cada quinzena
    df_cliente['quinzena_id'] = df_cliente['data_venda'].dt.to_period('M').astype(str) + '_Q' + df_cliente['quinzena'].astype(str)
   
    # Agrupar por quinzena
    compras_quinzena = df_cliente.groupby('quinzena_id').size().reset_index()
    compras_quinzena.columns = ['quinzena_id', 'quantidade_compras']
    compras_quinzena['comprou'] = 1
   
    # Criar DataFrame com todas as quinzenas no período
    data_inicial = df_cliente['data_venda'].min()
    data_final = df_cliente['data_venda'].max()
   
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

# Gerar CSV
print("\nGerando arquivo CSV...")
# Obter o diretório do script atual
script_dir = os.path.dirname(os.path.abspath(__file__))

# Definir o caminho completo do arquivo
nome_arquivo_resumo = os.path.join(script_dir, 'resumo_por_cliente.csv')

# Criar DataFrame com últimas compras
ultimas_compras = df_vendas.groupby('id_cliente')['data_venda'].max().reset_index()
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
resumo_cliente = pd.merge(resumo_cliente, df_clientes_info[['id_cliente', 'nome']], on='id_cliente', how='left')

# Arredondar colunas numéricas
cols_to_round = ['prob_media', 'prob_minima', 'prob_maxima', 'regularidade']
for col in cols_to_round:
    if col in resumo_cliente.columns:
        resumo_cliente[col] = resumo_cliente[col].round(2)

# Exportar para CSV
resumo_cliente.to_csv(nome_arquivo_resumo, index=False)

print(f"\nArquivo gerado com sucesso: {nome_arquivo_resumo}")
print("Resumo_por_Cliente: Estatísticas agregadas por cliente")