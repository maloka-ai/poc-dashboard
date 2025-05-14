import io
import pandas as pd
import datetime
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dash import html, dcc, dash_table, callback, Input, Output, State
from dash.exceptions import PreventUpdate

from utils import create_card, content_style

def get_produtos_inativos_layout(data):
    """
    Cria o layout da página de produtos inativos com gráficos e tabelas interativas
    para análise de produtos que não são vendidos há um determinado período.
    """
    if data.get("df_relatorio_produtos") is None:
        return html.Div([
            html.H2("Análise de Produtos Inativos", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de produtos para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo relatorio_produtos.xlsx está presente no diretório de dados",  
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    else:
        # Carregar os dados do DataFrame
        df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')
    
    if data.get["df_analise_curva_cobertura"] is None:
        print("Verifique se o arquivo relatorio_produtos.xlsx está presente no diretório de dados")
    else:
        # Carregar os dados do DataFrame
        df_analise_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')

    # Garantir que a coluna 'recencia' esteja no formato de data
    if 'recencia' in df_produtos.columns and df_produtos['recencia'].dtype == 'object':
        # Tratamento para valores problemáticos como "0" ou vazios
        df_produtos['recencia'] = pd.to_datetime(df_produtos['recencia'], errors='coerce')
        
        # Definir uma data padrão para valores que não puderam ser convertidos (NULL/NaT)
        # Usando a data atual para calcular corretamente os dias de inatividade
        data_atual = datetime.datetime.now()
        df_produtos['recencia'].fillna(data_atual, inplace=True)
    
    df_produtos['antiguidade'] = pd.to_datetime(df_produtos['antiguidade'], errors='coerce')
    
    # Calcular os dias de inatividade
    data_atual = datetime.datetime.now()
    df_produtos['dias_inativo'] = df_produtos['dias_desde_ultima_venda']
    
    # ID único para os componentes
    dias_slider_id = 'dias-inatividade-slider'
    produtos_table_id = 'table-produtos-inativos'
    tempo_inativo_id = 'tempo-inatividade-display'
    contagem_produtos_id = 'contagem-produtos-inativos'
    produto_analise_id = 'produto-analise-detalhada'
    
    # Criamos um layout com um slider para definir o tempo de inatividade
    layout = html.Div([
        html.H2("Análise de Produtos Inativos", className="dashboard-title"),
        
        # Cartão com slider para definir os dias de inatividade
        create_card(
            "Filtro de Tempo de Inatividade",
            html.Div([
                html.P("Selecione o período mínimo de inatividade para filtrar os produtos:", className="mb-2"),
                html.Div([
                    dcc.Slider(
                        id=dias_slider_id,
                        min=0,
                        max=365,
                        step=7,
                        marks={
                            0: '0d',
                            7: '7d',
                            30: '1m',
                            60: '2m',
                            90: '3m',
                            120: '4m',
                            150: '5m',
                            180: '6m',
                            210: '7m',
                            240: '8m',
                            270: '9m',
                            300: '10m',
                            330: '11m',
                            365: '12m'
                        },
                        value=0,
                        className="mb-3"
                    ),
                    html.Div([
                        html.H4(id=tempo_inativo_id, className="text-center font-weight-bold"),
                        html.Div(id=contagem_produtos_id, className="text-center text-muted")
                    ], className="mt-3")
                ])
            ])
        ),
        
        # Cartão com tabela detalhada
        create_card(
            "Lista de Produtos Inativos",
            html.Div([
                html.P("Esta tabela apresenta todos os produtos que não foram vendidos pelo período selecionado acima. Clique em um produto para ver análise detalhada.", 
                       className="text-muted mb-3"),
                html.Div(id=produtos_table_id)
            ])
        ),
        
        # Cartão para análise detalhada do produto
        create_card(
            "Análise Detalhada do Produto",
            html.Div([
                html.Div(id="produto-selecionado-info", className="mb-3"),
                html.Div(id=produto_analise_id)
            ])
        ),
        
        # Cartão explicativo
        create_card(
            "Interpretação dos Dados",
            html.Div([
                html.P("Os produtos inativos representam itens que não tiveram movimento de venda por um período significativo, o que pode indicar:"),
                html.Ul([
                    html.Li("Produtos com potencial obsolescência que podem ser descontinuados"),
                    html.Li("Oportunidades para campanhas promocionais para escoamento de estoque"),
                    html.Li("Tendências de mercado que estão mudando o perfil de consumo"),
                    html.Li("Possíveis problemas de cadastro ou visibilidade do produto no catálogo")
                ]),
                html.P("Recomendamos a revisão periódica destes itens para tomada de decisões estratégicas sobre o portfólio.")
            ])
        ),
        
        # Armazenamento dos dados para compartilhar entre callbacks
        dcc.Store(id='produto-selecionado-store'),
        
        # Callback para atualizar os componentes com base no slider
        dcc.Loading(
            id="loading-produtos-inativos",
            type="circle",
            children=[
                html.Div(id="hidden-div-produtos-inativos")
            ]
        )
    ], style=content_style)
    
    return layout
