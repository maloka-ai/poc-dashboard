import io
import pandas as pd
import plotly.express as px
from dash import html, dcc
import plotly.graph_objects as go
import numpy as np

from utils import formatar_percentual
from utils import create_card, create_metric_row, content_style, color


def get_retencao_layout(data):
    try:
        if data.get("df_RT_Anual") is None:
            return html.Div([
                html.H2("Análise de Retenção Anual", className="dashboard-title"),
                create_card(
                    "Dados Indisponíveis",
                    html.Div([
                        html.P("Não foram encontrados dados de retenção anual para este cliente.", className="text-center text-muted my-4"),
                        html.I(className="fas fa-user-clock fa-4x text-muted d-block text-center mb-3"),
                        html.P("Verifique se o arquivo metricas_retencao_anual.xlsx está presente", 
                              className="text-muted text-center")
                    ])
                )
            ], style=content_style)
        
        df_RT_Anual = pd.read_json(io.StringIO(data["df_RT_Anual"]), orient='split')
        
        # Calculate metrics for the metrics row - ajustado para calcular apenas após o primeiro ano
        avg_retention = df_RT_Anual[(df_RT_Anual['period_index'] > 0) & ~pd.isna(df_RT_Anual['retention_rate'])]['retention_rate'].mean() * 100  # Apenas períodos > 0
        first_year_retention = df_RT_Anual[df_RT_Anual['period_index'] == 1]['retention_rate'].mean() * 100 if 1 in df_RT_Anual['period_index'].values else 0
        second_year_retention = df_RT_Anual[df_RT_Anual['period_index'] == 2]['retention_rate'].mean() * 100 if 2 in df_RT_Anual['period_index'].values else 0
        
        # Handle NaN values
        if pd.isna(avg_retention): avg_retention = 0
        if pd.isna(first_year_retention): first_year_retention = 0
        if pd.isna(second_year_retention): second_year_retention = 0
        
        # Create metrics row
        metrics = [
            {"title": "Retenção Média", "value": formatar_percentual(avg_retention), "color": color['primary']},
            {"title": "Retenção Primeiro Ano", "value": formatar_percentual(first_year_retention), "color": color['secondary']},
            {"title": "Retenção Segundo Ano", "value": formatar_percentual(second_year_retention), "color": color['accent']},
            {"title": "Diferença 1º-2º Ano", "value": formatar_percentual(first_year_retention - second_year_retention), 
             "change": second_year_retention - first_year_retention, "color": color['success']}
        ]
        
        metrics_row = create_metric_row(metrics)
        
        # Enhanced retention heatmap
        cohort_pivot = df_RT_Anual.pivot(
            index='cohort_year',
            columns='period_index', 
            values='retention_rate'
        )
        cohort_pivot = cohort_pivot * 100
        
        # Ensure index is integer and filter for valid years
        cohort_pivot.index = cohort_pivot.index.astype(int)
        
        # Create enhanced heatmap
        fig_retention = px.imshow(
            cohort_pivot,
            text_auto=False,
            aspect="auto",
            labels={
                "x": "Período (Anos desde a Primeira Compra)",
                "y": "Coorte (Ano da Primeira Compra)",
                "color": "Taxa de Retenção (%)"
            },
            x=cohort_pivot.columns,
            y=cohort_pivot.index,
            color_continuous_scale="YlGnBu",
            template='plotly_white'
        )
        
        annotations = []
        for i, y_val in enumerate(cohort_pivot.index):
            for j, x_val in enumerate(cohort_pivot.columns):
                value = cohort_pivot.iloc[i, j]
                if not np.isnan(value) and value is not None:
                    text_color = 'white' if value >= 95 else 'black'
                    
                    annotations.append(dict(
                        x=x_val,
                        y=y_val,
                        text=f'{value:.1f}%'.replace(".", ","),
                        showarrow=False,
                        font=dict(color=text_color, size=12, family="Montserrat")
                    ))

        # Remover texto automático
        fig_retention.data[0].text = None
        fig_retention.data[0].texttemplate = None

        # Adicionar anotações personalizadas
        fig_retention.update_layout(annotations=annotations)
        
        # Update layout
        fig_retention.update_layout(
            height=600,
            margin=dict(t=30, b=50, l=50, r=50),
            coloraxis_colorbar=dict(
                title=dict(
                    text="Retenção (%)",
                    side="right",
                    font=dict(size=14, family="Montserrat")
                ),
                ticks="outside",
                tickfont=dict(size=12, family="Montserrat")
            ),
            xaxis=dict(
                title="Período (Anos desde a Primeira Compra)",
                title_font=dict(size=14, family="Montserrat"),
                tickfont=dict(size=12, family="Montserrat")
            ),
            yaxis=dict(
                title="Coorte (Ano da Primeira Compra)",
                title_font=dict(size=14, family="Montserrat"),
                tickfont=dict(size=12, family="Montserrat")
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Update axes to show only the valid years and integers
        fig_retention.update_yaxes(
            tickmode='array',
            tickvals=cohort_pivot.index.tolist(),
            ticktext=[str(year) for year in cohort_pivot.index.tolist()]
        )
        
        fig_retention.update_xaxes(
            tickmode='linear',
            dtick=1
        )
        
        # Update text appearance
        fig_retention.update_traces(
            textfont=dict(size=12, family="Montserrat", color="black")
        )
        
        # Create cohort analysis line chart - verificar se há dados suficientes
        if len(df_RT_Anual['period_index'].unique()) > 0:
            retention_by_period = df_RT_Anual.groupby('period_index')['retention_rate'].mean() * 100
            fig_retention_curve = px.line(
                x=retention_by_period.index,
                y=retention_by_period.values,
                labels={"x": "Período (Anos)", "y": "Taxa de Retenção Média (%)"},
                markers=True,
                template='plotly_white'
            )
            
            fig_retention_curve.update_traces(
                line=dict(width=3, color=color['secondary']),
                marker=dict(size=10, color=color['secondary']),
                mode='lines+markers+text',
                text=[f"{val:.1f}%".replace(".", ",") for val in retention_by_period.values],
                textposition='top center',
                textfont=dict(family="Montserrat", size=12)
            )
            
            fig_retention_curve.update_layout(
                title="Curva de Retenção Média por Período",
                title_font=dict(size=16, family="Montserrat", color=color['primary']),
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                xaxis=dict(
                    title="Período (Anos desde a Primeira Compra)",
                    title_font=dict(size=14, family="Montserrat"),
                    tickvals=list(range(0, int(retention_by_period.index.max()) + 1)),
                    gridcolor='rgba(0,0,0,0.05)'
                ),
                yaxis=dict(
                    title="Taxa de Retenção Média (%)",
                    title_font=dict(size=14, family="Montserrat"),
                    gridcolor='rgba(0,0,0,0.05)'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        else:
            # Se não tiver dados suficientes, cria um gráfico placeholder
            fig_retention_curve = go.Figure()
            fig_retention_curve.add_annotation(
                x=0.5, y=0.5,
                text="Dados insuficientes para gerar a curva de retenção",
                showarrow=False,
                font=dict(size=14, family="Montserrat")
            )
            fig_retention_curve.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        
        # Layout with cards
        layout = html.Div(
            [
                html.H2("Análise de Retenção Anual", className="dashboard-title"),
                
                # Summary metrics row
                metrics_row,
                
                # Retention Heatmap
                create_card(
                    "Cohort Analysis - Taxa de Retenção (Anual)",
                    dcc.Graph(
                        id='retention-heatmap',
                        figure=fig_retention,
                        config={"responsive": True}
                    )
                ),
                
                # Retention Curve
                create_card(
                    "Curva de Retenção",
                    dcc.Graph(
                        id='retention-curve',
                        figure=fig_retention_curve,
                        config={"responsive": True}
                    )
                ),
                
                # Explanation card
                create_card(
                    "Como interpretar a Cohort Analysis",
                    html.Div([
                        html.P("A análise de coortes mostra a taxa de retenção de clientes ao longo do tempo, agrupados pelo ano de sua primeira compra."),
                        html.Ul([
                            html.Li("Cada linha representa uma coorte (grupo de clientes que começaram no mesmo ano)"),
                            html.Li("Cada coluna representa o período de tempo desde a primeira compra"),
                            html.Li("As células mostram a porcentagem de clientes que continuam comprando após o período indicado"),
                            html.Li("Cores mais escuras indicam taxas de retenção mais altas")
                        ]),
                        html.P("Esta visualização permite identificar quais coortes têm melhor desempenho a longo prazo e como evolui a retenção com o passar do tempo.")
                    ])
                )
            ],
            style=content_style,
        )
        
        return layout
        
    except Exception as e:
        # Em caso de erro, exibir mensagem amigável e informações do erro
        return html.Div([
            html.H2("Análise de Retenção Anual", className="dashboard-title"),
            
            create_card(
                "Erro ao carregar os dados",
                html.Div([
                    html.P("Ocorreu um problema ao carregar os dados de retenção. Detalhes do erro:"),
                    html.Pre(str(e), style={"background": "#f8f9fa", "padding": "15px", "borderRadius": "5px", "whiteSpace": "pre-wrap"}),
                    html.P("Tente recarregar a página ou entre em contato com o suporte técnico.")
                ])
            )
        ], style=content_style)