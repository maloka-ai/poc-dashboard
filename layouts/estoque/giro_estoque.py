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
    
    # Gráfico 1: Distribuição de produtos por Curva ABC (Barras)
    curva_abc_counts = df_curva_cobertura['Curva ABC'].value_counts().reset_index()
    curva_abc_counts.columns = ['curva_abc', 'count']
    
    # Ordem personalizada para a Curva ABC
    curva_abc_counts = curva_abc_counts.sort_values(by='count', ascending=False)
    
    # Definir cores específicas para cada categoria da Curva ABC
    color_map = {
        'A': gradient_colors['green_gradient'][0],
        'B': gradient_colors['blue_gradient'][0],
        'C': 'orange',
        'Sem Venda': 'darkred'
    }
    
    fig_barras_abc = px.bar(
        curva_abc_counts, 
        x='curva_abc', 
        y='count',
        text='count',
        labels={'curva_abc': 'Curva ABC', 'count': 'Quantidade de Produtos'},
        color='curva_abc',
        color_discrete_map=color_map  # Usar o mapeamento de cores personalizado
    )
    
    # Configurando o texto nas barras
    fig_barras_abc.update_traces(
        texttemplate='%{text}',
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>Produtos: %{y}<extra></extra>',
        marker_line_width=1.5,
        opacity=0.8,
        marker_line_color="white",
    )
    
    fig_barras_abc.update_layout(
        legend_title='Curva ABC',
        margin=dict(t=50, b=0, l=0, r=0),
        showlegend=False,  # Remover legenda já que as cores são explicativas
        xaxis_title='',
        yaxis_title='Quantidade de Produtos',
        clickmode='event+select'  # Habilitar modo de clique para seleção
    )
    
    # Gráfico 2: Barras com quantidade e porcentagem por situação
    situacao_counts = df_curva_cobertura['Situação do Produto'].value_counts().reset_index()
    situacao_counts.columns = ['Situação do Produto', 'count']
    
    total_produtos = situacao_counts['count'].sum()
    situacao_counts['porcentagem'] = (situacao_counts['count'] / total_produtos * 100).round(1)
    
    fig_barras = go.Figure()
    
    # Adicionando barras para contagem
    fig_barras.add_trace(go.Bar(
        x=situacao_counts['Situação do Produto'],
        y=situacao_counts['porcentagem'],
        text=[f"{count} ({pct}%)" for count, pct in zip(situacao_counts['count'], situacao_counts['porcentagem'])],
        textposition='auto',
        name='Quantidade',
        marker_color=gradient_colors['blue_gradient'][0],
        marker_line_width=1.5,
        opacity=0.8,
        marker_line_color="white",
    ))
    
    # Configurando o layout com dois eixos Y
    fig_barras.update_layout(
        xaxis=dict(title='Situação'),
        yaxis=dict(
            title=dict(
                text='Quantidade',
                font=dict(color='rgb(55, 83, 109)')
            ),
            side='left'
        ),
        yaxis2=dict(
            title=dict(
                text='Porcentagem (%)',
                font=dict(color='rgb(255, 127, 14)')
            ),
            overlaying='y',
            side='right',
            range=[0, 100]
        ),
        legend=dict(x=0.01, y=0.99),
        barmode='group',
        margin=dict(t=50, b=50, l=50, r=50),
        clickmode='event+select'  # Habilitar modo de clique para seleção
    )

    #layout final com os gráficos
    layout = html.Div([
        html.H2("Análise de Situação do Estoque", className="dashboard-title"),
        dcc.Store(id='selected-data', data=data),
        # Linha de métricas
        metrics_row,
        
        # Primeira linha - Gráfico de barras da Curva ABC e sua tabela
        html.Div([
            html.Div([
                create_card(
                    "Distribuição de Produtos por Curva ABC (Clique para filtrar)",
                    dcc.Graph(figure=fig_barras_abc, id='grafico-curva-abc-barras', clear_on_unhover=True)
                )
            ], className="col-md-12"),
        ], className="row mb-4"),
            
        # Tabela filtrada por Curva ABC
        html.Div([
            html.Div([
                create_card(
                    "Produtos filtrados por Curva ABC",
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-mouse-pointer fa-3x text-muted d-block text-center mb-3"),
                            html.H4("Clique em uma barra no gráfico acima", className="text-center mb-2"),
                            html.P("Para visualizar os produtos por Curva ABC, selecione uma barra no gráfico acima.",
                                className="text-center text-muted")
                        ], id="tabela-curva-abc-container")
                    ])
                )
            ], className="col-md-12"),
        ], className="row mb-4"),

        # Segunda linha - Gráfico de barras da Situação do Produto e sua tabela
        html.Div([
            html.Div([
                create_card(
                    "Quantidade e Porcentagem por Situação do Produto (Clique para filtrar)",
                    dcc.Graph(figure=fig_barras, id='grafico-situacao-barras', clear_on_unhover=True)
                )
            ], className="col-md-12"),
        ], className="row mb-4"),

        # Tabela filtrada por Situação
        html.Div([
            html.Div([
                create_card(
                    "Produtos filtrados por Situação",
                    html.Div([
                        html.Div([
                            html.I(className="fas fa-mouse-pointer fa-3x text-muted d-block text-center mb-3"),
                            html.H4("Clique em uma barra no gráfico acima", className="text-center mb-2"),
                            html.P("Para visualizar os produtos por Situação, selecione uma barra no gráfico acima.",
                                className="text-center text-muted")
                        ], id="tabela-situacao-container")
                    ])
                )
            ], className="col-md-12"),
        ], className="row mb-4"),

    ], style=content_style)

    return layout