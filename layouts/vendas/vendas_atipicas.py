import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, dash_table

from utils import formatar_numero
from utils import create_card, create_metric_row, content_style, color, gradient_colors

def get_vendas_atipicas_layout(data):
    """
    Cria o layout da página de vendas atípicas com gráficos e tabelas interativas
    para análise de comportamentos fora do padrão no estoque.
    """
    if data.get("df_Vendas_Atipicas") is None:
        return html.Div([
            html.H2("Vendas Atípicas", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de vendas atípicas para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo vendas_atipicas_atual.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    # Carregamos os dados de vendas atípicas
    df_atipicas = pd.read_json(io.StringIO(data["df_Vendas_Atipicas"]), orient='split')
    
    # Convertemos a coluna 'data' para o formato de data, se ainda não estiver
    if df_atipicas['data'].dtype == 'object':
        df_atipicas['data'] = pd.to_datetime(df_atipicas['data'])

    df_atipicas['Dia_formatada'] = df_atipicas['data'].dt.strftime('%d/%m/%Y')
    
    # Calculamos métricas gerais para cards de resumo
    total_produtos_atipicos = len(df_atipicas)
    total_quantidade_atipica = df_atipicas['quantidade_atipica'].sum()
    media_por_produto = total_quantidade_atipica / total_produtos_atipicos if total_produtos_atipicos > 0 else 0
    
    # Criamos as métricas para a primeira linha de cards
    metrics = [
        {"title": "Total de Produtos Atípicos", "value": formatar_numero(total_produtos_atipicos), "color": color['primary']},
        {"title": "Quantidade Total Atípica", "value": formatar_numero(total_quantidade_atipica), "color": color['accent']},
        {"title": "Média por Produto", "value": formatar_numero(media_por_produto, 1), "color": color['secondary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Criamos um gráfico de barras para os produtos com maior quantidade atípica
    top_produtos = df_atipicas.sort_values('quantidade_atipica', ascending=False).head(10)
    
    fig_top_produtos = px.bar(
        top_produtos,
        y='produto',
        x='quantidade_atipica',
        orientation='h',
        color='quantidade_atipica',
        color_continuous_scale='Blues',
        labels={'quantidade_atipica': 'Quantidade Atípica', 'produto': 'Produto'},
        template='plotly_white'
    )
    
    fig_top_produtos.update_layout(
        title="Top 10 Produtos com Vendas Atípicas",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        xaxis_title="Quantidade",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),  # Para mostrar o maior valor no topo
        height=500,
        margin=dict(l=200, r=20, t=70, b=70),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Criamos uma tabela interativa com os dados completos
    table = dash_table.DataTable(
        id='table-vendas-atipicas',
        columns=[
            {"name": "Data", "id": "Dia_formatada"},
            {"name": "Quantidade Atípica", "id": "quantidade_atipica"},
            {"name": "Média de Vendas Útimos 12m", "id": "media_vendas"},
            {"name": "Cliente", "id": "cliente"},
            {"name": "Produto", "id": "produto"},
            {"name": "Estoque Atual", "id": "estoque_atualizado"},
            {"name": "ID Venda", "id": "id_venda"},
            {"name": "ID Produto", "id": "id_produto"},
        ],
        data=df_atipicas.reset_index().to_dict("records"),
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        page_size=10,
        export_format="xlsx",
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
                "if": {"column_id": "quantidade_atipica"},
                "fontWeight": "bold",
                "color": color['accent']
            },
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ]
    )
    
    # Incluímos todos os elementos no layout
    layout = html.Div([
        html.H2("Análise de Vendas Atípicas", className="dashboard-title"),
        
        # Linha de cartões de métricas
        metrics_row,
        
        # Primeira linha de gráficos
        create_card(
            "Top Produtos com Vendas Atípicas",
            dcc.Graph(id="grafico-top-produtos", figure=fig_top_produtos, config={"responsive": True})
        ), 
        
        # Terceira linha - Tabela de dados
        create_card(
            "Detalhamento de Vendas Atípicas",
            html.Div([
                html.P("Esta tabela apresenta todos os produtos com vendas fora do padrão esperado. Utilize os filtros e ordenação para análise detalhada.", className="text-muted mb-3"),
                table
            ])
        ),
        
        # Quarta linha - Cartão explicativo
        create_card(
            "Interpretação dos Dados",
            html.Div([
                html.P("As vendas atípicas representam situações onde o volume de vendas foi significativamente diferente do padrão esperado para aquele produto, podendo indicar:"),
                html.Ul([
                    html.Li("Oportunidades de expansão para produtos com vendas acima do esperado"),
                    html.Li("Clientes com potencial para aumento de volume"),
                    html.Li("Produtos que podem precisar de ajuste no estoque ou previsão"),
                    html.Li("Possíveis problemas de registro ou cadastro quando extremamente fora do padrão")
                ]),
                html.P("Recomendamos a análise detalhada dos casos mais significativos para definir estratégias de negócio.")
            ])
        )
    ], style=content_style)
    
    return layout