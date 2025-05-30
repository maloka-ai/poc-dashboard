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
from flask import Flask, redirect, session, send_from_directory
import psycopg2
from werkzeug.security import check_password_hash
import bcrypt

# Importar funções modularizadas para carregamento de dados
from data_load import (get_available_data_types, load_data)

from data_load.cache_config import setup_diskcache, clear_client_cache

# import dos callbacks
from callbacks.sidebar import register_sidebar_callbacks
from callbacks.clientes import register_callbacks as register_clientes_callbacks
from callbacks.estoque import register_callbacks as register_estoque_callbacks
from callbacks.interacao import register_callbacks as register_interacao_callbacks
from callbacks.vendas import register_callbacks as register_vendas_callbacks
from data_load.load_callbacks import register_data_callbacks

# imports dos layouts
from layouts.clientes import (get_segmentacao_layout, get_rfma_layout, get_recorrencia_mensal_layout, get_recorrencia_trimestral_layout, get_recorrencia_anual_layout, get_retencao_layout, get_predicao_layout)
from layouts.vendas import (get_faturamento_anual_layout, get_vendas_atipicas_layout)
from layouts.estoque import (get_produtos_layout, get_produtos_inativos_layout, get_giro_estoque_layout)
# from layouts.interacao import (get_chat_layout)

#helpers da sidebar
from utils.sidebar_utils import (create_sidebar, get_available_data_types)

#helpers de layout
from utils import (color, gradient_colors, content_style, button_style, login_color)

# =============================================================================
# Setup caching for improved performance
# =============================================================================
cache = setup_diskcache()
# cache, long_callback_manager = setup_diskcache()
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
    # long_callback_manager=long_callback_manager if long_callback_manager else None,
    server=server,  # Associar ao servidor Flask
    url_base_pathname='/app/'
)

register_sidebar_callbacks(application)
register_clientes_callbacks(application)
register_estoque_callbacks(application)
register_interacao_callbacks(application)
register_data_callbacks(application)
register_vendas_callbacks(application)

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
    dcc.Store(id='login-button-state', data={'color': login_color['buttonOff']}),
    html.Div(id='page-content')
])

# =============================================================================
# Login Layout
# =============================================================================

# Definir uma página de login específica com IDs corretos
login_layout = html.Div([
    html.Div([  # Container para logo e título
        html.Img(src="assets/logo_maloka.png", style={
            "width": "60px", 
            "height": "auto",
            "display": "block",
            "margin": "0 auto 10px auto"  # Centraliza a logo
        }),
        html.H5("MALOKA'AI", style={
            "textAlign": "center", 
            "marginBottom": "5px", 
            "color": login_color['title']
        }),
        html.H6("Converse com seus dados", style={
            "textAlign": "center", 
            "marginBottom": "1px",
            "fontWeight": "bold",
            "fontSize": "0.9rem",
            "fontStyle": "italic",
            "color": login_color['textHighlight'],
            "opacity": "0.8"
        }),
        html.H6("e aumente as suas vendas", style={
            "textAlign": "center", 
            "marginBottom": "10px",
            "fontWeight": "normal",
            "fontSize": "0.9rem",
            "fontStyle": "italic",
            "color": login_color['textHighlight'],
            "opacity": "0.8"
        }),
        html.Div([
            html.Label("E-mail:", style={"textAlign": "left", "display": "block", "marginBottom": "5px"}),
            dcc.Input(
                id="input-email", 
                type="email", 
                style={
                    "width": "100%", 
                    "marginBottom": "15px",
                    "display": "block",
                    "margin": "0 auto 15px auto",
                    "outline": "none",  
                    "boxShadow": "none" 
                }
            ),
            html.Label("Senha:", style={"textAlign": "left", "display": "block", "marginBottom": "5px"}),
            dcc.Input(
                id="input-senha", 
                type="password",
                style={
                    "width": "100%", 
                    "marginBottom": "25px",
                    "display": "block",
                    "margin": "0 auto 20px auto",
                    "outline": "none",  
                    "boxShadow": "none" 
                }
            ),
            html.Div([  # Container para botão (para centralização)
                dbc.Button(
                    "Entrar", 
                    id="botao-login",
                    style={
                        "width": "100%", 
                        "backgroundColor": login_color['buttonOff'],
                        "outline": "none",  # Remove o contorno de foco
                        "boxShadow": "none",    # Remove possíveis sombras de foco
                        "border": "none",       # Remove bordas completamente
                    },
                    className="mb-3"
                            ),
            ], style={"textAlign": "center"}),
            html.Div(id="output-login", style={"textAlign": "center"})  # Mensagens de erro/sucesso centralizadas
        ], style={
            "width": "250px",  # Um pouco menor para melhor proporção
            "margin": "0 auto", 
            "padding": "25px", 
            "border": "1px solid #ddd", 
            "borderRadius": "8px", 
            "backgroundColor": login_color['background'],
            "boxShadow": "0 2px 10px rgba(0,0,0,0.1)"
        })
    ], style={"width": "100%", "textAlign": "center"})  # Container externo para facilitar alinhamento
], style={
    "height": "100vh", 
    "background": login_color['background'], 
    "display": "flex", 
    "alignItems": "center", 
    "justifyContent": "center",
    "flexDirection": "column"
})
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
    
    if not email or not senha:
        return dbc.Alert("Por favor, preencha email e senha.", color="warning"), dash.no_update

    # Buscar usuário no banco de dados
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"), 
            port=os.getenv("DB_PORT", 5432),
            user=os.getenv("DB_USER", "adduser"),
            password=os.getenv("DB_PASS"),
            database="security"
        )
        cur = conn.cursor()
        cur.execute("SELECT password_hash, company, is_active FROM security.users WHERE email = %s", (email.strip().lower(),))
        result = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        return dbc.Alert(f"Erro na conexão com o banco: {str(e)}", color="danger"), dash.no_update

    if not result:
        return dbc.Alert("Usuário não encontrado.", color="danger"), dash.no_update
    
    password_hash, company, is_active = result
    if not is_active:
        return dbc.Alert("Conta inativa.", color="danger"), dash.no_update

    try:
        if not bcrypt.checkpw(senha.strip().encode('utf-8'), password_hash.encode('utf-8')):
            return dbc.Alert("Senha incorreta.", color="danger"), dash.no_update
    except Exception as e:
        return dbc.Alert(f"Erro na validação da senha: {str(e)}", color="danger"), dash.no_update

    try:
        print(f"Armazenando '{company}' na sessão")
        session['cliente'] = company
        session.modified = True
        return dbc.Alert("Login bem-sucedido! Redirecionando...", color="success"), "/"
    except Exception as e:
        return dbc.Alert(f"Erro ao armazenar na sessão: {str(e)}", color="danger"), dash.no_update
    
# =============================================================================
# Callback para atualizar o estilo do botão de login
# =============================================================================
@application.callback(
    Output("botao-login", "style"),
    [Input("input-email", "value"),
     Input("input-senha", "value")]
)
def atualizar_estilo_botao(email, senha):
    if email and senha:  # Se ambos os campos estiverem preenchidos
        return {"width": "100%", "backgroundColor": login_color['buttonOn']}
    else:  # Se algum campo estiver vazio
        return {"width": "100%", "backgroundColor": login_color['buttonOff']}

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

@server.route('/home')
def serve_home():
    return send_from_directory('landing', 'home.html')

@server.route('/lp')
def serve_lp():
    return send_from_directory('landing', 'lp.html')

# =============================================================================
# Callback para mostrar login ou dashboard
# =============================================================================

@application.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    prevent_initial_call=False
)
def display_page(pathname):
    print(f"[DEBUG] display_page INICIADO - URL: {pathname} - Cliente na sessão: {'sim' if 'cliente' in session else 'não'}")
    print(f"[DEBUG] Trigger foi: {dash.callback_context.triggered}")

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
    State("selected-client", "data"),
    State("selected-data-type", "data"),
    prevent_initial_call=True
)
def render_page_content(pathname, data, client, data_type):
    print(f"[DEBUG] render_page_content iniciado: pathname={pathname}, data={type(data)}")
    print(f"[DEBUG] data contém keys: {list(data.keys()) if data else []}")
    # Verificar se temos dados carregados e válidos
    if data is None:
        # Forçar o carregamento se estiver vazio
        print(f"[DEBUG] Dados vazios, tentando carregar dados para {client}_{data_type}")
        try:
            data_loaded = load_data(client, data_type, app_cache)
            if data_loaded and not data_loaded.get("error", False):
                data = {}  # Inicializa o dicionário para evitar erro abaixo
                # Converter DataFrames para formato JSON
                for key, df in data_loaded.items():
                    if key.startswith("df_") or key == "df":
                        if df is not None:
                            data[key] = df.to_json(date_format='iso', orient='split')
                        else:
                            data[key] = None
                    else:
                        data[key] = df
                # Adicionar informação do cliente
                data["client_info"] = f"{client}_{data_type}"
            else:
                print(f"[ERRO] Falha ao carregar dados: {data_loaded.get('message', 'Erro desconhecido')}")
        except Exception as e:
            print(f"[ERRO] Exceção ao carregar dados: {str(e)}")
            # Continuar com data=None para mostrar mensagem de carregamento
    
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
    # if pathname == "/" or pathname == "/rfma":
    #     return get_rfma_layout(data), None
    if pathname == "/segmentacao" or pathname == "/app/" or pathname == "/":
        return get_segmentacao_layout(data) , None
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
    elif pathname == "/estoque/giro-estoque":
        return get_giro_estoque_layout(data), None
    # elif pathname == "/chat" or pathname == "/app/": 
    #     return get_chat_layout(data), None
    
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
