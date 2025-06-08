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
        sug_1m = float(produto['sugestao_1m']) if 'sugestao_1m' in produto else 0
        sug_3m = float(produto['sugestao_3m']) if 'sugestao_3m' in produto else 0
        
        # Nome do produto
        nome_produto = produto.get('nome_produto', produto.get('Produto', f"Produto {produto.get('id_produto', '')}"))
        
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

def criar_grafico_produto(df_produto, id_produto):
    """
    Cria um gráfico de consumo mensal para um produto específico,
    adaptado para lidar com os formatos de colunas do sistema de recomendação.
    
    Args:
        df_produto: DataFrame contendo os dados dos produtos
        id_produto: Código do produto para gerar o gráfico
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Filtrar o produto específico
        produto = df_produto[df_produto['id_produto'] == id_produto].iloc[0]
        
        # Primeiro, procurar colunas no formato 'qtd_vendas_YYYY-MM'
        colunas_meses = [col for col in df_produto.columns if col.startswith('qtd_vendas_')]
        
        # Se não encontrar no formato padrão, tentar encontrar no formato 'YYYY_MM'
        if not colunas_meses:
            colunas_meses = [col for col in df_produto.columns if col.startswith('202')]
            
        # Se ainda assim não encontrar, verificar outros formatos possíveis
        if not colunas_meses:
            # Tentar encontrar colunas numéricas que possam representar meses
            colunas_numericas = [col for col in df_produto.columns 
                               if isinstance(col, str) and col not in ['id_produto', 'nome_produto', 'estoque_atual', 
                                                                     'media_3M', 'sugestao_1m', 'sugestao_3m', 'ultimo_preco_compra', 'ultimo_fornecedor']]
            
            # Se tivermos pelo menos 12 colunas numéricas, podemos assumir que são meses
            if len(colunas_numericas) >= 12:
                colunas_meses = colunas_numericas[:13]  # Limitar a 14 meses como no exemplo
                
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
        
        # Garantir ordem cronológica das colunas
        if colunas_meses and any(col.startswith('qtd_vendas_') for col in colunas_meses):
            # Extrair datas das colunas qtd_vendas_YYYY-MM e ordenar
            colunas_meses.sort(key=lambda x: x.replace('qtd_vendas_', ''))
        else:
            colunas_meses.sort()
        
        # Extrair valores mensais de consumo
        valores = []
        for col in colunas_meses:
            try:
                valores.append(float(produto[col]))
            except (ValueError, TypeError):
                # Se não conseguir converter para float, usar 0
                valores.append(0)
        
        # Obter as sugestões de compra
        sug_1m = float(produto['sugestao_1m'] if 'sugestao_1m' in produto else 
                      produto.get('sugestao_1m', 0))
        sug_3m = float(produto['sugestao_3m'] if 'sugestao_3m' in produto else 
                      produto.get('sugestao_3m', 0))
        
        # Criar rótulos para os meses
        meses_labels = []
        for col in colunas_meses:
            if col.startswith('qtd_vendas_'):
                # Extrair 'YYYY-MM' do formato 'qtd_vendas_YYYY-MM'
                data_str = col.replace('qtd_vendas_', '')
                ano, mes = data_str.split('-')
                ano_curto = ano[2:]  # Pegar só os dois últimos dígitos do ano
            elif '_' in col:
                # Formato 'YYYY_MM'
                ano, mes = col.split('_')
                ano_curto = ano[2:]  # Pegar só os dois últimos dígitos do ano
            else:
                # Se não conseguir extrair, usar a coluna como está
                meses_labels.append(col)
                continue
                
            # Converter mês numérico para nome abreviado
            mes_nomes = {
                '01': 'Jan', '1': 'Jan',
                '02': 'Fev', '2': 'Fev',
                '03': 'Mar', '3': 'Mar',
                '04': 'Abr', '4': 'Abr',
                '05': 'Mai', '5': 'Mai',
                '06': 'Jun', '6': 'Jun',
                '07': 'Jul', '7': 'Jul',
                '08': 'Ago', '8': 'Ago',
                '09': 'Set', '9': 'Set',
                '10': 'Out', 
                '11': 'Nov', 
                '12': 'Dez'
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
        
        # Determinar o nome do produto a exibir no título
        nome_produto_cols = ['nome_produto', 'Produto']
        nome_produto = None
        for col in nome_produto_cols:
            if col in produto and produto[col]:
                nome_produto = produto[col]
                break
        if not nome_produto:
            nome_produto = f"Produto {id_produto}"
        
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
        print(f"Erro ao gerar gráfico para o produto {id_produto}: {str(e)}")
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
        
        if data is None or data.get("df_metricas_compra") is None:
            return "Dados não disponíveis", "Não foi possível carregar os dados dos produtos."
        
        try:
            # Obter o produto selecionado da tabela
            row_id = active_cell["row"]
            if row_id >= len(virtual_data):
                return "Erro de seleção", "A linha selecionada está fora dos limites da tabela."
                
            produto_selecionado = virtual_data[row_id]
            
            # Encontrar a coluna que contém o código do produto
            codigo_colunas = ['id_produto', 'Código', 'codigo', 'ID']
            desc_colunas = ['nome_produto', 'Produto', 'Descrição', 'Nome', 'descricao']
            
            id_produto = None
            for col in codigo_colunas:
                if col in produto_selecionado and produto_selecionado[col]:
                    id_produto = str(produto_selecionado[col])
                    break
                    
            if not id_produto:
                return "Código não encontrado", "Não foi possível identificar o código do produto."
                
            # Obter a descrição do produto
            nome_produto = None
            for col in desc_colunas:
                if col in produto_selecionado and produto_selecionado[col]:
                    nome_produto = produto_selecionado[col]
                    break
                    
            if not nome_produto:
                nome_produto = f"Produto {id_produto}"
            
            # Carregar dados de produtos
            df_produtos = pd.read_json(io.StringIO(data["df_metricas_compra"]), orient='split')
            
            # Verificar se o produto existe no dataframe
            # Tentar diferentes formatos de código para aumentar compatibilidade
            id_produto_encontrado = False
            for valor in [id_produto, int(id_produto) if id_produto.isdigit() else id_produto]:
                if valor in df_produtos['id_produto'].values:
                    id_produto = valor
                    id_produto_encontrado = True
                    break
            
            if not id_produto_encontrado:
                return f"Produto não encontrado: {id_produto}", html.Div([
                    html.P(f"O produto com código {id_produto} não foi encontrado na base de dados.", 
                        className="text-center text-muted my-4")
                ])
            
            # Chamar a função para criar o gráfico
            fig = criar_grafico_produto(df_produtos, id_produto)

            # Verificar se todos os custos são zero
            def todos_custos_zerados():
                custo1 = produto_selecionado.get('ultimo_preco_compra', 'R$ 0,00')
                custo2 = produto_selecionado.get('penultimo_preco_compra', 'R$ 0,00')
                custo3 = produto_selecionado.get('antepultimo_preco_compra', 'R$ 0,00')
                
                # Converter para string se for número
                if not isinstance(custo1, str): custo1 = str(custo1)
                if not isinstance(custo2, str): custo2 = str(custo2)
                if not isinstance(custo3, str): custo3 = str(custo3)
                
                # Verificar se todos são zero ou vazios
                return (custo1 == 'R$ 0,00' or custo1 == '') and (custo2 == 'R$ 0,00' or custo2 == '') and (custo3 == 'R$ 0,00' or custo3 == '')
                    
            # Adicionar título legível e detalhes
            header = None if todos_custos_zerados() else html.Div([
                # Informações de fornecedor 1
                html.H6("Últimas 3 Compras", className="mt-4 mb-3"),
                html.Div([
                    html.Div([
                        # Usando blocos com grande espaçamento horizontal
                        html.Div([
                            html.Span("Último-", className="font-weight-bold"),
                        ], style={"display": "inline-block", "marginRight": "10px"}),
                        html.Div([
                            html.Span("Data: ", className="font-weight-bold"),
                            html.Span(format_iso_date(produto_selecionado.get('data_ultima_compra', '-')))
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Qtd Comprada: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('ultima_qtd_comprada', '-')}")
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Preço de Compra: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('ultimo_preco_compra', '-')}")
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Fornecedor: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('ultimo_fornecedor', '-')}")
                        ], style={"display": "inline-block"}) if produto_selecionado.get('ultimo_fornecedor') and produto_selecionado.get('ultimo_fornecedor') != '0' and produto_selecionado.get('ultimo_fornecedor') != 0.0 else None
                    ], className="text-muted")
                ], className="mt-4 pb-3 border-bottom") if (
                produto_selecionado.get('ultimo_fornecedor') != '' or 
                produto_selecionado.get('ultimo_preco_compra') != 'R$ 0,00' and 
                produto_selecionado.get('ultimo_preco_compra') != 0.0) 
                else None,

                # Informações de fornecedor 2
                html.Div([
                    html.Div([
                        # Usando blocos com grande espaçamento horizontal
                        html.Div([
                            html.Span("Penúltimo-", className="font-weight-bold"),
                        ], style={"display": "inline-block", "marginRight": "10px"}),
                        html.Div([
                            html.Span("Data: ", className="font-weight-bold"),
                            html.Span(format_iso_date(produto_selecionado.get('data_penultima_compra', '-')))
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Qtd Comprada: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('penultima_qtd_comprada', '-')}")
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Custo de Compra: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('penultimo_preco_compra', '-')}")
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Fornecedor: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('penultimo_fornecedor', '-')}")
                        ], style={"display": "inline-block"}) if produto_selecionado.get('penultimo_fornecedor') and produto_selecionado.get('penultimo_fornecedor') != '0' and produto_selecionado.get('penultimo_fornecedor') != 0.0 else None
                    ], className="text-muted")
                ], className="mt-4 pb-3 border-bottom") if (
                produto_selecionado.get('penultimo_fornecedor') != '' or 
                produto_selecionado.get('penultimo_preco_compra') != 'R$ 0,00' and 
                produto_selecionado.get('penultimo_preco_compra') != 0.0) 
                else None,

                # Informações de fornecedor 3
                html.Div([
                    html.Div([
                        # Usando blocos com grande espaçamento horizontal
                        html.Div([
                            html.Span("Antepenúltimo-", className="font-weight-bold"),
                        ], style={"display": "inline-block", "marginRight": "10px"}),
                        html.Div([
                            html.Span("Data: ", className="font-weight-bold"),
                            html.Span(format_iso_date(produto_selecionado.get('data_antepenultima_compra', '-')))
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Qtd Comprada: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('anteultima_qtd_comprada', '-')}")
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Custo de Compra: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('antepenultimo_preco_compra', '-')}")
                        ], style={"display": "inline-block", "marginRight": "30px"}),
                        
                        html.Div([
                            html.Span("Fornecedor: ", className="font-weight-bold"),
                            html.Span(f"{produto_selecionado.get('antepenultimo_fornecedor', '-')}")
                        ], style={"display": "inline-block"}) if produto_selecionado.get('antepenultimo_fornecedor') and produto_selecionado.get('antepenultimo_fornecedor') != '0' and produto_selecionado.get('antepenultimo_fornecedor') != 0.0 else None
                    ], className="text-muted")
                ], className="mt-4 pb-3 border-bottom") if (
                produto_selecionado.get('antepenultimo_fornecedor') != '' or 
                produto_selecionado.get('antepenultimo_preco_compra') != 'R$ 0,00' and 
                produto_selecionado.get('antepenultimo_preco_compra') != 0.0) 
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
        else:
            # Contagem normal de todos os produtos por criticidade
            contagem_criticidade = df_criticos['criticidade'].value_counts().sort_index()
            # Adicionar o total
            total_produtos = len(df_criticos)

        # Adicionar o total
        total_series = pd.Series([total_produtos], index=['TODOS'])
        contagem_criticidade = pd.concat([contagem_criticidade, total_series])
        
        # Calcular porcentagens para anotações
        porcentagens = contagem_criticidade.copy()
        for idx in porcentagens.index:
            if idx == 'TODOS':
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
                'CRÍTICO': 'darkred',
                'MUITO BAIXO': 'orange',
                'BAIXO': color['warning'],
                'ADEQUADO': gradient_colors['green_gradient'][0],
                'EXCESSO': color['secondary'],
                'TODOS': color['primary']
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
        produto_col = 'nome_produto' if 'nome_produto' in df_criticos.columns else 'Produto' if 'Produto' in df_criticos.columns else None
        
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
        df_ordenado = df_filtrado.sort_values('cobertura_meses')
        
        # Selecionar os Top 20
        top_20 = df_ordenado.head(20)
        
        # Criar a coluna de exibição do produto
        top_20['produto_display'] = top_20[produto_col].apply(lambda x: (x[:30] + '...') if len(str(x)) > 30 else x)
        
        # Criar o gráfico
        fig = px.bar(
            top_20,
            y='produto_display',
            x='cobertura_meses',
            orientation='h',
            color='cobertura_meses',
            color_continuous_scale=['darkred', 'orange', color['warning']],
            range_color=[0, 50 if filtro_ativo else 100],  # Ajusta range de cores com base no filtro
            labels={'cobertura_meses': 'Cobertura (%)', 'produto_display': 'Produto'},
            template='plotly_white'
        )
        
        if 'id_produto' in top_20.columns:
            fig.update_traces(
                hovertemplate='<b>%{y}</b><br>Código: %{customdata[0]}<br>Cobertura: %{x:.1f}%',
                customdata=top_20[['id_produto']]
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
                x=row.cobertura_meses,
                y=row.produto_display,
                text=f"{row.cobertura_meses:.1f}%".replace(".", ","),
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
            produtos_criticos = len(df_filtrado[df_filtrado['criticidade'] == 'CRÍTICO'])
            produtos_muito_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'MUITO BAIXO'])
            produtos_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'BAIXO'])
            produtos_adequados = len(df_filtrado[df_filtrado['criticidade'] == 'ADEQUADO'])
            produtos_excesso = len(df_filtrado[df_filtrado['criticidade'] == 'EXCESSO'])
            
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
            produtos_criticos = len(df_criticos[df_criticos['criticidade'] == 'CRÍTICO'])
            produtos_muito_baixos = len(df_criticos[df_criticos['criticidade'] == 'MUITO BAIXO'])
            produtos_baixos = len(df_criticos[df_criticos['criticidade'] == 'BAIXO'])
            produtos_adequados = len(df_criticos[df_criticos['criticidade'] == 'ADEQUADO'])
            produtos_excesso = len(df_criticos[df_criticos['criticidade'] == 'EXCESSO'])
            
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
        [Input("filtro-criticos-ativo", "data"),
        Input("produtos-criticidade-bar", "clickData")],
        [State("selected-data", "data")]
    )
    def update_produtos_criticidade_list(filtro_ativo, clickData_bar, data):
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
        
        df_produtos = pd.read_json(io.StringIO(data["df_metricas_compra"]), orient='split')

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
        
        if trigger_id == 'produtos-criticidade-bar' and isinstance(clickData_bar, dict) and 'points' in clickData_bar:
            try:
                selected_criticidade = clickData_bar['points'][0]['x']
            except (KeyError, IndexError, TypeError):
                # Em caso de erro na estrutura do objeto, não selecionamos criticidade
                pass
        
        if selected_criticidade is None:
            return "Produtos do Nível de Cobertura Selecionado", html.Div([
                html.P("Não foi possível identificar a cobertura selecionada.", className="text-center text-muted my-4")
            ])
        
        # Checar se foi selecionado "Todos"
        if selected_criticidade == 'TODOS':
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
            "id_produto", 
            "nome_produto", 
            "estoque_atual", 
            # "critico", 
            "media_3M", 
            "cobertura_meses", 
            "sugestao_1m", 
            "sugestao_3m", 
            "data_ultima_compra", 
            "ultima_qtd_comprada", 
            "ultimo_preco_compra", 
            "ultimo_fornecedor", 
            "data_penultima_compra",
            "penultima_qtd_comprada",
            "penultimo_preco_compra",
            "peultimo_fornecedor",
            "data_antepenultima_compra",
            "antepenultima_qtd_comprada", 
            "antepenultimo_preco_compra", 
            "antepeultimo_fornecedor"
        ]
        
        # Usar apenas colunas que existem no DataFrame
        existing_columns = [col for col in display_columns if col in filtered_df.columns]
        if not existing_columns:
            return header_text, "Estrutura de dados incompatível para exibição de detalhes."
        
        # Renomear colunas para melhor visualização
        col_rename = {
            "id_produto": "Código",
            "nome_produto": "Produto",
            "estoque_atual": "Estoque Atual",
            # "critico": "Reposição Não-Local (Crítico)",
            "media_3M": "Consumo Médio (3M)",
            "cobertura_meses": "Cobertura (%)",
            "sugestao_1m": "Sugestão (1M)",
            "sugestao_3m": "Sugestão (3M)",
            # ultima compra
            "data_ultima_compra": "Data Última Compra",
            "ultima_qtd_comprada": "Última Quantidade Comprada",
            "ultimo_preco_compra": "Útimo Preço de Compra",
            "ultimo_fornecedor": "Útimo Fornecedor",
            # penúltima compra
            "data_penultima_compra": "Data Penúltima Compra",
            "penultima_qtd_comprada": "Penúltima Quantidade Comprada",
            "penultimo_preco_compra": "Penúltimo Preço de Compra",
            "peultimo_fornecedor": "Penúltimo Fornecedor",
            # antepenúltima compra
            "data_antepenultima_compra": "Data Antepenúltima Compra",
            "antepenultima_qtd_comprada": "Antepenúltima Quantidade Comprada",
            "antepenultimo_preco_compra": "Antepenúltimo Preço de Compra",
            "antepeultimo_fornecedor": "Antepenúltimo Fornecedor"
        }
        
        # Formatação especial para valores monetários e percentuais
        filtered_df_display = filtered_df[existing_columns].copy()
        
        if 'cobertura_meses' in filtered_df_display.columns:
            filtered_df_display['cobertura_meses'] = filtered_df_display['cobertura_meses'].apply(
                lambda x: f"{x:.1f}%".replace(".", ",")
            )
        
        # Verificar e converter para o formato correto antes de aplicar formatação
        for custo_col in ['ultimo_preco_compra', 'penultimo_preco_compra', 'antepenultimo_preco_compra']:
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
        for data_col in ['data_ultima_compra', 'data_penultima_compra', 'data_antepenultima_compra']:
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
                    "if": {"column_id": "cobertura_meses"},
                    "fontWeight": "bold",
                    "color": "darkred" if selected_criticidade == "CRÍTICO" else 
                            "orange" if selected_criticidade == "MUITO BAIXO" else
                            color['warning'] if selected_criticidade == "BAIXO" else
                            "green" if selected_criticidade == "ADEQUADO" else color['secondary']
                },
                {
                    "if": {"column_id": "ultimo_preco_compra"},
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