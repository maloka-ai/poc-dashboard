from dash import html
import dash_bootstrap_components as dbc

from utils import create_card, content_style

def get_chat_layout(data):
    # Modern chat interface styled like ChatGPT
    chat_layout = html.Div(
        [
            html.H2("Assistente de Análises", className="dashboard-title"),
            
            # Introduction card
            create_card(
                "Como posso ajudar?",
                html.Div([
                    html.P("O assistente de análises pode responder perguntas sobre seus dados de clientes. Por exemplo:"),
                    html.Ul([
                        html.Li("Quais são os segmentos com maior valor monetário?"),
                        html.Li("Como está a retenção anual dos clientes?"),
                        html.Li("Quais clientes têm maior probabilidade de compra nos próximos 30 dias?"),
                        html.Li("Qual foi a evolução das vendas desde 2021?")
                    ]),
                    html.P("Faça sua pergunta abaixo e ajudarei com insights e análises!")
                ])
            ),
            
            # Chat container
            html.Div([
                # Chat history
                html.Div(
                    id='chat-history',
                    className="chat-history",
                    children=[],
                ),
                
                # Input area
                html.Div([
                    dbc.Input(
                        id='user-input',
                        placeholder="Digite sua pergunta sobre os dados...",
                        type="text",
                        className="chat-input",
                    ),
                    dbc.Button(
                        "↑",  # Caractere Unicode de seta para cima
                        id='submit-button',
                        color="warning",
                        className="ms-2",
                        style={
                            "borderRadius": "50%", 
                            "width": "40px", 
                            "height": "40px", 
                            "padding": "0",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "backgroundColor": "#FF8C00",  # Cor laranja personalizada
                            "fontSize": "30px",  # Aumentar o tamanho do ícone
                            "fontWeight": "normal",  # Manter o peso da fonte normal
                        }
                    )
                ], className="chat-input-container")
            ], className="chat-container")
        ],
        style=content_style
    )
    
    return chat_layout