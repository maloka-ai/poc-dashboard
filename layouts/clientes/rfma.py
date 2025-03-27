import io
import pandas as pd
import plotly.express as px
from dash import html, dcc
import dash_bootstrap_components as dbc

from utils import formatar_numero, formatar_moeda
from utils import create_card, create_metric_row, content_style, colors

def get_rfma_layout(data):
    if data.get("df") is None:
        return html.Div([
            html.H2("Análise RFMA de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados RFMA para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-user-tag fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo analytics_cliente está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df = pd.read_json(io.StringIO(data["df"]), orient='split')
    
    # Calculate metrics for the metrics row
    avg_recency = df['Recency'].mean()
    avg_frequency = df['Frequency'].mean()
    avg_monetary = df['Monetary'].mean()
    avg_age = df['Age'].mean()
    
    # Create metrics row
    metrics = [
        {"title": "Média de Recência (dias)", "value": formatar_numero(avg_recency, 1), "color": colors[0]},
        {"title": "Média de Frequência", "value": formatar_numero(avg_frequency, 1), "color": colors[1]},
        {"title": "Valor Médio (R$)", "value": formatar_moeda(avg_monetary), "color": colors[2]},
        {"title": "Média de Antiguidade (dias)", "value": formatar_numero(avg_age, 1), "color": colors[3]}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    figures = []
    x_axis_titles_rfma = {
        "Recency": "Intervalo de Recência (dias)",
        "Frequency": "Intervalo de Frequência (compras)",
        "Monetary": "Intervalo de Valor Monetário (R$)",
        "Age": "Intervalo de Idade (dias)"
    }
    
    rfma_metrics_order = [
        ("Recency", "R_range", colors[0]),
        ("Frequency", "F_range", colors[1]),
        ("Monetary", "M_range", colors[2]),
        ("Age", "A_range", colors[3]),
    ]
    
    for metric, col, color in rfma_metrics_order:
        if col in df.columns:
            counts = df[col].value_counts()
            ordered_index = sorted(counts.index, key=lambda x: float(x.split('-')[0].replace('+', '')))
            counts = counts.loc[ordered_index]
            
            # Add gradient colors for each bar
            color_scale = [color, f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.7)"]
            
            fig = px.bar(
                x=counts.index,
                y=counts.values,
                labels={'x': col, 'y': 'Número de Clientes'},
                color_discrete_sequence=[color],
                text=counts.values,
                category_orders={col: ordered_index},
                template='plotly_white'
            )
            
            x_title = x_axis_titles_rfma.get(metric, col)
            
            fig.update_layout(
                xaxis_title=x_title, 
                yaxis_title="Número de Clientes",
                margin=dict(t=20, b=50, l=50, r=50),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            fig.update_traces(
                textposition='outside',
                textfont=dict(size=12, family="Montserrat"),
                marker=dict(
                    color=color,
                    opacity=0.8,
                    line=dict(width=1, color=color)
                )
            )
            
            fig.update_xaxes(
                title_font=dict(size=12, family="Montserrat"),
                gridcolor='rgba(0,0,0,0.05)'
            )
            
            fig.update_yaxes(
                title_font=dict(size=12, family="Montserrat"),
                gridcolor='rgba(0,0,0,0.05)'
            )
            
            figures.append(fig)
    
    return html.Div(
        [
            html.H2("Análise RFMA de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # First row of charts
            dbc.Row(
                [
                    dbc.Col(
                        create_card(
                            "Distribuição de Recência",
                            dcc.Graph(id="recency-dist", figure=figures[0] if len(figures)>0 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                    dbc.Col(
                        create_card(
                            "Distribuição de Frequência",
                            dcc.Graph(id="frequency-dist", figure=figures[1] if len(figures)>1 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                ],
                className="mb-4",
            ),
            
            # Second row of charts
            dbc.Row(
                [
                    dbc.Col(
                        create_card(
                            "Distribuição de Valor Monetário",
                            dcc.Graph(id="monetary-dist", figure=figures[2] if len(figures)>2 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                    dbc.Col(
                        create_card(
                            "Distribuição de Antiguidade",
                            dcc.Graph(id="age-dist", figure=figures[3] if len(figures)>3 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                ],
                className="mb-4",
            ),
        ],
        style=content_style,
    )