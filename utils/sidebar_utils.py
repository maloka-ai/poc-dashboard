# Funções compartilhadas entre application.py e callbacks/sidebar.py
import time
import os
import dash_bootstrap_components as dbc
from dash import html, dcc

collapse_states = {
    "clientes": False,
    "faturamento": False,
    "estoque": False
}

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

def get_available_clients():
    """Lista todos os clientes disponíveis na pasta de dados"""
    clients = []
    if os.path.exists("dados"):
        clients = [d for d in os.listdir("dados") if os.path.isdir(os.path.join("dados", d))]
    
    return clients

def create_sidebar(client=None, available_data_types=None, collapse_states=None, nav_link_style=None, color=None, gradient_colors=None):
    # Valores padrão
    if collapse_states is None:
        collapse_states = {
            "clientes": False,
            "faturamento": False,
            "estoque": False
        }
    
    # Valores padrão para estilos
    if nav_link_style is None:
        nav_link_style = {
            "color": "rgba(255, 255, 255, 0.7)",
            "fontSize": "0.85rem",
            "borderRadius": "5px",
            "paddingLeft": "0.8rem"
        }
    
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

    # Cores padrão se não fornecidas
    if color is None:
        color = {
            "primary": "#0077B6",
            "secondary": "#5A6C73",
            "warning": "#FBC02D"
        }
    
    if gradient_colors is None:
        gradient_colors = {
            "blue_gradient": ["#0077B6", "#00B4D8", "#90E0EF"],
            "green_gradient": ["#2E7D32", "#4CAF50", "#8BC34A"]
        }
    
    sidebar = html.Div(
        [
            # Armazenar o estado de colapso no armazenamento da sessão
            dcc.Store(
                id="collapse-states-store",
                storage_type="session",
                data=collapse_states
            ),
            # Logo do Maloka'AI
            html.Div(
                [
                    html.Img(src="assets/logo_maloka.png", style={"width": "60px", "height": "auto"}),
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
                                href="/rfma", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            # Outros links de navegação...
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
                    is_open=collapse_states.get("clientes", False),
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
                    is_open=collapse_states.get("faturamento", False),
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
                                [html.I(className="fas fa-exclamation-circle me-2"), "Reposição de Estoque"], 
                                href="/estoque/produtos",
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-exclamation-circle me-2"), "Inatividade e Giro por SKU"],
                                href="/estoque/produtos-inativos",
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            # dbc.NavLink(
                            #     [html.I(className="fas fa-exclamation-circle me-2"), "Giro de Estoque e Curva ABC"], 
                            #     href="/estoque/giro-estoque",
                            #     active="exact",
                            #     style=nav_link_style,
                            #     className="my-1"
                            # ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="estoque-collapse",
                    is_open=collapse_states.get("estoque", False),
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
        ],
        className="sidebar"
    )
    print("###### SIDEBAR GERADA ######")
    return sidebar