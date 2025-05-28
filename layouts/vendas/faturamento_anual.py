import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, dash_table
import traceback
import datetime

from utils import formatar_moeda, formatar_percentual
from utils import create_card, create_metric_row, content_style, color, gradient_colors

def get_faturamento_anual_layout(data, selected_client=None):
    # Dicionário para armazenar os gráficos que foram criados com sucesso
    graficos_processados = {
        "metricas": False,
        "grafico_evolucao_anual": False,
        "grafico_faturamento_anual": False,
        "grafico_faturamento_mensal": False,
        "grafico_faturamento_lojas": False,
        "grafico_faturamento_diario": False
    }

    tabela_processada = {
        "tabela_faturamento_diario": False,
    }
    
    # Variáveis de saída para os gráficos
    metrics_row = None
    fig_fat = None
    fig_ano = None
    fig_mensal = None
    grafico_lojas = None
    grafico_diario = None
    titulo_grafico2 = "Faturamento Anual"
    
    # Verificação inicial dos dados
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
    
    # -------------------------------------------------------
    # --- Gráfico 1: Evolução Percentual Anual das Vendas ---
    # -------------------------------------------------------
    try:
        df_fat = pd.read_json(io.StringIO(data["df_fat_Anual"]), orient='split')
        df_fat = df_fat.sort_values("Ano")
        
        # Verificar se já temos a coluna de evolução, senão calculá-la
        if 'Evolucao Total (%)' not in df_fat.columns:
            df_fat['Evolucao Total (%)'] = df_fat['Total'].pct_change() * 100
        
        df_fat['label'] = df_fat.apply(lambda row: f"{formatar_percentual(row['Evolucao Total (%)'])}\n{formatar_moeda(row['Total'])}" 
                                    if not pd.isna(row['Evolucao Total (%)']) else f"{formatar_moeda(row['Total'])}", axis=1)
        
        # Calculate YoY growth for the metrics row
        total_sales = df_fat['Total'].iloc[-1] if not df_fat.empty else 0
        
        # Verificar se temos dados de produtos e serviços para criar gráfico de barras empilhadas
        has_product_service = 'Faturamento em Produtos' in df_fat.columns and 'Faturamento em Serviços' in df_fat.columns

        if has_product_service:
            # Gráfico empilhado com Produtos e Serviços
            fig_fat = go.Figure()
            
            # Adicionar barras para serviços
            fig_fat.add_trace(go.Bar(
                x=df_fat['Ano'],
                y=df_fat['Faturamento em Serviços'],
                name='Serviços',
                text=df_fat['Faturamento em Serviços'].apply(formatar_moeda),
                textposition='inside',
                insidetextanchor='middle',
                marker_color=color['secondary'],
                hovertemplate='Serviços: %{text}<extra></extra>'
            ))
            
            # Adicionar barras para produtos
            fig_fat.add_trace(go.Bar(
                x=df_fat['Ano'],
                y=df_fat['Faturamento em Produtos'],
                name='Produtos',
                text=df_fat['Faturamento em Produtos'].apply(formatar_moeda),
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
        
        graficos_processados["grafico_evolucao_anual"] = True
    except Exception as e:
        print(f"Erro no processamento do Gráfico 1 (Evolução Percentual Anual): {e}")
        traceback.print_exc()
        graficos_processados["grafico_evolucao_anual"] = False
    
    # MÉTRICAS: Faturamento total, atual, ticket médio
    try:
        # Obter o faturamento do mês atual até o último dia de venda
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
        
        # Calcular ticket médio de produtos e serviços se os dados existirem
        ticket_medio_produtos = None
        ticket_medio_servicos = None
        
        # Verificar se temos dados de produtos e serviços
        if ('Faturamento em Produtos' in df_fat.columns and 'Faturamento em Serviços' in df_fat.columns and
            'Qtd Produtos' in df_fat.columns and 'Qtd Serviços' in df_fat.columns):
            try:
                # Filtramos para o ano mais recente não vazio
                df_fat_atual = df_fat.sort_values('Ano', ascending=False)
                
                # Encontrar a primeira linha com valores válidos para produtos
                for i, row in df_fat_atual.iterrows():
                    if not pd.isna(row['Faturamento em Produtos']) and not pd.isna(row['Qtd Produtos']) and row['Qtd Produtos'] > 0:
                        ticket_medio_produtos = row['Faturamento em Produtos'] / row['Qtd Produtos']
                        break
                        
                # Encontrar a primeira linha com valores válidos para serviços
                for i, row in df_fat_atual.iterrows():
                    if not pd.isna(row['Faturamento em Serviços']) and not pd.isna(row['Qtd Serviços']) and row['Qtd Serviços'] > 0:
                        ticket_medio_servicos = row['Faturamento em Serviços'] / row['Qtd Serviços']
                        break
                        
            except Exception as e:
                print(f"Erro ao calcular ticket médio: {e}")
        
        # Criar a lista de métricas base
        metrics = [
            {"title": "Faturamento Total (Ano Atual)", "value": formatar_moeda(total_sales), "color": color['accent'], "value_style": {"fontSize": "20px"}},
            {"title": "Faturamento Mês Atual", "value": formatar_moeda(current_month_sales), "color": color['success'], "value_style": {"fontSize": "20px"}}
        ]
        
        # Adicionar métricas de ticket médio se disponíveis
        if ticket_medio_produtos is not None:
            metrics.append({
                "title": "Valor Médio Produto", 
                "value": formatar_moeda(ticket_medio_produtos), 
                "color": color['warning'],
                "value_style": {"fontSize": "20px"}
            })
        
        if ticket_medio_servicos is not None:
            metrics.append({
                "title": "Valor Médio Serviço", 
                "value": formatar_moeda(ticket_medio_servicos), 
                "color": color['neutral'],
                "value_style": {"fontSize": "20px"}
            })

        # Obter o ano atual
        ano_atual = datetime.datetime.now().year

        # Filtrar o dataframe pelo ano atual antes de obter o ticket médio e a quantidade de vendas
        df_fat_atual = df_fat[df_fat['Ano'] == ano_atual] if not df_fat.empty and ano_atual in df_fat['Ano'].values else (df_fat.iloc[-1:] if not df_fat.empty else pd.DataFrame())

        # Verificar se temos a quantidade de vendas disponível
        qtd_vendas = df_fat_atual['Qtd Vendas'].iloc[0] if not df_fat_atual.empty and 'Qtd Vendas' in df_fat_atual.columns else None

        # Adicionar a métrica com a quantidade de tickets entre parênteses
        metrics.append({
            "title": f"Ticket Médio Ano Atual ({int(qtd_vendas):,} tickets)" if qtd_vendas is not None else "Ticket Médio Ano Atual",
            "value": formatar_moeda(df_fat_atual['Ticket Médio Anual'].iloc[0]) if not df_fat_atual.empty and 'Ticket Médio Anual' in df_fat_atual.columns else "N/A",
            "color": color['primary'],
            "value_style": {"fontSize": "20px"}
        })
        
        metrics_row = create_metric_row(metrics)
        graficos_processados["metricas"] = True
    except Exception as e:
        print(f"Erro no processamento das métricas: {e}")
        traceback.print_exc()
        graficos_processados["metricas"] = False
    
    # ------------------------------------------
    # --- Gráfico 2: Faturamento Anual ---------
    # ------------------------------------------
    try:
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
            
            # Preparar os valores formatados para o hover
            df_ano['Cadastrado_Formatado'] = df_ano['Cadastrado'].apply(formatar_moeda)
            df_ano['SemCadastro_Formatado'] = df_ano['Sem Cadastro'].apply(formatar_moeda)
            df_ano['Total_Formatado'] = (df_ano['Cadastrado'] + df_ano['Sem Cadastro']).apply(formatar_moeda)
            
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
                template='plotly_white',
                custom_data=[df_ano['Cadastrado_Formatado'], df_ano['SemCadastro_Formatado'], df_ano['Total_Formatado']]
            )
            
            # Configurar o hovertemplate para cada trace
            for i, trace in enumerate(fig_ano.data):
                if i == 0:  # Cadastrado
                    trace.hovertemplate = '<b>Ano:</b> %{x}<br><b>Cadastrado:</b> %{customdata[0]}<br><b>Total:</b> %{customdata[2]}<extra></extra>'
                else:  # Sem Cadastro
                    trace.hovertemplate = '<b>Ano:</b> %{x}<br><b>Sem Cadastro:</b> %{customdata[1]}<br><b>Total:</b> %{customdata[2]}<extra></extra>'
            
            # Configurar texto dentro das barras
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
                        raise ValueError("Não foi possível identificar a coluna de faturamento nos dados anuais.")
                    
                    # Usar a primeira coluna numérica
                    for col in potential_total_columns:
                        if pd.api.types.is_numeric_dtype(df_ano[col]):
                            df_ano['total_item'] = df_ano[col]
                            break
            
            # Adicionar valores formatados para o hover
            df_ano['total_formatado'] = df_ano['total_item'].apply(formatar_moeda)
            
            # Gráfico de barras padrão para outros clientes
            fig_ano = px.bar(
                df_ano,
                x='Ano',
                y='total_item',
                color_discrete_sequence=[gradient_colors['blue_gradient'][1]],
                template='plotly_white',
                custom_data=['total_formatado']  # Adicionar o valor formatado aos dados personalizados
            )
            
            # Configurar o hovertemplate para mostrar o valor formatado
            fig_ano.update_traces(
                hovertemplate='<b>Ano:</b> %{x}<br><b>Faturamento:</b> %{customdata[0]}<extra></extra>'
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
        
        graficos_processados["grafico_faturamento_anual"] = True
    except Exception as e:
        print(f"Erro no processamento do Gráfico 2 (Faturamento Anual): {e}")
        traceback.print_exc()
        graficos_processados["grafico_faturamento_anual"] = False
    
    # ----------------------------------------------
    # --- Gráfico 3: Faturamento Mensal por Ano ----
    # ----------------------------------------------
    try:
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
        custom_colors = ["orange", "darkred", gradient_colors['blue_gradient'][0], color['accent'], gradient_colors['green_gradient'][0], "red", gradient_colors['blue_gradient'][2], gradient_colors['green_gradient'][2]]
        
        df_mensal_long['Faturamento_Formatado'] = df_mensal_long['Faturamento'].apply(formatar_moeda)
        
        fig_mensal = px.bar(
            df_mensal_long,
            x="Mês",
            y="Faturamento",
            color="Ano",
            barmode="group",
            color_discrete_sequence=custom_colors,
            template='plotly_white',
            custom_data=['Ano', 'Faturamento_Formatado']  # Adicionamos o valor formatado aos dados personalizados
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

        # Agora o hovertemplate usará o valor formatado
        fig_mensal.update_traces(
            hovertemplate='<b>Mês:</b> %{x}<br><b>Ano:</b> %{customdata[0]}<br><b>Faturamento:</b> %{customdata[1]}<extra></extra>',
            textfont=dict(size=10)
        )
        
        graficos_processados["grafico_faturamento_mensal"] = True
    except Exception as e:
        print(f"Erro no processamento do Gráfico 3 (Faturamento Mensal por Ano): {e}")
        traceback.print_exc()
        graficos_processados["grafico_faturamento_mensal"] = False
    
    # ------------------------------------------------------
    # --- Gráfico 4: Faturamento Mensal por Ano por loja ---
    # ------------------------------------------------------
    try:
        df_mensal_lojas = pd.read_json(io.StringIO(data["df_fat_Mensal_lojas"]), orient='split')
        if 'Mês' not in df_mensal_lojas.columns:
            df_mensal_lojas = df_mensal_lojas.reset_index(drop=True)
            # Se o número de linhas for 12, atribuimos os meses de 1 a 12; caso contrário, usamos o número de linhas existente
            if len(df_mensal_lojas) == 12:
                df_mensal_lojas['Mês'] = list(range(1, 13))
            else:
                df_mensal_lojas['Mês'] = list(range(1, len(df_mensal) + 1))

        # Converter valores de faturamento para numérico (caso estejam como string)
        df_mensal_lojas['total_venda'] = pd.to_numeric(df_mensal_lojas['total_venda'].astype(str).str.replace(',', '.'), errors='coerce')

        # Obter a lista de anos disponíveis para o dropdown
        anos_disponiveis = sorted(df_mensal_lojas['Ano'].unique())
        ano_default = anos_disponiveis[-1] if anos_disponiveis else None  # Selecionar o último ano como padrão

        # Dados filtrados para o ano padrão
        df_filtrado = df_mensal_lojas[df_mensal_lojas['Ano'] == ano_default] if ano_default else pd.DataFrame()

        # Verificar se existem valores duplicados na combinação Mês/Loja
        if not df_filtrado.empty:
            duplicated = df_filtrado.duplicated(subset=['Mês', 'id_loja'], keep=False)
            if duplicated.any():
                df_filtrado = df_filtrado.groupby(['Mês', 'id_loja'], as_index=False).agg({'total_venda': 'sum'})
        
        cores_fixas_lojas = {
            1: "orange",
            2: "darkred",
            3: gradient_colors['blue_gradient'][0],
            4: gradient_colors['green_gradient'][0],
            5: color['accent'],
            6: gradient_colors['blue_gradient'][2],
            7: gradient_colors['green_gradient'][2],
        }
        
        # Usar cores fixas se a loja estiver no dicionário, ou gerar cores dinâmicas para outras lojas
        lojas_unicas = df_mensal_lojas['id_loja'].unique()
        cores_lojas = {}
        
        for loja in lojas_unicas:
            if isinstance(loja, (int, float)) and int(loja) in cores_fixas_lojas:
                cores_lojas[loja] = cores_fixas_lojas[int(loja)]
            elif str(loja).isdigit() and int(str(loja)) in cores_fixas_lojas:
                cores_lojas[loja] = cores_fixas_lojas[int(str(loja))]
            else:
                # Usar um índice no conjunto de cores padrão do Plotly para lojas não mapeadas
                indice_cor = list(lojas_unicas).index(loja) % len(px.colors.qualitative.Bold)
                cores_lojas[loja] = px.colors.qualitative.Bold[indice_cor]
        
        # Criar figura para o gráfico de barras usando o Graph Objects para mais controle
        fig_lojas = go.Figure()
        
        # Adicionar barras para cada loja separadamente (semelhante ao gráfico mensal)
        for loja in df_filtrado['id_loja'].unique():
            df_loja = df_filtrado[df_filtrado['id_loja'] == loja]
            
            # Aqui assumimos que existe uma coluna 'nome' no df_filtrado
            nome_loja = df_loja['nome'].iloc[0] if 'nome' in df_loja.columns and not df_loja.empty else f"Loja {loja}"
            
            # Formatar os valores para exibição
            valores_formatados = df_loja['total_venda'].apply(formatar_moeda)
            
            fig_lojas.add_trace(go.Bar(
                x=df_loja['Mês'],
                y=df_loja['total_venda'],
                name=nome_loja,
                marker_color=cores_lojas.get(loja, '#333333'),
                hovertemplate=f'Loja {nome_loja}: %{valores_formatados}<extra></extra>'
            ))
        
        # Configurar layout do gráfico
        fig_lojas.update_layout(
            barmode='group',  # Forçar agrupamento
            xaxis_title="Mês",
            yaxis_title="Faturamento (R$)",
            margin=dict(t=70, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
            # Melhorando a legenda
            legend=dict(
                orientation="h",  # Orientação horizontal
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title_text="Lojas:",
                font=dict(size=12),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.1)',
                borderwidth=1
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            bargap=0.15,  # Espaço entre grupos de barras
            bargroupgap=0.05  # Espaço entre barras do mesmo grupo
        )

        # Definir rótulos dos meses no eixo x
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        fig_lojas.update_xaxes(
            range=[0.5, 12.5],
            tickmode='array',
            tickvals=list(range(1, 13)),
            ticktext=meses,
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )

        fig_lojas.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )

        # Criar componente do gráfico
        grafico_lojas = html.Div([
            html.Div([
                html.Div([
                    html.Label("Selecione o Ano:", className="mb-2 font-weight-bold"),
                    dcc.Dropdown(
                        id='dropdown-ano-lojas',
                        options=[{'label': str(ano), 'value': ano} for ano in anos_disponiveis],
                        value=ano_default,
                        clearable=False,
                        style={'width': '150px'}
                    ),
                ], className="col-md-3"),
                html.Div([
                    html.Label("Selecione as Lojas:", className="mb-2 font-weight-bold"),
                    dcc.Dropdown(
                        id='dropdown-loja-mensal',
                        options=[
                            {'label': row['nome'], 'value': row['id_loja']} 
                            for _, row in df_mensal_lojas.drop_duplicates(['id_loja', 'nome']).iterrows()
                            if 'nome' in df_mensal_lojas.columns and 'id_loja' in df_mensal_lojas.columns
                        ],
                        value=[],
                        multi=True,  # Habilita a seleção múltipla
                        placeholder="Selecione lojas para filtrar",
                        style={'width': '100%'}
                    ),
                ], className="col-md-6"),
            ], className="row mb-4"),
            dcc.Graph(
                id='grafico-lojas-mensal',
                figure=fig_lojas,
                config={"responsive": True}
            )
        ], className="mb-5")
        
        graficos_processados["grafico_faturamento_lojas"] = True
    except Exception as e:
        print(f"Erro no processamento do Gráfico 4 (Faturamento Mensal por Loja): {e}")
        traceback.print_exc()
        graficos_processados["grafico_faturamento_lojas"] = False
    
    # ----------------------------------------------------------
    # --- Gráfico 5: Faturamento Diário nos últimos 3 meses ----
    # ----------------------------------------------------------
    try:
        df_diario = pd.read_json(io.StringIO(data["df_fat_Diario"]), orient='split')

        # Converter valores com vírgula para ponto (formato numérico correto)
        df_diario['total_venda'] = df_diario['total_venda'].astype(str).str.replace(',', '.').astype(float)

        # Obter lista de períodos disponíveis (Mês/Ano) para o dropdown
        periodos_disponiveis = sorted(df_diario['Período'].unique(), reverse=True)
        periodo_default = periodos_disponiveis[0] if periodos_disponiveis else None  # Período mais recente como padrão

        # Filtrar dados para o período padrão
        df_filtrado_diario = df_diario[df_diario['Período'] == periodo_default] if periodo_default else pd.DataFrame()
        df_filtrado_diario = df_filtrado_diario.sort_values('Dia')  # Garantir que os dias estejam em ordem

        # Criar gráfico de linhas com pontos para visualização diária
        fig_diario = go.Figure()

        # Preparar texto para hover com formato monetário correto
        hover_texts = [formatar_moeda(valor) for valor in df_filtrado_diario['total_venda']]

        # Criar customdata com informações adicionais (opcional: mês e ano)
        if 'Mês' in df_filtrado_diario.columns and 'Ano' in df_filtrado_diario.columns:
            customdata = pd.DataFrame({
                'valor_formatado': hover_texts,
                'mes': df_filtrado_diario['Mês'],
                'ano': df_filtrado_diario['Ano']
            })
            hovertemplate = '<b>Dia:</b> %{x}<br><b>Faturamento:</b> %{text}<br><b>Data:</b> %{customdata[1]}/%{customdata[2]}<extra></extra>'
        else:
            customdata = pd.DataFrame({'valor_formatado': hover_texts})
            hovertemplate = '<b>Dia:</b> %{x}<br><b>Faturamento:</b> %{text}<extra></extra>'
        
        # Adicionar linha com pontos
        fig_diario.add_trace(go.Scatter(
            x=df_filtrado_diario['Dia'],
            y=df_filtrado_diario['total_venda'],
            mode='lines+markers',
            name='Faturamento Diário',
            line=dict(color=color['accent'], width=3),
            marker=dict(size=8, color=color['accent'], line=dict(width=2, color='white')),
            text=hover_texts,
            customdata=customdata.values,
            hovertemplate=hovertemplate
        ))

        # Adicionar rótulos de valores para cada ponto
        for dia, valor in zip(df_filtrado_diario['Dia'], df_filtrado_diario['total_venda']):
            fig_diario.add_annotation(
                x=dia,
                y=valor,
                text=formatar_moeda(valor),
                showarrow=False,
                yshift=15,
                font=dict(size=10, family="Montserrat")
            )

        # Configuração do layout
        fig_diario.update_layout(
            xaxis_title="Dia do Mês",
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

        # Configuração dos eixos
        fig_diario.update_xaxes(
            tickmode='linear',
            dtick=1,  # Mostrar todos os dias
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )

        fig_diario.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )

        # Criar componente do gráfico com dropdown para seleção de período
        grafico_diario = html.Div([
            html.Div([
                html.Label("Selecione o Período:", className="mb-2 font-weight-bold"),
                dcc.Dropdown(
                    id='dropdown-periodo-diario',
                    options=[{'label': periodo, 'value': periodo} for periodo in periodos_disponiveis],
                    value=periodo_default,
                    clearable=False,
                    style={'width': '200px'}
                ),
            ], className="mb-4"),
            dcc.Graph(
                id='grafico-faturamento-diario',
                figure=fig_diario,
                config={"responsive": True}
            )
        ])
        
        graficos_processados["grafico_faturamento_diario"] = True
    except Exception as e:
        print(f"Erro no processamento do Gráfico 5 (Faturamento Diário por Período): {e}")
        traceback.print_exc()
        graficos_processados["grafico_faturamento_diario"] = False

    # ----------------------------------------------------------
    # --- Tabela: Faturamento Diário por Loja no Mês Atual -----
    # ----------------------------------------------------------
    try:
        # Usar diretamente os dados do df_fat_Diario_lojas
        df_fat_Diario_lojas = pd.read_json(io.StringIO(data["df_fat_Diario_lojas"]), orient='split')
        
        # Garantir que todos os valores numéricos estejam formatados corretamente
        colunas_numericas = [col for col in df_fat_Diario_lojas.columns if col != 'nome']
        
        # Criar uma cópia para formatar valores
        df_formatado = df_fat_Diario_lojas.copy()
        
        # Formatar valores monetários para todas as colunas numéricas
        for col in colunas_numericas:
            df_formatado[col] = df_formatado[col].apply(lambda x: formatar_moeda(x) if pd.notnull(x) and x != 0 else "-")
        
        # Converter todas as colunas para string para garantir compatibilidade com a DataTable
        df_formatado_dict = df_formatado.reset_index().to_dict('records')
        
        # Criar componente da tabela usando Dash DataTable
        tabela_faturamento = html.Div([
            html.H5("Mês Atual", className="mb-3"),
            dash_table.DataTable(
                id='tabela-faturamento-diario-lojas',
                columns=[
                    {"name": "Loja", "id": "nome"},
                    {"name": "Total", "id": "total_loja", "type": "text"},
                ] + [
                    {"name": f"Dia {dia}", "id": str(dia), "type": "text"} 
                    for dia in range(1, 32) if str(dia) in df_formatado.columns or dia in df_formatado.columns
                ],
                data=df_formatado_dict,
                style_table={
                    'overflowX': 'auto',
                    'minWidth': '100%',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'border': '1px solid black'
                },
                style_cell={
                    'textAlign': 'right',
                    'padding': '8px',
                    'border': '1px solid #ddd'
                },
                style_cell_conditional=[
                    {
                        'if': {'column_id': 'nome'},
                        'textAlign': 'left',
                        'fontWeight': 'bold',
                        'width': '180px'
                    },
                    {
                        'if': {'column_id': 'total_loja'},
                        'fontWeight': 'bold',
                        'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                        'width': '120px'
                    }
                ],
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    },
                    {
                        'if': {'filter_query': '{nome} contains "total"'},
                        'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                        'fontWeight': 'bold'
                    }
                ]
            )
        ], className="mb-5")

        tabela_processada["tabela_faturamento_diario"] = True
    except Exception as e:
        print(f"Erro no processamento da Tabela de Faturamento Diário por Loja: {e}")
        traceback.print_exc()
        tabela_processada["tabela_faturamento_diario"] = False
    
    
    # Construir o layout com os gráficos que foram criados com sucesso
    componentes_layout = [
        dcc.Store(id='store-faturamento-data', data=data),
        html.H2("Crescimento do Negócio", className="dashboard-title"),
    ]
    
    # Adicionar métricas se disponíveis
    if graficos_processados.get("metricas", False):
        componentes_layout.append(metrics_row)
    else:
        componentes_layout.append(
            create_card(
                "Métricas de Faturamento", 
                html.Div([
                    html.P("Não foi possível calcular as métricas de faturamento devido a um erro nos dados.", className="text-danger p-3"),
                    html.I(className="fas fa-exclamation-triangle fa-2x text-warning d-block text-center mb-3")
                ])
            )
        )
    
    # Adicionar cada gráfico se disponível, ou mensagem de erro caso contrário
    if graficos_processados.get("grafico_evolucao_anual", False):
        componentes_layout.append(
            create_card(
                "Evolução Percentual Anual das Vendas",
                dcc.Graph(figure=fig_fat, config={"responsive": True})
            )
        )

    ###--DEBUG--###
    # else:
    #     componentes_layout.append(
    #         create_card(
    #             "Evolução Percentual Anual das Vendas", 
    #             html.Div([
    #                 html.P("Não foi possível processar o gráfico de evolução anual devido a um erro nos dados.", className="text-danger p-3"),
    #                 html.I(className="fas fa-chart-line fa-2x text-warning d-block text-center mb-3")
    #             ])
    #         )
    #     )
    
    if graficos_processados.get("grafico_faturamento_anual", False):
        componentes_layout.append(
            create_card(
                titulo_grafico2,
                dcc.Graph(figure=fig_ano, config={"responsive": True})
            )
        )
    
    ###--DEBUG--###
    # else:
    #     componentes_layout.append(
    #         create_card(
    #             "Faturamento Anual", 
    #             html.Div([
    #                 html.P("Não foi possível processar o gráfico de faturamento anual devido a um erro nos dados.", className="text-danger p-3"),
    #                 html.I(className="fas fa-chart-bar fa-2x text-warning d-block text-center mb-3")
    #             ])
    #         )
    #     )
    
    if graficos_processados.get("grafico_faturamento_mensal", False):
        componentes_layout.append(
            create_card(
                "Faturamento Mensal por Ano",
                dcc.Graph(figure=fig_mensal, config={"responsive": True})
            )
        )

    ###--DEBUG--###
    # else:
    #     componentes_layout.append(
    #         create_card(
    #             "Faturamento Mensal por Ano", 
    #             html.Div([
    #                 html.P("Não foi possível processar o gráfico de faturamento mensal devido a um erro nos dados.", className="text-danger p-3"),
    #                 html.I(className="fas fa-calendar-alt fa-2x text-warning d-block text-center mb-3")
    #             ])
    #         )
    #     )
    
    if graficos_processados.get("grafico_faturamento_lojas", False):
        componentes_layout.append(
            create_card(
                "Faturamento Mensal por Loja",
                grafico_lojas
            )
        )
    
    ###--DEBUG--###
    # else:
    #     componentes_layout.append(
    #         create_card(
    #             "Faturamento Mensal por Loja", 
    #             html.Div([
    #                 html.P("Não foi possível processar o gráfico de faturamento por loja devido a um erro nos dados.", className="text-danger p-3"),
    #                 html.I(className="fas fa-store fa-2x text-warning d-block text-center mb-3")
    #             ])
    #         )
    #     )
    
    if graficos_processados.get("grafico_faturamento_diario", False):
        componentes_layout.append(
            create_card(
                "Faturamento Diário por Período",
                grafico_diario
            )
        )

    ###--DEBUG--###
    # else:
    #     componentes_layout.append(
    #         create_card(
    #             "Faturamento Diário por Período", 
    #             html.Div([
    #                 html.P("Não foi possível processar o gráfico de faturamento diário devido a um erro nos dados.", className="text-danger p-3"),
    #                 html.I(className="fas fa-calendar-day fa-2x text-warning d-block text-center mb-3")
    #             ])
    #         )
    #     )

    if tabela_processada.get("tabela_faturamento_diario", False):
        componentes_layout.append(
                create_card(
                    "Tabela de Faturamento Diário por Loja",
                    tabela_faturamento
                )
            )
        
    ###--DEBUG--###
    # else: 
    #     componentes_layout.append(
    #         create_card(
    #             "Tabela de Faturamento Diário por Loja", 
    #             html.Div([
    #                 html.P("Não foi possível processar a tabela de faturamento diário devido a um erro nos dados.", className="text-danger p-3"),
    #                 html.I(className="fas fa-table fa-2x text-warning d-block text-center mb-3")
    #             ])
    #         )
    #     )
    
    # Se nenhum gráfico foi gerado com sucesso, exibir erro
    if not any(graficos_processados.values()):
        return html.Div([
            html.H2("Crescimento do Negócio", className="dashboard-title"),
            create_card(
                "Erro ao carregar os dados",
                html.Div([
                    html.P("Ocorreu um problema ao processar todos os gráficos. Nenhum gráfico pôde ser gerado."),
                    html.P("Verifique os logs para mais detalhes ou entre em contato com o suporte técnico.")
                ])
            )
        ], style=content_style)
    
    return html.Div(componentes_layout, style=content_style)