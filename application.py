import io
import os
import glob
import zipfile
import base64
import dash
import dash_bootstrap_components as dbc
import dotenv
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import openai
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache
from flask_caching import Cache
import time
from dash_bootstrap_templates import load_figure_template
from flask import Flask, redirect, url_for, session, request

# Imports das funções de layout modularizadas
from layouts.clientes import (
    get_segmentacao_layout,
    get_rfma_layout,
    get_recorrencia_mensal_layout,
    get_recorrencia_trimestral_layout,
    get_recorrencia_anual_layout,
    get_retencao_layout,
    get_predicao_layout
)
from layouts.vendas import (
    get_faturamento_anual_layout,
    get_vendas_atipicas_layout
)
from layouts.estoque import (
    get_produtos_layout
)
from layouts.interacao import (
    get_chat_layout
)

# Imports das funções utilitárias
from utils import (
    formatar_moeda,
    formatar_percentual,
    formatar_numero,
    format_iso_date
)
from utils import (
    create_card,
    create_metric_tile,
    create_metric_row,
    color,
    gradient_colors,
    cores_segmento,
    content_style,
    button_style,
    nav_link_style,
    card_style,
    card_header_style,
    card_body_style
)

# =============================================================================
# Setup caching for improved performance
# =============================================================================
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

# Otimize as configurações do diskcache
cache.reset('size', int(1e9))  # Limite de 1GB para o cache

# Adicione configurações adicionais para melhor performance
cache.set('cull_limit', 0)  # Desabilita culling automático para melhor performance durante operações intensivas
cache.set('statistics', True)  # Habilita estatísticas para monitoramento


# =============================================================================
# Funções auxiliares pro chat
# =============================================================================
openai.api_key = os.getenv("chatKey")

# Contexto padrão - caso não haja contexto específico para um cliente
CONTEXTO_PADRAO = """
Este é um sistema de análise de clientes para varejo. O sistema fornece insights sobre segmentação de clientes,
métrica RFMA (Recência, Frequência, Valor Monetário e Antiguidade), análises de retenção, recorrência e previsão de compras.

As políticas de atendimento, entrega, pagamento e garantia são específicas para cada cliente.

Este contexto é utilizado para orientar análises e respostas sobre clientes, entregas, pagamentos e garantias.
"""

SEGMENTOS_PADRAO = """ 
    cond_novos = (df_seg['Recency'] <= 30) & (df_seg['Age'] <= 30) 
    
    cond_campeoes = (df_seg['Recency'] <= 180) & \
                    (df_seg['Frequency'] >= 7) & (df_seg['M_decil'] == 10) 
                    
    cond_fieis_baixo_valor = (df_seg['Recency'] <= 180) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 4) & (df_seg['M_decil'] <= 8) #
    
    cond_fieis_alto_valor = (df_seg['Recency'] <= 180) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 4) & (df_seg['M_decil'] > 8) 
                 
    cond_recentes_alto = (df_seg['Recency'] <= 180) & \
                         (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] > 6) 
                         
    cond_recentes_baixo = (df_seg['Recency'] <= 180) & \
                          (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] <= 6)
    
    # Clientes menos ativos
    cond_sumidos = (df_seg['Recency'] >= 180) & (df_seg['Recency'] < 365) 
    cond_inativos = (df_seg['Recency'] >= 365)

    # Segmentação de Clientes

    Nossa estratégia de segmentação divide os clientes em 8 grupos distintos, baseados em comportamento de compra e valor:

    ## Clientes Ativos

    *Novos*: Clientes recentes (últimos 30 dias) e novos na base (menos de 30 dias).

    *Campeões*: Alto valor (top 10% em gastos) com frequência elevada (7+ compras) e compra nos últimos 6 meses.

    *Fiéis de Alto Valor*: Relacionamento longo (mais de 2 anos), frequência regular (4+ compras), alto valor (top 20% em gastos) e compra nos últimos 6 meses.

    *Fiéis de Baixo Valor*: Relacionamento longo (mais de 2 anos), frequência regular (4+ compras), valor moderado a baixo (até 80% em gastos) e compra nos últimos 6 meses.

    *Recentes de Alto Valor*: Compra nos últimos 6 meses, pelo menos 1 compra e valor significativo (top 40% em gastos).

    *Recentes de Baixo Valor*: Compra nos últimos 6 meses, pelo menos 1 compra e valor moderado a baixo (abaixo dos 60% em gastos).

    ## Clientes Menos Ativos

    *Sumidos*: Sem atividade entre 6 meses e 1 ano.

    *Inativos*: Sem atividade há mais de 1 ano.
"""

DATAFRAME_KEYS = """
{'DF': Index(['id_cliente', 'Recency', 'Frequency', 'Monetary', 'Age', 'R_range',
        'F_range', 'M_range', 'A_range', 'R_decil', 'F_decil', 'M_decil',
        'A_decil', 'Segmento', 'nome', 'cpf', 'email', 'telefone'],
       dtype='object'),
 'DF_RC_MENSAL': Index(['yearmonth', 'retained_customers', 'prev_total_customers',
        'retention_rate'],
       dtype='object'),
 'DF_RC_TRIMESTRAL': Index(['trimestre', 'trimestre_obj', 'total_customers', 'returning_customers',
        'new_customers', 'recurrence_rate'],
       dtype='object'),
 'DF_RC_ANUAL': Index(['ano', 'ano_obj', 'total_customers', 'returning_customers',
        'new_customers', 'retention_rate', 'new_rate', 'returning_rate'],
       dtype='object'),
 'DF_RT_ANUAL': Index(['cohort_year', 'period_index', 'num_customers', 'cohort_size',
        'retention_rate'],
       dtype='object'),
 'DF_PREVISOES': Index(['id_cliente', 'Recency', 'Frequency', 'Monetary', 'Age', 'R_range',
        'F_range', 'M_range', 'A_range', 'R_decil', 'F_decil', 'M_decil',
        'A_decil', 'Segmento', 'nome', 'cpf', 'email', 'telefone',
        'frequency_adjusted', 'recency_bg', 'T', 'predicted_purchases_30d',
        'categoria_previsao'],
"""

# Estado das collapses da sidebar
INITIAL_COLLAPSE_STATE = False  # False = iniciar fechados, True = iniciar abertos
collapse_states = {
    "clientes": INITIAL_COLLAPSE_STATE,
    "faturamento": INITIAL_COLLAPSE_STATE,
    "estoque": INITIAL_COLLAPSE_STATE
}

def classificar_pergunta(pergunta):
    prompt = f"""
    Você é um assistente que classifica perguntas sobre análise de clientes do varejo.
    Classifique a seguinte pergunta em uma das categorias de análise: 
    - "RFMA" (Recência, Frequência, Valor Monetário, Tempo de Primeira Compra)
    - "Recorrência" (Mensal, Trimestral ou Anual)
    - "Retenção Anual"
    - "Previsão de Retorno"
    - "Fora do Escopo" (caso não se encaixe nas categorias acima)

    Qualquer pergunta sobre clientes deve ser encaixada numa categoria que não "Fora do Escopo"

    Pergunta: "{pergunta}"
    Se "Fora do Escopo" for uma categoria, não deve haver nenhuma outra. Caso contrário, é possível ter uma ou mais categorias
    Formato de saída: categoria1 (obrigatória), categoria2 (opcional)... 
    """
    
    response = openai.chat.completions.create(
        model="gpt-4o", 
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2
    )
    return [elemento.strip() for elemento in response.choices[0].message.content.split(",")]

def selecionar_dataframes(pergunta, categorias_pergunta):
    prompt = f"""
    Você é um assistente que seleciona DataFrames para responder perguntas sobre clientes no varejo.  
    Temos os seguintes DataFrames disponíveis e suas chaves:  

    {DATAFRAME_KEYS}

    Abaixo está uma lista de categorias extraídas das perguntas:
    {str(categorias_pergunta)}

    Abaixo está a pergunta que foi feita:
    {pergunta}

    Com base nisso, retorne uma lista dos nomes dos DataFrames que contêm informações relevantes.  
    Responda apenas com os nomes dos DataFrames, separados por vírgula.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}], 
        temperature=0.2
    )

    dataframes_usados = [df.strip() for df in response.choices[0].message.content.split(",")]
    return dataframes_usados

# =============================================================================
# Funções para gerenciar clientes e bases de dados
# =============================================================================
def get_available_clients():
    """Lista todos os clientes disponíveis na pasta de dados"""
    clients = []
    if os.path.exists("dados"):
        clients = [d for d in os.listdir("dados") if os.path.isdir(os.path.join("dados", d))]
    
    return clients

def get_available_data_types(client):
    """Lista tipos de dados disponíveis para um cliente"""
    data_types = []
    
    # Verificar no novo formato onde os diretórios estão dentro de dados/{cliente}
    client_path = os.path.join("dados", client)
    if os.path.exists(client_path):
        # Procurar pastas que seguem o padrão Dados_{cliente}_{PF/PJ}
        for item in os.listdir(client_path):
            item_path = os.path.join(client_path, item)
            if os.path.isdir(item_path):
                # Verificar se segue o padrão Dados_{cliente}_{tipo}
                if item.startswith(f"Dados_{client}_"):
                    # Extrair o tipo (PF ou PJ)
                    tipo = item.split("_")[-1]
                    if tipo in ["PF", "PJ"] and tipo not in data_types:
                        data_types.append(tipo)
    
    # Verificar também o formato original (Dados_Cliente_PF) se estiver na raiz
    for tipo in ["PF", "PJ"]:
        path = f"Dados_{client}_{tipo}"
        if os.path.exists(path) and tipo not in data_types:
            data_types.append(tipo)
    
    return data_types

def get_client_context(client):
    """Obter o contexto de um cliente específico"""
    # Verifica a pasta contexts
    context_path = f"contexts/{client.lower()}.txt"
    if os.path.exists(context_path):
        with open(context_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Retorna o contexto padrão caso não exista um contexto específico
    return CONTEXTO_PADRAO

def get_client_segmentos(client):
    """Obter a definição de segmentos para um cliente específico"""
    # Verifica a pasta contexts
    segmentos_path = f"contexts/{client.lower()}_segmentos.txt"
    if os.path.exists(segmentos_path):
        with open(segmentos_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Retorna a definição padrão de segmentos
    return SEGMENTOS_PADRAO

def validate_client_data(client, data_type):
    # Verificar formato esperado: dados/{cliente}/Dados_{cliente}_{data_type}
    expected_path = os.path.join("dados", client, f"Dados_{client}_{data_type}")
    
    # Verificar formato antigo na raiz
    old_format_path = f"Dados_{client}_{data_type}"
    
    # Determinar qual caminho usar
    if os.path.exists(expected_path):
        base_path = expected_path
    elif os.path.exists(old_format_path):
        base_path = old_format_path
    else:
        return False, [f"Diretório não encontrado: nem {expected_path} nem {old_format_path} existem"]
    
    # Lista de arquivos requeridos
    required_files = [
        "analytics_cliente_*.csv",  # Usando glob pattern
        "metricas_recorrencia_mensal.xlsx",
        "metricas_recorrencia_trimestral.xlsx",
        "metricas_recorrencia_anual.xlsx"
    ]
    
    missing_files = []
    
    for req_file in required_files:
        if "*" in req_file:
            # Para arquivos com wildcard
            matches = glob.glob(f"{base_path}/{req_file}")
            if not matches:
                missing_files.append(req_file)
        else:
            # Para arquivos com nome exato
            if not os.path.exists(f"{base_path}/{req_file}"):
                missing_files.append(req_file)
    
    return len(missing_files) == 0, missing_files

def process_upload(contents, filename, destination_folder):
    """Processa um arquivo enviado via upload"""
    if not contents:
        return "Nenhum arquivo enviado."
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    
    if filename.endswith('.zip'):
        # Salvar arquivo ZIP
        zip_path = os.path.join(destination_folder, filename)
        with open(zip_path, 'wb') as f:
            f.write(decoded)
        
        # Extrair ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination_folder)
        
        # Remover arquivo ZIP
        os.remove(zip_path)
        return f"Arquivos extraídos com sucesso em {destination_folder}"
    else:
        # Salvar arquivo individual
        file_path = os.path.join(destination_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(decoded)
        return f"Arquivo {filename} salvo em {destination_folder}"

# =============================================================================
# Função para carregar os dados conforme o cliente e base escolhidos
# =============================================================================
@cache.memoize(expire=900)  # Cache for 15 minutes
def load_data(client, data_type):
    """
    Carrega dados para um cliente e tipo específicos
    
    Args:
        client (str): Nome do cliente (ex: 'BENY', 'CLIENTE2')
        data_type (str): Tipo de dados ('PF' ou 'PJ')
    """
    print(f"[CACHE] Verificando cache para {client}_{data_type}")
    print("Carrega dados para um cliente e tipo específicos")

    # Adicionar chave de versão para invalidar cache quando necessário
    cache_version = "v1.0"  
    cache_key = f"{client}_{data_type}_{cache_version}"

    # Verificar se já existe em cache com esta chave específica
    cached_data = app_cache.get(cache_key)
    if cached_data is not None:
        print(f"[CACHE] Encontrado no cache: {cache_key}")
        return cached_data
    
    print(f"[CACHE] Cache não encontrado para {cache_key}, carregando dados...")
    
    
    # Verificar formato esperado: dados/{cliente}/Dados_{cliente}_{data_type}
    expected_path = os.path.join("dados", client, f"Dados_{client}_{data_type}")
        
    # Verificar formato antigo na raiz
    old_format_path = f"Dados_{client}_{data_type}"
        
    # Determinar qual caminho usar
    if os.path.exists(expected_path):
        base_path = expected_path
    elif os.path.exists(old_format_path):
        base_path = old_format_path
    else:
        return {
            "error": True,
            "message": f"Não foram encontrados dados para {client} - {data_type} nos caminhos:\n- {expected_path}\n- {old_format_path}"
        }
        
    # Verificar se existem os arquivos necessários
    valid, missing_files = validate_client_data(client, data_type)
    if not valid:
        return {
            "error": True,
            "message": f"Arquivos necessários ausentes para {client} - {data_type}: {', '.join(missing_files)}"
        }
        
    # Caminhos dinâmicos para arquivos
    analytics_path = glob.glob(f"{base_path}/analytics_cliente_*.csv")
    rc_mensal_path = f"{base_path}/metricas_recorrencia_mensal.xlsx"
    rc_trimestral_path = f"{base_path}/metricas_recorrencia_trimestral.xlsx"
    rc_anual_path = f"{base_path}/metricas_recorrencia_anual.xlsx"
    previsoes_path = f"{base_path}/rfma_previsoes_ajustado.xlsx"
    rt_anual_path = f"{base_path}/metricas_retencao_anual.xlsx"
    fat_anual_path = f"{base_path}/faturamento_anual.xlsx"
    fat_anual_geral_path = f"{base_path}/faturamento_anual_geral.xlsx"
    fat_mensal_path = f"{base_path}/faturamento_mensal.xlsx"
    vendas_atipicas_path = f"{base_path}/vendas_atipicas_atual.xlsx"
    relatorio_produtos_path = f"{base_path}/relatorio_produtos.xlsx"
    
    # Carregar arquivos
    df = pd.read_csv(analytics_path[0])
    df_RC_Mensal = pd.read_excel(rc_mensal_path) if os.path.exists(rc_mensal_path) else None
    df_RC_Trimestral = pd.read_excel(rc_trimestral_path) if os.path.exists(rc_trimestral_path) else None
    df_RC_Anual = pd.read_excel(rc_anual_path) if os.path.exists(rc_anual_path) else None
    df_Previsoes = pd.read_excel(previsoes_path) if os.path.exists(previsoes_path) else None
    df_RT_Anual = pd.read_excel(rt_anual_path) if os.path.exists(rt_anual_path) else None
    df_fat_Anual = pd.read_excel(fat_anual_path) if os.path.exists(fat_anual_path) else None
    df_fat_Anual_Geral = pd.read_excel(fat_anual_geral_path) if os.path.exists(fat_anual_geral_path) else None
    df_fat_Mensal = pd.read_excel(fat_mensal_path) if os.path.exists(fat_mensal_path) else None
    df_Vendas_Atipicas = pd.read_excel(vendas_atipicas_path) if os.path.exists(vendas_atipicas_path) else None
    df_relatorio_produtos = pd.read_excel(relatorio_produtos_path, sheet_name=0) if os.path.exists(relatorio_produtos_path) else None

    titulo = f"{client} - {data_type}"

    # =============================================================================
    # Processamento dos dados
    # =============================================================================
    if df_RC_Mensal is not None:
        df_RC_Mensal['retention_rate'] = df_RC_Mensal['retention_rate'].round(2)
    
    if df_RC_Trimestral is not None:
        df_RC_Trimestral['recurrence_rate'] = df_RC_Trimestral['recurrence_rate'].round(2)
    
    if df_RC_Anual is not None:
        df_RC_Anual['new_rate'] = df_RC_Anual['new_rate'].round(2)
        df_RC_Anual['returning_rate'] = df_RC_Anual['returning_rate'].round(2)
        df_RC_Anual['retention_rate'] = df_RC_Anual['retention_rate'].round(2)
    
    # Obter contexto específico do cliente
    company_context = get_client_context(client)
    segmentos_context = get_client_segmentos(client)

    # Preparar o resultado final
    result = {
        "df": df,
        "df_RC_Mensal": df_RC_Mensal,
        "df_RC_Trimestral": df_RC_Trimestral,
        "df_RC_Anual": df_RC_Anual,
        "df_Previsoes": df_Previsoes,
        "df_RT_Anual": df_RT_Anual,
        "df_fat_Anual": df_fat_Anual,
        "df_fat_Anual_Geral": df_fat_Anual_Geral,
        "df_fat_Mensal": df_fat_Mensal,
        "df_Vendas_Atipicas": df_Vendas_Atipicas,
        "df_relatorio_produtos": df_relatorio_produtos,
        "titulo": titulo,
        "company_context": company_context,
        "segmentos_context": segmentos_context,
        "error": False
    }
    
    # Salvar no cache antes de retornar
    try:
        # Salvar no cache do Flask com um timeout específico (1 hora = 3600 segundos)
        app_cache.set(cache_key, result, timeout=900)
        print(f"[CACHE] Dados salvos em cache com chave: {cache_key}")
    except Exception as e:
        print(f"[CACHE] Erro ao salvar no cache: {str(e)}")
    
    print(f"[CACHE] Dados carregados para {client}_{data_type}")
    return result

##Retirei formatters



# Loading custom figure template based on our color scheme
load_figure_template('bootstrap')

# rfma_metrics = {
#     "Recency": ("R_range", colors[0]),
#     "Frequency": ("F_range", colors[1]),
#     "Monetary": ("M_range", colors[2]),
#     "Age": ("A_range", colors[3]),
# }



# =============================================================================
# Inicializar o application
# =============================================================================
server = Flask(__name__)
server.secret_key = 'maloka_ai_secret_key_2025'  # Mesma chave do sistema de login

application = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap'],
    suppress_callback_exceptions=True,
    long_callback_manager=long_callback_manager,
    server=server,  # Associar ao servidor Flask
    url_base_pathname='/app/'
)

# Configure caching for app
app_cache = Cache(server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './flask_cache_dir',
    'CACHE_DEFAULT_TIMEOUT': 900,  # 15 minutos de timeout padrão
    'CACHE_THRESHOLD': 1000,  # Número máximo de itens no cache
    'CACHE_OPTIONS': {'mode': 0o755}  # Permissões de diretório
})

# Adicione isto na seção dos estilos
ESTILO_CUSTOMIZADO = {
    'login-container': {
        'background': f"linear-gradient(135deg, {gradient_colors['blue_gradient'][0]} 0%, {gradient_colors['blue_gradient'][2]} 100%)",
        'height': '100vh',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center'
    },
    'login-card': {
        'backgroundColor': 'rgba(255, 255, 255, 0.9)',
        'borderRadius': '15px',
        'boxShadow': '0 10px 25px rgba(0,0,0,0.1)',
        'padding': '30px',
        'width': '350px'
    },
    'login-title': {
        'color': gradient_colors['blue_gradient'][0],
        'textAlign': 'center',
        'marginBottom': '25px',
        'fontWeight': 'bold'
    },
    'login-button': {
        'background': f"linear-gradient(135deg, {gradient_colors['blue_gradient'][0]} 0%, {gradient_colors['blue_gradient'][1]} 100%)",
        'border': 'none',
        'borderRadius': '25px'
    },
    'logo': {
        'maxWidth': '200px',
        'marginBottom': '20px',
        'display': 'block',
        'margin': '0 auto'
    }
}
# =============================================================================
# Estilos de layout
# =============================================================================
# Modern sidebar style
sidebar_style = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "280px",
    "padding": "2rem 1.5rem",
    "background": f"linear-gradient(180deg, {color['primary']} 0%, #033B4A 100%)",
    "overflow-y": "auto",
    "height": "100vh",
    "box-shadow": "4px 0px 10px rgba(0, 0, 0, 0.1)",
    "z-index": "1000",
    "transition": "all 0.3s"
}

# Content style with more spacing


# Card styles




# =============================================================================
# Custom components for improved UI
# =============================================================================


loading_component = dcc.Loading(
    id="loading",
    type="dot",
    children=html.Div(id="loading-output"),
    color=color['secondary']
)

# =============================================================================
# Sidebar com seleção dinâmica de cliente e tipo de dados
# =============================================================================
def create_sidebar(client=None, available_data_types=None):
    # Se client não foi fornecido, tentar obter um cliente padrão
    if client is None:
        clients = get_available_clients()
        if clients:
            client = clients[0]

    # Se available_data_types não foi fornecido, buscar com base no cliente
    if available_data_types is None:
        available_data_types = get_available_data_types(client)

    if not available_data_types:
        available_data_types = ["PF", "PJ"]

    # Mostrar a seleção de tipo de dados apenas se houver mais de um tipo disponível
    show_data_type_selection = len(available_data_types) > 1

    
    sidebar = html.Div(
        [
            html.Div(
                [
                    html.Img(src="assets/maloka_logo.png", style={"width": "60px", "height": "auto"}),
                    html.H4("MALOKA'AI", style={"color": "white", "margin": "0 0 0 10px", "font-weight": "700", "letter-spacing": "1px"})
                ],
                style={"display": "flex", "alignItems": "center", "paddingBottom": "1.5rem"}
            ),
            # App title that will be updated based on the selected data source
            html.H4(client, style={
                "color": "white", 
                "textAlign": "center", 
                "font-weight": "700",
                "marginBottom": "1rem",
                "letter-spacing": "0.5px"
            }),
            html.H5("Dashboard de Análise", style={
                "color": "rgba(255, 255, 255, 0.8)", 
                "textAlign": "center",
                "marginBottom": "1.5rem",
                "font-weight": "400",
                "letter-spacing": "0.5px"
            }),
            html.Hr(style={"borderColor": "rgba(255, 255, 255, 0.2)", "margin": "1.5rem 0"}),
            
            # Navigation sections with icons and improved styling
            html.Div([
                html.P("INTERAÇÃO", style={"color": "rgba(255, 255, 255, 0.5)", "fontSize": "0.8rem", "letterSpacing": "1px", "marginBottom": "0.5rem", "marginLeft": "0.5rem"}),
                dbc.Nav(
                    [
                        dbc.NavLink(
                            [html.I(className="fas fa-comments me-2"), "Chat Assistente"], 
                            href="/chat", 
                            active="exact",
                            style=nav_link_style,
                            className="my-1"
                        ),
                    ],
                    vertical=True,
                    pills=True,
                ),
            ], style={"marginBottom": "1.5rem"}),
            
            # Primeiro Collapse: "Meus Clientes" - Análises de cliente
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-users me-2"), "Relacionamento com Clientes"],
                    id="clientes-collapse-button",
                    color="link",
                    style={
                        "color": "rgba(255, 255, 255, 0.8)",
                        "fontWeight": "500",
                        "fontSize": "0.9rem",
                        "textDecoration": "none",
                        "width": "100%",
                        "textAlign": "left",
                        "padding": "0.5rem 0.8rem",
                        "marginBottom": "0rem"
                    }
                ),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="fas fa-users me-2"), "Segmentação de Clientes"], 
                                href="/segmentacao", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-user-tag me-2"), "Clientes por RFMA"], 
                                href="/", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-sync me-2"), "Recorrência Mensal"], 
                                href="/recorrencia/mensal", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-calendar-check me-2"), "Recorrência Trimestral"], 
                                href="/recorrencia/trimestral", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="far fa-calendar-alt me-2"), "Recorrência Anual"], 
                                href="/recorrencia/anual", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-user-clock me-2"), "Retenção Anual"], 
                                href="/retencao", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-chart-pie me-2"), "Previsão de Retorno"], 
                                href="/predicao", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="clientes-collapse",
                    is_open=collapse_states["clientes"],
                    style={"paddingLeft": "1rem"}
                ),
            ], style={"marginBottom": "1.5rem"}),
            
            # Segunda Collapse: "Faturamento" - Análise financeira
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-chart-line me-2"), "Vendas"],
                    id="faturamento-collapse-button",
                    color="link",
                    style={
                        "color": "rgba(255, 255, 255, 0.8)",
                        "fontWeight": "500",
                        "fontSize": "0.9rem",
                        "textDecoration": "none",
                        "width": "100%",
                        "textAlign": "left",
                        "padding": "0.5rem 0.8rem",
                        "marginBottom": "0rem"
                    }
                ),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="fas fa-chart-line me-2"), "Crescimento do Negócio"], 
                                href="/faturamento/anual", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-exclamation-triangle me-2"), "Vendas Atípicas"], 
                                href="/estoque/vendas-atipicas", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="faturamento-collapse",
                    is_open=collapse_states["faturamento"],
                    style={"paddingLeft": "1rem"}
                ),
            ], style={"marginBottom": "1.5rem"}),

            # Terceira Collapse: "Estoque" - Gestão de estoque
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-boxes me-2"), "Gestão do Estoque"],
                    id="estoque-collapse-button",
                    color="link",
                    style={
                        "color": "rgba(255, 255, 255, 0.8)",
                        "fontWeight": "500",
                        "fontSize": "0.9rem",
                        "textDecoration": "none",
                        "width": "100%",
                        "textAlign": "left",
                        "padding": "0.5rem 0.8rem",
                        "marginBottom": "0rem"
                    }
                ),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="fas fa-exclamation-circle me-2"), "Recomendação de Compras"], 
                                href="/estoque/produtos",
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="estoque-collapse",
                    is_open=collapse_states["estoque"],
                    style={"paddingLeft": "1rem"}
                ),
            ], style={"marginBottom": "1.5rem"}),

            html.Hr(style={"borderColor": "rgba(255, 255, 255, 0.2)", "margin": "1.5rem 0"}),
            
            # Data type selection dropdown
            html.Div([
                html.H5("Selecione a Base de Dados:", style={"color": "white", "fontSize": "1rem", "marginBottom": "1rem", "textAlign": "center"}),
                dcc.Dropdown(
                    id="data-type-selection",
                    options=[{"label": data_type, "value": data_type} for data_type in available_data_types],
                    value=available_data_types[0] if available_data_types else None,
                    clearable=False,
                    style={"color": "black", "backgroundColor": "white"}
                )
            ], style={
                "marginTop": "1rem",
                "background": "rgba(255, 255, 255, 0.05)",
                "padding": "1.5rem",
                "borderRadius": "12px",
                "display": "block" if show_data_type_selection else "none"  # Mostrar apenas se necessário
            }),


            # Botão de logout
            html.Div([
                html.A(  # Link HTML direto
                    html.Button(
                        [html.I(className="fas fa-sign-out-alt me-2"), "Sair"],
                        className="btn btn-danger w-100 mt-4"
                    ),
                    href="/logout/",  # Link direto para a rota de logout
                    style={"textDecoration": "none"}
                )
            ]),


            # Time last updated indicator
            html.Div([
                html.P("Última atualização:", style={"color": "rgba(255, 255, 255, 0.5)", "fontSize": "0.8rem", "marginBottom": "0.2rem"}),
                html.P(id="last-updated", children=time.strftime("%d/%m/%Y %H:%M:%S"), style={"color": "white", "fontSize": "0.9rem", "fontWeight": "600"})
            ], style={
                "marginTop": "2rem", 
                "textAlign": "center"
            })
        ],
        className="sidebar"
    )
    print("###### SIDEBAR GERADA ######")
    return sidebar

# =============================================================================
# Callbacks para controlar os collapses da sidebar
# =============================================================================

# dashboard.py - Callback para inicializar sidebar
@application.callback(
    Output("sidebar-container", "children"),
    Output("selected-client", "data"),
    Output("sidebar-initialized", "data"),
    [Input("url", "search"),
     Input("sidebar-initialized", "data")],
    prevent_initial_call=False
)
def initialize_sidebar(search, is_initialized):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Se a sidebar já foi inicializada e o trigger não é a URL após login, não recria a sidebar
    if is_initialized and (trigger_id != 'url' or ('cliente=' not in search if search else True)):
        return dash.no_update, dash.no_update, True
    
    # Extrair cliente da URL (passado pelo sistema de login)
    if search and 'cliente=' in search:
        # Extrair o cliente do parâmetro de consulta (ex: ?cliente=BENY)
        cliente = search.split('cliente=')[1].split('&')[0]
    else:
        # Verificar se há um cliente na sessão
        if 'cliente' in session:
            cliente = session['cliente']
        else:
            # Se não tiver cliente na URL nem na sessão, redirecionar para login
            return html.Div("Redirecionando para login..."), None, False
    
    # Obter tipos de dados disponíveis para o cliente
    available_data_types = get_available_data_types(cliente)
    
    # Criar sidebar com o cliente específico
    sidebar = create_sidebar(cliente, available_data_types)
    print("Sidebar gerada para", cliente)
    
    return sidebar, cliente, True

# Callbacks das collapses
@application.callback(
    Output("clientes-collapse", "is_open"),
    [Input("clientes-collapse-button", "n_clicks")],
    [State("clientes-collapse", "is_open")],
    prevent_initial_call=True 
)
def toggle_clientes_collapse(n, is_open):
    global collapse_states  # Acessa a variável global
    if n:
        # Atualiza a variável global com o novo estado
        collapse_states["clientes"] = not is_open
        return not is_open
    return is_open

@application.callback(
    Output("faturamento-collapse", "is_open"),
    [Input("faturamento-collapse-button", "n_clicks")],
    [State("faturamento-collapse", "is_open")],
    prevent_initial_call=True 
)
def toggle_faturamento_collapse(n, is_open):
    global collapse_states  # Acessa a variável global
    if n:
        # Atualiza a variável global com o novo estado
        collapse_states["faturamento"] = not is_open
        return not is_open
    return is_open

@application.callback(
    Output("estoque-collapse", "is_open"),
    [Input("estoque-collapse-button", "n_clicks")],
    [State("estoque-collapse", "is_open")],
    prevent_initial_call=True 
)
def toggle_estoque_collapse(n, is_open):
    global collapse_states  # Acessa a variável global
    if n:
        # Atualiza a variável global com o novo estado
        collapse_states["estoque"] = not is_open
        return not is_open
    return is_open

@application.callback(
    Output("titulo-app", "children"),
    [Input("selected-client", "data"),
     Input("selected-data-type", "data")]
)
def update_sidebar_title(selected_client):
    if selected_client is None:
        return "Client"
    return f"{selected_client}"

# =============================================================================
# Layout principal (layout condicional baseado na autenticação)
# =============================================================================
application.layout = html.Div([
    dcc.Location(id='url', refresh=True),  # refresh=True para permitir recarregar após login
    dcc.Store(id='sidebar-initialized', storage_type='session', data=False),  # Novo: estado para controlar inicialização da sidebar
    html.Div(id='page-content')
])

# Definir uma página de login específica com IDs corretos
login_layout = html.Div([
    html.H2("Login MALOKA'AI", style={"textAlign": "center", "marginTop": "50px", "color": gradient_colors['blue_gradient'][0]}),
    html.Div([
        html.Label("Email:"),
        dcc.Input(id="input-email", type="email", placeholder="Digite seu email", style={"width": "100%", "marginBottom": "10px"}),
        html.Label("Senha:"),
        dcc.Input(id="input-senha", type="password", placeholder="Digite sua senha", style={"width": "100%", "marginBottom": "20px"}),
        dbc.Button("Entrar", id="botao-login", style={"width": "100%"}, className="mb-3"),
        html.Div(id="output-login")  # Este é o ID que o callback vai usar
    ], style={"width": "300px", "margin": "0 auto", "padding": "20px", "border": "1px solid #ddd", "borderRadius": "5px", "backgroundColor": "white"})
], style={"height": "100vh", "background": f"linear-gradient(135deg, {gradient_colors['blue_gradient'][0]} 0%, {gradient_colors['blue_gradient'][2]} 100%)", "paddingTop": "10vh"})

@application.callback(
    [Output("output-login", "children"),
     Output("url", "pathname")],
    Input("botao-login", "n_clicks"),
    [State("input-email", "value"),
     State("input-senha", "value")],
    prevent_initial_call=True
)
def validar_login(n_clicks, email, senha):
    if n_clicks is None:
        return dash.no_update, dash.no_update
    
    # Verificação básica de preenchimento
    if not email or not senha:
        return dbc.Alert("Por favor, preencha email e senha.", color="warning"), dash.no_update
    
    # Verificar se a senha está correta - com trim
    SENHA_PADRAO = os.getenv("senhaLogin")
    if senha.strip() != SENHA_PADRAO:
        return dbc.Alert("Senha incorreta.", color="danger"), dash.no_update
    
    # Extrair domínio do email - método mais robusto
    email = email.strip().lower()
    dominio = None
    
    try:
        if '@' in email:
            # Obter a parte após o @
            dominio = '@' + email.split('@')[1]
            
            # Listar os domínios válidos com mais casos
            DOMINIOS_VALIDOS = {
                '@bibi': 'BIBI',
                '@bibi.com': 'BIBI',
                '@beny': 'BENY',
                '@beny.com': 'BENY',
                '@espantalho': 'ESPANTALHO',
                '@espantalho.com': 'ESPANTALHO',
                '@add': 'ADD',
                '@add.com': 'ADD'
            }
            
            # Verificar se o domínio está na lista
            if dominio in DOMINIOS_VALIDOS:
                empresa = DOMINIOS_VALIDOS[dominio]
                
                # Tentar armazenar na sessão com tratamento de erro
                try:
                    session['cliente'] = empresa
                    # Verificar se foi armazenado corretamente
                    if session.get('cliente') == empresa:
                        return dbc.Alert(f"Login bem-sucedido! Redirecionando...", color="success"), "/"
                    else:
                        return dbc.Alert("Erro ao armazenar na sessão. Tente novamente.", color="danger"), dash.no_update
                except Exception as e:
                    return dbc.Alert(f"Erro na sessão: {str(e)}", color="danger"), dash.no_update
            else:
                return dbc.Alert(f"Domínio '{dominio}' não está cadastrado.", color="danger"), dash.no_update
        else:
            return dbc.Alert("Email inválido. Use o formato usuario@dominio.com", color="danger"), dash.no_update
    except Exception as e:
        return dbc.Alert(f"Erro ao processar login: {str(e)}", color="danger"), dash.no_update
         
          
# Callback para mostrar conteúdo baseado na URL/autenticação
@application.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    # Log para rastreamento
    print(f"Callback display_page executado - URL: {pathname} - Cliente na sessão: {'sim' if 'cliente' in session else 'não'}")
    
    # Verificar se não está autenticado
    if 'cliente' not in session:
        print("Usuário não autenticado, exibindo login_layout")
        # Retornar a página de login
        return login_layout
    
    # Se estiver autenticado
    try:
        cliente = session['cliente']
        available_data_types = get_available_data_types(cliente)
        print(f"Usuário autenticado, carregando dashboard para cliente: {cliente}")
        
        # Layout do dashboard
        return html.Div([
            dcc.Store(id='selected-data', storage_type='session'),
            dcc.Store(id='selected-client', data=cliente),
            dcc.Store(id='selected-data-type', data="PF"),
            dcc.Store(id='last-data-load-time', data=time.time()),
            dcc.Loading(
                id="loading-overlay",
                type="circle",
                children=html.Div(id="loading-output-overlay"),
                style={"position": "fixed", "top": "50%", "left": "50%", 
                    "transform": "translate(-50%, -50%)", "zIndex": "9999"}
            ),
            html.Div(id="sidebar-container", children=create_sidebar(cliente, available_data_types)),
            html.Div(id="page-content-dashboard", children=[])
        ])
    except Exception as e:
        print(f"ERRO no callback display_page: {str(e)}")
        # Em caso de erro, mostrar mensagem de erro
        return html.Div([
            html.H3("Erro ao renderizar a página", style={"color": "red"}),
            html.Pre(f"Pathname: {pathname}"),
            html.Pre(f"Erro: {str(e)}"),
            html.Button("Voltar para o início", id="error-redirect-button")
        ])

# Rota raiz
@server.route('/')
def index():
    # Log para rastreamento
    print("Acessando rota raiz '/'")
    try:
        # Redirecionar para a aplicação Dash
        return redirect('/app/')
    except Exception as e:
        print(f"ERRO na rota '/': {str(e)}")
        return f"Erro no redirecionamento: {str(e)}"

# Rota principal da aplicação
@server.route('/app/')
def app_index():
    # Log para rastreamento
    print(f"Acessando rota '/app/' - Cliente na sessão: {'sim' if 'cliente' in session else 'não'}")
    return application.index()  # Sempre retornar o app.index() - o Dash decidirá o que mostrar

# Rota de login específica
@server.route('/app/login/')
def login_page():
    # Log para rastreamento
    print(f"Acessando rota '/app/login/'")
    # Se já estiver autenticado, redirecionar para o dashboard
    if 'cliente' in session:
        return redirect('/app/')
    # Caso contrário, mostrar a aplicação Dash que decidirá mostrar o login_layout
    return application.index()

# Atualize a rota de logout para ser mais direta:
@server.route('/logout/')
def logout():
    """
    Limpa o cache do usuário atual e encerra a sessão antes de redirecionar para a página de login
    """
    try:
        # Obter informações do cliente atual para limpar apenas o seu cache
        cliente_atual = session.get('cliente', None)
        
        # Limpar a sessão
        session.clear()
        
        # Se temos informação do cliente, limpar apenas seu cache específico
        if cliente_atual:
            print(f"Limpando cache para o cliente: {cliente_atual}")
            
            # Limpar apenas os itens de cache específicos deste cliente
            # Padrão para chaves de cache deste cliente: "{cliente_atual}_*"
            cache_keys = []
            
            # Busca no disco cache
            try:
                for key in cache.iterkeys():
                    key_str = str(key)
                    if cliente_atual in key_str:
                        cache.delete(key)
                        cache_keys.append(key_str)
                        
                # Busca no flask cache
                # Note que isso é mais complicado devido à forma como o flask-cache armazena chaves
                with app_cache.app.app_context():
                    for key in list(app_cache.cache._cache.keys()):
                        key_str = str(key)
                        if cliente_atual in key_str:
                            app_cache.delete(key)
                            cache_keys.append(key_str)
                
                print(f"Cache limpo para {cliente_atual}. Chaves afetadas: {len(cache_keys)}")
            except Exception as e:
                print(f"Erro ao limpar cache específico: {str(e)}")
        else:
            # Se não temos informação do cliente, não limpar o cache
            # para evitar afetar outros usuários
            print("Logout sem limpeza de cache - cliente não identificado")
            
        # Redirecionar para a página de login
        return redirect('/')
    except Exception as e:
        print(f"Erro durante logout: {str(e)}")
        return redirect('/')

@server.route('/debug-session/')
def debug_session():
    # Retorna informações sobre a sessão atual
    print("Acessando rota de debug '/debug-session/'")
    session_info = {
        'has_session': 'sim' if 'cliente' in session else 'não',
        'cliente': session.get('cliente', 'nenhum')
    }
    return f"Informações da sessão: {session_info}"
      

def update_data_source(selected_data_type, last_load_time, selected_client):
    # Validar entradas
    if not selected_client or not selected_data_type:
        return None, None, "Selecione o tipo de dados", time.strftime("%d/%m/%Y %H:%M:%S"), last_load_time, None
    
    # Calculate if we need to reload data (every hour)
    current_time = time.time()
    time_diff = current_time - last_load_time
    
    # Verificar se o contexto da chamada foi por mudança de cliente/data-type
    if dash.callback_context.triggered_id not in ['client-selection', 'data-type-selection'] and time_diff < 900:
        # Just update the last updated time
        formatted_time = time.strftime("%d/%m/%Y %H:%M:%S")
        titulo = f"{selected_client} - {selected_data_type}"
        
        return dash.no_update, selected_client, selected_data_type, titulo, formatted_time, last_load_time, None
    
    # Carregar dados para o cliente e tipo selecionados
    data = load_data(selected_client, selected_data_type)
    formatted_time = time.strftime("%d/%m/%Y %H:%M:%S")
    
    if data.get("error", False):
        error_message = data.get("message", "Erro ao carregar dados")
        return None, selected_client, selected_data_type, f"ERRO: {error_message}", formatted_time, current_time, error_message
    
    return {
        "df": data["df"].to_json(date_format='iso', orient='split') if data["df"] is not None else None,
        "df_RC_Mensal": data["df_RC_Mensal"].to_json(date_format='iso', orient='split') if data["df_RC_Mensal"] is not None else None,
        "df_RC_Trimestral": data["df_RC_Trimestral"].to_json(date_format='iso', orient='split') if data["df_RC_Trimestral"] is not None else None,
        "df_RC_Anual": data["df_RC_Anual"].to_json(date_format='iso', orient='split') if data["df_RC_Anual"] is not None else None,
        "df_Previsoes": data["df_Previsoes"].to_json(date_format='iso', orient='split') if data["df_Previsoes"] is not None else None,
        "df_RT_Anual": data["df_RT_Anual"].to_json(date_format='iso', orient='split') if data["df_RT_Anual"] is not None else None,
        "df_fat_Anual": data["df_fat_Anual"].to_json(date_format='iso', orient='split') if data["df_fat_Anual"] is not None else None,
        "df_fat_Anual_Geral": data["df_fat_Anual_Geral"].to_json(date_format='iso', orient='split') if data["df_fat_Anual_Geral"] is not None else None,
        "df_fat_Mensal": data["df_fat_Mensal"].to_json(date_format='iso', orient='split') if data["df_fat_Mensal"] is not None else None,
        "company_context": data["company_context"],
        "segmentos_context": data["segmentos_context"]
    }, selected_client, selected_data_type, data["titulo"], formatted_time, current_time, None

# =============================================================================
# Páginas do Dashboard
# =============================================================================

@application.callback(
    [Output("produto-consumo-header", "children"),
     Output("produto-consumo-grafico", "children")],
    [Input("produtos-criticidade-table", "active_cell"),
     Input("produtos-criticidade-table", "derived_virtual_data"),
     Input("produtos-criticidade-table", "derived_virtual_selected_rows")],
    [State("selected-data", "data")]
)
def update_produto_consumo_grafico(active_cell, virtual_data, selected_rows, data):
    """
    Atualiza o gráfico de consumo quando um produto é selecionado na tabela.
    """
    # Verificar se temos seleção e dados válidos
    if active_cell is None or virtual_data is None or not virtual_data:
        return "Gráfico de Consumo do Produto Selecionado", html.Div([
            html.P("Selecione um produto na lista acima para visualizar o gráfico de consumo.", 
                   className="text-center text-muted my-4"),
            html.Div(className="text-center", children=[
                html.I(className="fas fa-chart-line fa-2x text-muted"),
                html.P("O gráfico mostrará o histórico de consumo e sugestões de compra", 
                       className="text-muted mt-2")
            ])
        ])
    
    if data is None or data.get("df_relatorio_produtos") is None:
        return "Dados não disponíveis", "Não foi possível carregar os dados dos produtos."
    
    try:
        # Obter o produto selecionado da tabela
        row_id = active_cell["row"]
        if row_id >= len(virtual_data):
            return "Erro de seleção", "A linha selecionada está fora dos limites da tabela."
            
        produto_selecionado = virtual_data[row_id]
        
        # Encontrar a coluna que contém o código do produto
        codigo_colunas = ['cd_produto', 'Código', 'codigo', 'ID']
        desc_colunas = ['desc_produto', 'Produto', 'Descrição', 'Nome', 'descricao']
        
        cd_produto = None
        for col in codigo_colunas:
            if col in produto_selecionado and produto_selecionado[col]:
                cd_produto = str(produto_selecionado[col])
                break
                
        if not cd_produto:
            return "Código não encontrado", "Não foi possível identificar o código do produto."
            
        # Obter a descrição do produto
        desc_produto = None
        for col in desc_colunas:
            if col in produto_selecionado and produto_selecionado[col]:
                desc_produto = produto_selecionado[col]
                break
                
        if not desc_produto:
            desc_produto = f"Produto {cd_produto}"
        
        # Carregar dados de produtos
        df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')
        
        # Verificar se o produto existe no dataframe
        # Tentar diferentes formatos de código para aumentar compatibilidade
        cd_produto_encontrado = False
        for valor in [cd_produto, int(cd_produto) if cd_produto.isdigit() else cd_produto]:
            if valor in df_produtos['cd_produto'].values:
                cd_produto = valor
                cd_produto_encontrado = True
                break
        
        if not cd_produto_encontrado:
            return f"Produto não encontrado: {cd_produto}", html.Div([
                html.P(f"O produto com código {cd_produto} não foi encontrado na base de dados.", 
                       className="text-center text-muted my-4")
            ])
        
        # Chamar a função para criar o gráfico
        fig = criar_grafico_produto(df_produtos, cd_produto)

        # Verificar se todos os custos são zero
        def todos_custos_zerados():
            custo1 = produto_selecionado.get('custo1', 'R$ 0,00')
            custo2 = produto_selecionado.get('custo2', '0')
            custo3 = produto_selecionado.get('custo3', '0')
            
            # Converter para string se for número
            if not isinstance(custo1, str): custo1 = str(custo1)
            if not isinstance(custo2, str): custo2 = str(custo2)
            if not isinstance(custo3, str): custo3 = str(custo3)
            
            # Verificar se todos são zero ou vazios
            return (custo1 == 'R$ 0,00' or custo1 == '') and (custo2 == '0' or custo2 == '') and (custo3 == '0' or custo3 == '')
                
        # Adicionar título legível e detalhes
        header = None if todos_custos_zerados() else html.Div([
            # Informações de fornecedor 1
            html.H6("Últimas Compras", className="mt-4 mb-3"),
            html.Div([
                html.Div([
                    # Usando blocos com grande espaçamento horizontal
                    html.Div([
                        html.Span("Data: ", className="font-weight-bold"),
                        html.Span(format_iso_date(produto_selecionado.get('Data1', '-')))
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Qtd: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Quantidade1', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Custo Unitário: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('custo1', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Fornecedor: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Fornecedor1', '-')}")
                    ], style={"display": "inline-block"}) if produto_selecionado.get('Fornecedor1') and produto_selecionado.get('Fornecedor1') != '0' and produto_selecionado.get('Fornecedor1') != 0.0 else None
                ], className="text-muted")
            ], className="mt-4 pb-3 border-bottom") if (
            produto_selecionado.get('Fornecedor1') != '0' and 
            produto_selecionado.get('Fornecedor1') != 0.0 or 
            produto_selecionado.get('custo1') != 'R$ 0,00' and 
            produto_selecionado.get('custo1') != 0.0) 
            else None,

            # Informações de fornecedor 2
            html.Div([
                html.Div([
                    # Usando blocos com grande espaçamento horizontal
                    html.Div([
                        html.Span("Data: ", className="font-weight-bold"),
                        html.Span(format_iso_date(produto_selecionado.get('Data2', '-')))
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Qtd: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Quantidade2', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Custo Unitário: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('custo2', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Fornecedor: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Fornecedor2', '-')}")
                    ], style={"display": "inline-block"}) if produto_selecionado.get('Fornecedor2') and produto_selecionado.get('Fornecedor2') != '0' and produto_selecionado.get('Fornecedor2') != 0.0 else None
                ], className="text-muted")
            ], className="mt-4 pb-3 border-bottom") if (
            produto_selecionado.get('Fornecedor2') != '0' and 
            produto_selecionado.get('Fornecedor2') != 0.0 or 
            produto_selecionado.get('custo2') != 'R$ 0,00' and 
            produto_selecionado.get('custo2') != 0.0) 
            else None,

            # Informações de fornecedor 3
            html.Div([
                html.Div([
                    # Usando blocos com grande espaçamento horizontal
                    html.Div([
                        html.Span("Data: ", className="font-weight-bold"),
                        html.Span(format_iso_date(produto_selecionado.get('Data3', '-')))
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Qtd: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Quantidade3', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Custo Unitário: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('custo3', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Fornecedor: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Fornecedor3', '-')}")
                    ], style={"display": "inline-block"}) if produto_selecionado.get('Fornecedor3') and produto_selecionado.get('Fornecedor3') != '0' and produto_selecionado.get('Fornecedor3') != 0.0 else None
                ], className="text-muted")
            ], className="mt-4 pb-3 border-bottom") if (
            produto_selecionado.get('Fornecedor3') != '0' and 
            produto_selecionado.get('Fornecedor3') != 0.0 or 
            produto_selecionado.get('custo3') != 'R$ 0,00' and 
            produto_selecionado.get('custo3') != 0.0) 
            else None,
        ])
        
        # Adicionar o gráfico com legenda explicativa
        grafico_component = html.Div([
            dcc.Graph(
                figure=fig,
                config={"responsive": True},
                style={"height": "500px"}
            ),
            html.Div([
                html.P([
                    "O gráfico mostra o histórico de consumo nos últimos meses e a sugestão de compra.",
                    html.Br(),
                    html.Span("Sugestão 1M: ", className="font-weight-bold"),
                    "Quantidade sugerida para compra no próximo mês.", 
                    html.Br(),
                    html.Span("Sugestão 3M: ", className="font-weight-bold"),
                    "Quantidade sugerida para compra nos próximos três meses."
                ], className="text-muted small mt-2")
            ])
        ])
        
        return header, grafico_component
    
    except Exception as e:
        return "Erro ao gerar gráfico", html.Div([
            html.P(f"Ocorreu um erro ao gerar o gráfico: {str(e)}", 
                   className="text-center text-danger my-4"),
            html.Pre(str(e), className="bg-light p-3 text-danger")
        ])


# Callback para atualizar o estado do filtro e o texto do botão
@application.callback(
    [Output("filtro-criticos-ativo", "data"),
     Output("btn-filtro-criticos", "children"),
     Output("btn-filtro-criticos", "color")],
    Input("btn-filtro-criticos", "n_clicks"),
    State("filtro-criticos-ativo", "data"),
    prevent_initial_call=True
)
def toggle_filtro_criticos(n_clicks, filtro_ativo):
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update
    
    # Inverte o estado atual do filtro
    novo_estado = not filtro_ativo
    
    # Texto e cor do botão dependendo do estado
    if novo_estado:
        # Se o filtro estiver ativo (mostrando apenas críticos)
        texto_botao = [html.I(className="fas fa-filter me-2"), "Mostrar Todos os Produtos"]
        cor_botao = "primary"
    else:
        # Se o filtro estiver inativo (mostrando todos)
        texto_botao = [html.I(className="fas fa-filter me-2"), "Mostrar Produtos com Reposição Não-Local"]
        cor_botao = "danger"
    
    return novo_estado, texto_botao, cor_botao

# Callback para atualizar o gráfico de barras com base no filtro
@application.callback(
    Output("produtos-criticidade-bar", "figure"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
)
def update_grafico_barras(filtro_ativo, produtos_data):
    if produtos_data is None:
        return dash.no_update
    
    # Carregamos os dados
    df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
    
    # Se o filtro estiver ativo, filtrar para mostrar apenas produtos críticos
    if filtro_ativo:
        # Em vez de filtrar a contagem, vamos filtrar o dataframe original
        df_filtrado = df_criticos[df_criticos['critico'] == True]

        contagem_criticidade = df_filtrado['criticidade'].value_counts().sort_index()

        total_produtos = len(df_filtrado)
        total_series = pd.Series([total_produtos], index=['Todos'])
        contagem_criticidade = pd.concat([contagem_criticidade, total_series])
    else:
        # Contagem normal de todos os produtos por criticidade
        contagem_criticidade = df_criticos['criticidade'].value_counts().sort_index()
        # Adicionar o total
        total_produtos = len(df_criticos)
        total_series = pd.Series([total_produtos], index=['Todos'])
        contagem_criticidade = pd.concat([contagem_criticidade, total_series])
    
    # Calcular porcentagens para anotações
    porcentagens = contagem_criticidade.copy()
    for idx in porcentagens.index:
        if idx == 'Todos':
            print("cheguei nos 100%")
            porcentagens[idx] = 100.0  # Forçar 100% para o total
        else:
            porcentagens[idx] = (contagem_criticidade[idx] / total_produtos * 100).round(1)
    
    # Criar gráfico de barras
    fig = px.bar(
        x=contagem_criticidade.index,
        y=contagem_criticidade.values,
        color=contagem_criticidade.index,
        color_discrete_map={
            'Crítico': 'darkred',
            'Muito Baixo': 'orange',
            'Baixo': color['warning'],
            'Adequado': gradient_colors['green_gradient'][0],
            'Excesso': color['secondary'],
            'Todos': color['primary']
        },
        labels={'x': 'Nível de Criticidade', 'y': 'Quantidade de Produtos'},
        template='plotly_white'
    )
    
    # Adicionar valores nas barras
    for i, v in enumerate(contagem_criticidade.values):
        percentage = porcentagens[contagem_criticidade.index[i]]
        fig.add_annotation(
            x=contagem_criticidade.index[i],
            y=v,
            text=f"{str(v)} ({percentage:.1f}%)".replace(".", ","),
            showarrow=False,
            yshift=10,
            font=dict(size=14, color="black", family="Montserrat", weight="bold")
        )
    
    fig.update_layout(
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        xaxis_title="Nível de Criticidade",
        yaxis_title="Quantidade de Produtos",
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# Callback para atualizar o Top 20 produtos críticos com base no filtro
@application.callback(
    Output("produtos-criticidade-top20", "figure"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
)
def update_grafico_top20(filtro_ativo, produtos_data):
    if produtos_data is None:
        return dash.no_update
    
    # Carregamos os dados
    df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
    
    # Verificar a coluna de descrição do produto
    produto_col = 'desc_produto' if 'desc_produto' in df_criticos.columns else 'Produto' if 'Produto' in df_criticos.columns else None
    
    if not produto_col:
        # Se não tiver coluna de produto, retorna um gráfico vazio
        fig = go.Figure()
        fig.update_layout(
            title="Coluna de descrição de produto não encontrada",
            title_font=dict(size=16, family="Montserrat", color=color['primary'])
        )
        return fig
    
    # Filtrar os dados com base no estado do filtro
    if filtro_ativo:
        df_filtrado = df_criticos[df_criticos['critico'] == True]
    else:
        df_filtrado = df_criticos
    
    # Ordenar pelo percentual de cobertura
    df_ordenado = df_filtrado.sort_values('percentual_cobertura')
    
    # Selecionar os Top 20
    top_20 = df_ordenado.head(20)
    
    # Criar a coluna de exibição do produto
    top_20['produto_display'] = top_20[produto_col].apply(lambda x: (x[:30] + '...') if len(str(x)) > 30 else x)
    
    # Criar o gráfico
    fig = px.bar(
        top_20,
        y='produto_display',
        x='percentual_cobertura',
        orientation='h',
        color='percentual_cobertura',
        color_continuous_scale=['darkred', 'orange', color['warning']],
        range_color=[0, 50 if filtro_ativo else 100],  # Ajusta range de cores com base no filtro
        labels={'percentual_cobertura': 'Cobertura (%)', 'produto_display': 'Produto'},
        template='plotly_white'
    )
    
    if 'cd_produto' in top_20.columns:
        fig.update_traces(
            hovertemplate='<b>%{y}</b><br>Código: %{customdata[0]}<br>Cobertura: %{x:.1f}%',
            customdata=top_20[['cd_produto']]
        )
    
    fig.update_layout(
        title=f"Top 20 Produtos{' Críticos' if filtro_ativo else ''}",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        yaxis_title="",
        xaxis_title="Percentual de Cobertura (%)",
        margin=dict(l=200, r=20, t=30, b=30),
        height=500,
        yaxis=dict(autorange="reversed"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Adicionar linha em 30% para referência de criticidade
    fig.add_shape(
        type="line",
        x0=30, y0=-0.5,
        x1=30, y1=len(top_20) - 0.5,
        line=dict(color="darkred", width=2, dash="dash"),
    )
    
    # Adicionar valores de percentual nas barras
    for i, row in enumerate(top_20.itertuples()):
        fig.add_annotation(
            x=row.percentual_cobertura,
            y=row.produto_display,
            text=f"{row.percentual_cobertura:.1f}%".replace(".", ","),
            showarrow=False,
            xshift=15,
            font=dict(size=12, color="black", family="Montserrat")
        )
    
    return fig

@application.callback(
    Output("div-metrics-row", "children"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
)
def update_metricas(filtro_ativo, produtos_data):
    if produtos_data is None:
        return dash.no_update
    
    # Carregamos os dados
    df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
    
    # Se o filtro estiver ativo, mostrar apenas informações de produtos críticos
    if filtro_ativo:
        df_filtrado = df_criticos[df_criticos['critico'] == True]
        
        # Contar produtos por cada categoria de criticidade
        total_produtos = len(df_filtrado)
        produtos_criticos = len(df_filtrado[df_filtrado['criticidade'] == 'Crítico'])
        produtos_muito_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'Muito Baixo'])
        produtos_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'Baixo'])
        produtos_adequados = len(df_filtrado[df_filtrado['criticidade'] == 'Adequado'])
        produtos_excesso = len(df_filtrado[df_filtrado['criticidade'] == 'Excesso'])
        
        # Criar métricas para a primeira linha de cards - mostrando todas as categorias
        metrics = [
            {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
            {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
            {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
            {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
            {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
            {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
        ]
        
    else:
        # Contar produtos por cada categoria de criticidade
        total_produtos = len(df_criticos)
        produtos_criticos = len(df_criticos[df_criticos['criticidade'] == 'Crítico'])
        produtos_muito_baixos = len(df_criticos[df_criticos['criticidade'] == 'Muito Baixo'])
        produtos_baixos = len(df_criticos[df_criticos['criticidade'] == 'Baixo'])
        produtos_adequados = len(df_criticos[df_criticos['criticidade'] == 'Adequado'])
        produtos_excesso = len(df_criticos[df_criticos['criticidade'] == 'Excesso'])
        
        # Criar métricas para a primeira linha de cards - mostrando todas as categorias
        metrics = [
            {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
            {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
            {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
            {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
            {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
            {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
        ]
    
    # Retornar a linha de métricas criada
    return create_metric_row(metrics)

@application.callback(
    [Output("produtos-criticidade-header", "children"),
     Output("produtos-criticidade-list", "children")],
    [Input("produtos-criticidade-bar", "clickData"),
     Input("filtro-criticos-ativo", "data")],
    [State("selected-data", "data")]
)
def update_produtos_criticidade_list(clickData_bar, filtro_ativo, data):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return "Produtos do Nível de Cobertura Selecionado", html.Div([
            html.P("Selecione um nível de cobertura no gráfico para ver os produtos.", 
                  className="text-center text-muted my-4")
        ])
    
    if data is None or data.get("df_relatorio_produtos") is None:
        return "Dados Indisponíveis", html.Div([
            html.P("Não foi possível carregar os dados dos produtos.", 
                  className="text-center text-muted my-4")
        ])
    
    df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')

    if filtro_ativo:
        df_produtos = df_produtos[df_produtos['critico'] == True]
    
    # Converta as colunas de string para lowercase para facilitar buscas case-insensitive
    string_columns = df_produtos.select_dtypes(include=['object']).columns
    for col in string_columns:
        try:
            # Tentar converter para lowercase, mas ignorar erros (se houver valores não-string)
            df_produtos[f"{col}_lower"] = df_produtos[col].str.lower()
        except:
            pass
    
    # Determine which chart was clicked
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Initialize default criticidade
    selected_criticidade = None
    
    if trigger_id == 'produtos-criticidade-bar' and clickData_bar:
        selected_criticidade = clickData_bar['points'][0]['x']
    
    if selected_criticidade is None:
        return "Produtos do Nível de Cobertura Selecionado", html.Div([
            html.P("Não foi possível identificar a cobertura selecionada.", className="text-center text-muted my-4")
        ])
    
    # Checar se foi selecionado "Todos"
    if selected_criticidade == 'Todos':
        header_text = "Todos os Produtos"
        filtered_df = df_produtos  # Usar todo o DataFrame
    else:
        header_text = f"Produtos com Criticidade: {selected_criticidade}"
        # Filtrar TODOS os produtos desta criticidade
        filtered_df = df_produtos[df_produtos["criticidade"] == selected_criticidade]
    
    if filtered_df.empty:
        return header_text, "Nenhum produto encontrado para a criticidade selecionada."
    
    # Determinar colunas de exibição
    display_columns = [
        "cd_produto", "desc_produto", "critico", "estoque_atualizado", "Media 3M", 
        "percentual_cobertura", "Sug 1M", "Sug 3M", 
        "Data1", "Quantidade1", "custo1", "Fornecedor1", 
        "Data2", "Quantidade2", "custo2", "Fornecedor2",
        "Data3", "Quantidade3", "custo3", "Fornecedor3"
    ]
    
    # Usar apenas colunas que existem no DataFrame
    existing_columns = [col for col in display_columns if col in filtered_df.columns]
    if not existing_columns:
        return header_text, "Estrutura de dados incompatível para exibição de detalhes."
    
    # Renomear colunas para melhor visualização
    col_rename = {
        "cd_produto": "Código",
        "desc_produto": "Produto",
        "critico": "Reposição Não-Local (Crítico)",
        "estoque_atualizado": "Estoque Atual",
        "Media 3M": "Consumo Médio (3M)",
        "percentual_cobertura": "Cobertura (%)",
        "Sug 1M": "Sugestão (1M)",
        "Sug 3M": "Sugestão (3M)",
        "Data1": "Data 1",
        "Quantidade1": "Quantidade 1",
        "custo1": "Custo Unitário 1",
        "Fornecedor1": "Fornecedor 1",
        "Data2": "Data 2",
        "Quantidade2": "Quantidade 2",
        "custo2": "Custo Unitário 2",
        "Fornecedor2": "Fornecedor 2",
        "Quantidade3": "Quantidade 3",
        "Data3": "Data 3",
        "custo3": "Custo Unitário 3",
        "Fornecedor3": "Fornecedor 3"
    }
    
    # Formatação especial para valores monetários e percentuais
    filtered_df_display = filtered_df[existing_columns].copy()
    
    if 'percentual_cobertura' in filtered_df_display.columns:
        filtered_df_display['percentual_cobertura'] = filtered_df_display['percentual_cobertura'].apply(
            lambda x: f"{x:.1f}%".replace(".", ",")
        )
    
    # Formatar colunas monetárias - AQUI ESTÁ O ERRO
    # Verificar e converter para o formato correto antes de aplicar formatação
    for custo_col in ['custo1', 'custo2', 'custo3']:
        if custo_col in filtered_df_display.columns:
            # Verificar se a coluna já está formatada como string de moeda
            def format_currency_safely(value):
                try:
                    if pd.isna(value) or value == "":
                        return ""
                    # Se já for uma string que começa com R$, retornar diretamente
                    if isinstance(value, str) and value.strip().startswith('R$'):
                        return value
                    # Caso contrário, tentar converter para float e formatar
                    return formatar_moeda(float(value)) if value != 0 else ""
                except (ValueError, TypeError):
                    # Em caso de erro, retornar o valor original
                    return str(value) if not pd.isna(value) else ""
            
            filtered_df_display[custo_col] = filtered_df_display[custo_col].apply(format_currency_safely)
    
    # Formatar datas
    for data_col in ['Data1', 'Data2', 'Data3']:
        if data_col in filtered_df_display.columns:
            filtered_df_display[data_col] = filtered_df_display[data_col].apply(
                lambda x: format_iso_date(x) if not pd.isna(x) else ""
            )
    
    # Criar tabela aprimorada com filtro case-insensitive
    table = dash_table.DataTable(
        id='produtos-criticidade-table',  # ID único para a tabela
        columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
        data=filtered_df_display.to_dict("records"),
        page_size=10,  # Aumentado para mostrar mais produtos por página
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "10px 15px",
            "fontFamily": "Montserrat",
            "fontSize": "14px"
        },
        style_header={
            "backgroundColor": "rgb(240,240,240)",
            "fontWeight": "bold",
            "textAlign": "center",
            "fontSize": "14px",
            "fontFamily": "Montserrat"
        },
        style_data_conditional=[
            {
                "if": {"column_id": "percentual_cobertura"},
                "fontWeight": "bold",
                "color": "darkred" if selected_criticidade == "Crítico" else 
                        "orange" if selected_criticidade == "Muito Baixo" else
                        color['warning'] if selected_criticidade == "Baixo" else
                        "green" if selected_criticidade == "Adequado" else color['secondary']
            },
            {
                "if": {"column_id": "custo1"},
                "fontWeight": "bold"
            },
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ],
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        export_format="xlsx",
        # Configuração para tornar o filtro case-insensitive
        filter_options={
            'case': 'insensitive'   # Ignora maiúsculas/minúsculas nos filtros
        }
    )
    
    # Adicionar resumo acima da tabela
    total_categoria = len(filtered_df)
    summary = html.Div([
        html.P([
            f"Exibindo todos os ", 
            html.Strong(formatar_numero(total_categoria)), 
            f" produtos com cobertura: ", 
            html.Strong(selected_criticidade)
        ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
    ])
    
    return header_text, html.Div([summary, table])

# """"""""""""""""""""""""""""""""""""""""""""""""""""""
# Geração de gráficos de consumo de produtos
# """"""""""""""""""""""""""""""""""""""""""""""""""""""

def criar_grafico_simulado(produto, valores, meses_labels):
    """
    Cria um gráfico simulado quando as colunas não estão no formato esperado.
    
    Args:
        produto: Série com os dados do produto
        valores: Lista de valores mensais
        meses_labels: Lista de rótulos para os meses
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Obter as sugestões de compra
        sug_1m = float(produto['Sug 1M']) if 'Sug 1M' in produto else 0
        sug_3m = float(produto['Sug 3M']) if 'Sug 3M' in produto else 0
        
        # Nome do produto
        nome_produto = produto.get('desc_produto', produto.get('Produto', f"Produto {produto.get('cd_produto', '')}"))
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Adicionar linha de consumo mensal
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=valores,
                mode='lines+markers+text',
                name='Consumo',
                line=dict(color='#0077B6', width=3),
                marker=dict(size=8, color='#0077B6'),
                text=[str(int(v)) for v in valores],
                textposition='top center',
                textfont=dict(size=10)
            )
        )
        
        # Adicionar barras para Sugestão 1M e 3M
        x_all = meses_labels + ['Sugestão\n1M', 'Sugestão\n3M']
        
        # Adicionar barra para Sugestão 1M
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n1M'],
                y=[sug_1m],
                name='Sugestão 1M',
                marker_color='#0077B6',
                text=[str(int(sug_1m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Adicionar barra para Sugestão 3M 
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n3M'],
                y=[sug_3m],
                name='Sugestão 3M',
                marker_color='#0077B6',
                text=[str(int(sug_3m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Configurar layout
        fig.update_layout(
            title=f"Consumo Mensal - {nome_produto}",
            title_font=dict(size=16, family="Montserrat", color='#001514'),
            xaxis=dict(
                title="",
                tickmode='array',
                tickvals=x_all,
                ticktext=x_all,
                tickangle=-45,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title="Quantidade",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=80),
            height=500
        )
        
        # Adicionar linha horizontal no zero
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=len(x_all) - 1,
            y1=0,
            line=dict(color="black", width=1)
        )
        
        return fig
    
    except Exception as e:
        print(f"Erro ao gerar gráfico simulado: {str(e)}")
        # Retornar um gráfico de erro
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao gerar gráfico simulado: {str(e)}",
            showarrow=False,
            font=dict(size=12, color="red")
        )
        return fig

def criar_grafico_produto(df_produto, cd_produto):
    """
    Cria um gráfico de consumo mensal para um produto específico,
    similar ao da imagem de referência.
    
    Args:
        df_produto: DataFrame contendo os dados dos produtos
        cd_produto: Código do produto para gerar o gráfico
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Filtrar o produto específico
        produto = df_produto[df_produto['cd_produto'] == cd_produto].iloc[0]
        
        # Obter colunas que representam meses (formato: YYYY_MM)
        colunas_meses = [col for col in df_produto.columns if col.startswith('202')]
        
        # Se não houver colunas de meses no formato YYYY_MM, verificar outros formatos possíveis
        if not colunas_meses:
            # Tentar encontrar colunas numéricas que possam representar meses
            colunas_numericas = [col for col in df_produto.columns 
                                if isinstance(col, str) and col not in ['cd_produto', 'desc_produto', 'estoque_atualizado', 
                                                                       'Media 3M', 'Sug 1M', 'Sug 3M', 'custo1', 'Fornecedor1']]
            
            # Se tivermos pelo menos 12 colunas numéricas, podemos assumir que são meses
            if len(colunas_numericas) >= 12:
                colunas_meses = colunas_numericas[:14]  # Limitar a 14 meses como no exemplo
                
                # Criar rótulos simulados de meses (Jan-24, Fev-24, etc.)
                meses_labels = [
                    'Jan-24', 'Fev-24', 'Mar-24', 'Abr-24', 'Mai-24', 'Jun-24', 
                    'Jul-24', 'Ago-24', 'Set-24', 'Out-24', 'Nov-24', 'Dez-24', 
                    'Jan-25', 'Fev-25'
                ][:len(colunas_meses)]
                
                # Simular valores se estiverem faltando
                valores = []
                for col in colunas_meses:
                    try:
                        val = float(produto[col])
                        valores.append(val)
                    except:
                        valores.append(0)  # Valor padrão se não conseguir converter
                
                return criar_grafico_simulado(produto, valores, meses_labels)
        
        colunas_meses.sort()  # Garantir ordem cronológica
        
        # Extrair valores mensais de consumo
        valores = []
        for col in colunas_meses:
            try:
                valores.append(float(produto[col]))
            except (ValueError, TypeError):
                # Se não conseguir converter para float, usar 0
                valores.append(0)
        
        # Obter as sugestões de compra
        sug_1m = float(produto['Sug 1M']) if 'Sug 1M' in produto else 0
        sug_3m = float(produto['Sug 3M']) if 'Sug 3M' in produto else 0
        
        # Criar rótulos para os meses no formato "MMM-YY"
        meses_labels = []
        for col in colunas_meses:
            ano, mes = col.split('_')
            ano_curto = ano[2:]  # Pegar só os dois últimos dígitos do ano
            # Converter mês numérico para nome abreviado
            mes_nomes = {
                '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
                '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
                '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
            }
            mes_nome = mes_nomes.get(mes, mes)
            meses_labels.append(f"{mes_nome}-{ano_curto}")

        # Calcular a média móvel de 3 meses
        media_movel_3m = []
        for i in range(len(valores)):
            if i < 2:  # Para os dois primeiros meses, não temos 3 meses completos
                media_movel_3m.append(None)
            else:
                # Média dos 3 meses anteriores (incluindo o atual)
                media = sum(valores[i-2:i+1]) / 3
                media_movel_3m.append(media)
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Adicionar linha de consumo mensal
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=valores,
                mode='lines+markers+text',
                name='Consumo',
                line=dict(color='#0077B6', width=3),
                marker=dict(size=8, color='#0077B6'),
                text=[str(int(v)) for v in valores],
                textposition='top center',
                textfont=dict(size=10)
            )
        )

        # Adicionar linha de média móvel de 3 meses
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=media_movel_3m,
                mode='lines',
                name='Média Móvel 3M',
                line=dict(color='#FF8C00', width=2, dash='dash'),
                hoverinfo='text',
                hovertext=[f'Média 3M: {round(m, 1)}' if m is not None else '' for m in media_movel_3m]
            )
        )
        
        # Adicionar barras para Sugestão 1M e 3M
        x_all = meses_labels + ['Sugestão\n1M', 'Sugestão\n3M']
        
        # Adicionar barra para Sugestão 1M
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n1M'],
                y=[sug_1m],
                name='Sugestão 1M',
                marker_color='#0077B6',
                text=[str(int(sug_1m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Adicionar barra para Sugestão 3M 
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n3M'],
                y=[sug_3m],
                name='Sugestão 3M',
                marker_color='#0077B6',
                text=[str(int(sug_3m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Configurar layout
        fig.update_layout(
            title=f"Consumo Mensal - {produto['desc_produto']}",
            title_font=dict(size=16, family="Montserrat", color='#001514'),
            xaxis=dict(
                title="",
                tickmode='array',
                tickvals=x_all,
                ticktext=x_all,
                tickangle=-45,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title="Quantidade",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=80),
            height=500
        )
        
        # Adicionar linha horizontal no zero
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=len(x_all) - 1,
            y1=0,
            line=dict(color="black", width=1)
        )
        
        return fig
    
    except Exception as e:
        print(f"Erro ao gerar gráfico para o produto {cd_produto}: {str(e)}")
        # Retornar um gráfico de erro
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao gerar gráfico: {str(e)}",
            showarrow=False,
            font=dict(size=12, color="red")
        )
        return fig

# =============================================================================
# Callback para renderizar o conteúdo conforme a URL
# =============================================================================
@application.callback(
    Output("page-content-dashboard", "children"),
    Output("loading-output-overlay", "children"),
    Input("url", "pathname"),
    Input("selected-data", "data"),
    prevent_initial_call=True
)
def render_page_content(pathname, data):       
    # Verificar se temos dados carregados e válidos
    if data is None:
        # Verificar se temos cliente e tipo de dados no store
        return html.Div([
            html.Div(className="text-center", style={"marginTop": "20%"},
                children=[
                    html.H4("Carregando dados...", className="mb-3"),
                    html.P("Aguarde enquanto os dados são preparados."),
                    html.Div(className="loading-spinner")
                ]
            )
        ], style=content_style), None
    
    # Verificar se os dados contêm a chave de identificação
    if 'client_info' not in data:
        return html.Div([
            html.Div(className="text-center", style={"marginTop": "20%"},
                children=[
                    html.H4("Dados incompletos", className="mb-3"),
                    html.P("Os dados carregados não contêm as informações necessárias."),
                    html.P("Tente selecionar novamente o cliente e o tipo de dados.")
                ]
            )
        ], style=content_style), None
    
    # Log para depuração
    print(f"Renderizando {pathname} com dados do cliente {data['client_info']}")
    
    # Se chegamos aqui, os dados estão disponíveis
    # Pequeno delay para melhor experiência do usuário
    time.sleep(0.2)
    
    # Renderizar a página apropriada com base no pathname
    if pathname == "/" or pathname == "/rfma":
        return get_rfma_layout(data), None
    elif pathname == "/segmentacao":
        return get_segmentacao_layout(data), None
    elif pathname == "/recorrencia/mensal":
        return get_recorrencia_mensal_layout(data), None
    elif pathname == "/recorrencia/trimestral":
        return get_recorrencia_trimestral_layout(data), None
    elif pathname == "/recorrencia/anual":
        return get_recorrencia_anual_layout(data), None
    elif pathname == "/retencao":
        return get_retencao_layout(data), None
    elif pathname == "/predicao":
        return get_predicao_layout(data), None
    elif pathname == "/faturamento/anual": 
        return get_faturamento_anual_layout(data), None
    elif pathname == "/estoque/vendas-atipicas":
        return get_vendas_atipicas_layout(data), None
    elif pathname == "/estoque/produtos":
        return get_produtos_layout(data), None
    elif pathname == "/chat" or pathname == "/app/": 
        return get_chat_layout(data), None
    
    # 404 Page Not Found com estilização
    return html.Div(
        [
            html.Div(
                className="text-center",
                children=[
                    html.H1("404", className="display-1 text-muted"),
                    html.H2("Página não encontrada", className="mb-4"),
                    html.P("A página que você tentou acessar não existe no dashboard.", className="mb-4"),
                    dbc.Button(
                        [html.I(className="fas fa-home me-2"), "Voltar para o início"],
                        href="/",
                        color="primary",
                        style=button_style
                    )
                ]
            )
        ],
        style={**content_style, "display": "flex", "alignItems": "center", "justifyContent": "center"}
    ), None

# =============================================================================
# Callback separado para carregar dados
# =============================================================================
@application.callback(
    Output("selected-data", "data"),
    Input("selected-client", "data"),
    Input("selected-data-type", "data"),
    State("selected-data", "data"),
    State("last-data-load-time", "data"),
    prevent_initial_call=True
)
def load_data_callback(selected_client, selected_data_type, current_data, last_load_time):
    # Verificar se os inputs são válidos
    if not selected_client or not selected_data_type:
        return None
    
    # Criar uma chave de cache consistente
    cache_key = f"{selected_client}_{selected_data_type}"
    current_time = time.time()
    
    # Se já temos dados em cache para este cliente/tipo, verificar a idade
    if (current_data and 'client_info' in current_data and 
            current_data['client_info'] == cache_key and 
            last_load_time and current_time - last_load_time < 3600):  # Cache de 1 hora
        return current_data
    
    # Senão, carregue os dados
    print(f"**************** Cache vazio: Carregando dados para {selected_client} - {selected_data_type}")
    data = load_data(selected_client, selected_data_type)
    
    if data.get("error", False):
        error_data = {"client_info": cache_key, "error": True, "message": data.get("message")}
        return error_data
    
    # Crie um objeto com os dados serializados e a informação do cliente
    result = {
        "client_info": cache_key,
        "df": data["df"].to_json(date_format='iso', orient='split') if data["df"] is not None else None,
        "df_RC_Mensal": data["df_RC_Mensal"].to_json(date_format='iso', orient='split') if data["df_RC_Mensal"] is not None else None,
        "df_RC_Trimestral": data["df_RC_Trimestral"].to_json(date_format='iso', orient='split') if data["df_RC_Trimestral"] is not None else None,
        "df_RC_Anual": data["df_RC_Anual"].to_json(date_format='iso', orient='split') if data["df_RC_Anual"] is not None else None,
        "df_Previsoes": data["df_Previsoes"].to_json(date_format='iso', orient='split') if data["df_Previsoes"] is not None else None,
        "df_RT_Anual": data["df_RT_Anual"].to_json(date_format='iso', orient='split') if data["df_RT_Anual"] is not None else None,
        "df_fat_Anual": data["df_fat_Anual"].to_json(date_format='iso', orient='split') if data["df_fat_Anual"] is not None else None,
        "df_fat_Anual_Geral": data["df_fat_Anual_Geral"].to_json(date_format='iso', orient='split') if data["df_fat_Anual_Geral"] is not None else None,
        "df_fat_Mensal": data["df_fat_Mensal"].to_json(date_format='iso', orient='split') if data["df_fat_Mensal"] is not None else None,
        "df_Vendas_Atipicas": data["df_Vendas_Atipicas"].to_json(date_format='iso', orient='split') if data["df_Vendas_Atipicas"] is not None else None,
        "df_relatorio_produtos": data["df_relatorio_produtos"].to_json(date_format='iso', orient='split') if "df_relatorio_produtos" in data and data["df_relatorio_produtos"] is not None else None,
        "company_context": data["company_context"],
        "segmentos_context": data["segmentos_context"]
    }
    
    print(f"Dados carregados com sucesso para {selected_client} - {selected_data_type}")
    # Adicione seus dados ao objeto de resultado
    for key, value in data.items():
        if isinstance(value, pd.DataFrame):
            result[key] = value.to_json(date_format='iso', orient='split')
        else:
            result[key] = value
    
    return result

@application.callback(
    Output("selected-data", "data", allow_duplicate=True),
    Input("data-type-selection", "value"),
    State("selected-client", "data"),
    State("selected-data", "data"),
    prevent_initial_call=True
)
def update_data_type(selected_type, selected_client, current_data):
    if selected_type is None or selected_client is None:
        return dash.no_update
    
    # Crie a chave de cache
    cache_key = f"{selected_client}_{selected_type}"
    
    # Se já temos os dados e são do mesmo tipo, não recarregue
    if current_data and 'client_info' in current_data and current_data['client_info'] == cache_key:
        print(f"Usando cache existente para {cache_key}")
        return dash.no_update
    
    # Caso contrário, retorne None para forçar o carregamento dos dados corretos
    print(f"Cache inválido para {cache_key}. Forçando recarregamento.")
    return None
# =============================================================================
# Callbacks específicos para atualizar componentes nas páginas
# =============================================================================

@application.callback(
    Output('chat-history', 'children'),
    Output('user-input', 'value'),
    Input('submit-button', 'n_clicks'),
    State('user-input', 'value'),
    State('chat-history', 'children'),
    State('selected-data', 'data'),
    State('selected-client', 'data'),
    prevent_initial_call=True
)
def responde(n_clicks, user_input, chat_history, data, selected_client):
    if n_clicks is None or not user_input:
        return chat_history, ''

    if chat_history is None:
        chat_history = []  # Define chat_history como uma lista vazia

    # Add user message with styled container
    user_message = html.Div([
        html.Div([
            html.Strong("Você: "),
            html.Span(user_input)
        ], className="chat-message user-message")
    ], style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "1rem"})
    
    chat_history.append(user_message)
    
    # Add typing indicator while processing
    typing_indicator = html.Div([
        html.Div([
            html.Span("Pensando", style={"fontStyle": "italic"}),
            html.Span("...", id="typing-dots")
        ], className="chat-message bot-message", style={"backgroundColor": "#f0f0f0"})
    ], style={"display": "flex", "justifyContent": "flex-start", "marginBottom": "1rem"})
    
    chat_history.append(typing_indicator)

    # 1. Classificar a pergunta para extrair as categorias
    start_time = time.time()
    categorias = classificar_pergunta(user_input)
    
    # 2. Selecionar os DataFrames relevantes com base nas categorias
    dataframes = selecionar_dataframes(user_input, categorias)
    
    # 3. Importar dataframes
    if data:
        #segmentacao de clientes
        df = pd.read_json(io.StringIO(data["df"]), orient='split') if data.get("df") else None
        df_RC_Mensal = pd.read_json(io.StringIO(data["df_RC_Mensal"]), orient='split') if data.get("df_RC_Mensal") else None
        df_RC_Trimestral = pd.read_json(io.StringIO(data["df_RC_Trimestral"]), orient='split') if data.get("df_RC_Trimestral") else None
        df_RC_Anual = pd.read_json(io.StringIO(data["df_RC_Anual"]), orient='split') if data.get("df_RC_Anual") else None
        df_RT_Anual = pd.read_json(io.StringIO(data["df_RT_Anual"]), orient='split') if data.get("df_RT_Anual") else None
        df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split') if data.get("df_Previsoes") else None

        #estoque
        df_Vendas_Atipicas = pd.read_json(io.StringIO(data["df_Vendas_Atipicas"]), orient='split') if data.get("df_Vendas_Atipicas") else None
        df_relatorio_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split') if data.get("df_relatorio_produtos") else None

        #faturamento
        df_fat_Anual = pd.read_json(io.StringIO(data["df_fat_Anual"]), orient='split') if data.get("df_fat_Anual") else None
        df_fat_Anual_Geral = pd.read_json(io.StringIO(data["df_fat_Anual_Geral"]), orient='split') if data.get("df_fat_Anual_Geral") else None
        df_fat_Mensal = pd.read_json(io.StringIO(data["df_fat_Mensal"]), orient='split') if data.get("df_fat_Mensal") else None

        # Obter contexto específico do cliente
        company_context = data.get("company_context", CONTEXTO_PADRAO)
        segmentos_context = data.get("segmentos_context", SEGMENTOS_PADRAO)

        # 4. Construir o prompt com os dados disponíveis
        prompt = f"""
        Você é um assistente de análise de dados para um sistema de varejo.
        A pergunta é: "{user_input}"
        Dados disponíveis:
        - Contexto do negócio: {company_context}
        - Dataframes considerados úteis: {dataframes}
        - Categorias identificadas para a pergunta: {categorias}
        - Dataframes: {
            df, df_RC_Mensal, 
            df_RC_Trimestral, 
            df_RC_Anual, 
            df_RT_Anual, 
            df_Previsoes, 
            df_Vendas_Atipicas, 
            df_fat_Anual, 
            df_fat_Anual_Geral, 
            df_fat_Mensal, 
            df_relatorio_produtos
        }
        
        Perguntas sobre segmentos de clientes:
        - Para perguntas sobre os segmentos dos clientes, considere: {segmentos_context}
        
        Regras sobre a resposta final:
        - Responda de forma clara e objetiva com linguagem natural
        - Na resposta final, não deve haver nomes de dataframes, apenas a análise feita em cima dos dados disponíveis 
        - Considere que quem está falando com você é algum funcionário da empresa {selected_client}
        - Formate valores monetários com R$ e separadores de milhar
        - Evite respostas genéricas
        - Seja direto ao ponto e forneça números e insights específicos
        - Limite sua resposta a no máximo 4 parágrafos
        """
        
        # 4. Obter a resposta do modelo
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.4,
        )
        
        # Extrai a resposta do GPT-4
        gpt_response = response.choices[0].message.content
    else:
        # Resposta caso não existam dados disponíveis
        gpt_response = """
        Não há dados disponíveis para análise. Por favor, certifique-se de que:
        
        1. Você selecionou corretamente o cliente e tipo de dados no menu lateral
        2. Os arquivos necessários estão presentes para o cliente selecionado
        3. O sistema conseguiu carregar os dados sem erros
        
        Caso o problema persista, entre em contato com o suporte técnico.
        """
    
    # Calcular o tempo de resposta
    response_time = time.time() - start_time
    
    # Remove typing indicator and add the bot response with styled container
    chat_history = chat_history[:-1]  # Remove typing indicator
    
    bot_message = html.Div([
        html.Div([
            html.Strong("Assistente: "),
            html.Div(dcc.Markdown(gpt_response)),
            html.Div(f"Tempo de resposta: {response_time:.2f}s", 
                     style={"fontSize": "0.8rem", "color": "#888", "marginTop": "0.5rem", "textAlign": "right"})
        ], className="chat-message bot-message")
    ], style={"display": "flex", "justifyContent": "flex-start", "marginBottom": "1rem"})
    
    chat_history.append(bot_message)

    return chat_history, ''

@application.callback(
    [Output("client-list-header", "children"),
     Output("client-list", "children")],
    Input("segment-distribution", "clickData"),
    State("selected-data", "data"),
    prevent_initial_call=True
)
def update_client_list(clickData, data):
    if clickData is None:
        return "Clientes do Segmento Selecionado", html.Div([
            html.P("Selecione um segmento no gráfico acima para ver os clientes.", className="text-center text-muted my-4"),
            html.Div(className="text-center", children=[
                html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                html.P("Clique em uma barra para visualizar detalhes", className="text-muted mt-2")
            ])
        ])
    
    if data is None or data.get("df") is None:
        return "Clientes do Segmento Selecionado", "Dados não disponíveis."
    
    df = pd.read_json(io.StringIO(data["df"]), orient='split')
    
    # Extrair o segmento selecionado do clickData
    selected_segment = clickData["points"][0]["x"]
    header_text = f"Clientes do Segmento: {selected_segment}"
    
    # Filtrar o DataFrame para o segmento selecionado
    filtered_df = df[df["Segmento"] == selected_segment]
    
    if filtered_df.empty:
        return header_text, "Nenhum cliente encontrado para o segmento selecionado."
    
    # Determinar colunas de exibição
    if 'nome_fantasia' in df.columns:
        display_columns = ["id_cliente", "nome_fantasia", "Recency", "Frequency", "Monetary", "Age", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome_fantasia": "Cliente",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "Age": "Antiguidade (dias)",
            "email": "E-mail",
            "telefone": "Contato"
        }
    else:
        display_columns = ["id_cliente", "nome", "Recency", "Frequency", "Monetary", "Age", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome": "Cliente",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "Age": "Antiguidade (dias)",
            "email": "E-mail",
            "telefone": "Contato"
        }
    
    # Usar apenas colunas que existem no DataFrame
    existing_columns = [col for col in display_columns if col in filtered_df.columns]
    if not existing_columns:
        return header_text, "Estrutura de dados incompatível para exibição de detalhes."
    
    # Formatar valores monetários
    filtered_df_display = filtered_df[existing_columns].copy()
    if 'Monetary' in filtered_df_display.columns:
        filtered_df_display['Monetary'] = filtered_df_display['Monetary'].apply(lambda x: formatar_moeda(x))
    
    # Criar tabela aprimorada
    table = dash_table.DataTable(
        id='client-segment-table',  # ID único para a tabela
        columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
        data=filtered_df_display.to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "10px 15px",
            "fontFamily": "Montserrat",
            "fontSize": "14px"
        },
        style_header={
            "backgroundColor": "rgb(240,240,240)",
            "fontWeight": "bold",
            "textAlign": "center",
            "fontSize": "14px",
            "fontFamily": "Montserrat"
        },
        style_data_conditional=[
            {
                "if": {"column_id": "Monetary"},
                "fontWeight": "bold"
            },
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            },
            {
                "if": {"column_id": "id_cliente"},
                "width": "100px"
            }
        ],
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        export_format="xlsx"
    )
    
    # Adicionar resumo acima da tabela
    summary = html.Div([
        html.P([
            f"Exibindo ", 
            html.Strong(formatar_numero(len(filtered_df))), 
            f" clientes do segmento ", 
            html.Strong(selected_segment),
            f". Valor monetário médio: ",
            html.Strong(formatar_moeda(filtered_df['Monetary'].mean())),
            f". Frequência média: ",
            html.Strong(f"{filtered_df['Frequency'].mean():.1f}".replace(".", ",") + " compras")
        ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
    ])
    
    return header_text, html.Div([summary, table])

@application.callback(
    [Output("predicao-client-list-header", "children"),
     Output("predicao-client-list", "children")],
    [Input("predicao-pie", "clickData"),
     Input("predicao-bar", "clickData")],
    Input("selected-data", "data")
)
def update_predicao_client_list(clickData_pie, clickData_bar, data):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        # No clicks yet
        return "Clientes da Categoria Selecionada", html.Div([
            html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4"),
            html.Div(className="text-center", children=[
                html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                html.P("Clique em uma categoria para visualizar detalhes", className="text-muted mt-2")
            ])
        ])
    
    if data is None or data.get("df_Previsoes") is None:
        return "Clientes da Categoria Selecionada", "Dados não disponíveis."
    
    df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split')
    
    # Determine which chart was clicked
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'predicao-pie' and clickData_pie:
        selected_category = clickData_pie['points'][0]['label']
    elif trigger_id == 'predicao-bar' and clickData_bar:
        selected_category = clickData_bar['points'][0]['x']
    else:
        return "Clientes da Categoria Selecionada", html.Div([
            html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4")
        ])
    
    header_text = f"Clientes da Categoria: {selected_category}"
    filtered_df = df_Previsoes[df_Previsoes["categoria_previsao"] == selected_category]
    
    if filtered_df.empty:
        return header_text, "Nenhum cliente encontrado para a categoria selecionada."
    
    # Verifica se a coluna 'nome_fantasia' existe
    if 'nome_fantasia' in df_Previsoes.columns:
        display_columns = ["id_cliente", "nome_fantasia", "predicted_purchases_30d", "Recency", "Frequency", "Monetary", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome_fantasia": "Cliente",
            "predicted_purchases_30d": "Previsão de Compras (30d)",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "email": "E-mail",
            "telefone": "Contato"
        }
    else:
        display_columns = ["id_cliente", "nome", "predicted_purchases_30d", "Recency", "Frequency", "Monetary", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome": "Cliente",
            "predicted_purchases_30d": "Previsão de Compras (30d)",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "email": "E-mail",
            "telefone": "Contato"
        }
    
    # Usar apenas colunas que existem no DataFrame
    existing_columns = [col for col in display_columns if col in filtered_df.columns]
    if not existing_columns:
        return header_text, "Estrutura de dados incompatível para exibição de detalhes."
    
    # Format monetary values and predictions
    filtered_df_display = filtered_df[existing_columns].copy()
    if 'Monetary' in filtered_df_display.columns:
        filtered_df_display['Monetary'] = filtered_df_display['Monetary'].apply(lambda x: formatar_moeda(x))
    
    if 'predicted_purchases_30d' in filtered_df_display.columns:
        filtered_df_display['predicted_purchases_30d'] = filtered_df_display['predicted_purchases_30d'].apply(
            lambda x: f"{x:.2f}".replace(".", ",")
        )
    
    # Enhanced modern table
    table = dash_table.DataTable(
        columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
        data=filtered_df_display.to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "10px 15px",
            "fontFamily": "Montserrat",
            "fontSize": "14px"
        },
        style_header={
            "backgroundColor": "rgb(240,240,240)",
            "fontWeight": "bold",
            "textAlign": "center",
            "fontSize": "14px",
            "fontFamily": "Montserrat"
        },
        style_data_conditional=[
            {
                "if": {"column_id": "predicted_purchases_30d"},
                "fontWeight": "bold",
                "color": color['secondary']
            },
            {
                "if": {"column_id": "Monetary"},
                "fontWeight": "bold"
            },
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ],
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        export_format="xlsx"
    )
    
    # Add a summary row above the table
    avg_predicted = filtered_df['predicted_purchases_30d'].mean()
    avg_monetary = filtered_df['Monetary'].mean()
    
    summary = html.Div([
        html.P([
            f"Exibindo ", 
            html.Strong(formatar_numero(len(filtered_df))), 
            f" clientes com ", 
            html.Strong(selected_category),
            f". Previsão média: ",
            html.Strong(f"{avg_predicted:.2f}".replace(".", ",") + " compras em 30 dias"),
            f". Valor monetário médio: ",
            html.Strong(formatar_moeda(avg_monetary))
        ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
    ])
    
    # Action buttons for marketing campaigns
    action_buttons = html.Div([
        dbc.Button(
            [html.I(className="fas fa-envelope me-2"), "Preparar E-mail Marketing"],
            color="primary",
            className="me-2",
            style=button_style
        ),
        dbc.Button(
            [html.I(className="fas fa-mobile-alt me-2"), "Preparar SMS"],
            color="secondary",
            className="me-2",
            style=button_style
        ),
        dbc.Button(
            [html.I(className="fas fa-download me-2"), "Exportar Lista"],
            color="success",
            style=button_style
        )
    ], className="mb-3")
    
    return header_text, html.Div([summary, action_buttons, table])

# =============================================================================
# Execução do servidor
# =============================================================================
if __name__ == "__main__":
    # Crie os diretórios necessários
    os.makedirs("dados", exist_ok=True)
    os.makedirs("contexts", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    
    print("Iniciando servidor Dashboard...")
    server.config['DEBUG'] = False
    server.secret_key = 'maloka_ai_secret_key_2025'
    
    # Rode na porta padrão (127.0.0.1:5000)
    server.run()
