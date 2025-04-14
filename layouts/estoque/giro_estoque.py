import io
import pandas as pd
import datetime
from dash import html, dcc
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from utils import create_card, content_style

def get_giro_estoque_layout(data):
    """
    Cria o layout da página de produtos inativos com gráficos e tabelas interativas
    para análise de produtos que não são vendidos há um determinado período.
    """
    if data.get("df_analise_giro") is None:
        return html.Div([
            html.H2("Análise de Produtos Inativos", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de produtos para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo analise_giro_completa.xlsx está presente no diretório de dados",  
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    # Carregar os dados do DataFrame
    df_giro_estoque = pd.read_json(io.StringIO(data["df_analise_giro"]), orient='split')
    
    # Supondo que o DataFrame df_giro_estoque já tenha as colunas necessárias:
    # classificacao_giro, cobertura_dias, classe_abc
    
    # Gráfico 1: Distribuição de Giro (Pizza)
    classificacao_counts = df_giro_estoque['classificacao_giro'].value_counts().reset_index()
    classificacao_counts.columns = ['classificacao_giro', 'count']
    
    fig_pie = px.pie(
        classificacao_counts, 
        values='count', 
        names='classificacao_giro',
        title='Distribuição de Produtos por Classificação de Giro',
        color_discrete_sequence=px.colors.sequential.Viridis,
        hover_data=['count']
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Produtos: %{value}<br>Porcentagem: %{percent}'
    )
    
    fig_pie.update_layout(
        legend_title='Classificação',
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    # Gráfico 2: Distribuição de Cobertura (Histograma)
    df_cobertura = df_giro_estoque[(df_giro_estoque['cobertura_dias'].notnull()) & 
                                  (df_giro_estoque['cobertura_dias'] <= 365)].copy()
    
    fig_hist = px.histogram(
        df_cobertura,
        x='cobertura_dias',
        nbins=30,
        title='Distribuição de Produtos por Cobertura de Estoque',
        labels={'cobertura_dias': 'Cobertura de Estoque (Dias)'},
        marginal='box'
    )
    
    # Adicionar linhas de referência
    fig_hist.add_vline(x=30, line_dash="dash", line_color="red",
                       annotation_text="1 mês", annotation_position="top right")
    fig_hist.add_vline(x=90, line_dash="dash", line_color="orange",
                      annotation_text="3 meses", annotation_position="top right")
    fig_hist.add_vline(x=180, line_dash="dash", line_color="green",
                      annotation_text="6 meses", annotation_position="top right")
    
    fig_hist.update_layout(
        xaxis_title='Cobertura de Estoque (Dias)',
        yaxis_title='Número de Produtos',
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    # Gráfico 3: ABC vs Giro (Heatmap)
    cross_table = pd.crosstab(df_giro_estoque['classe_abc'], df_giro_estoque['classificacao_giro'])
    
    fig_heatmap = px.imshow(
        cross_table,
        text_auto=True,
        labels=dict(x='Classificação de Giro', y='Classe ABC', color='Número de Produtos'),
        color_continuous_scale='YlGnBu',
        aspect="auto",
        title='Relação entre Classe ABC e Classificação de Giro'
    )
    
    fig_heatmap.update_layout(
        margin=dict(t=50, b=0, l=0, r=0)
    )
    
    # Montando o layout final com os três gráficos
    return html.Div([
        html.H2("Análise de Giro de Estoque", className="dashboard-title"),
        
        # Primeira linha com o gráfico de pizza
        html.Div([
            create_card(
                "Distribuição de Produtos por Classificação de Giro",
                dcc.Graph(figure=fig_pie, id='grafico-giro-pizza')
            )
        ], className="row mb-4"),
        
        # Segunda linha com o histograma de cobertura
        html.Div([
            create_card(
                "Distribuição de Produtos por Cobertura de Estoque",
                dcc.Graph(figure=fig_hist, id='grafico-cobertura-hist')
            )
        ], className="row mb-4"),
        
        # Terceira linha com o heatmap ABC vs Giro
        html.Div([
            create_card(
                "Relação entre Classe ABC e Classificação de Giro",
                dcc.Graph(figure=fig_heatmap, id='grafico-abc-giro-heatmap')
            )
        ], className="row mb-4"),
        
    ], style=content_style)



