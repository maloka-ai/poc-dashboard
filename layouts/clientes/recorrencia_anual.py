import io
import pandas as pd
import plotly.express as px
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import formatar_numero, formatar_percentual
from utils import create_card, create_metric_row, content_style, color

def get_recorrencia_anual_layout(data):
    if data.get("df_RC_Anual") is None:
        return html.Div([
            html.H2("Recorrência Anual", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de recorrência anual para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="far fa-calendar-alt fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo metricas_recorrencia_anual.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_RC_Anual = pd.read_json(io.StringIO(data["df_RC_Anual"]), orient='split')
    
    # Calculate metrics for the metrics row
    current_retention = df_RC_Anual['retention_rate'].iloc[-1] if not df_RC_Anual.empty else 0
    current_new_rate = df_RC_Anual['new_rate'].iloc[-1] if not df_RC_Anual.empty else 0
    current_returning_rate = df_RC_Anual['returning_rate'].iloc[-1] if not df_RC_Anual.empty else 0
    
    retention_change = df_RC_Anual['retention_rate'].iloc[-1] - df_RC_Anual['retention_rate'].iloc[-2] if len(df_RC_Anual) > 1 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Taxa de Retenção Atual", "value": formatar_percentual(current_retention), "change": retention_change, "color": color['accent']},
        {"title": "Taxa de Novos Clientes", "value": formatar_percentual(current_new_rate), "color": color['secondary']},
        {"title": "Taxa de Recorrentes", "value": formatar_percentual(current_returning_rate), "color": color['success']},
        {"title": "Total de Clientes (Último Ano)", "value": formatar_numero(df_RC_Anual['total_customers'].iloc[-1]), "color": color['primary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced annual retention chart
    fig_anual = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bars for new and returning customer rates
    fig_anual.add_trace(
        go.Bar(
            x=df_RC_Anual['ano'],
            y=df_RC_Anual['new_rate'],
            name='Novos Clientes (%)',
            marker_color=color['accent'],
            text=df_RC_Anual['new_customers'],
            textposition='inside',
            textfont=dict(family="Montserrat", size=12, color="white")
        ),
        secondary_y=False
    )
    
    fig_anual.add_trace(
        go.Bar(
            x=df_RC_Anual['ano'],
            y=df_RC_Anual['returning_rate'],
            name='Clientes Recorrentes (%)',
            marker_color=color['secondary'],
            text=df_RC_Anual['returning_customers'],
            textposition='inside',
            textfont=dict(family="Montserrat", size=12, color="white")
        ),
        secondary_y=False
    )
    
    # Add line for retention rate
    fig_anual.add_trace(
        go.Scatter(
            x=df_RC_Anual['ano'],
            y=df_RC_Anual['retention_rate'],
            name='Taxa de Retenção',
            mode='lines+markers+text',
            text=df_RC_Anual['retention_rate'].apply(lambda x: f'{x:.1f}%'),
            textposition='top center',
            textfont=dict(family="Montserrat", size=12),
            line=dict(color=color['success'], width=3),
            marker=dict(size=10, line=dict(width=2, color='white'))
        ),
        secondary_y=True
    )
    
    # Update layout
    fig_anual.update_layout(
        barmode='stack',
        xaxis_title="Ano",
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title_font=dict(family="Montserrat")
    )
    
    fig_anual.update_yaxes(
        title_text="Percentual de Clientes (%)", 
        secondary_y=False,
        gridcolor='rgba(0,0,0,0.05)',
        title_font=dict(size=14, family="Montserrat")
    )
    
    fig_anual.update_yaxes(
        title_text="Taxa de Retenção (%)", 
        secondary_y=True,
        gridcolor='rgba(0,0,0,0.05)',
        title_font=dict(size=14, family="Montserrat")
    )
    
    fig_anual.update_xaxes(
        tickmode='array', 
        tickvals=df_RC_Anual['ano'].unique(),
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Enhanced table
    colunas_anuais = ["ano", "total_customers", "returning_customers", "new_customers", "retention_rate", "new_rate", "returning_rate"]
    renomear_anual = {
        "ano": "Ano",
        "total_customers": "Total de Clientes",
        "returning_customers": "Clientes Recorrentes",
        "new_customers": "Novos Clientes",
        "retention_rate": "Taxa de Retenção (%)",
        "new_rate": "Taxa de Novos Clientes (%)",
        "returning_rate": "Taxa de Clientes Recorrentes (%)",
    }   
    df_anual_filtrado = df_RC_Anual[colunas_anuais]
    
    # Customer trending chart
    fig_customers = px.line(
        df_RC_Anual,
        x='ano',
        y=['total_customers', 'returning_customers', 'new_customers'],
        markers=True,
        labels={"value": "Número de Clientes", "variable": "Tipo"},
        color_discrete_map={
            'total_customers': color['primary'],
            'returning_customers': color['secondary'],
            'new_customers': color['accent']
        },
        template='plotly_white'
    )
    
    # Rename series
    for trace in fig_customers.data:
        if trace.name == 'total_customers':
            trace.name = "Total de Clientes"
        elif trace.name == 'returning_customers':
            trace.name = "Clientes Recorrentes"
        elif trace.name == 'new_customers':
            trace.name = "Novos Clientes"
    
    fig_customers.update_layout(
        xaxis_title="Ano",
        yaxis_title="Número de Clientes",
        margin=dict(t=50, b=50, l=50, r=50),
        height=450,
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
    
    fig_customers.update_xaxes(
        tickmode='array', 
        tickvals=df_RC_Anual['ano'].unique(),
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    fig_customers.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Layout with cards
    layout = html.Div([
        html.H2("Recorrência Anual", className="dashboard-title"),
        
        # Summary metrics row
        metrics_row,
        
        # Charts in row
        dbc.Row([
            dbc.Col(
                create_card(
                    "Composição de Clientes e Taxa de Retenção Anual",
                    dcc.Graph(id='recorrencia-anual-graph', figure=fig_anual, config={"responsive": True})
                ),
                lg=7, md=12
            ),
            dbc.Col(
                create_card(
                    "Evolução Anual de Clientes",
                    dcc.Graph(id='recorrencia-anual-customers', figure=fig_customers, config={"responsive": True})
                ),
                lg=5, md=12
            )
        ], className="mb-4"),
        
        # Table with detailed metrics
        create_card(
            "Métricas Anuais Detalhadas",
            dash_table.DataTable(
                id='table-recorrencia-anual',
                columns=[
                    {"name": renomear_anual.get(col, col), "id": col}
                    for col in colunas_anuais
                ],
                data=df_anual_filtrado.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "center",
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
                        "if": {"column_id": "retention_rate"},
                        "fontWeight": "bold",
                        "color": color['success']
                    },
                    {
                        "if": {"column_id": "new_rate"},
                        "color": color['accent']
                    },
                    {
                        "if": {"column_id": "returning_rate"},
                        "color": color['secondary']
                    },
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ]
            )
        )
    ], style=content_style)
    
    return layout