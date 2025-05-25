import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime

from utils.formatters import formatar_percentual, formatar_numero, format_iso_date
from utils.helpers import color, button_style, create_card, create_metric_row, content_style

def get_predicao_layout(data):
    # if data.get("df_Previsoes") is None:
    #     return html.Div([
    #         html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
    #         create_card(
    #             "Dados Indisponíveis",
    #             html.Div([
    #                 html.P("Não foram encontrados dados de previsão para este cliente.", className="text-center text-muted my-4"),
    #                 html.I(className="fas fa-chart-pie fa-4x text-muted d-block text-center mb-3"),
    #                 html.P("Verifique se o arquivo rfma_previsoes_ajustado.xlsx está presente", 
    #                        className="text-muted text-center")
    #             ])
    #         )
    #     ], style=content_style)
    
    # df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split')
    
    if data.get("df_previsao_retorno") is None:
        return html.Div([
            html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de previsão para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-chart-pie fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo previsao_retorno.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_previsao_retorno = pd.read_json(io.StringIO(data["df_previsao_retorno"]), orient='split')
    
    # # Calculate metrics for the metrics row
    # total_customers = len(df_Previsoes)
    # high_prob_customers = len(df_Previsoes[df_Previsoes['categoria_previsao'] == 'Alta Probabilidade de Compra'])
    # low_prob_customers = len(df_Previsoes[df_Previsoes['categoria_previsao'] == 'Baixa Probabilidade de Compra'])
    # high_prob_pct = (high_prob_customers / total_customers * 100) if total_customers > 0 else 0
    
    # # Create metrics row
    # metrics = [
    #     {"title": "Total de Clientes", "value": formatar_numero(total_customers), "color": color['primary']},
    #     {"title": "Alta Probabilidade", "value": formatar_numero(high_prob_customers), "color": color['secondary']},
    #     {"title": "Baixa Probabilidade", "value": formatar_numero(low_prob_customers), "color": color['accent']},
    #     {"title": "% Alta Probabilidade", "value": formatar_percentual(high_prob_pct), "color": color['success']}
    # ]
    
    # metrics_row = create_metric_row(metrics)
    
    # # Enhanced prediction chart
    # previsao_counts = df_Previsoes['categoria_previsao'].value_counts().reset_index()
    # previsao_counts.columns = ['categoria_previsao', 'count']
    
    # # Create pie chart for prediction categories
    # fig_pie = px.pie(
    #     previsao_counts,
    #     values='count',
    #     names='categoria_previsao',
    #     color='categoria_previsao',
    #     color_discrete_map={
    #         'Baixa Probabilidade de Compra': color['accent'],
    #         'Alta Probabilidade de Compra': color['secondary']
    #     },
    #     template='plotly_white',
    #     hole=0.4,
    #     custom_data=['categoria_previsao']
    # )
    
    # fig_pie.update_layout(
    #     margin=dict(t=30, b=30, l=30, r=30),
    #     height=450,
    #     legend=dict(
    #         orientation="h",
    #         yanchor="bottom",
    #         y=-0.2,
    #         xanchor="center",
    #         x=0.5
    #     ),
    #     clickmode='event+select',
    #     hovermode='closest',
    # )
    
    # fig_pie.update_traces(
    #     textposition='inside',
    #     textinfo='percent',
    #     textfont=dict(size=14, family="Montserrat", color="white"),
    #     pull=[0.05, 0],
    #     hovertemplate='<b>%{label}</b><br>Clientes: %{value}<br>Percentual: %{percent:.1%}<extra></extra>'

    # )
    
    # # Calculate average predicted purchases
    # avg_predicted = df_Previsoes['predicted_purchases_30d'].mean()
    
    # # Create distribution of predicted purchases
    # fig_dist = px.histogram(
    #     df_Previsoes,
    #     x='predicted_purchases_30d',
    #     color='categoria_previsao',
    #     color_discrete_map={
    #         'Baixa Probabilidade de Compra': color['accent'],
    #         'Alta Probabilidade de Compra': color['secondary']
    #     },
    #     template='plotly_white',
    #     barmode='overlay',
    #     opacity=0.7,
    #     nbins=20
    # )
    
    # # Add vertical line for average
    # fig_dist.add_shape(
    #     type="line",
    #     x0=avg_predicted,
    #     y0=0,
    #     x1=avg_predicted,
    #     y1=1,
    #     yref="paper",
    #     line=dict(
    #         color=color['primary'],
    #         width=2,
    #         dash="dash",
    #     )
    # )
    
    # fig_dist.add_annotation(
    #     x=avg_predicted,
    #     y=0.95,
    #     yref="paper",
    #     text=f"Média: {str(avg_predicted).replace('.', ',')}",
    #     showarrow=True,
    #     arrowhead=1,
    #     ax=40,
    #     ay=-40,
    #     font=dict(size=12, family="Montserrat")
    # )
    
    # fig_dist.update_layout(
    #     title_font=dict(size=16, family="Montserrat", color=color['primary']),
    #     height=500,
    #     margin=dict(t=50, b=50, l=50, r=50),
    #     xaxis=dict(
    #         title="Previsão de Compras (30 dias)",
    #         title_font=dict(size=14, family="Montserrat"),
    #         gridcolor='rgba(0,0,0,0.05)'
    #     ),
    #     yaxis=dict(
    #         title="Número de Clientes",
    #         title_font=dict(size=14, family="Montserrat"),
    #         gridcolor='rgba(0,0,0,0.05)'
    #     ),
    #     legend=dict(
    #         orientation="h",
    #         yanchor="bottom",
    #         y=1.02,
    #         xanchor="right",
    #         x=1
    #     ),
    #     plot_bgcolor='rgba(0,0,0,0)',
    #     paper_bgcolor='rgba(0,0,0,0)'
    # )
    
    # Adicionar visualizações para df_previsao_retorno
    # Preparar dados para a tabela de clientes
    df_cliente_display = df_previsao_retorno.copy()
    
    # Ordenar por probabilidade média (decrescente)
    df_cliente_display = df_cliente_display.sort_values(by='prob_media', ascending=False)
    
    # Preparar as colunas para exibição
    columns = [
        {"name": "Cliente", "id": "nome"},
        {"name": "Prob. Média", "id": "prob_media_fmt"},
        {"name": "Última Compra", "id": "ultima_compra_fmt"},
        {"name": "Próxima Compra", "id": "proxima_compra_fmt"},
        {"name": "Situação", "id": "situacao"},
        {"name": "Regularidade", "id": "regularidade"}
    ]
    
    # Formatar os dados para a tabela
    df_cliente_display['prob_media_fmt'] = df_cliente_display['prob_media'].apply(
        lambda x: formatar_percentual(x * 100) if pd.notnull(x) else "N/A"
    )
    
    df_cliente_display['ultima_compra_fmt'] = df_cliente_display['ultima_compra'].apply(
        lambda x: format_iso_date(x) if pd.notnull(x) else "N/A"
    )
    
    df_cliente_display['proxima_compra_fmt'] = df_cliente_display['proxima_compra'].apply(
        lambda x: format_iso_date(x) if pd.notnull(x) else "N/A"
    )

    # Adicionar coluna auxiliar para agrupar situações em ATIVO ou INATIVO
    # mas mantendo os valores originais na coluna situacao
    df_cliente_display['situacao_grupo'] = df_cliente_display['situacao'].apply(
        lambda x: "INATIVO" if "INATIVO" in str(x).upper() else "ATIVO"
    )
    
    # Criar o gráfico de radar para comparação de clientes
    # Selecionar os 5 principais clientes por probabilidade média
    top_clients = df_cliente_display.nlargest(5, 'prob_media')
    
    # Criar figura de radar
    fig_radar = go.Figure()
    
    # Métricas para o radar
    metrics = ['prob_media', 'regularidade', 'total_compras_historico']
    metrics_label = {
        'prob_media': 'Probabilidade', 
        'regularidade': 'Regularidade', 
        'total_compras_historico': 'Total Histórico'
    }
    
    # Normalizar os dados para o radar
    radar_data = top_clients.copy()
    for metric in metrics:
        if radar_data[metric].max() > 0:
            radar_data[metric] = radar_data[metric] / radar_data[metric].max()
    
    # Adicionar cada cliente ao radar
    for i, row in radar_data.iterrows():
        fig_radar.add_trace(go.Scatterpolar(
            r=[row[m] for m in metrics] + [row[metrics[0]]],  # Repetir o primeiro para fechar o polígono
            theta=[metrics_label[m] for m in metrics] + [metrics_label[metrics[0]]],
            fill='toself',
            name=row['nome'][:20] + ('...' if len(row['nome']) > 20 else '')
        ))
    
    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        height=500,
        margin=dict(t=30, b=100, l=50, r=50)
    )
    
    # Criar gráfico de barras para probabilidades médias
    fig_prob = px.bar(
        df_cliente_display.nlargest(10, 'prob_media'),
        y='nome',
        x='prob_media',
        orientation='h',
        labels={
            'prob_media': 'Probabilidade Média',
            'nome': 'Cliente'
        },
        color='prob_media',
        color_continuous_scale=px.colors.sequential.Viridis,
        template='plotly_white'
    )
    
    fig_prob.update_layout(
        title="Top 10 Clientes por Probabilidade de Retorno",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        height=500,
        margin=dict(t=50, b=50, l=200, r=50),
        yaxis=dict(
            title="",
            autorange="reversed"
        ),
        xaxis=dict(
            title="Probabilidade Média",
            tickformat='.0%'
        ),
        coloraxis_showscale=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Obter valores únicos para o filtro de situação - apenas ATIVO, INATIVO e Todos
    situacoes = ['Todos', 'ATIVO', 'INATIVO']

    # Obter valores únicos para o filtro de padrão de compra
    padroes_compra = ['Todos'] + sorted(df_cliente_display['padrao_compra'].unique().tolist())
    
    # Métricas adicionais para retorno de clientes
    ativos = len(df_cliente_display[df_cliente_display['situacao_grupo'] == 'ATIVO'])
    inativos = len(df_cliente_display[df_cliente_display['situacao_grupo'] == 'INATIVO'])
    total = len(df_cliente_display[df_cliente_display['situacao_grupo'] == 'INATIVO']) + len(df_cliente_display[df_cliente_display['situacao_grupo'] == 'ATIVO'])
    alta_prob_retorno = len(df_cliente_display[df_cliente_display['prob_media'] > 0.7])
    
    # Create metrics row
    retorno_metrics = [
        {"title": "Clientes Ativos", "value": formatar_numero(ativos), "color": color['success']},
        {"title": "Clientes Inativos", "value": formatar_numero(inativos), "color": color['accent']},
        {"title": "Alta Prob. Retorno", "value": formatar_numero(alta_prob_retorno), "color": color['secondary']},
        {"title": "% Ativos", "value": formatar_percentual((ativos / total * 100) if total > 0 else 0), "color": color['primary']}
    ]
    
    retorno_metrics_row = create_metric_row(retorno_metrics)
    
    # Layout with cards
    layout = html.Div(
        [
            html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            # metrics_row,
            
            # # Charts in row
            # dbc.Row([
            #     dbc.Col(
            #         create_card(
            #             "Distribuição de Previsões de Compra (30 dias)",
            #             dcc.Graph(id="predicao-dist", figure=fig_dist, config={"responsive": True})
            #         ),
            #         # style={"height": "800px"}
            #     ),
            #     dbc.Col(
            #         create_card(
            #             "Probabilidade de Compra nos Próximos 30 dias",
            #             dcc.Graph(id="predicao-pie", figure=fig_pie, config={"responsive": True})
            #         ),
            #         lg=4, md=12
            #     )
            # ], className="mb-4"),
            
            # # Client list
            # create_card(
            #     html.Div(id="predicao-client-list-header", children="Clientes da Categoria Selecionada"),
            #     html.Div(
            #         id="predicao-client-list",
            #         children=html.Div([
            #             html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4"),
            #             html.Div(className="text-center", children=[
            #                 html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
            #                 html.P("Clique em uma categoria para visualizar detalhes", className="text-muted mt-2")
            #             ])
            #         ])
            #     )
            # ),
            
            # Métricas de retorno
            retorno_metrics_row,
            
            dcc.Store(id='selected-data', data=data),
            
            # Seleção de cliente e detalhes com o histórico de desempenho
            dbc.Row([
                create_card(
                    "Filtros para Tabela de Previsão",
                    html.Div([
                        html.Div(className="alert alert-light border mb-3", children=[
                            html.I(className="fas fa-filter text-primary me-2"),
                            "Utilize os filtros abaixo para refinar a visualização da tabela de previsão"
                        ]),
                        dbc.Row([
                            dbc.Col(
                                html.Div([
                                    html.Label("Filtrar por Padrão de Compra:", className="mb-2 fw-bold"),
                                    dcc.RadioItems(
                                        id='client-filter-padrao-compra',
                                        options=[{'label': s, 'value': s} for s in padroes_compra],
                                        value='Todos',
                                        className="mb-3 d-flex flex-wrap gap-3",
                                        inputClassName="me-1",
                                        labelClassName="me-3",
                                        labelStyle={"cursor": "pointer"}
                                    )
                                ])
                            ),
                            dbc.Col(
                                html.Div([
                                    html.Label("Filtrar por Situação:", className="mb-2 fw-bold"),
                                    dcc.RadioItems(
                                        id='client-filter-situacao',
                                        options=[{'label': s, 'value': s} for s in situacoes],
                                        value='Todos',
                                        className="mb-3 d-flex flex-wrap gap-3",
                                        inputClassName="me-1",
                                        labelClassName="me-3",
                                        labelStyle={"cursor": "pointer"}
                                    )
                                ])
                            ),                            
                        ]),
                    ])
                ),
            ], className="mb-4"),

            
            # Tabela de todos os clientes
            create_card(
                html.Div(id="tabela-retorno-header", children="Tabela de Previsão de Retorno"),
                html.Div(
                    id="tabela-retorno-content",
                    children=html.Div([
                        html.P("Selecione uma categoria nos gráficos acima para visualizar os clientes.", className="text-center text-muted my-4"),
                        html.Div(className="text-center", children=[
                            html.I(className="fas fa-table fa-2x text-muted"),
                            html.P("A tabela será exibida após a seleção", className="text-muted mt-2")
                        ]),
                        html.Div(
                            html.Button(
                                [html.I(className="fas fa-file-excel me-2"), "Exportar para Excel"],
                                id="btn-export-clientes",
                                className="btn btn-success mb-3 mt-3",
                                style=button_style
                            ),
                            className="text-center"
                        )
                    ])
                )
            ),

            create_card(
                "Detalhes por Cliente",
                html.Div([
                    html.Div(
                        id="cliente-selecionado-indicador",
                        className="alert alert-info mb-3",
                        style={'display': 'none'},
                        children=[
                            html.Div([
                                html.I(className="fas fa-info-circle me-2"),
                                "Cliente selecionado: ",
                                html.Strong(id="cliente-selecionado-nome")
                            ]),
                            html.Button(
                                html.I(className="fas fa-times"),
                                id="btn-limpar-selecao",
                                className="btn btn-sm btn-outline-info",
                                style={'border': 'none'}
                            )
                        ]
                    ),
                    html.Div(id="cliente-detail-message", className="text-center text-muted my-3", children=[
                        html.I(className="fas fa-info-circle fa-2x mb-3"),
                        html.P("Selecione um cliente na tabela para visualizar detalhes")
                    ]),
                    html.Div(id='cliente-detail-div')
                ])
            ),
        ],
        style=content_style,
    )
    
    return layout