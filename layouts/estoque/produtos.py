import io
import pandas as pd
import plotly.express as px
from dash import html, dcc
import dash_bootstrap_components as dbc

from utils import formatar_numero
from utils import create_card, create_metric_row, content_style, gradient_colors, color


def get_produtos_layout(data):
    """
    Cria o layout da página de criticidade de produtos com gráficos e tabelas interativas
    para análise completa de todos os níveis de criticidade do estoque.
    """
    if data.get("df_metricas_compra") is None:
        return html.Div([
            html.H2("Análise de Cobertura de Estoque", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de produtos para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P(            "Verifique se o arquivo metricas_de_compra.csv está presente no diretório de dados",  
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    # Carregamos os dados de produtos críticos
    df_produtos = pd.read_json(io.StringIO(data["df_metricas_compra"]), orient='split')

    # Botão de filtro críticos (Toggle) - Adicionado
    filtro_criticos = html.Div([
        dbc.Button(
            [
                html.I(className="fas fa-filter me-2"), 
                "Mostrar Produtos com Reposição Não-Local"
            ],
            id="btn-filtro-criticos",
            color="danger",
            className="mb-3",
            style={"marginTop": "-2rem", "marginBottom": "1rem"}
        ),
        dcc.Store(id="filtro-criticos-ativo", data=False),
    ], className="d-flex justify-content-end")
    
    # Contar produtos por categoria de criticidade
    contagem_criticidade = df_produtos['criticidade'].value_counts().sort_index()
    
    # Calcular métricas para a primeira linha de cards
    total_produtos = len(df_produtos)

    # Criar uma Series com o total e concatenar com a contagem_criticidade
    total_series = pd.Series([total_produtos], index=['TODOS'])
    contagem_criticidade = pd.concat([contagem_criticidade, total_series])
        
    produtos_criticos = len(df_produtos[df_produtos['criticidade'] == "CRÍTICO"])
    produtos_muito_baixos = len(df_produtos[df_produtos['criticidade'] == "MUITO BAIXO"])
    produtos_baixos = len(df_produtos[df_produtos['criticidade'] == "BAIXO"])
    produtos_adequados = len(df_produtos[df_produtos['criticidade'] == "ADEQUADO"])
    produtos_excesso = len(df_produtos[df_produtos['criticidade'] == "EXCESSO"])
    
    # Criar métricas para a primeira linha de cards - mostrando todas as categorias
    metrics = [
        {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
        {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
        {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
        {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
        {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
        {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Criar gráfico de barras para criticidade (similar ao do Jupyter)
    fig_criticidade = px.bar(
        x=contagem_criticidade.index,
        y=contagem_criticidade.values,
        color=contagem_criticidade.index,
        color_discrete_map={
            'CRÍTICO': 'darkred',
            'MUITO BAIXO': 'orange',
            'BAIXO': color['warning'],
            'ADEQUADO': gradient_colors['green_gradient'][0],
            'EXCESSO': color['secondary'],
            'TODOS': color['primary']
        },
        labels={'x': 'Nível de Criticidade', 'y': 'Quantidade de Produtos'},
        template='plotly_white'
    )

    porcentagens = contagem_criticidade.copy()
    for idx in porcentagens.index:
        if idx == 'TODOS':
            porcentagens[idx] = 100.0  # Forçar 100% para o total
        else:
            porcentagens[idx] = (contagem_criticidade[idx] / total_produtos * 100).round(1)

    # Adicionar valores nas barras
    for i, v in enumerate(contagem_criticidade.values):
        percentage = porcentagens[contagem_criticidade.index[i]]
        fig_criticidade.add_annotation(
            x=contagem_criticidade.index[i],
            y=v,
            text=f"{str(v)} ({percentage:.1f}%)".replace(".", ","),
            showarrow=False,
            yshift=10,
            font=dict(size=14, color="black", family="Montserrat", weight="bold")
        )
    
    fig_criticidade.update_layout(
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        xaxis_title="Nível de Criticidade",
        yaxis_title="Quantidade de Produtos",
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    # Filtrar produtos críticos e ordenar pelo percentual de cobertura (do menor para o maior)
    df_produtos_criticos = df_produtos.sort_values('cobertura_percentual_30d')

    if len(df_produtos[df_produtos['criticidade'] == 'CRÍTICO']) > 0:
        top_20_criticos = df_produtos[df_produtos['criticidade'] == 'CRÍTICO'].sort_values('cobertura_percentual_30d').head(20)
    else:
        top_20_criticos = df_produtos_criticos.head(20)

    # Verificar a coluna de descrição do produto
    produto_col = 'nome_produto' if 'nome_produto' in df_produtos.columns else 'Produto' if 'Produto' in df_produtos.columns else None

    if produto_col:

        top_20_criticos['produto_display'] = top_20_criticos[produto_col].apply(lambda x: (x[:30] + '...') if len(str(x)) > 30 else x)
        
        fig_top_criticos = px.bar(
            top_20_criticos,
            y='produto_display',
            x='cobertura_percentual_30d',
            orientation='h',
            color='cobertura_percentual_30d',
            color_continuous_scale=['darkred', 'orange', color['warning']],
            range_color=[0, 50],
            labels={'cobertura_percentual_30d': 'Cobertura (%)', 'produto_display': 'Produto'},
            template='plotly_white'
        )
        
        if 'id_produto' in top_20_criticos.columns:
            fig_top_criticos.update_traces(
                hovertemplate='<b>%{y}</b><br>Código: %{customdata[0]}<br>Cobertura: %{x:.1f}%',
                customdata=top_20_criticos[['id_produto']]
            )
        
        fig_top_criticos.update_layout(
            title_font=dict(size=16, family="Montserrat", color=color['primary']),
            yaxis_title="",
            xaxis_title="Percentual de Cobertura (%)",
            margin=dict(l=200, r=20, t=30, b=30),
            height=500,
            yaxis=dict(autorange="reversed"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        
        fig_top_criticos.add_shape(
            type="line",
            x0=30, y0=-0.5,
            x1=30, y1=len(top_20_criticos) - 0.5,
            line=dict(color="darkred", width=2, dash="dash"),
        )
        
        
        for i, row in enumerate(top_20_criticos.itertuples()):
            fig_top_criticos.add_annotation(
                x=row.cobertura_meses,
                y=row.produto_display,
                text=f"{row.cobertura_meses:.1f}%".replace(".", ","),
                showarrow=False,
                xshift=15,
                font=dict(size=12, color="black", family="Montserrat")
            )

    # Layout final
    layout = html.Div([
        html.H2("Análise de Cobertura de Estoque", className="dashboard-title"),

        # Armazenamento para os dados de produtos
        dcc.Store(
            id="store-produtos-data", 
            data=data["df_metricas_compra"] if data and "df_metricas_compra" in data else None
        ),
        dcc.Store(id='selected-data', data=data),

        # # Botão de filtro críticos adicionado abaixo do título
        filtro_criticos,
        
        # Linha de cartões de métricas div metrics_row
        html.Div(id="div-metrics-row", children=metrics_row, className="mb-4"),
        
        # Primeira linha: Gráfico de criticidade e gráfico de pizza
        dbc.Row([
            dbc.Col(
                create_card(
                    "Produtos por Nível de Cobertura",
                    dcc.Graph(id="produtos-criticidade-bar", figure=fig_criticidade, config={"responsive": True})
                ),
                lg=6, md=12
            ),
            dbc.Col(
                create_card(
                    "Top 20 Produtos Mais Críticos",
                    dcc.Graph(id="produtos-criticidade-top20", figure=fig_top_criticos if produto_col else {}, config={"responsive": True})
                ),
                lg=6, md=12
            ),
        ], className="mb-4"),
        
        # Segunda linha: Tabela detalhada de produtos por criticidade
        create_card(
            html.Div(id="produtos-criticidade-header", children="Produtos do Nível de Cobertura Selecionado"),
            html.Div(
                id="produtos-criticidade-list",
                children=html.Div([
                    html.P("Selecione um nível de cobertura nos gráficos acima para ver os produtos.", className="text-center text-muted my-4"),
                    html.Div(className="text-center", children=[
                        html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                        html.P("Clique em uma fatia, barra ou ponto para visualizar detalhes", className="text-muted mt-2")
                    ])
                ])
            )
        ),

        html.H2("Recomendação de Compras", className="dashboard-title"),
        # Terceira linha: detalhe de um produto específico
        create_card(
            html.Div(id="produto-consumo-header", children="Gráfico de Consumo do Produto Selecionado"),
            html.Div(
                id="produto-consumo-grafico",
                children=html.Div([
                    html.P("Selecione um produto na lista acima para visualizar o gráfico de consumo.", 
                        className="text-center text-muted my-4"),
                    html.Div(className="text-center", children=[
                        html.I(className="fas fa-chart-line fa-2x text-muted"),
                        html.P("O gráfico mostrará o histórico de consumo e sugestões de compra", 
                            className="text-muted mt-2")
                    ])
                ])
            )
        ),
        # Quarta linha: Card explicativo
        create_card(
            "Interpretação dos Níveis de Cobertura",
            html.Div([
                html.P("A análise de cobertura de estoque é baseada no percentual de cobertura, calculado como a relação entre o estoque atual e o consumo médio trimestral:"),
                html.Ul([
                    html.Li([html.Span("Crítico (0-30%): ", style={"color": "darkred", "fontWeight": "bold"}), 
                           "Necessidade urgente de reposição. Risco iminente de ruptura de estoque."]),
                    html.Li([html.Span("Muito Baixo (30-50%): ", style={"color": "red", "fontWeight": "bold"}), 
                           "Estoque baixo, reposição necessária em curto prazo."]),
                    html.Li([html.Span("Baixo (50-80%): ", style={"color": "orange", "fontWeight": "bold"}), 
                           "Estoque moderado, monitorar e planejar reposição."]),
                    html.Li([html.Span("Adequado (80-100%): ", style={"color": "green", "fontWeight": "bold"}), 
                           "Nível de estoque ideal, bem dimensionado para o consumo."]),
                    html.Li([html.Span("Excesso (>100%): ", style={"color": "blue", "fontWeight": "bold"}), 
                           "Estoque acima do necessário, possível capital imobilizado."])
                ]),
                html.P("Recomenda-se priorizar a reposição dos itens críticos e com muito baixa cobertura para evitar rupturas e garantir o atendimento ao cliente.")
            ])
        )
    ], style=content_style)
    
    return layout