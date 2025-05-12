import dash
from dash import Input, Output, html, dash_table, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go

from utils.formatters import formatar_percentual, formatar_moeda, formatar_numero, format_iso_date
from utils.helpers import color, button_style, create_metric_row

def register_predicao_callbacks(app):
    """
    Registra todos os callbacks relacionados à página de previsão de clientes.
    
    Args:
        app: A instância do aplicativo Dash
    """

    @app.callback(
        [Output("predicao-client-list-header", "children"),
        Output("predicao-client-list", "children")],
        Input("predicao-pie", "clickData"),
        Input("selected-data", "data")
    )
    def update_predicao_client_list(clickData_pie, data):
        ctx = dash.callback_context
        
        if not ctx.triggered:
            # No clicks yet
            return "Clientes da Categoria Selecionada", html.Div([
                html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4"),
                html.Div(className="text-center", children=[
                    html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                    html.P("Clique em uma categoria para visualizar detalhes", className="text-muted mt-2")
                ])
            ])
        
        if data is None or data.get("df_Previsoes") is None:
            return "Clientes da Categoria Selecionada", "Dados não disponíveis."
        
        df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split')
        
        # Determine which chart was clicked
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        selected_category = None
        if trigger_id == 'predicao-pie' and clickData_pie:
            selected_category = clickData_pie['points'][0]['label']
        
        if not selected_category:
            return "Clientes da Categoria Selecionada", html.Div([
                html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4")
            ])
        
        header_text = f"Clientes da Categoria: {selected_category}"
        filtered_df = df_Previsoes[df_Previsoes["categoria_previsao"] == selected_category]
        
        if filtered_df.empty:
            return header_text, html.Div([
                html.P("Nenhum cliente encontrado para a categoria selecionada.", className="text-center text-muted my-4"),
                html.I(className="fas fa-search fa-3x text-muted d-block text-center mb-3")
            ])
        
        # Verifica se as colunas esperadas existem no DataFrame
        display_columns = []
        col_rename = {}
        
        # Definir as colunas baseadas nas colunas disponíveis
        if 'nome_fantasia' in df_Previsoes.columns:
            display_columns = ["id_cliente", "nome_fantasia", "predicted_purchases_30d", "Recency", "Frequency", "Monetary"]
            col_rename = {
                "id_cliente": "Código",
                "nome_fantasia": "Cliente",
                "predicted_purchases_30d": "Previsão (30d)",
                "Recency": "Recência (dias)",
                "Frequency": "Frequência",
                "Monetary": "Valor (R$)"
            }
        elif 'nome' in df_Previsoes.columns:
            display_columns = ["id_cliente", "nome", "predicted_purchases_30d", "Recency", "Frequency", "Monetary"]
            col_rename = {
                "id_cliente": "Código",
                "nome": "Cliente",
                "predicted_purchases_30d": "Previsão (30d)",
                "Recency": "Recência (dias)",
                "Frequency": "Frequência",
                "Monetary": "Valor (R$)"
            }
        else:
            # Usar colunas padrão disponíveis
            display_columns = ["id_cliente", "predicted_purchases_30d", "Recency", "Frequency", "Monetary"]
            col_rename = {
                "id_cliente": "Código",
                "predicted_purchases_30d": "Previsão (30d)",
                "Recency": "Recência (dias)",
                "Frequency": "Frequência",
                "Monetary": "Valor (R$)"
            }
        
        # Adicionar colunas de contato se disponíveis
        if 'cpf' in df_Previsoes.columns:   
            display_columns.append("cpf")
            col_rename["cpf"] = "CPF"

        if 'cnpj' in df_Previsoes.columns:   
            display_columns.append("cnpj")
            col_rename["cnpj"] = "CNPJ"

        if 'email' in df_Previsoes.columns:
            display_columns.append("email")
            col_rename["email"] = "E-mail"
        
        if 'telefone' in df_Previsoes.columns:
            display_columns.append("telefone")
            col_rename["telefone"] = "Contato"
        
        # Usar apenas colunas que existem no DataFrame
        existing_columns = [col for col in display_columns if col in filtered_df.columns]
        if not existing_columns:
            return header_text, html.Div([
                html.P("Estrutura de dados incompatível para exibição de detalhes.", className="text-center text-muted my-4"),
                html.I(className="fas fa-exclamation-triangle fa-3x text-warning d-block text-center mb-3")
            ])
        
        # Format monetary values and predictions
        filtered_df_display = filtered_df[existing_columns].copy()
        if 'Monetary' in filtered_df_display.columns:
            filtered_df_display['Monetary'] = filtered_df_display['Monetary'].apply(lambda x: formatar_moeda(x))
        
        if 'predicted_purchases_30d' in filtered_df_display.columns:
            filtered_df_display['predicted_purchases_30d'] = filtered_df_display['predicted_purchases_30d'].apply(
                lambda x: f"{x:.2f}".replace(".", ",")
            )
        
        # Enhanced modern table with better styling
        table = dash_table.DataTable(
            id="predicao-client-table",  # ID único para esta tabela
            columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
            data=filtered_df_display.to_dict("records"),
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "10px 15px",
                "fontFamily": "Montserrat",
                "fontSize": "14px",
                "whiteSpace": "normal",
                "height": "auto"
            },
            style_header={
                "backgroundColor": color['primary'],
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
                "fontSize": "14px",
                "fontFamily": "Montserrat",
                "padding": "10px"
            },
            style_data_conditional=[
                {
                    "if": {"column_id": "predicted_purchases_30d"},
                    "fontWeight": "bold",
                    "color": color['secondary']
                },
                {
                    "if": {"column_id": "Monetary"},
                    "fontWeight": "bold"
                },
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "rgba(0, 0, 0, 0.05)"
                }
            ],
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            export_format="xlsx"
        )
        
        # Add a summary row above the table
        avg_predicted = filtered_df['predicted_purchases_30d'].mean()
        avg_monetary = filtered_df['Monetary'].mean() if 'Monetary' in filtered_df.columns else 0
        
        summary = html.Div([
            html.P([
                f"Exibindo ", 
                html.Strong(formatar_numero(len(filtered_df))), 
                f" clientes com ", 
                html.Strong(selected_category),
                f". Previsão média: ",
                html.Strong(f"{avg_predicted:.2f}".replace(".", ",") + " compras em 30 dias"),
                f". Valor monetário médio: ",
                html.Strong(formatar_moeda(avg_monetary))
            ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
        ])
        
        return header_text, html.Div([summary, table])
    
    # Adicione este callback ao arquivo paste-2.txt (register_predicao_callbacks)

    @app.callback(
        [Output("tabela-retorno-header", "children"),
        Output("tabela-retorno-content", "children")],
        [Input("client-filter-situacao", "value"),
        Input("client-filter-padrao-compra", "value")],
        Input("selected-data", "data")
    )
    def update_tabela_retorno(selected_situacao, selected_padrao, data):
        selected_situacao = selected_situacao if selected_situacao is not None else 'Todos'
        selected_padrao = selected_padrao if selected_padrao is not None else 'Todos'
        
        if data is None or data.get("df_Previsoes") is None or data.get("df_previsao_retorno") is None:
            return "Tabela de Previsão de Retorno", "Dados não disponíveis."
        
        # Obter dados de previsão de retorno
        df_previsao_retorno = pd.read_json(io.StringIO(data["df_previsao_retorno"]), orient='split')

        # Calcular média de dias para padrões de compra dinâmicos (se houver a coluna)
        if 'dias_ate_proxima' in df_previsao_retorno.columns:
            media_dias = df_previsao_retorno['dias_ate_proxima'].mean()
            media_meses = round(media_dias / 30)
        else:
            media_meses = 0
        
        # Formatar dados para exibição
        df_cliente_display = df_previsao_retorno.copy()
        
        # Adicionar coluna auxiliar para agrupar situações
        df_cliente_display['situacao_grupo'] = df_cliente_display['situacao'].apply(
            lambda x: "INATIVO" if "INATIVO" in str(x).upper() else "ATIVO"
        )
        
        # Formatar colunas para exibição
        df_cliente_display['prob_media_fmt'] = df_cliente_display['prob_media'].apply(
            lambda x: formatar_percentual(x * 100) if pd.notnull(x) else "N/A"
        )
        
        df_cliente_display['ultima_compra_fmt'] = df_cliente_display['ultima_compra'].apply(
            lambda x: format_iso_date(x) if pd.notnull(x) else "N/A"
        )
        
        df_cliente_display['proxima_compra_fmt'] = df_cliente_display['proxima_compra'].apply(
            lambda x: format_iso_date(x) if pd.notnull(x) else "N/A"
        )

        df_cliente_display['regularidade'] = df_cliente_display['regularidade'].apply(
            lambda x: f"{round(x, 2):.2f}".replace(".", ",") if pd.notnull(x) else "N/A"
        )
        
        # Aplicar filtros baseados na categoria de previsão e nos filtros selecionados
        filtered_df = df_cliente_display
        header_text = "Tabela de Previsão de Retorno"
        filter_info = []
        
        # Aplicar filtro de situação
        if selected_situacao and selected_situacao != 'Todos':
            filtered_df = filtered_df[filtered_df['situacao_grupo'] == selected_situacao]
            filter_info.append(f"Situação: {selected_situacao}")
        
        # Aplicar filtro de padrão de compra
        if selected_padrao and selected_padrao != 'Todos':
            filtered_df = filtered_df[filtered_df['padrao_compra'].str.contains(selected_padrao, case=False, na=False)]
            filter_info.append(f"Padrão: {selected_padrao}")
        
        # Construir o título baseado nos filtros aplicados
        if len(filter_info) > 0:
            filter_description = " | ".join(filter_info)
            header_text = f"Tabela de Previsão de Retorno - {filter_description}"
        
        # Verificar se existem resultados após aplicar os filtros
        if filtered_df.empty:
            return header_text, html.Div([
                html.P("Nenhum cliente encontrado com os filtros selecionados.", className="text-center text-muted my-4"),
                html.I(className="fas fa-filter fa-3x text-muted d-block text-center mb-3"),
                html.Div(
                    html.Button(
                        [html.I(className="fas fa-sync-alt me-2"), "Limpar Filtros"],
                        id="btn-clear-filters",
                        className="btn btn-outline-secondary mb-3",
                        style=button_style
                    ),
                    className="text-center"
                )
            ])
        
        # Preparar as colunas para exibição
        columns = [
            {"name": "Cliente", "id": "nome_cliente"},
            {"name": "Prob. Média", "id": "prob_media_fmt"},
            {"name": "Última Compra", "id": "ultima_compra_fmt"},
            {"name": "Próxima Compra", "id": "proxima_compra_fmt"},
            {"name": "Situação", "id": "situacao"},
            {"name": "Regularidade", "id": "regularidade"},
            {"name": "Padrão de Compra", "id": "padrao_compra"}
        ]
        
        # Enhanced modern table
        table = dash_table.DataTable(
            id='client-table',
            columns=columns,
            data=filtered_df.to_dict("records"),
            page_size=10,
            style_table={"overflowX": "auto"},
            style_cell={
                "textAlign": "left",
                "padding": "10px 15px",
                "fontFamily": "Montserrat",
                "fontSize": "14px"
            },
            style_header={
                "backgroundColor": color['primary'],
                "color": "white",
                "fontWeight": "bold",
                "textAlign": "center",
                "fontSize": "14px",
                "fontFamily": "Montserrat",
                "padding": "10px"
            },
            style_data_conditional=[
                {
                    "if": {"column_id": "prob_media_fmt"},
                    "fontWeight": "bold",
                    "color": color['secondary']
                },
                {
                    'if': {
                        'filter_query': '{situacao} contains "Ativo"'
                    },
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                    'color': 'rgb(75, 192, 192)'
                },
                {
                    'if': {
                        'filter_query': '{situacao} contains "Inativo"'
                    },
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                    'color': 'rgb(255, 99, 132)'
                },
                {
                    'if': {
                        'filter_query': '{prob_media_fmt} contains ">80%"'
                    },
                    'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                    'color': 'rgb(153, 102, 255)',
                    'fontWeight': 'bold'
                },
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "rgba(0, 0, 0, 0.05)"
                }
            ],
            sort_action="native",
            filter_action="native",
            row_selectable="single",
            selected_rows=[],
        )
        
        # Add a summary row above the table
        total_clientes = len(filtered_df)
        avg_prob = filtered_df['prob_media'].mean() * 100
        ativos = len(filtered_df[filtered_df['situacao_grupo'] == 'ATIVO'])
        inativos = len(filtered_df[filtered_df['situacao_grupo'] == 'INATIVO'])
        
        summary = html.Div([
            html.P([
                f"Exibindo ", 
                html.Strong(formatar_numero(total_clientes)), 
                f" clientes. ",
                f"Probabilidade média: ",
                html.Strong(formatar_percentual(avg_prob)),
                f". Ativos: ",
                html.Strong(formatar_numero(ativos)),
                f", Inativos: ",
                html.Strong(formatar_numero(inativos))
            ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
        ])
        
        # Action buttons
        action_buttons = html.Div([
            html.Button(
                [html.I(className="fas fa-file-excel me-2"), "Exportar para Excel"],
                id="btn-export-clientes",
                className="btn btn-success mb-3 me-2",
                style=button_style
            ),
            html.Button(
                [html.I(className="fas fa-sync-alt me-2"), "Limpar Filtros"],
                id="btn-clear-filters",
                className="btn btn-outline-secondary mb-3",
                style=button_style
            )
        ], className="mb-3")
        
        return header_text, html.Div([summary, action_buttons, table, html.Div(id="client-export-status")])
    
    @app.callback(
        Output('client-filter-padrao-compra', 'options'),
        [Input("selected-data", "data")]
    )
    def update_padrao_compra_options(data):
        options = [
            {"label": "Todos", "value": "Todos"},
            {"label": "diário - todos os dias úteis", "value": "diário - todos os dias úteis"},
            {"label": "3x por semana", "value": "3x por semana"},
            {"label": "2x por semana", "value": "2x por semana"},
            {"label": "1x por semana", "value": "1x por semana"},
            {"label": "2x por quinzena", "value": "2x por quinzena"},
            {"label": "1x por quinzena", "value": "1x por quinzena"},
            {"label": "1x por mês", "value": "1x por mês"},
            {"label": "1x a cada 2 meses", "value": "1x a cada 2 meses"},
            {"label": "1x a cada 3 meses", "value": "1x a cada 3 meses"},
            {"label": "1x a cada 4 meses", "value": "1x a cada 4 meses"},
            {"label": "1x a cada 5 meses", "value": "1x a cada 5 meses"},
            {"label": "1x a cada 6 meses", "value": "1x a cada 6 meses"}
        ]
        
        # Se houver dados disponíveis e contém informação de dias até próxima compra
        if data is not None and data.get("df_previsao_retorno") is not None:
            df_previsao_retorno = pd.read_json(io.StringIO(data["df_previsao_retorno"]), orient='split')
            if 'dias_ate_proxima' in df_previsao_retorno.columns:
                media_dias = df_previsao_retorno['dias_ate_proxima'].mean()
                media_meses = round(media_dias / 30)
                if media_meses > 0 and media_meses not in [1, 2, 3, 4, 5, 6]:
                    options.append({"label": f"1x a cada {media_meses} meses", "value": f"1x a cada {media_meses} meses"})
        
        return options
    
    @app.callback(
        [Output('client-filter-situacao', 'size'),
        Output('client-filter-padrao-compra', 'size')],
        [Input('selected-data', 'data')]
    )
    def set_select_size(data):
        # O parâmetro 'size' determina quantas opções são exibidas de cada vez
        return 2, 2

    @app.callback(
        [Output('cliente-detail-div', 'children'),
        Output('cliente-detail-message', 'style')],
        [Input('client-table', 'selected_rows'),
        Input('client-table', 'data')],
        Input("selected-data", "data")
    )
    def update_cliente_detail(selected_rows, table_data, data):
        # Esconder a mensagem se um cliente for selecionado
        hide_message_style = {'display': 'none'}
        show_message_style = {'display': 'block'}
        
        if not selected_rows or len(selected_rows) == 0 or not table_data or data is None or data.get("df_previsao_retorno") is None:
            return [], show_message_style
        
        # Obter o cliente selecionado da tabela
        selected_cliente = table_data[selected_rows[0]]['nome_cliente']
        
        # Obter dados de previsão de retorno
        df_previsao_retorno = pd.read_json(io.StringIO(data["df_previsao_retorno"]), orient='split')
        
        # Verificar se o cliente selecionado existe nos dados
        if selected_cliente not in df_previsao_retorno['nome_cliente'].values:
            return [
                html.Div(
                    className="text-center my-4",
                    children=[
                        html.I(className="fas fa-exclamation-circle fa-3x text-warning mb-3"),
                        html.P(f"Cliente '{selected_cliente}' não encontrado nos dados de previsão.", className="text-muted")
                    ]
                )
            ], hide_message_style
        
        # Filtrar os dados para o cliente selecionado
        cliente_data = df_previsao_retorno[df_previsao_retorno['nome_cliente'] == selected_cliente].iloc[0]

        regularidade_formatada = f"{round(cliente_data['regularidade'], 2):.2f}".replace(".", ",") if pd.notnull(cliente_data['regularidade']) else "N/A"
        
        # Criar cards para métricas do cliente
        cliente_metrics = [
            {"title": "Probabilidade Média", "value": formatar_percentual(cliente_data['prob_media'] * 100), "color": color['primary']},
            {"title": "Última Compra", "value": format_iso_date(cliente_data['ultima_compra']), "color": color['secondary']},
            {"title": "Próxima Compra (Prev.)", "value": format_iso_date(cliente_data['proxima_compra']), "color": color['accent']},
            {"title": "Total de Compras", "value": formatar_numero(cliente_data['total_compras_historico']), "color": color['success']}
        ]
        
        cliente_metrics_row = create_metric_row(cliente_metrics)
        
        # Informações adicionais em formato de tabela
        info_table = html.Table(
            className="table table-striped table-hover",
            children=[
                html.Tbody([
                    html.Tr([html.Td("ID do Cliente"), html.Td(cliente_data['id_cliente'])]),
                    html.Tr([html.Td("Situação"), html.Td(cliente_data['situacao'])]),
                    html.Tr([html.Td("Regularidade"), html.Td(regularidade_formatada)]),
                    html.Tr([html.Td("Padrão de Compra"), html.Td(cliente_data['padrao_compra'])]),
                ])
            ]
        )
        
        return [
            cliente_metrics_row,
            html.Div(className="my-4", children=[
                html.H5("Informações Adicionais", className="mb-3"),
                info_table
            ]),
            # Espaço para gráfico de histórico (opcional)
            html.Div(id="cliente-historico-container")
        ], hide_message_style
    
    # Callback para filtrar clientes por situação
    @app.callback(
        Output('client-table', 'data'),
        [Input('client-filter-situacao', 'value'),
        Input('client-filter-padrao-compra', 'value'),
        Input('predicao-pie', 'clickData'),
        Input('predicao-bar', 'clickData')],
        Input("selected-data", "data")
    )
    def filter_clients_by_status_and_padrao(selected_situacao, selected_padrao, clickData_pie, clickData_bar, data):
        ctx = dash.callback_context
        
        if data is None or data.get("df_previsao_retorno") is None:
            return []
                
        # Obter dados de previsão de retorno
        df_previsao_retorno = pd.read_json(io.StringIO(data["df_previsao_retorno"]), orient='split')
        
        # Formatar dados para exibição
        df_cliente_display = df_previsao_retorno.copy()
        
        # Adicionar coluna auxiliar para agrupar situações em ATIVO ou INATIVO
        df_cliente_display['situacao_grupo'] = df_cliente_display['situacao'].apply(
            lambda x: "INATIVO" if "INATIVO" in str(x).upper() else "ATIVO"
        )
        
        # Formatar colunas para exibição
        df_cliente_display['prob_media_fmt'] = df_cliente_display['prob_media'].apply(
            lambda x: formatar_percentual(x * 100) if pd.notnull(x) else "N/A"
        )
        
        df_cliente_display['ultima_compra_fmt'] = df_cliente_display['ultima_compra'].apply(
            lambda x: format_iso_date(x) if pd.notnull(x) else "N/A"
        )
        
        df_cliente_display['proxima_compra_fmt'] = df_cliente_display['proxima_compra'].apply(
            lambda x: format_iso_date(x) if pd.notnull(x) else "N/A"
        )
        
        # Aplicar filtro de situação
        if selected_situacao and selected_situacao != 'Todos':
            df_cliente_display = df_cliente_display[df_cliente_display['situacao_grupo'] == selected_situacao]
        
        # Aplicar filtro de padrão de compra
        if selected_padrao and selected_padrao != 'Todos':
            df_cliente_display = df_cliente_display[df_cliente_display['padrao_compra'].str.contains(selected_padrao, case=False, na=False)]
        
        # Verificar se houve clique nos gráficos e aplicar filtro adicional
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
        
        if trigger_id == 'predicao-pie' and clickData_pie:
            categoria = clickData_pie['points'][0]['label']
            if categoria == "Alta Probabilidade de Compra":
                df_cliente_display = df_cliente_display[df_cliente_display['prob_media'] > 0.5]
            elif categoria == "Baixa Probabilidade de Compra":
                df_cliente_display = df_cliente_display[df_cliente_display['prob_media'] <= 0.5]
        
        elif trigger_id == 'predicao-bar' and clickData_bar:
            # Aqui você pode adicionar lógica para filtrar baseado no clique do gráfico de barras
            # Por exemplo, pode ser algo como:
            categoria = clickData_bar['points'][0]['x']
            if categoria == "Alta Probabilidade de Compra":
                df_cliente_display = df_cliente_display[df_cliente_display['prob_media'] > 0.5]
            elif categoria == "Baixa Probabilidade de Compra":
                df_cliente_display = df_cliente_display[df_cliente_display['prob_media'] <= 0.5]
                
        return df_cliente_display.to_dict('records')
    
    # Callback para o botão de exportação Excel
    @app.callback(
        Output("client-export-status", "children"),
        Input("btn-export-clientes", "n_clicks"),
        Input("selected-data", "data"),
        prevent_initial_call=True
    )
    def export_clientes_to_excel(n_clicks, data):
        if n_clicks is None or data is None or data.get("df_previsao_retorno") is None:
            return ""
            
        # Este callback apenas simularia a exportação
        # Em um ambiente real, você usaria dcc.Download e send_data_frame para exportar
        
        return html.Div([
            html.P("Dados exportados com sucesso!", className="text-success mt-2"),
            html.P("Arquivo salvo como: previsao_retorno_clientes.xlsx", className="text-muted small")
        ])
    
    @app.callback(
        [Output('client-filter-situacao', 'value'),
        Output('client-filter-padrao-compra', 'value')],
        [Input('btn-clear-filters', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_filters(n_clicks):
        if n_clicks:
            return 'Todos', 'Todos'
        # Esta condição não deveria ocorrer devido ao prevent_initial_call
        return dash.no_update, dash.no_update
    
    # Callback para destacar a linha selecionada na tabela
    @app.callback(
        Output('client-table', 'style_data_conditional'),
        [Input('client-table', 'selected_rows')]
    )
    def highlight_selected_row(selected_rows):
        # Estilos básicos condicionais
        conditional_styles = [
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgba(0, 0, 0, 0.05)'
            },
            {
                'if': {
                    'filter_query': '{situacao} contains "Ativo"'
                },
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'color': 'rgb(75, 192, 192)'
            },
            {
                'if': {
                    'filter_query': '{situacao} contains "Inativo"'
                },
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'color': 'rgb(255, 99, 132)'
            },
            {
                'if': {
                    'filter_query': '{prob_media_fmt} contains ">80%"'
                },
                'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                'color': 'rgb(153, 102, 255)',
                'fontWeight': 'bold'
            }
        ]
        
        # Adicionar estilo para linha selecionada
        if selected_rows and len(selected_rows) > 0:
            selected_style = {
                'if': {'row_index': selected_rows[0]},
                'backgroundColor': 'rgba(0, 123, 255, 0.2)',
                'color': 'rgb(0, 123, 255)',
                'fontWeight': 'bold',
                'border': '2px solid rgb(0, 123, 255)',
                'boxShadow': '0 0 10px rgba(0, 123, 255, 0.3)'
            }
            conditional_styles.append(selected_style)
        
        return conditional_styles
    
    @app.callback(
        [Output('cliente-selecionado-indicador', 'style'),
        Output('cliente-selecionado-nome', 'children')],
        [Input('client-table', 'selected_rows'),
        Input('client-table', 'data')]
    )
    def update_cliente_selecionado_indicador(selected_rows, table_data):
        if not selected_rows or len(selected_rows) == 0 or not table_data:
            return {'display': 'none'}, ""
        
        selected_cliente = table_data[selected_rows[0]]['nome_cliente']
        return {'display': 'block'}, selected_cliente
    
    @app.callback(
        Output('client-table', 'selected_rows'),
        [Input('btn-limpar-selecao', 'n_clicks')],
        prevent_initial_call=True
    )
    def clear_selected_rows(n_clicks):
        if n_clicks:
            return []
        return dash.no_update