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
        if 'Evolucao Total (%)' not in df_fat.columns:
            df_fat['Evolucao Total (%)'] = df_fat['Total'].pct_change() * 100
        
        df_fat['label'] = df_fat.apply(lambda row: f"{formatar_percentual(row['Evolucao Total (%)'])}\n{formatar_moeda(row['Total'])}" 
                                    if not pd.isna(row['Evolucao Total (%)']) else f"{formatar_moeda(row['Total'])}", axis=1)
        
        # Calculate YoY growth for the metrics row
        total_sales = df_fat['Total'].iloc[-1] if not df_fat.empty else 0
        
        # Obter o faturamento do mês atual até o último dia de venda
        # Precisamos verificar se temos os dados do mês atual no df_mensal
        # Assumindo que temos acesso ao df_mensal neste ponto
        current_month_sales = 0
        try:
            df_mensal = pd.read_json(io.StringIO(data["df_fat_Mensal"]), orient='split')
            
            # Identificar o último ano com dados
            anos_colunas = [col for col in df_mensal.columns if col != 'Mês' and not pd.isna(col)]
            if anos_colunas:
                ultimo_ano = max(anos_colunas)
                
                # Encontrar o último mês com valor não nulo para o último ano
                ultimo_valor = None
                ultimo_mes = None
                
                for index, row in df_mensal.iterrows():
                    if not pd.isna(row[ultimo_ano]) and row[ultimo_ano] != 0:
                        ultimo_valor = row[ultimo_ano]
                        ultimo_mes = row['Mês']
                
                if ultimo_valor is not None:
                    current_month_sales = ultimo_valor
                    print(f"Último valor encontrado: {current_month_sales} para o mês {ultimo_mes} de {ultimo_ano}")
                    
        except Exception as e:
            print(f"Erro ao obter faturamento do mês atual: {e}")
            current_month_sales = 0
        
        # Handle NaN values
        if pd.isna(current_month_sales): current_month_sales = 0
        
        # Handle NaN values
        if pd.isna(current_month_sales): current_month_sales = 0
        
        # Calcular ticket médio de produtos e serviços se os dados existirem
        ticket_medio_produtos = None
        ticket_medio_servicos = None
        
        # Verificar se temos dados de produtos e serviços
        if ('Produtos' in df_fat.columns and 'Serviços' in df_fat.columns and
            'Qtd Produtos' in df_fat.columns and 'Qtd Serviços' in df_fat.columns):
            try:
                # Filtramos para o ano mais recente não vazio
                df_fat_atual = df_fat.sort_values('Ano', ascending=False)
                
                # Encontrar a primeira linha com valores válidos para produtos
                for i, row in df_fat_atual.iterrows():
                    if not pd.isna(row['Produtos']) and not pd.isna(row['Qtd Produtos']) and row['Qtd Produtos'] > 0:
                        ticket_medio_produtos = row['Produtos'] / row['Qtd Produtos']
                        break
                        
                # Encontrar a primeira linha com valores válidos para serviços
                for i, row in df_fat_atual.iterrows():
                    if not pd.isna(row['Serviços']) and not pd.isna(row['Qtd Serviços']) and row['Qtd Serviços'] > 0:
                        ticket_medio_servicos = row['Serviços'] / row['Qtd Serviços']
                        break
                        
            except Exception as e:
                print(f"Erro ao calcular ticket médio: {e}")
        
        # Criar a lista de métricas base
        metrics = [
            {"title": "Faturamento Total (Ano Atual)", "value": formatar_moeda(total_sales), "color": color['accent']},
            {"title": "Faturamento Mês Atual", "value": formatar_moeda(current_month_sales), "color": color['success']}
        ]
        
        # Adicionar métricas de ticket médio se disponíveis
        if ticket_medio_produtos is not None:
            metrics.append({
                "title": "Ticket Médio Produtos", 
                "value": formatar_moeda(ticket_medio_produtos), 
                "color": color['warning']
            })
        
        if ticket_medio_servicos is not None:
            metrics.append({
                "title": "Ticket Médio Serviços", 
                "value": formatar_moeda(ticket_medio_servicos), 
                "color": color['neutral']
            })
        
        metrics_row = create_metric_row(metrics)
        
                # Verificar se temos dados de produtos e serviços para criar gráfico de barras empilhadas
        has_product_service = 'Produtos' in df_fat.columns and 'Serviços' in df_fat.columns

        if has_product_service:
            # Gráfico empilhado com Produtos e Serviços
            fig_fat = go.Figure()
            
            # Adicionar barras para serviços
            fig_fat.add_trace(go.Bar(
                x=df_fat['Ano'],
                y=df_fat['Serviços'],
                name='Serviços',
                text=df_fat['Serviços'].apply(formatar_moeda),
                textposition='inside',
                insidetextanchor='middle',
                marker_color=color['secondary'],
                hovertemplate='Serviços: %{text}<extra></extra>'
            ))
            
            # Adicionar barras para produtos
            fig_fat.add_trace(go.Bar(
                x=df_fat['Ano'],
                y=df_fat['Produtos'],
                name='Produtos',
                text=df_fat['Produtos'].apply(formatar_moeda),
                textposition='inside',
                insidetextanchor='middle',
                marker_color=color['accent'],
                hovertemplate='Produtos: %{text}<extra></extra>'
            ))
            
            # Adicionar total e evolução como anotação no topo das barras
            for i, row in df_fat.iterrows():
                total = row['Total']
                evolucao = row['Evolucao Total (%)']
                
                # Adicionar anotação para o total
                fig_fat.add_annotation(
                    x=row['Ano'],
                    y=total,
                    text=formatar_moeda(total),
                    showarrow=False,
                    yshift=15,
                    font=dict(size=12, family="Montserrat", color="black", weight="bold")
                )
        
                # Adicionar anotação para a evolução percentual acima do total
                if not pd.isna(evolucao):
                    fig_fat.add_annotation(
                        x=row['Ano'],
                        y=total,
                        text=formatar_percentual(evolucao),
                        showarrow=False,
                        yshift=35,  # Posição acima do valor total
                        font=dict(
                            size=12, 
                            family="Montserrat", 
                            color=color['success'] if evolucao >= 0 else color['danger']
                        )
                    )
            
            # Configuração do layout
            fig_fat.update_layout(
                barmode='stack',
                xaxis_title="Ano",
                yaxis_title="Faturamento (R$)",
                margin=dict(t=70, b=50, l=50, r=50),  # Aumentei o margin-top para acomodar as anotações
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
            
        else:
            # Para o caso quando não temos dados de produtos e serviços
            fig_fat = px.bar(
                df_fat,
                x='Ano',
                y='Total',  # Usamos Total diretamente
                color_discrete_sequence=[color['secondary']],
                template='plotly_white'
            )
            
            # Adicionar anotações para total e evolução
            for i, row in df_fat.iterrows():
                total = row['Total']
                evolucao = row['Evolucao Total (%)'] if 'Evolucao Total (%)' in df_fat.columns else None
                
                # Anotação para o valor total
                fig_fat.add_annotation(
                    x=row['Ano'],
                    y=total,
                    text=formatar_moeda(total),
                    showarrow=False,
                    yshift=10,
                    font=dict(size=12, family="Montserrat", color="black")
                )
                
                # Anotação para a evolução percentual acima do total
                if evolucao is not None and not pd.isna(evolucao):
                    fig_fat.add_annotation(
                        x=row['Ano'],
                        y=total,
                        text=formatar_percentual(evolucao),
                        showarrow=False,
                        yshift=30,  # Posição acima do valor total
                        font=dict(
                            size=12, 
                            family="Montserrat", 
                            color=color['success'] if evolucao >= 0 else color['danger']
                        )
                    )
            
            fig_fat.update_layout(
                margin=dict(t=70, b=50, l=50, r=50),
                height=500,
                hovermode="x unified"
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
        custom_colors = ["orange", "darkred", gradient_colors['blue_gradient'][0], color['accent'], gradient_colors['green_gradient'][1], "red", "purple", gradient_colors['blue_gradient'][2]]
        
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

