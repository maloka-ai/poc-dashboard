import io
import pandas as pd
import plotly.express as px
from dash import html, dcc
import dash_bootstrap_components as dbc

from utils import formatar_percentual, formatar_numero
from utils import create_card, create_metric_row, content_style, color

def get_predicao_layout(data):
    if data.get("df_Previsoes") is None:
        return html.Div([
            html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de previsão para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-chart-pie fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo rfma_previsoes_ajustado.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split')
    
    # Calculate metrics for the metrics row
    total_customers = len(df_Previsoes)
    high_prob_customers = len(df_Previsoes[df_Previsoes['categoria_previsao'] == 'Alta Probabilidade de Compra'])
    low_prob_customers = len(df_Previsoes[df_Previsoes['categoria_previsao'] == 'Baixa Probabilidade de Compra'])
    high_prob_pct = (high_prob_customers / total_customers * 100) if total_customers > 0 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Total de Clientes", "value": formatar_numero(total_customers), "color": color['primary']},
        {"title": "Alta Probabilidade", "value": formatar_numero(high_prob_customers), "color": color['secondary']},
        {"title": "Baixa Probabilidade", "value": formatar_numero(low_prob_customers), "color": color['accent']},
        {"title": "% Alta Probabilidade", "value": formatar_percentual(high_prob_pct), "color": color['success']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced prediction chart
    previsao_counts = df_Previsoes['categoria_previsao'].value_counts().reset_index()
    previsao_counts.columns = ['categoria_previsao', 'count']
    
    fig_pred = px.bar(
        previsao_counts,
        x='categoria_previsao',
        y='count',
        color='categoria_previsao',
        color_discrete_map={
            'Baixa Probabilidade de Compra': color['accent'],
            'Alta Probabilidade de Compra': color['secondary']
        },
        template='plotly_white'
    )
    
    # Add percentage labels
    for i, row in previsao_counts.iterrows():
        percentage = row['count'] / previsao_counts['count'].sum() * 100
        fig_pred.add_annotation(
            x=row['categoria_previsao'],
            y=row['count'],
            text=f"{formatar_numero(row['count'])} ({formatar_percentual(percentage)})",
            showarrow=False,
            yshift=10,
            font=dict(size=12, family="Montserrat")
        )
    
    fig_pred.update_layout(
        legend_title_text="Categoria de Previsão",
        margin=dict(t=30, b=50, l=50, r=50),
        height=500,
        xaxis=dict(
            title="Categoria de Previsão",
            title_font=dict(size=14, family="Montserrat"),
            tickfont=dict(size=12, family="Montserrat")
        ),
        yaxis=dict(
            title="Número de Clientes",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    
    # Create pie chart for prediction categories
    fig_pie = px.pie(
        previsao_counts,
        values='count',
        names='categoria_previsao',
        color='categoria_previsao',
        color_discrete_map={
            'Baixa Probabilidade de Compra': color['accent'],
            'Alta Probabilidade de Compra': color['secondary']
        },
        template='plotly_white',
        hole=0.4
    )
    
    fig_pie.update_layout(
        margin=dict(t=30, b=30, l=30, r=30),
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent',
        textfont=dict(size=14, family="Montserrat", color="white"),
        pull=[0.05, 0]
    )
    
    # Calculate average predicted purchases
    avg_predicted = df_Previsoes['predicted_purchases_30d'].mean()
    
    # Create distribution of predicted purchases
    fig_dist = px.histogram(
        df_Previsoes,
        x='predicted_purchases_30d',
        color='categoria_previsao',
        color_discrete_map={
            'Baixa Probabilidade de Compra': color['accent'],
            'Alta Probabilidade de Compra': color['secondary']
        },
        template='plotly_white',
        barmode='overlay',
        opacity=0.7,
        nbins=20
    )
    
    # Add vertical line for average
    fig_dist.add_shape(
        type="line",
        x0=avg_predicted,
        y0=0,
        x1=avg_predicted,
        y1=1,
        yref="paper",
        line=dict(
            color=color['primary'],
            width=2,
            dash="dash",
        )
    )
    
    fig_dist.add_annotation(
        x=avg_predicted,
        y=0.95,
        yref="paper",
        text=f"Média: {str(avg_predicted).replace('.', ',')}",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40,
        font=dict(size=12, family="Montserrat")
    )
    
    fig_dist.update_layout(
        title="Distribuição das Previsões de Compra",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis=dict(
            title="Previsão de Compras (30 dias)",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        yaxis=dict(
            title="Número de Clientes",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Layout with cards
    layout = html.Div(
        [
            html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # Charts in row
            dbc.Row([
                dbc.Col(
                    create_card(
                        "Probabilidade de Compra nos Próximos 30 dias",
                        dcc.Graph(id="predicao-bar", figure=fig_pred, config={"responsive": True})
                    ),
                    lg=8, md=12
                ),
                dbc.Col(
                    create_card(
                        "Proporção de Probabilidade",
                        dcc.Graph(id="predicao-pie", figure=fig_pie, config={"responsive": True})
                    ),
                    lg=4, md=12
                )
            ], className="mb-4"),
            
            # Distribution chart
            create_card(
                "Distribuição de Previsões de Compra (30 dias)",
                dcc.Graph(id="predicao-dist", figure=fig_dist, config={"responsive": True})
            ),
            
            # Client list
            create_card(
                html.Div(id="predicao-client-list-header", children="Clientes da Categoria Selecionada"),
                html.Div(
                    id="predicao-client-list",
                    children=html.Div([
                        html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4"),
                        html.Div(className="text-center", children=[
                            html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                            html.P("Clique em uma categoria para visualizar detalhes", className="text-muted mt-2")
                        ])
                    ])
                )
            )
        ],
        style=content_style,
    )
    
    return layout