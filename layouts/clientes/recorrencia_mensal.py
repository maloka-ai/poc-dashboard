import io
import pandas as pd
import plotly.express as px
from dash import html, dcc, dash_table
import plotly.graph_objects as go

from utils import formatar_percentual
from utils import create_card, create_metric_row, content_style, color

def get_recorrencia_mensal_layout(data):
    if data.get("df_RC_Mensal") is None:
        return html.Div([
            html.H2("Recorrência Mensal", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de recorrência mensal para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-sync fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo metricas_recorrencia_mensal.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_RC_Mensal = pd.read_json(io.StringIO(data["df_RC_Mensal"]), orient='split')
    
    # Calculate metrics for the metrics row
    current_retention = df_RC_Mensal['retention_rate'].iloc[-1] if not df_RC_Mensal.empty else 0
    avg_retention = df_RC_Mensal['retention_rate'].mean()
    max_retention = df_RC_Mensal['retention_rate'].max()
    min_retention = df_RC_Mensal['retention_rate'].min()
    
    retention_change = df_RC_Mensal['retention_rate'].iloc[-1] - df_RC_Mensal['retention_rate'].iloc[-2] if len(df_RC_Mensal) > 1 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Taxa de Recorrência Atual", "value": formatar_percentual(current_retention), "change": retention_change, "color": color['accent']},
        {"title": "Média de Recorrência", "value": formatar_percentual(avg_retention), "color": color['secondary']},
        {"title": "Maior Taxa", "value": formatar_percentual(max_retention), "color": color['success']},
        {"title": "Menor Taxa", "value": formatar_percentual(min_retention), "color": color['warning']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced monthly retention chart
    fig_mensal = px.line(
        df_RC_Mensal, 
        x='yearmonth', 
        y='retention_rate', 
        markers=True, 
        color_discrete_sequence=[color['secondary']],
        labels={'yearmonth': 'Mês/Ano', 'retention_rate': 'Taxa de Recorrência'},  # Renomeia os rótulos no hover
        template='plotly_white'
    )
    
    # Add thicker line and bigger markers
    fig_mensal.update_traces(
        line=dict(width=3),
        marker=dict(size=10, line=dict(width=2, color='white'))
    )
    
    # Add a moving average line
    window_size = 3
    if len(df_RC_Mensal) >= window_size:
        df_RC_Mensal['moving_avg'] = df_RC_Mensal['retention_rate'].rolling(window=window_size).mean()
        
        fig_mensal.add_trace(
            go.Scatter(
                x=df_RC_Mensal['yearmonth'],
                y=df_RC_Mensal['moving_avg'],
                mode='lines',
                name=f'Média Móvel ({window_size} meses)',
                line=dict(color=color['accent'], width=2, dash='dash')
            )
        )
    
    # # Add target line at 30%
    # fig_mensal.add_shape(
    #     type="line",
    #     x0=df_RC_Mensal['yearmonth'].iloc[0],
    #     y0=30,
    #     x1=df_RC_Mensal['yearmonth'].iloc[-1],
    #     y1=30,
    #     line=dict(
    #         color=color['success'],
    #         width=2,
    #         dash="dot",
    #     )
    # )
    
    # fig_mensal.add_annotation(
    #     x=df_RC_Mensal['yearmonth'].iloc[-1],
    #     y=30,
    #     text="Meta (30%)",
    #     showarrow=False,
    #     yshift=10,
    #     xshift=30,
    #     font=dict(size=12, color=color['success'])
    # )
    
    fig_mensal.update_layout(
        xaxis_title="Mês", 
        yaxis_title="Taxa de Recorrência (%)",
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
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig_mensal.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)',
        tickangle=-45
    )
    
    fig_mensal.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Enhanced table
    colunas_mensais = ["yearmonth", "retained_customers", "prev_total_customers", "retention_rate"]
    renomear_mensal = {
        "yearmonth": "Mês/Ano",
        "retained_customers": "Clientes Recorrentes",
        "prev_total_customers": "Novos Clientes",
        "retention_rate": "Taxa de Recorrência (%)",
    }
    df_mensal_filtrado = df_RC_Mensal[colunas_mensais]
    
    # Create visualization for customer counts
    fig_customers = px.bar(
        df_RC_Mensal,
        x='yearmonth',
        y=['retained_customers', 'prev_total_customers'],
        barmode="group",
        labels={"value": "Número de Clientes", "variable": "Tipo de Cliente", "yearmonth": "Mês/Ano", "prev_total_customers": "Novos Clientes"},
        color_discrete_map={
            'retained_customers': color['accent'],
            'prev_total_customers': color['secondary']
        },
        template='plotly_white'
    )
    
    fig_customers.update_layout(
        xaxis_title="Mês",
        yaxis_title="Número de Clientes",
        margin=dict(t=50, b=50, l=50, r=50),
        height=400,
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
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)',
        tickangle=-45
    )
    
    fig_customers.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Rename traces
    for trace in fig_customers.data:
        if trace.name == 'retained_customers':
            trace.name = "Clientes Recorrentes"
        elif trace.name == 'prev_total_customers':
            trace.name = "Novos Clientes"
    
    # Layout with cards
    layout = html.Div([
        html.H2("Recorrência Mensal", className="dashboard-title"),
        
        # Summary metrics row
        metrics_row,
        
        # Retention rate chart
        create_card(
            "Taxa de Recorrência Mensal (%)",
            dcc.Graph(id='recorrencia-mensal-graph', figure=fig_mensal, config={"responsive": True})
        ),
        
        # Customer counts chart
        create_card(
            "Composição de Clientes por Mês",
            dcc.Graph(id='recorrencia-mensal-customers', figure=fig_customers, config={"responsive": True})
        ),
        
        # Table with metrics
        create_card(
            "Métricas Mensais Detalhadas",
            dash_table.DataTable(
                id='table-recorrencia-mensal',
                columns=[{"name": renomear_mensal.get(col, col), "id": col} for col in colunas_mensais],
                data=df_mensal_filtrado.to_dict("records"),
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