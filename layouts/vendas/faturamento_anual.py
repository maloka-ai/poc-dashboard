import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc

from utils import formatar_moeda, formatar_percentual
from utils import create_card, create_metric_row, content_style, color, gradient_colors

def get_faturamento_anual_layout(data, selected_client=None):
    try:
        # -------------------------------------------------------
        # --- Gráfico 1: Evolução Percentual Anual das Vendas ---
        # -------------------------------------------------------
        if data.get("df_fat_Anual") is None:
            return html.Div([
                html.H2("Crescimento do Negócio", className="dashboard-title"),
                create_card(
                    "Dados Indisponíveis",
                    html.Div([
                        html.P("Não foram encontrados dados de faturamento para este cliente.", className="text-center text-muted my-4"),
                        html.I(className="fas fa-chart-line fa-4x text-muted d-block text-center mb-3"),
                        html.P("Verifique se os arquivos necessários estão presentes: faturamento_anual.xlsx, faturamento_anual_geral.xlsx, faturamento_mensal.xlsx", 
                               className="text-muted text-center")
                    ])
                )
            ], style=content_style)
        
        df_fat = pd.read_json(io.StringIO(data["df_fat_Anual"]), orient='split')
        df_fat = df_fat.sort_values("Ano")
        
        # Verificar se já temos a coluna de evolução, senão calculá-la
        if 'Evolucao (%)' not in df_fat.columns:
            df_fat['Evolucao (%)'] = df_fat['total_item'].pct_change() * 100
        
        df_fat['label'] = df_fat.apply(lambda row: f"{formatar_percentual(row['Evolucao (%)'])}\n{formatar_moeda(row['total_item'])}" 
                                    if not pd.isna(row['Evolucao (%)']) else f"{formatar_moeda(row['total_item'])}", axis=1)
        
        # Calculate YoY growth for the metrics row
        last_year_growth = df_fat['Evolucao (%)'].iloc[-1] if len(df_fat) > 1 and not df_fat.empty else 0
        total_sales = df_fat['total_item'].iloc[-1] if not df_fat.empty else 0
        avg_growth = df_fat['Evolucao (%)'].mean() if len(df_fat) > 1 else 0
        
        # Handle NaN values
        if pd.isna(last_year_growth): last_year_growth = 0
        if pd.isna(avg_growth): avg_growth = 0
        
        # Create metrics row
        metrics = [
            {"title": "Faturamento Total (Último Ano)", "value": formatar_moeda(total_sales), "color": color['accent']},
            {"title": "Crescimento Anual", "value": formatar_percentual(last_year_growth), "change": last_year_growth, "color": color['secondary']},
            {"title": "Média de Crescimento", "value": formatar_percentual(avg_growth), "color": color['success']}
        ]
        
        metrics_row = create_metric_row(metrics)
        
        # Enhanced growth chart
        fig_fat = px.bar(
            df_fat,
            x='Ano',
            y='Evolucao (%)',
            text='label',
            color_discrete_sequence=[color['secondary']],
            template='plotly_white'
        )
        
        fig_fat.update_xaxes(
            tickmode='array', 
            tickvals=df_fat['Ano'].unique(),
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_fat.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_fat.update_layout(
            xaxis_title="Ano",
            yaxis_title="Crescimento (%)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
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
        
        fig_fat.update_traces(
            textposition='outside', 
            textfont=dict(size=12, family="Montserrat"),
            selector=dict(type='bar')  # Aplicar apenas aos traces de tipo barra
        )

        # ------------------------------------------
        # --- Gráfico 2: Faturamento Anual ---------
        # ------------------------------------------

        df_ano = pd.read_json(io.StringIO(data["df_fat_Anual_Geral"]), orient='split')
        if df_ano.index.name == 'Ano' or (hasattr(df_ano.index, 'name') and df_ano.index.name is not None):
            # Se o índice for nomeado 'Ano', transforme-o em coluna
            df_ano = df_ano.reset_index()
        elif 'Ano' not in df_ano.columns:
            # Se não tiver coluna 'Ano', primeiro tente verificar se o índice tem valores que podem ser anos
            if df_ano.index.dtype in ['int64', 'float64'] and df_ano.index.min() >= 2000:
                # Parece que o índice contém anos, vamos usá-lo
                df_ano['Ano'] = df_ano.index
                df_ano = df_ano.reset_index(drop=True)
            else:
                # Ou tente criar uma sequência de anos com base no número de registros
                anos_desejados = [2021, 2022, 2023, 2024, 2025][:len(df_ano)]
                # Verificar se temos anos suficientes na nossa lista
                if len(anos_desejados) < len(df_ano):
                    # Adicionar mais anos se necessário
                    anos_extras = list(range(anos_desejados[-1] + 1, anos_desejados[-1] + 1 + (len(df_ano) - len(anos_desejados))))
                    anos_desejados.extend(anos_extras)
                df_ano['Ano'] = anos_desejados

        is_bibi_data = (
        'Cadastrado' in df_ano.columns and 
        'Sem Cadastro' in df_ano.columns
        )
        if is_bibi_data:
            # Para BIBI: gráfico de barras empilhadas Cadastrado vs Sem Cadastro
            fig_ano = px.bar(
                df_ano,
                x='Ano',
                y=['Cadastrado', 'Sem Cadastro'],
                barmode='stack',
                labels={"value": "Faturamento (R$)", "variable": "Tipo de Cliente"},
                color_discrete_map={
                    'Cadastrado': '#1f77b4',
                    'Sem Cadastro': '#ff7f0e'
                },
                template='plotly_white'
            )
            
            # Configurar texto dentro das barras
            # Update: Usar texttemplate para mostrar valores dentro das barras
            for i, bar in enumerate(fig_ano.data):
                # Formatar valores para mostrar dentro das barras
                text_values = []
                for val in bar.y:
                    if val is not None and val > 0:
                        text_values.append(formatar_moeda(val))
                    else:
                        text_values.append("")
                
                # Aplicar texto dentro das barras
                fig_ano.data[i].text = text_values
                fig_ano.data[i].textposition = 'inside'
                fig_ano.data[i].insidetextanchor = 'middle'
                fig_ano.data[i].textfont = dict(
                    family="Montserrat",
                    size=12,
                    color="white"
                )
            
            # Adicionar rótulos de total no topo das barras
            for i in range(len(df_ano)):
                total = df_ano.iloc[i]['Cadastrado'] + df_ano.iloc[i]['Sem Cadastro']
                fig_ano.add_annotation(
                    x=df_ano['Ano'].iloc[i],
                    y=total,
                    text=f"Total: {formatar_moeda(total)}",
                    showarrow=False,
                    yshift=10,
                    font=dict(size=12, color="black", family="Montserrat", weight="bold")
                )
            
            # Título específico para BIBI
            titulo_grafico2 = "Faturamento Anual - Clientes Cadastrados vs Sem Cadastro"
            
        else:
            # Para outros clientes: gráfico de barras simples com total_item
            # Verificar se temos a coluna total_item
            if 'total_item' not in df_ano.columns:
                # Se tiver Cadastrado e Sem Cadastro, podemos calcular o total
                if 'Cadastrado' in df_ano.columns and 'Sem Cadastro' in df_ano.columns:
                    df_ano['total_item'] = df_ano['Cadastrado'] + df_ano['Sem Cadastro']
                else:
                    # Procurar outras colunas numéricas
                    potential_total_columns = [col for col in df_ano.columns if col not in ['Ano', 'index']]
                    if not potential_total_columns:
                        return html.Div([
                            html.H2("Crescimento do Negócio", className="dashboard-title"),
                            create_card(
                                "Formato de Dados Incompatível",
                                html.Div([
                                    html.P("Não foi possível identificar a coluna de faturamento nos dados anuais.", className="text-center text-muted my-4"),
                                    html.I(className="fas fa-exclamation-triangle fa-4x text-warning d-block text-center mb-3")
                                ])
                            )
                        ], style=content_style)
                    
                    # Usar a primeira coluna numérica
                    for col in potential_total_columns:
                        if pd.api.types.is_numeric_dtype(df_ano[col]):
                            df_ano['total_item'] = df_ano[col]
                            break
            
            # Gráfico de barras padrão para outros clientes
            fig_ano = px.bar(
                df_ano,
                x='Ano',
                y='total_item',
                color_discrete_sequence=[gradient_colors['blue_gradient'][1]],
                template='plotly_white'
            )
            
            # Add value annotations
            for i, row in df_ano.iterrows():
                fig_ano.add_annotation(
                    x=row['Ano'],
                    y=row['total_item'],
                    text=formatar_moeda(row['total_item']),
                    showarrow=False,
                    yshift=10,
                    font=dict(size=12, color="black", family="Montserrat")
                )
            
            # Título padrão para outros clientes
            titulo_grafico2 = "Faturamento Anual"
        
        # Configurações comuns para o gráfico 2
        fig_ano.update_layout(
            xaxis_title="Ano",
            yaxis_title="Faturamento (R$)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
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
        
        fig_ano.update_xaxes(
            tickmode='array', 
            tickvals=df_ano['Ano'].unique(),
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_ano.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )

        # ----------------------------------------------
        # --- Gráfico 3: Faturamento Mensal por Ano ----
        # ----------------------------------------------

        df_mensal = pd.read_json(io.StringIO(data["df_fat_Mensal"]), orient='split')
        if 'Mês' not in df_mensal.columns:
            df_mensal = df_mensal.reset_index(drop=True)
            # Se o número de linhas for 12, atribuimos os meses de 1 a 12; caso contrário, usamos o número de linhas existente
            if len(df_mensal) == 12:
                df_mensal['Mês'] = list(range(1, 13))
            else:
                df_mensal['Mês'] = list(range(1, len(df_mensal) + 1))
        
        df_mensal_long = df_mensal.melt(id_vars="Mês", var_name="Ano", value_name="Faturamento")
        
        # Enhanced monthly sales chart with custom colors
        custom_colors = ["orange", "darkred", color['secondary'], color['accent'], gradient_colors['green_gradient'][1], color['warning']]
        
        fig_mensal = px.bar(
            df_mensal_long,
            x="Mês",
            y="Faturamento",
            color="Ano",
            barmode="group",
            color_discrete_sequence=custom_colors,
            template='plotly_white'
        )
        
        # Define os rótulos dos meses e ajusta o range do eixo x para evitar que a primeira barra seja cortada
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        fig_mensal.update_layout(
            xaxis_title="Mês",
            yaxis_title="Faturamento (R$)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
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
            range=[0.5, 12.5],
            tickmode='array',
            tickvals=list(range(1, 13)),
            ticktext=meses,
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_mensal.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        # --- Layout final: três cards com os gráficos ---
        layout = html.Div([
            html.H2("Crescimento do Negócio", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # Card for annual growth rate
            create_card(
                "Evolução Percentual Anual das Vendas",
                dcc.Graph(figure=fig_fat, config={"responsive": True}),
            ),
            
            # Card for annual sales
            create_card(
                titulo_grafico2,
                dcc.Graph(figure=fig_ano, config={"responsive": True}),
            ),
            
            # Card for monthly sales by year
            create_card(
                "Faturamento Mensal por Ano",
                dcc.Graph(figure=fig_mensal, config={"responsive": True}),
            ),
        ], style=content_style)
        
        return layout
        
    except Exception as e:
        # Em caso de erro, exibir mensagem amigável e informações do erro
        return html.Div([
            html.H2("Crescimento do Negócio", className="dashboard-title"),
            
            create_card(
                "Erro ao carregar os dados",
                html.Div([
                    html.P("Ocorreu um problema ao carregar os dados de faturamento. Detalhes do erro:"),
                    html.Pre(str(e), style={"background": "#f8f9fa", "padding": "15px", "borderRadius": "5px", "whiteSpace": "pre-wrap"}),
                    html.P("Tente recarregar a página ou entre em contato com o suporte técnico.")
                ])
            )
        ], style=content_style)

