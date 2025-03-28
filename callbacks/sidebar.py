import dash
from dash import Input, Output, State, html, callback_context
from flask import session

from utils.sidebar_utils import create_sidebar, get_available_data_types, collapse_states


def register_sidebar_callbacks(app):
    """
    Registra todos os callbacks relacionados à sidebar.
    
    Args:
        app: A instância do aplicativo Dash
    """
    
    @app.callback(
        Output("sidebar-container", "children"),
        Output("selected-client", "data"),
        Output("sidebar-initialized", "data"),
        [Input("url", "search"),
         Input("sidebar-initialized", "data")],
        prevent_initial_call=False
    )
    def initialize_sidebar(search, is_initialized):
        ctx = callback_context
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
    
    @app.callback(
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
    
    @app.callback(
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
    
    @app.callback(
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
    
    @app.callback(
        Output("titulo-app", "children"),
        [Input("selected-client", "data"),
         Input("selected-data-type", "data")]
    )
    def update_sidebar_title(selected_client):
        if selected_client is None:
            return "Client"
        return f"{selected_client}"