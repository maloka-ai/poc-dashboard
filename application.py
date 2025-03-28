import os
import glob
import zipfile
import base64
import dash
import dash_bootstrap_components as dbc
import dotenv
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import openai
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache
from flask_caching import Cache
from flask_session import Session
import time
from dash_bootstrap_templates import load_figure_template
from flask import Flask, redirect, session

# import dos callbacks
from callbacks.sidebar import register_sidebar_callbacks
from callbacks.clientes import register_callbacks as register_clientes_callbacks
from callbacks.estoque import register_callbacks as register_estoque_callbacks
from callbacks.interacao import register_callbacks as register_interacao_callbacks

# imports dos layouts
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

#helpers da sidebar
from utils.sidebar_utils import (
    create_sidebar, 
    get_available_clients, 
    get_available_data_types,
    collapse_states,
)

#helpers de layout
from utils import (
    color,
    gradient_colors,
    content_style,
    button_style,
    nav_link_style,
)

#helpers do chat
from utils import (
    CONTEXTO_PADRAO,
    SEGMENTOS_PADRAO,
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
dotenv.load_dotenv()
openai.api_key = os.getenv("chatKey")

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


# Loading custom figure template based on our color scheme
load_figure_template('bootstrap')

# =============================================================================
# Inicializar o application
# =============================================================================
server = Flask(__name__)
server.config.update(
    SECRET_KEY='maloka_ai_secret_key_2025',
    SESSION_TYPE='filesystem',
    SESSION_PERMANENT=False,
    SESSION_USE_SIGNER=True,
    SESSION_FILE_DIR='./flask_sessions'
)

# Inicializar extensão de sessão - ADICIONAR AQUI
sess = Session()
sess.init_app(server)

application = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap'],
    suppress_callback_exceptions=True,
    long_callback_manager=long_callback_manager,
    server=server,  # Associar ao servidor Flask
    url_base_pathname='/app/'
)

register_sidebar_callbacks(application)
register_clientes_callbacks(application)
register_estoque_callbacks(application)
register_interacao_callbacks(application)

# Configure caching for app
app_cache = Cache(server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './flask_cache_dir',
    'CACHE_DEFAULT_TIMEOUT': 900,  # 15 minutos de timeout padrão
    'CACHE_THRESHOLD': 1000,  # Número máximo de itens no cache
    'CACHE_OPTIONS': {'mode': 0o755}  # Permissões de diretório
})

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
    # Mapeamento direto para teste
    DOMINIOS_VALIDOS = {
        'bibi': 'BIBI',
        'beny': 'BENY',
        'espantalho': 'ESPANTALHO',
        'add': 'ADD',
        'teste': 'TESTE'  # Para facilitar testes
    }

     # Extrair domínio simplificado
    dominio = None
    if '@' in email:
        dominio = email.split('@')[1].split('.')[0].lower()
    
    # Verificar domínio
    if dominio in DOMINIOS_VALIDOS:
        empresa = DOMINIOS_VALIDOS[dominio]
        
        # Definir na sessão e testar
        try:
            print(f"Armazenando '{empresa}' na sessão")
            session['cliente'] = empresa
            print(f"Após armazenar: {dict(session)}")
            
            # Forçar que a sessão seja salva
            session.modified = True
            
            return dbc.Alert(f"Login bem-sucedido! Redirecionando...", color="success"), "/"
        except Exception as e:
            return dbc.Alert(f"Erro ao armazenar na sessão: {str(e)}", color="danger"), dash.no_update
    else:
        return dbc.Alert(f"Domínio não reconhecido.", color="danger"), dash.no_update
         
          
# Callback para mostrar conteúdo baseado na URL/autenticação
@application.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    prevent_initial_call=False
)
def display_page(pathname):
    # print(f"[DEBUG] display_page INICIADO - URL: {pathname} - Cliente na sessão: {'sim' if 'cliente' in session else 'não'}")
    # print(f"[DEBUG] Trigger foi: {dash.callback_context.triggered}")

    # Verificar cliente na sessão de forma simplificada
    cliente = session.get('cliente', None)
    # print(f"[DEBUG] Cliente na sessão: {cliente}")
    if cliente is None:
        # Se não estiver autenticado, exibir o layout de login
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
        print("Redirecionando para '/app/'")
        return redirect('/app/')
    except Exception as e:
        print(f"ERRO na rota '/': {str(e)}")
        return f"Erro no redirecionamento: {str(e)}"

# Rota principal da aplicação
@server.route('/app/')
def app_index():
    # Verificar se a sessão está funcionando
    print(f"Acessando rota '/app/' - Sessão antes: {dict(session)}")
    
    # Garantir que exista um valor padrão para cliente
    if 'cliente' not in session:
        # Definir um cliente padrão ou redirecioná-lo para o login explicitamente
        session['cliente'] = None
    
    print(f"Sessão após verificação: {dict(session)}")
    return application.index()

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
    # Debug
    # print(f"[DEBUG] render_page_content INICIADO - pathname: {pathname}")
    # print(f"[DEBUG] Estado dos dados: {'Possui dados' if data else 'Sem dados'}")
    
    # Verificar se temos dados carregados e válidos
    if data is None:
        # Debug
        # print(f"[DEBUG] render_page_content: dados é None, retornando tela de carregamento")
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
        #Debug
        # print(f"[DEBUG] render_page_content: dados não tem client_info, retornando tela de dados incompletos")
        return html.Div([
            html.Div(className="text-center", style={"marginTop": "20%"},
                children=[
                    html.H4("Dados incompletos", className="mb-3"),
                    html.P("Os dados carregados não contêm as informações necessárias."),
                    html.P("Tente selecionar novamente o cliente e o tipo de dados.")
                ]
            )
        ], style=content_style), None
    
    # Debug
    # print(f"[DEBUG] Renderizando {pathname} com dados do cliente {data['client_info']}")
    
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
# Execução do servidor
# =============================================================================
if __name__ == "__main__":
    
    print("Iniciando servidor Dashboard...")
    server.config['DEBUG'] = False
    server.secret_key = 'maloka_ai_secret_key_2025'

    os.makedirs('./flask_sessions', exist_ok=True)
    
    # Rode na porta padrão (127.0.0.1:5000)
    server.run()
