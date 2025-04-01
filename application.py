import os
import dash
import dash_bootstrap_components as dbc
import dotenv
from dash import dcc, html
from dash.dependencies import Input, Output, State
import openai
from flask_caching import Cache
from flask_session import Session
import time
from dash_bootstrap_templates import load_figure_template
from flask import Flask, redirect, session

# Importar funções modularizadas para carregamento de dados
from data_load import (get_available_data_types)

from data_load.cache_config import setup_diskcache, clear_client_cache

# import dos callbacks
from callbacks.sidebar import register_sidebar_callbacks
from callbacks.clientes import register_callbacks as register_clientes_callbacks
from callbacks.estoque import register_callbacks as register_estoque_callbacks
from callbacks.interacao import register_callbacks as register_interacao_callbacks
from data_load.load_callbacks import register_data_callbacks

# imports dos layouts
from layouts.clientes import (get_segmentacao_layout, get_rfma_layout, get_recorrencia_mensal_layout, get_recorrencia_trimestral_layout, get_recorrencia_anual_layout, get_retencao_layout, get_predicao_layout)
from layouts.vendas import (get_faturamento_anual_layout, get_vendas_atipicas_layout)
from layouts.estoque import (get_produtos_layout, get_produtos_inativos_layout)
from layouts.interacao import (get_chat_layout)

#helpers da sidebar
from utils.sidebar_utils import (create_sidebar, get_available_data_types)

#helpers de layout
from utils import (color, gradient_colors, content_style, button_style)

# =============================================================================
# Setup caching for improved performance
# =============================================================================
cache, long_callback_manager = setup_diskcache()
dotenv.load_dotenv()
openai.api_key = os.getenv("chatKey")

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

# Inicializar extensão de sessão Flask
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
register_data_callbacks(application)

# Configure caching for app
app_cache = Cache(server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './flask_cache_dir',
    'CACHE_DEFAULT_TIMEOUT': 900,  # 15 minutos de timeout padrão
    'CACHE_THRESHOLD': 1000,  # Número máximo de itens no cache
    'CACHE_OPTIONS': {'mode': 0o755}  # Permissões de diretório
})

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
# Layout principal (layout condicional baseado na autenticação)
# =============================================================================
application.layout = html.Div([
    dcc.Location(id='url', refresh=True),  # refresh=True para permitir recarregar após login
    dcc.Store(id='sidebar-initialized', storage_type='session', data=False),  # Novo: estado para controlar inicialização da sidebar
    html.Div(id='page-content')
])

# =============================================================================
# Login Layout
# =============================================================================

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

# =============================================================================
# Callback para validar login
# =============================================================================

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
         
          
# =============================================================================
# Rotas do Flask
# =============================================================================

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
            clear_client_cache(cache, app_cache, cliente_atual)
            
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

# =============================================================================
# Callback para mostrar login ou dashboard
# =============================================================================

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
    elif pathname == "/estoque/produtos-inativos":
        return get_produtos_inativos_layout(data), None
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
# Execução do servidor
# =============================================================================
if __name__ == "__main__":
    
    print("Iniciando servidor Dashboard...")
    server.config['DEBUG'] = False
    server.secret_key = 'maloka_ai_secret_key_2025'

    os.makedirs('./flask_sessions', exist_ok=True)
    
    # Rode na porta padrão (127.0.0.1:5000)
    server.run()
