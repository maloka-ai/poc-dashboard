import io
import dash
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, html, dcc, dash_table
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.formatters import format_iso_date, formatar_moeda, formatar_numero
from utils.helpers import color, create_metric_row, gradient_colors

def criar_grafico_simulado(produto, valores, meses_labels):
    """
    Cria um gráfico simulado quando as colunas não estão no formato esperado.
    
    Args:
        produto: Série com os dados do produto
        valores: Lista de valores mensais
        meses_labels: Lista de rótulos para os meses
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Obter as sugestões de compra
        sug_1m = float(produto['Sug 1M']) if 'Sug 1M' in produto else 0
        sug_3m = float(produto['Sug 3M']) if 'Sug 3M' in produto else 0
        
        # Nome do produto
        nome_produto = produto.get('desc_produto', produto.get('Produto', f"Produto {produto.get('cd_produto', '')}"))
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Adicionar linha de consumo mensal
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=valores,
                mode='lines+markers+text',
                name='Consumo',
                line=dict(color='#0077B6', width=3),
                marker=dict(size=8, color='#0077B6'),
                text=[str(int(v)) for v in valores],
                textposition='top center',
                textfont=dict(size=10)
            )
        )
        
        # Adicionar barras para Sugestão 1M e 3M
        x_all = meses_labels + ['Sugestão\n1M', 'Sugestão\n3M']
        
        # Adicionar barra para Sugestão 1M
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n1M'],
                y=[sug_1m],
                name='Sugestão 1M',
                marker_color='#0077B6',
                text=[str(int(sug_1m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Adicionar barra para Sugestão 3M 
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n3M'],
                y=[sug_3m],
                name='Sugestão 3M',
                marker_color='#0077B6',
                text=[str(int(sug_3m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Configurar layout
        fig.update_layout(
            title=f"Consumo Mensal - {nome_produto}",
            title_font=dict(size=16, family="Montserrat", color='#001514'),
            xaxis=dict(
                title="",
                tickmode='array',
                tickvals=x_all,
                ticktext=x_all,
                tickangle=-45,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title="Quantidade",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=80),
            height=500
        )
        
        # Adicionar linha horizontal no zero
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=len(x_all) - 1,
            y1=0,
            line=dict(color="black", width=1)
        )
        
        return fig
    
    except Exception as e:
        print(f"Erro ao gerar gráfico simulado: {str(e)}")
        # Retornar um gráfico de erro
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao gerar gráfico simulado: {str(e)}",
            showarrow=False,
            font=dict(size=12, color="red")
        )
        return fig

def criar_grafico_produto(df_produto, cd_produto):
    """
    Cria um gráfico de consumo mensal para um produto específico,
    similar ao da imagem de referência.
    
    Args:
        df_produto: DataFrame contendo os dados dos produtos
        cd_produto: Código do produto para gerar o gráfico
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Filtrar o produto específico
        produto = df_produto[df_produto['cd_produto'] == cd_produto].iloc[0]
        
        # Obter colunas que representam meses (formato: YYYY_MM)
        colunas_meses = [col for col in df_produto.columns if col.startswith('202')]
        
        # Se não houver colunas de meses no formato YYYY_MM, verificar outros formatos possíveis
        if not colunas_meses:
            # Tentar encontrar colunas numéricas que possam representar meses
            colunas_numericas = [col for col in df_produto.columns 
                                if isinstance(col, str) and col not in ['cd_produto', 'desc_produto', 'estoque_atualizado', 
                                                                       'Media 3M', 'Sug 1M', 'Sug 3M', 'custo1', 'Fornecedor1']]
            
            # Se tivermos pelo menos 12 colunas numéricas, podemos assumir que são meses
            if len(colunas_numericas) >= 12:
                colunas_meses = colunas_numericas[:14]  # Limitar a 14 meses como no exemplo
                
                # Criar rótulos simulados de meses (Jan-24, Fev-24, etc.)
                meses_labels = [
                    'Jan-24', 'Fev-24', 'Mar-24', 'Abr-24', 'Mai-24', 'Jun-24', 
                    'Jul-24', 'Ago-24', 'Set-24', 'Out-24', 'Nov-24', 'Dez-24', 
                    'Jan-25', 'Fev-25'
                ][:len(colunas_meses)]
                
                # Simular valores se estiverem faltando
                valores = []
                for col in colunas_meses:
                    try:
                        val = float(produto[col])
                        valores.append(val)
                    except:
                        valores.append(0)  # Valor padrão se não conseguir converter
                
                return criar_grafico_simulado(produto, valores, meses_labels)
        
        colunas_meses.sort()  # Garantir ordem cronológica
        
        # Extrair valores mensais de consumo
        valores = []
        for col in colunas_meses:
            try:
                valores.append(float(produto[col]))
            except (ValueError, TypeError):
                # Se não conseguir converter para float, usar 0
                valores.append(0)
        
        # Obter as sugestões de compra
        sug_1m = float(produto['Sug 1M']) if 'Sug 1M' in produto else 0
        sug_3m = float(produto['Sug 3M']) if 'Sug 3M' in produto else 0
        
        # Criar rótulos para os meses no formato "MMM-YY"
        meses_labels = []
        for col in colunas_meses:
            ano, mes = col.split('_')
            ano_curto = ano[2:]  # Pegar só os dois últimos dígitos do ano
            # Converter mês numérico para nome abreviado
            mes_nomes = {
                '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
                '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
                '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
            }
            mes_nome = mes_nomes.get(mes, mes)
            meses_labels.append(f"{mes_nome}-{ano_curto}")

        # Calcular a média móvel de 3 meses
        media_movel_3m = []
        for i in range(len(valores)):
            if i < 2:  # Para os dois primeiros meses, não temos 3 meses completos
                media_movel_3m.append(None)
            else:
                # Média dos 3 meses anteriores (incluindo o atual)
                media = sum(valores[i-2:i+1]) / 3
                media_movel_3m.append(media)
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Adicionar linha de consumo mensal
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=valores,
                mode='lines+markers+text',
                name='Consumo',
                line=dict(color='#0077B6', width=3),
                marker=dict(size=8, color='#0077B6'),
                text=[str(int(v)) for v in valores],
                textposition='top center',
                textfont=dict(size=10)
            )
        )

        # Adicionar linha de média móvel de 3 meses
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=media_movel_3m,
                mode='lines',
                name='Média Móvel 3M',
                line=dict(color='#FF8C00', width=2, dash='dash'),
                hoverinfo='text',
                hovertext=[f'Média 3M: {round(m, 1)}' if m is not None else '' for m in media_movel_3m]
            )
        )
        
        # Adicionar barras para Sugestão 1M e 3M
        x_all = meses_labels + ['Sugestão\n1M', 'Sugestão\n3M']
        
        # Adicionar barra para Sugestão 1M
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n1M'],
                y=[sug_1m],
                name='Sugestão 1M',
                marker_color='#0077B6',
                text=[str(int(sug_1m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Adicionar barra para Sugestão 3M 
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n3M'],
                y=[sug_3m],
                name='Sugestão 3M',
                marker_color='#0077B6',
                text=[str(int(sug_3m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Configurar layout
        fig.update_layout(
            title=f"Consumo Mensal - {produto['desc_produto']}",
            title_font=dict(size=16, family="Montserrat", color='#001514'),
            xaxis=dict(
                title="",
                tickmode='array',
                tickvals=x_all,
                ticktext=x_all,
                tickangle=-45,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title="Quantidade",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=80),
            height=500
        )
        
        # Adicionar linha horizontal no zero
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=len(x_all) - 1,
            y1=0,
            line=dict(color="black", width=1)
        )
        
        return fig
    
    except Exception as e:
        print(f"Erro ao gerar gráfico para o produto {cd_produto}: {str(e)}")
        # Retornar um gráfico de erro
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao gerar gráfico: {str(e)}",
            showarrow=False,
            font=dict(size=12, color="red")
        )
        return fig

def register_produtos_callbacks(app):
    """
    Registra todos os callbacks relacionados à página de produtos de estoque.
    
    Args:
        app: A instância do aplicativo Dash
    """
    
    @app.callback(
    [Output("produto-consumo-header", "children"),
     Output("produto-consumo-grafico", "children")],
    [Input("produtos-criticidade-table", "active_cell"),
     Input("produtos-criticidade-table", "derived_virtual_data"),
     Input("produtos-criticidade-table", "derived_virtual_selected_rows")],
    [State("selected-data", "data")]
    )
    def update_produto_consumo_grafico(active_cell, virtual_data, selected_rows, data):
        """
        Atualiza o gráfico de consumo quando um produto é selecionado na tabela.
        """
        # Verificar se temos seleção e dados válidos
        if active_cell is None or virtual_data is None or not virtual_data:
            return "Gráfico de Consumo do Produto Selecionado", html.Div([
                html.P("Selecione um produto na lista acima para visualizar o gráfico de consumo.", 
                    className="text-center text-muted my-4"),
                html.Div(className="text-center", children=[
                    html.I(className="fas fa-chart-line fa-2x text-muted"),
                    html.P("O gráfico mostrará o histórico de consumo e sugestões de compra", 
                        className="text-muted mt-2")
                ])
            ])
        
        if data is None or data.get("df_relatorio_produtos") is None:
            return "Dados não disponíveis", "Não foi possível carregar os dados dos produtos."
        
        try:
            # Obter o produto selecionado da tabela
            row_id = active_cell["row"]
            if row_id >= len(virtual_data):
                return "Erro de seleção", "A linha selecionada está fora dos limites da tabela."
                
            produto_selecionado = virtual_data[row_id]
            
            # Encontrar a coluna que contém o código do produto
            codigo_colunas = ['cd_produto', 'Código', 'codigo', 'ID']
            desc_colunas = ['desc_produto', 'Produto', 'Descrição', 'Nome', 'descricao']
            
            cd_produto = None
            for col in codigo_colunas:
                if col in produto_selecionado and produto_selecionado[col]:
                    cd_produto = str(produto_selecionado[col])
                    break
                    
            if not cd_produto:
                return "Código não encontrado", "Não foi possível identificar o código do produto."
                
            # Obter a descrição do produto
            desc_produto = None
            for col in desc_colunas:
                if col in produto_selecionado and produto_selecionado[col]:
                    desc_produto = produto_selecionado[col]
                    break
                    
            if not desc_produto:
                desc_produto = f"Produto {cd_produto}"
            
            # Carregar dados de produtos
            df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')
            
            # Verificar se o produto existe no dataframe
            # Tentar diferentes formatos de código para aumentar compatibilidade
            cd_produto_encontrado = False
            for valor in [cd_produto, int(cd_produto) if cd_produto.isdigit() else cd_produto]:
                if valor in df_produtos['cd_produto'].values:
                    cd_produto = valor
                    cd_produto_encontrado = True
                    break
            
            if not cd_produto_encontrado:
                return f"Produto não encontrado: {cd_produto}", html.Div([
                    html.P(f"O produto com código {cd_produto} não foi encontrado na base de dados.", 
                        className="text-center text-muted my-4")
                ])
            
            # Chamar a função para criar o gráfico
            fig = criar_grafico_produto(df_produtos, cd_produto)

            # Verificar se todos os custos são zero
            def todos_custos_zerados():
                custo1 = produto_selecionado.get('custo1', 'R$ 0,00')
                custo2 = produto_selecionado.get('custo2', '0')
                custo3 = produto_selecionado.get('custo3', '0')
                
                # Converter para string se for número
                if not isinstance(custo1, str): custo1 = str(custo1)
                if not isinstance(custo2, str): custo2 = str(custo2)
                if not isinstance(custo3, str): custo3 = str(custo3)
                
                # Verificar se todos são zero ou vazios
                return (custo1 == 'R$ 0,00' or custo1 == '') and (custo2 == '0' or custo2 == '') and (custo3 == '0' or custo3 == '')
                    
            # Adicionar título legível e detalhes
            header = None if todos_custos_zerados() else html.Div([
                # Informações de fornecedor 1
                html.H6("Últimas Compras", className="mt-4 mb-3"),
                html.Div([
                    html.Div([
                        # Usando blocos com grande espaçamento horizontal
                        html.Div([
                            html.Span("Data: ", className="font-weight-bold"),
                            html.Span(format_iso_date(produto_selecionado.get('Data1', '-')))
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Qtd: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('Quantidade1', '-')}")
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Custo Unitário: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('custo1', '-')}")
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Fornecedor: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('Fornecedor1', '-')}")
                        ], style={"display": "inline-block"}) if produto_selecionado.get('Fornecedor1') and produto_selecionado.get('Fornecedor1') != '0' and produto_selecionado.get('Fornecedor1') != 0.0 else None
                    ], className="text-muted")
                ], className="mt-4 pb-3 border-bottom") if (
                produto_selecionado.get('Fornecedor1') != '0' and 
                produto_selecionado.get('Fornecedor1') != 0.0 or 
                produto_selecionado.get('custo1') != 'R$ 0,00' and 
                produto_selecionado.get('custo1') != 0.0) 
                else None,

                # Informações de fornecedor 2
                html.Div([
                    html.Div([
                        # Usando blocos com grande espaçamento horizontal
                        html.Div([
                            html.Span("Data: ", className="font-weight-bold"),
                            html.Span(format_iso_date(produto_selecionado.get('Data2', '-')))
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Qtd: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('Quantidade2', '-')}")
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Custo Unitário: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('custo2', '-')}")
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Fornecedor: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('Fornecedor2', '-')}")
                        ], style={"display": "inline-block"}) if produto_selecionado.get('Fornecedor2') and produto_selecionado.get('Fornecedor2') != '0' and produto_selecionado.get('Fornecedor2') != 0.0 else None
                    ], className="text-muted")
                ], className="mt-4 pb-3 border-bottom") if (
                produto_selecionado.get('Fornecedor2') != '0' and 
                produto_selecionado.get('Fornecedor2') != 0.0 or 
                produto_selecionado.get('custo2') != 'R$ 0,00' and 
                produto_selecionado.get('custo2') != 0.0) 
                else None,

                # Informações de fornecedor 3
                html.Div([
                    html.Div([
                        # Usando blocos com grande espaçamento horizontal
                        html.Div([
                            html.Span("Data: ", className="font-weight-bold"),
                            html.Span(format_iso_date(produto_selecionado.get('Data3', '-')))
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Qtd: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('Quantidade3', '-')}")
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Custo Unitário: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('custo3', '-')}")
                        ], style={"display": "inline-block", "marginRight": "60px"}),
                        
                        html.Div([
                            html.Span("Fornecedor: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('Fornecedor3', '-')}")
                        ], style={"display": "inline-block"}) if produto_selecionado.get('Fornecedor3') and produto_selecionado.get('Fornecedor3') != '0' and produto_selecionado.get('Fornecedor3') != 0.0 else None
                    ], className="text-muted")
                ], className="mt-4 pb-3 border-bottom") if (
                produto_selecionado.get('Fornecedor3') != '0' and 
                produto_selecionado.get('Fornecedor3') != 0.0 or 
                produto_selecionado.get('custo3') != 'R$ 0,00' and 
                produto_selecionado.get('custo3') != 0.0) 
                else None,
            ])
            
            # Adicionar o gráfico com legenda explicativa
            grafico_component = html.Div([
                dcc.Graph(
                    figure=fig,
                    config={"responsive": True},
                    style={"height": "500px"}
                ),
                html.Div([
                    html.P([
                        "O gráfico mostra o histórico de consumo nos últimos meses e a sugestão de compra.",
                        html.Br(),
                        html.Span("Sugestão 1M: ", className="font-weight-bold"),
                        "Quantidade sugerida para compra no próximo mês.", 
                        html.Br(),
                        html.Span("Sugestão 3M: ", className="font-weight-bold"),
                        "Quantidade sugerida para compra nos próximos três meses."
                    ], className="text-muted small mt-2")
                ])
            ])
            
            return header, grafico_component
        
        except Exception as e:
            return "Erro ao gerar gráfico", html.Div([
                html.P(f"Ocorreu um erro ao gerar o gráfico: {str(e)}", 
                    className="text-center text-danger my-4"),
                html.Pre(str(e), className="bg-light p-3 text-danger")
            ])


    
    @app.callback(
    [Output("filtro-criticos-ativo", "data"),
     Output("btn-filtro-criticos", "children"),
     Output("btn-filtro-criticos", "color")],
    Input("btn-filtro-criticos", "n_clicks"),
    State("filtro-criticos-ativo", "data"),
    prevent_initial_call=True
    )
    def toggle_filtro_criticos(n_clicks, filtro_ativo):
        if n_clicks is None:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Inverte o estado atual do filtro
        novo_estado = not filtro_ativo
        
        # Texto e cor do botão dependendo do estado
        if novo_estado:
            # Se o filtro estiver ativo (mostrando apenas críticos)
            texto_botao = [html.I(className="fas fa-filter me-2"), "Mostrar Todos os Produtos"]
            cor_botao = "primary"
        else:
            # Se o filtro estiver inativo (mostrando todos)
            texto_botao = [html.I(className="fas fa-filter me-2"), "Mostrar Produtos com Reposição Não-Local"]
            cor_botao = "danger"
        
        return novo_estado, texto_botao, cor_botao
    

    @app.callback(
    Output("produtos-criticidade-bar", "figure"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
    )
    def update_grafico_barras(filtro_ativo, produtos_data):
        if produtos_data is None:
            return dash.no_update
        
        # Carregamos os dados
        df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
        
        # Se o filtro estiver ativo, filtrar para mostrar apenas produtos críticos
        if filtro_ativo:
            # Em vez de filtrar a contagem, vamos filtrar o dataframe original
            df_filtrado = df_criticos[df_criticos['critico'] == True]

            contagem_criticidade = df_filtrado['criticidade'].value_counts().sort_index()

            total_produtos = len(df_filtrado)
            total_series = pd.Series([total_produtos], index=['Todos'])
            contagem_criticidade = pd.concat([contagem_criticidade, total_series])
        else:
            # Contagem normal de todos os produtos por criticidade
            contagem_criticidade = df_criticos['criticidade'].value_counts().sort_index()
            # Adicionar o total
            total_produtos = len(df_criticos)
            total_series = pd.Series([total_produtos], index=['Todos'])
            contagem_criticidade = pd.concat([contagem_criticidade, total_series])
        
        # Calcular porcentagens para anotações
        porcentagens = contagem_criticidade.copy()
        for idx in porcentagens.index:
            if idx == 'Todos':
                print("cheguei nos 100%")
                porcentagens[idx] = 100.0  # Forçar 100% para o total
            else:
                porcentagens[idx] = (contagem_criticidade[idx] / total_produtos * 100).round(1)
        
        # Criar gráfico de barras
        fig = px.bar(
            x=contagem_criticidade.index,
            y=contagem_criticidade.values,
            color=contagem_criticidade.index,
            color_discrete_map={
                'Crítico': 'darkred',
                'Muito Baixo': 'orange',
                'Baixo': color['warning'],
                'Adequado': gradient_colors['green_gradient'][0],
                'Excesso': color['secondary'],
                'Todos': color['primary']
            },
            labels={'x': 'Nível de Criticidade', 'y': 'Quantidade de Produtos'},
            template='plotly_white'
        )
        
        # Adicionar valores nas barras
        for i, v in enumerate(contagem_criticidade.values):
            percentage = porcentagens[contagem_criticidade.index[i]]
            fig.add_annotation(
                x=contagem_criticidade.index[i],
                y=v,
                text=f"{str(v)} ({percentage:.1f}%)".replace(".", ","),
                showarrow=False,
                yshift=10,
                font=dict(size=14, color="black", family="Montserrat", weight="bold")
            )
        
        fig.update_layout(
            title_font=dict(size=16, family="Montserrat", color=color['primary']),
            xaxis_title="Nível de Criticidade",
            yaxis_title="Quantidade de Produtos",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        return fig

    # Callback para atualizar o Top 20 produtos críticos com base no filtro
    @app.callback(
        Output("produtos-criticidade-top20", "figure"),
        [Input("filtro-criticos-ativo", "data"),
        Input("store-produtos-data", "data")],
        prevent_initial_call=True
    )
    def update_grafico_top20(filtro_ativo, produtos_data):
        if produtos_data is None:
            return dash.no_update
        
        # Carregamos os dados
        df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
        
        # Verificar a coluna de descrição do produto
        produto_col = 'desc_produto' if 'desc_produto' in df_criticos.columns else 'Produto' if 'Produto' in df_criticos.columns else None
        
        if not produto_col:
            # Se não tiver coluna de produto, retorna um gráfico vazio
            fig = go.Figure()
            fig.update_layout(
                title="Coluna de descrição de produto não encontrada",
                title_font=dict(size=16, family="Montserrat", color=color['primary'])
            )
            return fig
        
        # Filtrar os dados com base no estado do filtro
        if filtro_ativo:
            df_filtrado = df_criticos[df_criticos['critico'] == True]
        else:
            df_filtrado = df_criticos
        
        # Ordenar pelo percentual de cobertura
        df_ordenado = df_filtrado.sort_values('percentual_cobertura')
        
        # Selecionar os Top 20
        top_20 = df_ordenado.head(20)
        
        # Criar a coluna de exibição do produto
        top_20['produto_display'] = top_20[produto_col].apply(lambda x: (x[:30] + '...') if len(str(x)) > 30 else x)
        
        # Criar o gráfico
        fig = px.bar(
            top_20,
            y='produto_display',
            x='percentual_cobertura',
            orientation='h',
            color='percentual_cobertura',
            color_continuous_scale=['darkred', 'orange', color['warning']],
            range_color=[0, 50 if filtro_ativo else 100],  # Ajusta range de cores com base no filtro
            labels={'percentual_cobertura': 'Cobertura (%)', 'produto_display': 'Produto'},
            template='plotly_white'
        )
        
        if 'cd_produto' in top_20.columns:
            fig.update_traces(
                hovertemplate='<b>%{y}</b><br>Código: %{customdata[0]}<br>Cobertura: %{x:.1f}%',
                customdata=top_20[['cd_produto']]
            )
        
        fig.update_layout(
            title=f"Top 20 Produtos{' Críticos' if filtro_ativo else ''}",
            title_font=dict(size=16, family="Montserrat", color=color['primary']),
            yaxis_title="",
            xaxis_title="Percentual de Cobertura (%)",
            margin=dict(l=200, r=20, t=30, b=30),
            height=500,
            yaxis=dict(autorange="reversed"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Adicionar linha em 30% para referência de criticidade
        fig.add_shape(
            type="line",
            x0=30, y0=-0.5,
            x1=30, y1=len(top_20) - 0.5,
            line=dict(color="darkred", width=2, dash="dash"),
        )
        
        # Adicionar valores de percentual nas barras
        for i, row in enumerate(top_20.itertuples()):
            fig.add_annotation(
                x=row.percentual_cobertura,
                y=row.produto_display,
                text=f"{row.percentual_cobertura:.1f}%".replace(".", ","),
                showarrow=False,
                xshift=15,
                font=dict(size=12, color="black", family="Montserrat")
            )
        
        return fig

    @app.callback(
        Output("div-metrics-row", "children"),
        [Input("filtro-criticos-ativo", "data"),
        Input("store-produtos-data", "data")],
        prevent_initial_call=True
    )
    def update_metricas(filtro_ativo, produtos_data):
        if produtos_data is None:
            return dash.no_update
        
        # Carregamos os dados
        df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
        
        # Se o filtro estiver ativo, mostrar apenas informações de produtos críticos
        if filtro_ativo:
            df_filtrado = df_criticos[df_criticos['critico'] == True]
            
            # Contar produtos por cada categoria de criticidade
            total_produtos = len(df_filtrado)
            produtos_criticos = len(df_filtrado[df_filtrado['criticidade'] == 'Crítico'])
            produtos_muito_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'Muito Baixo'])
            produtos_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'Baixo'])
            produtos_adequados = len(df_filtrado[df_filtrado['criticidade'] == 'Adequado'])
            produtos_excesso = len(df_filtrado[df_filtrado['criticidade'] == 'Excesso'])
            
            # Criar métricas para a primeira linha de cards - mostrando todas as categorias
            metrics = [
                {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
                {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
                {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
                {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
                {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
                {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
            ]
            
        else:
            # Contar produtos por cada categoria de criticidade
            total_produtos = len(df_criticos)
            produtos_criticos = len(df_criticos[df_criticos['criticidade'] == 'Crítico'])
            produtos_muito_baixos = len(df_criticos[df_criticos['criticidade'] == 'Muito Baixo'])
            produtos_baixos = len(df_criticos[df_criticos['criticidade'] == 'Baixo'])
            produtos_adequados = len(df_criticos[df_criticos['criticidade'] == 'Adequado'])
            produtos_excesso = len(df_criticos[df_criticos['criticidade'] == 'Excesso'])
            
            # Criar métricas para a primeira linha de cards - mostrando todas as categorias
            metrics = [
                {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
                {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
                {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
                {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
                {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
                {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
            ]
        
        # Retornar a linha de métricas criada
        return create_metric_row(metrics)

    @app.callback(
        [Output("produtos-criticidade-header", "children"),
        Output("produtos-criticidade-list", "children")],
        [Input("produtos-criticidade-bar", "clickData"),
        Input("filtro-criticos-ativo", "data")],
        [State("selected-data", "data")]
    )
    def update_produtos_criticidade_list(clickData_bar, filtro_ativo, data):
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return "Produtos do Nível de Cobertura Selecionado", html.Div([
                html.P("Selecione um nível de cobertura no gráfico para ver os produtos.", 
                    className="text-center text-muted my-4")
            ])
        
        if data is None or data.get("df_relatorio_produtos") is None:
            return "Dados Indisponíveis", html.Div([
                html.P("Não foi possível carregar os dados dos produtos.", 
                    className="text-center text-muted my-4")
            ])
        
        df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')

        if filtro_ativo:
            df_produtos = df_produtos[df_produtos['critico'] == True]
        
        # Converta as colunas de string para lowercase para facilitar buscas case-insensitive
        string_columns = df_produtos.select_dtypes(include=['object']).columns
        for col in string_columns:
            try:
                # Tentar converter para lowercase, mas ignorar erros (se houver valores não-string)
                df_produtos[f"{col}_lower"] = df_produtos[col].str.lower()
            except:
                pass
        
        # Determine which chart was clicked
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Initialize default criticidade
        selected_criticidade = None
        
        if trigger_id == 'produtos-criticidade-bar' and clickData_bar:
            selected_criticidade = clickData_bar['points'][0]['x']
        
        if selected_criticidade is None:
            return "Produtos do Nível de Cobertura Selecionado", html.Div([
                html.P("Não foi possível identificar a cobertura selecionada.", className="text-center text-muted my-4")
            ])
        
        # Checar se foi selecionado "Todos"
        if selected_criticidade == 'Todos':
            header_text = "Todos os Produtos"
            filtered_df = df_produtos  # Usar todo o DataFrame
        else:
            header_text = f"Produtos com Criticidade: {selected_criticidade}"
            # Filtrar TODOS os produtos desta criticidade
            filtered_df = df_produtos[df_produtos["criticidade"] == selected_criticidade]
        
        if filtered_df.empty:
            return header_text, "Nenhum produto encontrado para a criticidade selecionada."
        
        # Determinar colunas de exibição
        display_columns = [
            "cd_produto", "desc_produto", "critico", "estoque_atualizado", "Media 3M", 
            "percentual_cobertura", "Sug 1M", "Sug 3M", 
            "Data1", "Quantidade1", "custo1", "Fornecedor1", 
            "Data2", "Quantidade2", "custo2", "Fornecedor2",
            "Data3", "Quantidade3", "custo3", "Fornecedor3"
        ]
        
        # Usar apenas colunas que existem no DataFrame
        existing_columns = [col for col in display_columns if col in filtered_df.columns]
        if not existing_columns:
            return header_text, "Estrutura de dados incompatível para exibição de detalhes."
        
        # Renomear colunas para melhor visualização
        col_rename = {
            "cd_produto": "Código",
            "desc_produto": "Produto",
            "critico": "Reposição Não-Local (Crítico)",
            "estoque_atualizado": "Estoque Atual",
            "Media 3M": "Consumo Médio (3M)",
            "percentual_cobertura": "Cobertura (%)",
            "Sug 1M": "Sugestão (1M)",
            "Sug 3M": "Sugestão (3M)",
            "Data1": "Data 1",
            "Quantidade1": "Quantidade 1",
            "custo1": "Custo Unitário 1",
            "Fornecedor1": "Fornecedor 1",
            "Data2": "Data 2",
            "Quantidade2": "Quantidade 2",
            "custo2": "Custo Unitário 2",
            "Fornecedor2": "Fornecedor 2",
            "Quantidade3": "Quantidade 3",
            "Data3": "Data 3",
            "custo3": "Custo Unitário 3",
            "Fornecedor3": "Fornecedor 3"
        }
        
        # Formatação especial para valores monetários e percentuais
        filtered_df_display = filtered_df[existing_columns].copy()
        
        if 'percentual_cobertura' in filtered_df_display.columns:
            filtered_df_display['percentual_cobertura'] = filtered_df_display['percentual_cobertura'].apply(
                lambda x: f"{x:.1f}%".replace(".", ",")
            )
        
        # Formatar colunas monetárias - AQUI ESTÁ O ERRO
        # Verificar e converter para o formato correto antes de aplicar formatação
        for custo_col in ['custo1', 'custo2', 'custo3']:
            if custo_col in filtered_df_display.columns:
                # Verificar se a coluna já está formatada como string de moeda
                def format_currency_safely(value):
                    try:
                        if pd.isna(value) or value == "":
                            return ""
                        # Se já for uma string que começa com R$, retornar diretamente
                        if isinstance(value, str) and value.strip().startswith('R$'):
                            return value
                        # Caso contrário, tentar converter para float e formatar
                        return formatar_moeda(float(value)) if value != 0 else ""
                    except (ValueError, TypeError):
                        # Em caso de erro, retornar o valor original
                        return str(value) if not pd.isna(value) else ""
                
                filtered_df_display[custo_col] = filtered_df_display[custo_col].apply(format_currency_safely)
        
        # Formatar datas
        for data_col in ['Data1', 'Data2', 'Data3']:
            if data_col in filtered_df_display.columns:
                filtered_df_display[data_col] = filtered_df_display[data_col].apply(
                    lambda x: format_iso_date(x) if not pd.isna(x) else ""
                )
        
        # Criar tabela aprimorada com filtro case-insensitive
        table = dash_table.DataTable(
            id='produtos-criticidade-table',  # ID único para a tabela
            columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
            data=filtered_df_display.to_dict("records"),
            page_size=10,  # Aumentado para mostrar mais produtos por página
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
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
                    "if": {"column_id": "percentual_cobertura"},
                    "fontWeight": "bold",
                    "color": "darkred" if selected_criticidade == "Crítico" else 
                            "orange" if selected_criticidade == "Muito Baixo" else
                            color['warning'] if selected_criticidade == "Baixo" else
                            "green" if selected_criticidade == "Adequado" else color['secondary']
                },
                {
                    "if": {"column_id": "custo1"},
                    "fontWeight": "bold"
                },
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "rgb(248, 248, 248)"
                }
            ],
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            export_format="xlsx",
            # Configuração para tornar o filtro case-insensitive
            filter_options={
                'case': 'insensitive'   # Ignora maiúsculas/minúsculas nos filtros
            }
        )
        
        # Adicionar resumo acima da tabela
        total_categoria = len(filtered_df)
        summary = html.Div([
            html.P([
                f"Exibindo todos os ", 
                html.Strong(formatar_numero(total_categoria)), 
                f" produtos com cobertura: ", 
                html.Strong(selected_criticidade)
            ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
        ])
        
        return header_text, html.Div([summary, table])