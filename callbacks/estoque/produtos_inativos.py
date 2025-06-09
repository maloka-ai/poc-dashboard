import os
import warnings
import dash
from dash import Input, Output, html, dash_table, dcc
import dotenv
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import io
import datetime
from datetime import datetime, timedelta

import psycopg2
from utils import formatar_numero
from utils.helpers import color

warnings.filterwarnings('ignore')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

def register_produtos_inativos_callbacks(app):
    """
    Registra todos os callbacks relacionados à página de produtos inativos.
    
    Args:
        app: A instância do aplicativo Dash
    """
    
    @app.callback(
        [Output("table-produtos-inativos", 'children'),
         Output("tempo-inatividade-display", 'children'),
         Output("contagem-produtos-inativos", 'children')],
        [Input("dias-inatividade-slider", 'value'),
         Input("selected-data", "data")]
    )
    def update_produtos_inativos(dias_selecionados, data):
        if data is None or data.get("df_analise_curva_cobertura") is None:
            return (
                "Dados não disponíveis.",
                "Sem dados de produtos",
                go.Figure(),
                "Nenhum produto encontrado"
            )
            
        # Carregar os dados do DataFrame
        df_produtos = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
        
        # Garantir que a coluna 'Data Última Venda' esteja no formato de data
        if 'Data Última Venda' in df_produtos.columns and df_produtos['Data Última Venda'].dtype == 'object':
            # Usar errors='coerce' para tratar valores problemáticos como "0" ou vazios
            df_produtos['Data Última Venda'] = pd.to_datetime(df_produtos['Data Última Venda'], errors='coerce')
            
            # Definir uma data padrão para valores que não puderam ser convertidos (NULL/NaT)
            # Usando a data atual para calcular corretamente os dias de inatividade
            data_atual = datetime.now()
            df_produtos['Data Última Venda'].fillna(data_atual, inplace=True)
        
        # Calcular os dias de inatividade
        data_atual = datetime.now()
        df_produtos['dias_inativo'] = df_produtos['Recência (dias)']
        
        # Filtramos os produtos inativos pelo número de dias
        df_filtrado = df_produtos[df_produtos['dias_inativo'] >= dias_selecionados].copy()
        
        # Formatamos o texto do período
        if dias_selecionados < 30:
            periodo_texto = f"{dias_selecionados} dias"
        elif dias_selecionados < 365:
            meses = dias_selecionados // 30
            periodo_texto = f"{meses} {'mês' if meses == 1 else 'meses'}"
        else:
            anos = dias_selecionados // 365
            periodo_texto = f"{anos} {'ano' if anos == 1 else 'anos'}"
        
        texto_tempo = f"Produtos inativos há mais de {periodo_texto}"
        texto_contagem = f"Total de {len(df_filtrado)} produtos encontrados"
        
        df_filtrado['Data Última Venda'] = pd.to_datetime(df_filtrado['Data Última Venda'], errors='coerce')
        # Formatamos as datas e valores para a tabela
        df_filtrado['recencia_formatada'] = df_filtrado['Data Última Venda'].dt.strftime('%d/%m/%Y')
        df_filtrado['dias_inativo_formatado'] = df_filtrado['dias_inativo'].apply(lambda x: formatar_numero(x, 0))
        
        # Determinamos quais colunas mostrar (adaptando se certas colunas existirem)
        columns = [
            {"name": "ID", "id": "SKU"},
            {"name": "Produto", "id": "Descrição do Produto"},
            {"name": "Estoque Atual", "id": "Estoque Total"},
            {"name": "Dias Inativo", "id": "dias_inativo_formatado"},
            {"name": "Última Venda", "id": "recencia_formatada"},
        ]

        # Criamos a tabela com os dados filtrados
        table = dash_table.DataTable(
            id='datatable-produtos-inativos',
            columns=columns,
            data=df_filtrado.reset_index().to_dict("records"),
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            page_size=10,
            export_format="xlsx",
            row_selectable="single",
            selected_rows=[],
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
                    "if": {"column_id": "dias_inativo_formatado"},
                    "fontWeight": "bold",
                    "color": color['accent']
                },
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "rgb(248, 248, 248)"
                }
            ]
        )
        
        # Adicionar informações sobre como usar a tabela
        if len(df_filtrado) > 0:
            table_container = html.Div([
                html.P([
                    "Exibindo ", 
                    html.Strong(formatar_numero(len(df_filtrado))), 
                    " produtos."
                ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"}),
                table
            ])
        else:
            table_container = html.Div([
                html.P("Nenhum produto inativo encontrado para o período selecionado.", className="text-center text-muted my-4"),
                html.I(className="fas fa-box-open fa-3x text-muted d-block text-center mb-3"),
                html.P("Tente reduzir o período de inatividade usando o slider acima.", className="text-center text-muted")
            ])
        
        return table_container, texto_tempo, texto_contagem
    
    @app.callback(
        [Output('produto-selecionado-store', 'data'),
        Output('produto-selecionado-info', 'children')],
        [Input('datatable-produtos-inativos', 'selected_rows'),
        Input('datatable-produtos-inativos', 'data')]
    )
    def armazenar_produto_selecionado(selected_rows, data):  
        # Verificar se há alguma linha selecionada
        if not selected_rows or not data:
            return None, html.Div("Selecione um produto na tabela para visualizar detalhes.", className="text-muted my-3")
        
        # Pegar o produto selecionado
        produto = data[selected_rows[0]]
        
        # Criar cabeçalho de informações - adapt column names to match what's actually in your data
        info = html.Div([
            html.H4(f"Produto: {produto['Descrição do Produto']}", className="mb-2"),
            html.Div([
                html.Span(f"Código: {produto['SKU']} | "),
                html.Span(f"Última Venda: {produto['recencia_formatada']} | ")
            ], className="text-muted mb-3")
        ])
    
        # Return using the correct ID field from your data
        return {'id_produto': produto['SKU'], 'desc_produto': produto['Descrição do Produto']}, info

    @app.callback(
        Output('produto-analise-detalhada', 'children'),
        [Input('produto-selecionado-store', 'data')]
    )
    def mostrar_analise_produto(produto_data):
        """
        Realiza a análise de estoque do produto selecionado e mostra os gráficos
        e informações detalhadas.
        """
        if not produto_data:
            return html.Div("")
            
        nome_produto = produto_data['desc_produto']
        
        try:
            # Conectar ao banco para obter os dados
            # (Aqui estamos simulando os dados para o exemplo)
            resultado = obter_dados_estoque_produto(nome_produto)
            
            if resultado is None:
                return html.Div([
                    html.P("Não foi possível analisar este produto. Verifique se existem dados de estoque disponíveis.",
                           className="text-danger")
                ])
                
            # Criar os gráficos e análises baseado no DataFrame retornado
            # Gráfico de evolução de estoque
            df_evolucao = resultado
            
            fig_evolucao = go.Figure()
            
            # Adicionar linha de estoque diário
            fig_evolucao.add_trace(go.Scatter(
                x=df_evolucao['data'],
                y=df_evolucao['estoque'],
                mode='lines',
                name='Estoque Diário',
                line=dict(color='#3498db', width=1.5),
                opacity=0.7
            ))
            
            # Adicionar média móvel
            fig_evolucao.add_trace(go.Scatter(
                x=df_evolucao['data'],
                y=df_evolucao['media_movel_7d'],
                mode='lines',
                name='Média Móvel (7 dias)',
                line=dict(color='#e74c3c', width=2)
            ))
            
            # Adicionar linha de estoque médio
            estoque_medio = df_evolucao['estoque'].mean()
            fig_evolucao.add_trace(go.Scatter(
                x=[df_evolucao['data'].iloc[0], df_evolucao['data'].iloc[-1]],
                y=[estoque_medio, estoque_medio],
                mode='lines',
                name=f'Estoque Médio: {estoque_medio:.1f}',
                line=dict(color='#2ecc71', width=2, dash='dash'),
                opacity=0.7
            ))
            
            # Destacar estoque atual
            estoque_atual = df_evolucao['estoque'].iloc[-1]
            fig_evolucao.add_trace(go.Scatter(
                x=[df_evolucao['data'].iloc[-1]],
                y=[estoque_atual],
                mode='markers',
                name=f'Estoque Atual: {estoque_atual:.0f}',
                marker=dict(color='#9b59b6', size=12)
            ))
            
            # Destacar valores extremos
            idx_min = df_evolucao['estoque'].idxmin()
            idx_max = df_evolucao['estoque'].idxmax()
            estoque_min = df_evolucao['estoque'].min()
            estoque_max = df_evolucao['estoque'].max()
            
            fig_evolucao.add_trace(go.Scatter(
                x=[df_evolucao['data'][idx_min]],
                y=[estoque_min],
                mode='markers',
                name=f'Mínimo: {estoque_min:.0f}',
                marker=dict(color='#e67e22', size=10)
            ))
            
            fig_evolucao.add_trace(go.Scatter(
                x=[df_evolucao['data'][idx_max]],
                y=[estoque_max],
                mode='markers',
                name=f'Máximo: {estoque_max:.0f}',
                marker=dict(color='#16a085', size=10)
            ))
            
            # Layout do gráfico
            fig_evolucao.update_layout(
                title='Evolução Diária do Estoque',
                xaxis_title='Data',
                yaxis_title='Quantidade em Estoque',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=40, r=40, t=60, b=40),
                height=450
            )
            
            # Gráfico de movimentações
            datas_mov = pd.date_range(start=df_evolucao['data'].min(), end=df_evolucao['data'].max(), freq='7D')
            np.random.seed(42)
            entradas = np.random.randint(0, 50, size=len(datas_mov))
            saidas = np.random.randint(0, 20, size=len(datas_mov))
            
            fig_movimentacao = go.Figure()
            
            # Barras de entrada
            fig_movimentacao.add_trace(go.Bar(
                x=datas_mov,
                y=entradas,
                name='Entradas',
                marker_color='green',
                opacity=0.7
            ))
            
            # Barras de saída (negativas)
            fig_movimentacao.add_trace(go.Bar(
                x=datas_mov,
                y=-saidas,
                name='Saídas',
                marker_color='red',
                opacity=0.7
            ))
            
            # Layout do gráfico
            fig_movimentacao.update_layout(
                title='Movimentações de Estoque',
                xaxis_title='Data',
                yaxis_title='Quantidade',
                barmode='relative',
                margin=dict(l=40, r=40, t=60, b=40),
                height=250
            )
            
            giro_estoque = df_evolucao.attrs['giro_estoque']
            cobertura_estoque = df_evolucao.attrs['cobertura_estoque']

            # Calcular estatísticas para resumo
            dias_zerados = sum(df_evolucao['estoque'] <= 0)
            pct_dias_zerados = (dias_zerados / len(df_evolucao)) * 100
            
            # Calcular tendência
            n_amostras = len(df_evolucao)
            n_amostras_10pct = max(1, int(n_amostras * 0.1))
            
            estoque_inicial = df_evolucao['estoque'].iloc[:n_amostras_10pct].mean()
            estoque_final = df_evolucao['estoque'].iloc[-n_amostras_10pct:].mean()
            
            if estoque_inicial > 0:
                variacao_pct = ((estoque_final - estoque_inicial) / estoque_inicial) * 100
            else:
                variacao_pct = float('inf') if estoque_final > 0 else 0
                
            # Determinar tendência
            if variacao_pct > 10:
                tendencia = "CRESCIMENTO"
                cor_tendencia = "text-success"
            elif variacao_pct < -10:
                tendencia = "REDUÇÃO"
                cor_tendencia = "text-danger"
            else:
                tendencia = "ESTÁVEL"
                cor_tendencia = "text-primary"
                
            
            # Criar o conteúdo completo
            return html.Div([
                # Gráfico de evolução do estoque
                html.Div([
                    dcc.Graph(
                        figure=fig_evolucao,
                        config={'displayModeBar': False}
                    )
                ], className="mb-4"),
                
                # Resumo estatístico
                html.Div([
                    html.H5("Resumo Estatístico", className="border-bottom pb-2 mb-3"),
                    html.Div([
                        # Primeira linha
                        html.Div([
                            # Coluna 1 - Estoque Atual
                            html.Div([
                                html.Div("Estoque Atual", className="small text-muted"),
                                html.Div(f"{estoque_atual:.0f}", className="h4 mb-0 font-weight-bold")
                            ], className="col-md-3"),
                            
                            # Coluna 2 - Estoque Médio
                            html.Div([
                                html.Div("Estoque Médio", className="small text-muted"),
                                html.Div(f"{estoque_medio:.1f}", className="h4 mb-0 font-weight-bold")
                            ], className="col-md-3"),
                            
                            # Coluna 3 - Estoque Mínimo
                            html.Div([
                                html.Div("Estoque Mínimo", className="small text-muted"),
                                html.Div(f"{estoque_min:.0f}", className="h4 mb-0 font-weight-bold")
                            ], className="col-md-3"),
                            
                            # Coluna 4 - Estoque Máximo
                            html.Div([
                                html.Div("Estoque Máximo", className="small text-muted"),
                                html.Div(f"{estoque_max:.0f}", className="h4 mb-0 font-weight-bold")
                            ], className="col-md-3"),

                            # Coluna 5 - Dias com Estoque Zero
                            html.Div([
                                html.Div("Dias com Estoque Zero", className="small text-muted"),
                                html.Div([
                                    html.Span(f"{dias_zerados}", className="h4 mb-0 font-weight-bold text-danger"),
                                    html.Span(f" ({pct_dias_zerados:.1f}%)", className="small text-muted ml-1")
                                ])
                            ], className="col-md-3"),
                        ], className="row mb-4"),
                        
                        # # Segunda linha
                        # html.Div([
                        #     # Coluna 1 - Dias com Estoque Zero
                        #     html.Div([
                        #         html.Div("Dias com Estoque Zero", className="small text-muted"),
                        #         html.Div([
                        #             html.Span(f"{dias_zerados}", className="h4 mb-0 font-weight-bold text-danger"),
                        #             html.Span(f" ({pct_dias_zerados:.1f}%)", className="small text-muted ml-1")
                        #         ])
                        #     ], className="col-md-3"),
                            
                            # Coluna 2 - Tendência
                            # html.Div([
                            #     html.Div("Tendência", className="small text-muted"),
                            #     html.Div([
                            #         html.Span(f"{tendencia}", className=f"h6 mb-0 font-weight-bold {cor_tendencia}"),
                            #         html.Span(f" ({variacao_pct:.1f}%)", className="small text-muted ml-1")
                            #     ])
                            # ], className="col-md-3"),

                            # # Coluna 3 - Giro de Estoque
                            # html.Div([
                            #     html.Div("Giro de Estoque (anual)", className="small text-muted"),
                            #     html.Div(f"{giro_estoque:.1f}", className="h4 mb-0 font-weight-bold")
                            # ], className="col-md-3"),
                            
                            # # Coluna 4 - Cobertura de Estoque
                            # html.Div([
                            #     html.Div("Cobertura de Estoque (dias)", className="small text-muted"),
                            #     html.Div(f"{cobertura_estoque:.1f}", className="h4 mb-0 font-weight-bold")
                            # ], className="col-md-3"),
                        # ], className="row mb-4"),
                    ])
                ], className="mb-4 p-3 bg-light rounded"),
                
            ])
            
        except Exception as e:
            return html.Div([
                html.P(f"Erro ao analisar o produto: {str(e)}",
                      className="text-danger")
            ])
    
    return None


################################################################################################################################################
#"Função para puxar dados da aws e fazer analise de giro de estoque do produto")
################################################################################################################################################
def obter_dados_estoque_produto(nome_produto):
    """
    Analisa o estoque diário de um produto específico pelo ID
    
    Args:
        id_produto: ID do produto para análise
    
    Returns:
        DataFrame com evolução diária e gráficos gerados
    """
    print(f"Iniciando análise para o produto ID: {nome_produto}")
    dotenv.load_dotenv()
    
    try:
        # Conectar ao PostgreSQL
        print("Conectando ao banco de dados...")
        conn = psycopg2.connect(
            host= os.getenv("DB_HOST"),
            dbname="add",
            user= os.getenv("DB_USER"),
            password= os.getenv("DB_PASS"),
            port= os.getenv("DB_PORT"),
        )
        
        # Consultar dados do produto
        query_produto = f"SELECT * FROM maloka_core.produto WHERE nome = '{nome_produto}'"
        df_produto = pd.read_sql_query(query_produto, conn)
        
        if len(df_produto) == 0:
            print(f"ERRO: Produto com ID {nome_produto} não encontrado.")
            return None
            
        # Se o produto foi encontrado, obtenha o ID para buscar os movimentos
        id_produto = df_produto['id_produto'].iloc[0] if 'id_produto' in df_produto.columns else None
        nome_produto_db = df_produto['nome'].iloc[0]
        print(f"Produto encontrado: {nome_produto_db}" + (f" (ID: {id_produto})" if id_produto else ""))
        
        
        # Consultar movimentos do produto
        query_estoque = f"""
        SELECT * FROM maloka_core.estoque_movimento 
        WHERE id_produto = '{id_produto}'
        ORDER BY data_movimento ASC
        """
        
        df_movimentos = pd.read_sql_query(query_estoque, conn)
        
        # Fechar conexão
        conn.close()
        
        if len(df_movimentos) == 0:
            print(f"ERRO: Nenhum movimento de estoque encontrado para o produto {id_produto}.")
            return None
            
        print(f"Encontrados {len(df_movimentos)} registros de movimento.")
        
        # Processamento dos dados
        df_movimentos['data_movimento'] = pd.to_datetime(df_movimentos['data_movimento'])
        
        # Determinar período de análise
        data_inicial = df_movimentos['data_movimento'].min()
        data_final = df_movimentos['data_movimento'].max()
        
        # Limitar a análise apenas ao último ano
        data_um_ano_atras = data_final - timedelta(days=365)
        data_inicial_original = data_inicial
        data_inicial = max(data_inicial, data_um_ano_atras)
        
        # Filtrar movimentos apenas do último ano
        df_movimentos = df_movimentos[df_movimentos['data_movimento'] >= data_inicial]
        
        print(f"Período de análise: {data_inicial.strftime('%d/%m/%Y')} até {data_final.strftime('%d/%m/%Y')}")
        print(f"Nota: Análise limitada ao último ano (dados originais começam em {data_inicial_original.strftime('%d/%m/%Y')})")
        
        # Criar DataFrame com todas as datas no intervalo
        todas_datas = pd.date_range(start=data_inicial, end=data_final, freq='D')
        df_diario = pd.DataFrame({'data': todas_datas})
        
        # Para cada data, encontrar o estoque mais recente (último movimento até essa data)
        estoque_diario = []
        
        # Obter o estoque inicial (último movimento antes do período analisado)
        movimentos_anteriores = df_movimentos[df_movimentos['data_movimento'] < data_inicial]
        estoque_inicial = 0
        if len(movimentos_anteriores) > 0:
            estoque_inicial = movimentos_anteriores.iloc[-1]['estoque_depois']
        
        for data in df_diario['data']:
            # Filtrar movimentos até esta data
            movimentos_ate_data = df_movimentos[df_movimentos['data_movimento'] <= data]
            
            if len(movimentos_ate_data) > 0:
                # Último movimento
                ultimo_movimento = movimentos_ate_data.iloc[-1]
                estoque = ultimo_movimento['estoque_depois']
                ultima_movimentacao = ultimo_movimento['data_movimento']
                tipo_ultimo_movimento = ultimo_movimento['tipo']
            else:
                estoque = estoque_inicial
                ultima_movimentacao = None
                tipo_ultimo_movimento = None
            
            estoque_diario.append({
                'data': data,
                'estoque': estoque,
                'ultima_movimentacao': ultima_movimentacao,
                'tipo_ultimo_movimento': tipo_ultimo_movimento
            })
       
        # Criar DataFrame com evolução diária
        df_evolucao_diaria = pd.DataFrame(estoque_diario)
        estoque_medio = df_evolucao_diaria['estoque'].mean()
        estoque_atual = df_evolucao_diaria['estoque'].iloc[-1]

        # Calcular dias com zero estoque
        dias_zerados = sum(df_evolucao_diaria['estoque'] <= 0)
        pct_dias_zerados = (dias_zerados / len(df_evolucao_diaria)) * 100
            
        # Adicionar média móvel para suavizar flutuações
        df_evolucao_diaria['media_movel_7d'] = df_evolucao_diaria['estoque'].rolling(window=7, min_periods=1).mean()
            
        # Calcular métricas de giro e cobertura de estoque
        # 1. Calcular total de saídas no período
        saidas = df_movimentos[df_movimentos['tipo'] == 'S']
        total_saidas = saidas['quantidade'].sum() if len(saidas) > 0 else 0
            
        # 2. Calcular média diária de saídas (demanda média diária)
        dias_periodo = (data_final - data_inicial).days + 1
        demanda_media_diaria = total_saidas / dias_periodo if dias_periodo > 0 else 0
            
        # 3. Calcular índice de giro de estoque (anualizado)
        # Giro = (Total de saídas no período / Estoque médio) * (365 / dias no período)
        if estoque_medio > 0:
            giro_estoque = (total_saidas / estoque_medio) * (365 / dias_periodo)
        else:
            giro_estoque = float('inf') if total_saidas > 0 else 0
        
        # 4. Calcular cobertura de estoque (em dias)
        # Cobertura = Estoque atual / demanda média diária
        if demanda_media_diaria > 0:
            cobertura_estoque = estoque_atual / demanda_media_diaria
        else:
            cobertura_estoque = float('inf') if estoque_atual > 0 else 0    
        
        # Calcular tendência (primeiros 10% vs últimos 10%)
        n_amostras = len(df_evolucao_diaria)
        n_amostras_10pct = max(1, int(n_amostras * 0.1))

        estoque_inicial = df_evolucao_diaria['estoque'].iloc[:n_amostras_10pct].mean()
        estoque_final = df_evolucao_diaria['estoque'].iloc[-n_amostras_10pct:].mean()

        # Adicionar giro e cobertura ao DataFrame como atributos personalizados
        df_evolucao_diaria.attrs['giro_estoque'] = giro_estoque
        df_evolucao_diaria.attrs['cobertura_estoque'] = cobertura_estoque
        df_evolucao_diaria.attrs['estoque_medio'] = estoque_medio
        df_evolucao_diaria.attrs['dias_zerados'] = dias_zerados
        df_evolucao_diaria.attrs['pct_dias_zerados'] = pct_dias_zerados

        # Adicionar também outros metadados úteis
        if estoque_inicial > 0:
            variacao_pct = ((estoque_final - estoque_inicial) / estoque_inicial) * 100
        else:
            variacao_pct = float('inf') if estoque_final > 0 else 0
            
        df_evolucao_diaria.attrs['variacao_pct'] = variacao_pct
        df_evolucao_diaria.attrs['demanda_media_diaria'] = demanda_media_diaria

        return df_evolucao_diaria
        
    except Exception as e:
        print(f"Erro na análise: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
