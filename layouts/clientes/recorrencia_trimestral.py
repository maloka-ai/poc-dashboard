import io
import pandas as pd
import plotly.express as px
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import numpy as np

from utils import formatar_numero, formatar_percentual
from utils import create_card, create_metric_row, content_style, color

def get_recorrencia_trimestral_layout(data):
    if data.get("df_RC_Trimestral") is None:
        return html.Div([
            html.H2("Recorrência Trimestral", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de recorrência trimestral para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-calendar-check fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo metricas_recorrencia_trimestral.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_RC_Trimestral = pd.read_json(io.StringIO(data["df_RC_Trimestral"]), orient='split')
    
    # Calculate metrics for the metrics row
    current_rate = df_RC_Trimestral['recurrence_rate'].iloc[-1] if not df_RC_Trimestral.empty else 0
    avg_rate = df_RC_Trimestral['recurrence_rate'].mean()
    max_rate = df_RC_Trimestral['recurrence_rate'].max()
    
    rate_change = df_RC_Trimestral['recurrence_rate'].iloc[-1] - df_RC_Trimestral['recurrence_rate'].iloc[-2] if len(df_RC_Trimestral) > 1 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Taxa de Recorrência Atual", "value": formatar_percentual(current_rate), "change": rate_change, "color": color['accent']},
        {"title": "Média de Recorrência", "value": formatar_percentual(avg_rate), "color": color['secondary']},
        {"title": "Maior Taxa", "value": formatar_percentual(max_rate), "color": color['success']},
        {"title": "Total de Clientes (Último Trimestre)", "value": formatar_numero(df_RC_Trimestral['total_customers'].iloc[-1]), "color": color['primary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced trimestral retention line chart
    fig_trimestral_line = px.line(
        df_RC_Trimestral, 
        x='trimestre', 
        y='recurrence_rate', 
        markers=True, 
        color_discrete_sequence=[color['secondary']],
        labels={'recurrence_rate': 'Taxa de Recorrência (%)', 'trimestre': 'Trimestre'},  # Renomeia os rótulos no hover
        template='plotly_white'
    )

    # # Customizar ainda mais o hover
    # fig_trimestral_line.update_traces(
    #     hovertemplate='<b>%{x}</b><br>Taxa de Recorrência: %{y:.1f}%<extra></extra>',
    #     name='Taxa de Recorrência'  # Renomeia o nome da série na legenda
    # )
    
    # Add thicker line and bigger markers
    fig_trimestral_line.update_traces(
        line=dict(width=3),
        marker=dict(size=10, line=dict(width=2, color='white'))
    )
    
    # # Add a target line at 35%
    # fig_trimestral_line.add_shape(
    #     type="line",
    #     x0=df_RC_Trimestral['trimestre'].iloc[0],
    #     y0=35,
    #     x1=df_RC_Trimestral['trimestre'].iloc[-1],
    #     y1=35,
    #     line=dict(
    #         color=color['success'],
    #         width=2,
    #         dash="dot",
    #     )
    # )
    
    # fig_trimestral_line.add_annotation(
    #     x=df_RC_Trimestral['trimestre'].iloc[-1],
    #     y=35,
    #     text="Meta (35%)",
    #     showarrow=False,
    #     yshift=10,
    #     xshift=30,
    #     font=dict(size=12, color=color['success'])
    # )
    
    fig_trimestral_line.update_layout(
        xaxis_title="Trimestre", 
        yaxis_title="Taxa de Recorrência (%)", 
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
    
    fig_trimestral_line.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    fig_trimestral_line.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Enhanced customer composition chart
    fig_trimestral_bar = px.bar(
        df_RC_Trimestral, 
        x='trimestre', 
        y=['new_customers', 'returning_customers'], 
        barmode="stack",
        labels={"value": "Número de Clientes", "variable": "Tipo de Cliente"},
        color_discrete_map={
            'new_customers': color['accent'],
            'returning_customers': color['secondary']
        },
        template='plotly_white'
    )
    
    # Add percentages as text on the bars
    total_customers = df_RC_Trimestral['new_customers'] + df_RC_Trimestral['returning_customers']
    new_pct = (df_RC_Trimestral['new_customers'] / total_customers * 100).round(1)
    ret_pct = (df_RC_Trimestral['returning_customers'] / total_customers * 100).round(1)
    
    # Custom data for hover
    fig_trimestral_bar.update_traces(
        customdata=np.vstack((
            df_RC_Trimestral['new_customers'] if len(fig_trimestral_bar.data) > 0 and fig_trimestral_bar.data[0].name == 'new_customers' else df_RC_Trimestral['returning_customers'],
            new_pct if len(fig_trimestral_bar.data) > 0 and fig_trimestral_bar.data[0].name == 'new_customers' else ret_pct
        )).T,
        hovertemplate='%{y} clientes (%{customdata[1]:.1f}%)<extra>%{fullData.name}</extra>'
    )
    
    fig_trimestral_bar.update_layout(
        xaxis_title="Trimestre", 
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
    
    fig_trimestral_bar.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    fig_trimestral_bar.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Rename traces for better readability
    for trace in fig_trimestral_bar.data:
        if trace.name == 'new_customers':
            trace.name = "Novos Clientes"
        elif trace.name == 'returning_customers':
            trace.name = "Clientes Recorrentes"
        
        # Add count text
        text_values = []
        for value in trace.y:
            if value > 0:
                text_values.append(f"{int(value)}")
            else:
                text_values.append("")
        
        trace.text = text_values
        trace.textposition = 'inside'
        trace.textfont = dict(family="Montserrat", size=12, color="white")
    
    # Table with detailed metrics
    colunas_trimestrais = ["trimestre", "total_customers", "returning_customers", "new_customers", "recurrence_rate"]
    renomear_trimestral = {
        "trimestre": "Trimestre",
        "total_customers": "Total de Clientes",
        "returning_customers": "Clientes Recorrentes",
        "new_customers": "Novos Clientes",
        "recurrence_rate": "Taxa de Recorrência (%)",
    }
    df_trimestral_filtrado = df_RC_Trimestral[colunas_trimestrais]
    
    # Layout with cards
    layout = html.Div([
        html.H2("Recorrência Trimestral", className="dashboard-title"),
        
        # Summary metrics row
        metrics_row,
        
        # Charts in row
        dbc.Row([
            dbc.Col(
                create_card(
                    "Taxa de Recorrência Trimestral",
                    dcc.Graph(id='recorrencia-trimestral-line', figure=fig_trimestral_line, config={"responsive": True})
                ),
                lg=6, md=12
            ),
            dbc.Col(
                create_card(
                    "Composição de Clientes por Trimestre",
                    dcc.Graph(id='recorrencia-trimestral-bar', figure=fig_trimestral_bar, config={"responsive": True})
                ),
                lg=6, md=12
            )
        ], className="mb-4"),
        
        # Table with detailed metrics
        create_card(
            "Métricas Trimestrais Detalhadas",
            dash_table.DataTable(
                id='table-recorrencia-trimestral',
                columns=[
                    {"name": renomear_trimestral.get(col, col), "id": col}
                    for col in colunas_trimestrais
                ],
                data=df_trimestral_filtrado.to_dict("records"),
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
                        "if": {"column_id": "recurrence_rate"},
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