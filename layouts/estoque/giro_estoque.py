import io
import pandas as pd
from dash import html, dcc
import plotly.express as px
import plotly.graph_objects as go

from utils import create_card, content_style, create_metric_row, color, gradient_colors

def get_giro_estoque_layout(data):
    """
    Cria o layout da página de produtos inativos com gráficos e tabelas interativas
    para análise de produtos que não são vendidos há um determinado período.
    """
    if data.get("df_analise_curva_cobertura") is None:
        return html.Div([
            html.H2("Análise de Produtos Inativos", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de produtos para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo analise_curva_cobertura.xlsx está presente no diretório de dados",  
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    # Carregar os dados do DataFrame
    df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
    
    # Definir o período de análise
    periodo_analise = "90 dias"
    
    # Calcular métricas para as curvas ABC
    total_produtos = len(df_curva_cobertura)
    produtos_curva_a = len(df_curva_cobertura[df_curva_cobertura['Curva ABC'] == 'A'])
    produtos_curva_b = len(df_curva_cobertura[df_curva_cobertura['Curva ABC'] == 'B'])
    produtos_curva_c = len(df_curva_cobertura[df_curva_cobertura['Curva ABC'] == 'C'])
    produtos_sem_venda = len(df_curva_cobertura[df_curva_cobertura['Curva ABC'] == 'Sem Venda'])
    
    # Função para formatar números com separador de milhar
    def formatar_numero(numero):
        return f"{numero:,}".replace(",", ".")
    
    # Criar métricas
    metrics = [
        {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": gradient_colors['blue_gradient'][0]},
        {"title": "Curva A (90 dias)", "value": formatar_numero(produtos_curva_a), "color": 'darkred'},
        {"title": "Curva B (90 dias)", "value": formatar_numero(produtos_curva_b), "color": 'orange'},
        {"title": "Curva C (90 dias)", "value": formatar_numero(produtos_curva_c), "color": gradient_colors['green_gradient'][0]},
        {"title": "Sem Venda (90 dias)", "value": formatar_numero(produtos_sem_venda), "color": color['warning']},
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Gráfico 1: Distribuição de produtos por Curva ABC (Pizza)
    curva_abc_counts = df_curva_cobertura['Curva ABC'].value_counts().reset_index()
    curva_abc_counts.columns = ['curva_abc', 'count']
    
    fig_pie = px.pie(
        curva_abc_counts, 
        values='count', 
        names='curva_abc',
        color_discrete_sequence=px.colors.sequential.Viridis,
        hover_data=['count']
    )
    
    fig_pie.update_traces(
        textposition='outside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Produtos: %{value}<br>Porcentagem: %{percent}'
    )
    
    fig_pie.update_layout(
        legend_title='Curva ABC',
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    # Gráfico 2: Barras com quantidade e porcentagem por situação
    situacao_counts = df_curva_cobertura['situacao'].value_counts().reset_index()
    situacao_counts.columns = ['situacao', 'count']
    
    total_produtos = situacao_counts['count'].sum()
    situacao_counts['porcentagem'] = (situacao_counts['count'] / total_produtos * 100).round(1)
    
    fig_barras = go.Figure()
    
    # Adicionando barras para contagem
    fig_barras.add_trace(go.Bar(
        x=situacao_counts['situacao'],
        y=situacao_counts['count'],
        text=situacao_counts['count'],
        textposition='auto',
        name='Quantidade',
        marker_color='rgb(55, 83, 109)'
    ))
    
    # Adicionando linha para porcentagem
    fig_barras.add_trace(go.Scatter(
        x=situacao_counts['situacao'],
        y=situacao_counts['porcentagem'],
        text=[f'{p}%' for p in situacao_counts['porcentagem']],
        mode='lines+markers+text',
        textposition='top center',
        name='Porcentagem',
        yaxis='y2',
        marker=dict(size=10, color='rgb(255, 127, 14)'),
        line=dict(width=3, color='rgb(255, 127, 14)')
    ))

    fig_barras.update_traces(
        marker_line_width=1.5,
        opacity=0.8,
        marker_line_color="white",
        selector=dict(type="bar")
    )
    
    # Configurando o layout com dois eixos Y
    fig_barras.update_layout(
        title_text='Quantidade e Porcentagem por Situação do Produto',
        xaxis=dict(title='Situação'),
        yaxis=dict(
            title='Quantidade',
            titlefont=dict(color='rgb(55, 83, 109)'),
            tickfont=dict(color='rgb(55, 83, 109)'),
            side='left'
        ),
        yaxis2=dict(
            title='Porcentagem (%)',
            titlefont=dict(color='rgb(255, 127, 14)'),
            tickfont=dict(color='rgb(255, 127, 14)'),
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        legend=dict(x=0.01, y=0.99),
        barmode='group',
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    # Montando o layout final com os gráficos
    return html.Div([
        html.H2("Análise de Situação do Estoque", className="dashboard-title"),

        # Linha de métricas
        metrics_row,
        
        html.Div([
            create_card(
                "Distribuição de Produtos por Curva ABC",
                dcc.Graph(figure=fig_pie, id='grafico-curva-abc-pizza')
        )
            ], className="col-md-6"),
            
        html.Div([
            create_card(
                "Quantidade e Porcentagem por Situação do Produto",
                dcc.Graph(figure=fig_barras, id='grafico-situacao-barras')
            )
        ], className="col-md-6"),

        html.Div([
            html.Div(id="tabela-produtos-container", className="mt-4", style={'display': 'none'})
        ], className="row mb-4"),
    ], style=content_style)

