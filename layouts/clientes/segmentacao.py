import io
import pandas as pd
import plotly.express as px
from dash import html, dcc
import dash_bootstrap_components as dbc

from utils import formatar_numero
from utils import create_card, create_metric_row, content_style, color, gradient_colors, cores_segmento

def get_segmentacao_layout(data):
    if data.get("df") is None:
        return html.Div([
            html.H2("Segmentação de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de segmentação para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-users fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo analytics_cliente está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df = pd.read_json(io.StringIO(data["df"]), orient='split')
    
    # Calculate metrics for the metrics row
    total_clients = len(df)
    active_clients = len(df[df['Segmento'].isin(['Novos', 'Campeões', 'Fiéis Alto Valor', 'Fiéis Baixo Valor', 'Recentes Alto Valor', 'Recentes Baixo Valor'])])
    inactive_clients = len(df[df['Segmento'].isin(['Sumidos', 'Inativos'])])
    champions = len(df[df['Segmento'] == 'Campeões'])
    
    # Create metrics row
    metrics = [
        {"title": "Total de Clientes", "value": formatar_numero(total_clients), "color": color['primary']},
        {"title": "Clientes Ativos", "value": formatar_numero(active_clients), "color": color['success']},
        {"title": "Clientes Inativos", "value": formatar_numero(inactive_clients), "color": color['danger']},
        {"title": "Clientes Campeões", "value": formatar_numero(champions), "color": gradient_colors['green_gradient'][0]}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Construir gráfico diretamente aqui, em vez de depender de um callback
    segment_counts = df['Segmento'].value_counts().reset_index()
    segment_counts.columns = ['Segmento', 'Quantidade de Clientes']

    # Calcular percentuais
    total_clients = segment_counts['Quantidade de Clientes'].sum()
    segment_counts['Percentual'] = segment_counts['Quantidade de Clientes'] / total_clients * 100

    # Adicionar linha para "Todos"
    todos_row = pd.DataFrame({
        'Segmento': ['Todos'],
        'Quantidade de Clientes': [total_clients],
        'Percentual': [100.0]
    })
    
    # Ordenar os segmentos originais por quantidade (do maior para o menor)
    segment_counts = segment_counts.sort_values('Quantidade de Clientes', ascending=False)
    
    # Concatenar o DataFrame original com a linha "Todos"
    segment_counts = pd.concat([todos_row, segment_counts], ignore_index=True)
    
    # Obter a ordem personalizada: "Todos" primeiro, seguido pelos demais segmentos ordenados por quantidade
    segment_order = ["Todos"] + segment_counts[segment_counts['Segmento'] != 'Todos']['Segmento'].tolist()
    
    # Criar o gráfico de barras diretamente na função
    fig_segments = px.bar(
        segment_counts, 
        x='Segmento', 
        y='Quantidade de Clientes', 
        color='Segmento', 
        labels={"Segmento": "Segmentos"},
        color_discrete_map=cores_segmento,
        template='plotly_white',
        category_orders={"Segmento": segment_order}
    )
    
    # Adicionar anotações de valores
    for i, row in segment_counts.iterrows():
        # Formatar percentual com 1 casa decimal
        formatted_pct = f"{row['Percentual']:.1f}%".replace('.', ',')
        
        fig_segments.add_annotation(
            x=row['Segmento'],
            y=row['Quantidade de Clientes'],
            text=f"{formatar_numero(row['Quantidade de Clientes'])} ({formatted_pct})",
            showarrow=False,
            yshift=10,
            font=dict(size=12, family="Montserrat")
        )
    
    fig_segments.update_layout(
        margin=dict(t=30, b=50, l=50, r=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=500,
        showlegend=False,
        yaxis=dict(
            title="Quantidade de Clientes",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        xaxis=dict(
            title="Segmentos",
            title_font=dict(size=14, family="Montserrat"),
            tickfont=dict(size=12),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        clickmode='event+select'
    )
    
    # Layout with cards
    layout = html.Div(
        [
            html.H2("Segmentação de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # Distribution row
            dbc.Row(
            [
                dbc.Col(
                    create_card(
                        "Distribuição de Segmentos",
                        dcc.Graph(
                            id="segment-distribution",
                            figure=fig_segments,
                            config={"responsive": True, "displayModeBar": False}
                        )
                    ),
                    width=12  # Ocupa toda a largura disponível
                ),
            ],
            className="mb-4",
        ),
            
            # Client list
            create_card(
                html.Div(id="client-list-header", children="Clientes do Segmento Selecionado"),
                html.Div(
                    id="client-list",
                    children=html.Div([
                        html.P("Selecione um segmento no gráfico acima para ver os clientes.", className="text-center text-muted my-4"),
                        html.Div(className="text-center", children=[
                            html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                            html.P("Clique em uma barra para visualizar detalhes", className="text-muted mt-2")
                        ])
                    ])
                )
            )
        ],
        style=content_style,
    )
    return layout