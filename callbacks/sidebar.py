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

    # Função auxiliar para determinar qual collapse deve estar aberta com base na URL
    def get_active_collapse(pathname):
        """
        Determina qual collapse deve estar aberta com base no pathname atual
        """
        if pathname:
            if any(x in pathname for x in ['/segmentacao', '/rfma', '/recorrencia', '/retencao', '/predicao']):
                return "clientes"
            elif any(x in pathname for x in ['/faturamento', '/estoque/vendas-atipicas']):
                return "faturamento"
            elif any(x in pathname for x in ['/estoque/produtos']):
                return "estoque"
        return None
    
    @app.callback(
        Output("sidebar-container", "children"),
        Output("selected-client", "data"),
        Output("sidebar-initialized", "data"),
        Output("collapse-states-store", "data"),
        [Input("url", "pathname"),  # Mudar para pathname em vez de search
        Input("url", "search"),
        Input("collapse-states-store", "data")],
        [State("sidebar-initialized", "data")],
        prevent_initial_call=False
    )
    def initialize_sidebar(pathname, search, stored_collapse_states, is_initialized):
        ctx = callback_context
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        # Verificar qual collapse deve estar aberta com base na URL atual
        active_collapse = get_active_collapse(pathname)
        
        # Se a alteração foi apenas da rota (pathname) e não de parâmetros (search), 
        # é necessário atualizar os estados das collapses com base na URL
        if trigger_id == 'url' and pathname and is_initialized:
            # Atualizar as collapses com base na URL, mas não recriar a sidebar
            if stored_collapse_states and active_collapse:
                updated_states = stored_collapse_states.copy()
                # Manter a collapse ativa aberta
                updated_states[active_collapse] = True
                return dash.no_update, dash.no_update, True, updated_states
            return dash.no_update, dash.no_update, True, stored_collapse_states
        
        # Se a sidebar já foi inicializada e o trigger não é a URL após login, não recria a sidebar
        if is_initialized and (trigger_id != 'url' or ('cliente=' not in search if search else True)):
            # Ainda atualizar estados da collapse se necessário
            if stored_collapse_states and active_collapse:
                updated_states = stored_collapse_states.copy()
                updated_states[active_collapse] = True
                return dash.no_update, dash.no_update, True, updated_states
            return dash.no_update, dash.no_update, True, stored_collapse_states
        
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
                return html.Div("Redirecionando para login..."), None, False, dash.no_update
        
        # Obter tipos de dados disponíveis para o cliente
        available_data_types = get_available_data_types(cliente)
        
        # Usar os estados salvos no armazenamento se disponíveis, ou criar novos
        actual_collapse_states = stored_collapse_states if stored_collapse_states else collapse_states.copy()
        
        # Se tivermos uma URL ativa, garantir que a collapse correspondente esteja aberta
        if active_collapse and actual_collapse_states:
            actual_collapse_states[active_collapse] = True
        
        # Criar sidebar com o cliente específico e estados de collapse atuais
        sidebar = create_sidebar(cliente, available_data_types, actual_collapse_states)
        print("Sidebar gerada para", cliente, "com estados:", actual_collapse_states)
        
        return sidebar, cliente, True, actual_collapse_states
    
    @app.callback(
        Output("clientes-collapse", "is_open"),
        Output("collapse-states-store", "data", allow_duplicate=True),
        [Input("clientes-collapse-button", "n_clicks")],
        [State("clientes-collapse", "is_open"), 
        State("collapse-states-store", "data")],
        prevent_initial_call=True 
    )
    def toggle_clientes_collapse(n, is_open, stored_states):
        # Garantir que temos um dicionário válido
        if stored_states is None:
            stored_states = collapse_states.copy()
        else:
            stored_states = stored_states.copy()  # Criar uma cópia para modificar
        
        # Alternar o estado
        new_state = not is_open
        stored_states["clientes"] = new_state
        
        print(f"Toggle clientes: {new_state}, Estados: {stored_states}")
        return new_state, stored_states
    
    @app.callback(
        Output("faturamento-collapse", "is_open"),
        Output("collapse-states-store", "data", allow_duplicate=True),
        [Input("faturamento-collapse-button", "n_clicks")],
        [State("faturamento-collapse", "is_open"),
         State("collapse-states-store", "data")],
        prevent_initial_call=True 
    )
    def toggle_faturamento_collapse(n, is_open, stored_states):
        # Garantir que temos um dicionário válido
        if stored_states is None:
            stored_states = collapse_states.copy()
        else:
            stored_states = stored_states.copy()  # Criar uma cópia para modificar
        
        # Alternar o estado
        new_state = not is_open
        stored_states["faturamento"] = new_state
        
        print(f"Toggle faturamento: {new_state}, Estados: {stored_states}")
        return new_state, stored_states
    
    @app.callback(
        Output("estoque-collapse", "is_open"),
        Output("collapse-states-store", "data", allow_duplicate=True),
        [Input("estoque-collapse-button", "n_clicks")],
        [State("estoque-collapse", "is_open"),
         State("collapse-states-store", "data")],
        prevent_initial_call=True 
    )
    def toggle_estoque_collapse(n, is_open, stored_states):
        # Garantir que temos um dicionário válido
        if stored_states is None:
            stored_states = collapse_states.copy()
        else:
            stored_states = stored_states.copy()  # Criar uma cópia para modificar
        
        # Alternar o estado
        new_state = not is_open
        stored_states["estoque"] = new_state
        
        print(f"Toggle estoque: {new_state}, Estados: {stored_states}")
        return new_state, stored_states
    
    @app.callback(
        Output("titulo-app", "children"),
        [Input("selected-client", "data")]
    )
    def update_sidebar_title(selected_client):
        if selected_client is None:
            return "Client"
        return f"{selected_client}"
    
    #Callback para manter os estados das collapses quando a página for atualizada
    @app.callback(
        Output("clientes-collapse", "is_open", allow_duplicate=True),
        Output("faturamento-collapse", "is_open", allow_duplicate=True),
        Output("estoque-collapse", "is_open", allow_duplicate=True),
        Input("url", "pathname"),
        State("collapse-states-store", "data"),
        prevent_initial_call='initial_duplicate'
    )
    def sync_collapse_states(pathname, stored_states):
        """Mantém os estados das collapses sincronizados ao navegar entre páginas"""
        if stored_states is None:
            return collapse_states["clientes"], collapse_states["faturamento"], collapse_states["estoque"]
        
        # Verificar qual collapse deve estar aberta com base na URL
        active_collapse = get_active_collapse(pathname)
        if active_collapse:
            updated_states = stored_states.copy()
            updated_states[active_collapse] = True
            return updated_states["clientes"], updated_states["faturamento"], updated_states["estoque"]
        
        return stored_states["clientes"], stored_states["faturamento"], stored_states["estoque"]