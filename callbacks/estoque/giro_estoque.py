import io
import pandas as pd
from dash import html, callback_context
from dash.dependencies import Input, Output, State
from dash import dash_table
from utils import color
from dash import no_update

def register_giro_estoque_callbacks(app):

    @app.callback(
        [Output("lista-categorias-content", "children"),
        Output("pagina-atual", "children"),
        Output("btn-pagina-anterior", "disabled"),
        Output("btn-proxima-pagina", "disabled")],
        [Input("btn-pagina-anterior", "n_clicks"),
        Input("btn-proxima-pagina", "n_clicks")],
        [State("pagina-atual", "children"),
        State("selected-data", "data")]
    )
    def atualizar_paginacao(btn_anterior, btn_proximo, pagina_atual_str, data):
        ctx = callback_context
        if not ctx.triggered:
            # Primeira renderização, exibir a primeira página
            pagina_atual = 1
        else:
            # Determinar qual botão foi clicado
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
            pagina_atual = int(pagina_atual_str)
            
            if trigger_id == "btn-pagina-anterior" and pagina_atual > 1:
                pagina_atual -= 1
            elif trigger_id == "btn-proxima-pagina":
                pagina_atual += 1
        
        # Carregar dados do Store
        df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
        df_com_vendas = df_curva_cobertura[df_curva_cobertura['Curva ABC'].isin(['A', 'B', 'C'])]
        categoria_vendas = df_com_vendas.groupby('Categoria')['valor_vendas_ultimos_90_dias'].sum().reset_index()
        total_vendas = categoria_vendas['valor_vendas_ultimos_90_dias'].sum()
        categoria_vendas['Porcentagem'] = (categoria_vendas['valor_vendas_ultimos_90_dias'] / total_vendas * 100).round(1)
        categoria_vendas = categoria_vendas.sort_values(by='valor_vendas_ultimos_90_dias', ascending=False)
        
        # Criar elementos da lista ordenada
        lista_categorias = []
        for index, row in categoria_vendas.iterrows():
            categoria = row['Categoria']
            valor = row['valor_vendas_ultimos_90_dias']
            porcentagem = row['Porcentagem']
            
            # Formatação...
            valor_formatado = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            item = html.Div([
                html.Div([
                    # html.Span(f"{index + 1}. ", className="me-1 text-muted"),
                    html.Span(f"{categoria}", style={"fontWeight": "bold"}),
                ], className="d-flex align-items-center"),
                html.Div([
                    html.Span(f"{valor_formatado}", className="me-2"),
                    html.Span(f"({porcentagem}%)", className="text-muted"),
                ], className="d-flex align-items-center"),
            ], className="d-flex justify-content-between py-2 border-bottom")
            
            lista_categorias.append(item)
        
        # Dividir a lista em páginas
        itens_por_pagina = 10
        total_paginas = (len(lista_categorias) + itens_por_pagina - 1) // itens_por_pagina
        
        # Calcular o índice inicial e final para a página atual
        inicio = (pagina_atual - 1) * itens_por_pagina
        fim = min(inicio + itens_por_pagina, len(lista_categorias))
        
        # Selecionar apenas os itens da página atual
        itens_pagina_atual = lista_categorias[inicio:fim]
        
        # Estados dos botões de paginação
        btn_anterior_disabled = pagina_atual <= 1
        btn_proximo_disabled = pagina_atual >= total_paginas
        
        return itens_pagina_atual, str(pagina_atual), btn_anterior_disabled, btn_proximo_disabled

    # Callback para o gráfico de Curva ABC e sua tabela
    @app.callback(
        [
            Output("tabela-curva-abc-container", "children"),
            Output("grafico-curva-abc-barras", "figure")
        ],
        [
            Input("grafico-curva-abc-barras", "clickData")
        ],
        [
            State("grafico-curva-abc-barras", "figure"),
            State("selected-data", "data")
        ]
    )
    def update_curva_abc_table(curva_click_data, curva_figure, data):
        if not curva_click_data:
            return no_update, no_update
        
        try:
            # Verificar se data contém os dados necessários
            if not data or 'df_analise_curva_cobertura' not in data:
                return html.Div([
                    html.P("Dados necessários não encontrados", className="text-danger text-center my-4"),
                    html.I(className="fas fa-database fa-3x text-danger d-block text-center mb-3"),
                    html.P("Os dados de análise não estão disponíveis.", className="text-center text-muted")
                ]), no_update
            
            # Carregar dados com tratamento de erro
            try:
                df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
                if df_curva_cobertura.empty:
                    raise ValueError("DataFrame está vazio")
            except Exception as e:
                return html.Div([
                    html.P(f"Erro ao carregar os dados: {str(e)}", className="text-danger text-center my-4"),
                    html.I(className="fas fa-file-excel fa-3x text-danger d-block text-center mb-3")
                ]), no_update
            
            # Extrair o filtro com base no clique
            filtro_curva = None
            if curva_click_data and 'points' in curva_click_data and curva_click_data['points']:
                filtro_curva = curva_click_data['points'][0]['x']
            
            # Aplicar filtro ao DataFrame
            df_filtrado = df_curva_cobertura.copy()
            if filtro_curva:
                df_filtrado = df_filtrado[df_filtrado['Curva ABC'] == filtro_curva]
            
            # Atualizar o gráfico de curva ABC
            atualizar_grafico_curva_abc(curva_figure, filtro_curva)
            
            # Selecionar colunas relevantes para exibição na tabela
            colunas_base = [
                'SKU', 
                'ID Categoria',
                'EAN',
                'Descrição do Produto', 
                'Categoria', 
                'Estoque Total', 
                'Situação do Produto', 
                'Curva ABC',
                'Data Última Venda'
            ]
            
            # Identificar e adicionar colunas de estoque por loja disponíveis
            colunas_estoque_loja = [col for col in df_curva_cobertura.columns if col.startswith('Estoque Loja')]
            
            # Combinar colunas base com colunas de estoque de loja
            colunas_exibir = colunas_base + colunas_estoque_loja
            # Verificar se todas as colunas existem no DataFrame
            colunas_existentes = [col for col in colunas_exibir if col in df_filtrado.columns]
            
            if not colunas_existentes:
                return html.Div([
                    html.P("Nenhuma coluna válida encontrada nos dados", className="text-warning text-center my-4"),
                    html.I(className="fas fa-columns fa-3x text-warning d-block text-center mb-3")
                ]), curva_figure
            
            df_exibir = df_filtrado[colunas_existentes].copy()
            
            # Formatar a data
            if 'Data Última Venda' in df_exibir.columns:
                df_exibir['Data Última Venda'] = pd.to_datetime(df_exibir['Data Última Venda'], errors='coerce').dt.strftime('%d/%m/%Y')
            
            # Criar componente da tabela
            table = dash_table.DataTable(
                id='datatable-curva-abc',
                columns=[{"name": col, "id": col} for col in df_exibir.columns],
                data=df_exibir.reset_index().to_dict("records"),
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
                        "if": {"column_id": "Curva ABC"},
                        "fontWeight": "bold",
                        "color": color['accent']
                    },
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ]
            )
            
            titulo_filtro = f"Curva ABC: {filtro_curva}" if filtro_curva else "Todos os produtos"
            
            if len(df_exibir) > 0:
                return html.Div([
                    html.P([
                        "Exibindo ", 
                        html.Strong(f"{len(df_exibir)}"), 
                        f" produtos - {titulo_filtro}"
                    ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"}),
                    table
                ]), curva_figure
            else:
                return html.Div([
                    html.P(f"Nenhum produto encontrado para {titulo_filtro}", className="text-center text-muted my-4"),
                    html.I(className="fas fa-box-open fa-3x text-muted d-block text-center mb-3")
                ]), curva_figure
            
        except Exception as e:
            print(f"Erro ao processar dados da tabela Curva ABC: {e}")
            return html.Div([
                html.P(f"Erro ao processar dados: {str(e)}", className="text-danger text-center my-4"),
                html.I(className="fas fa-exclamation-triangle fa-3x text-danger d-block text-center mb-3")
            ]), no_update
    
    # Callback para o gráfico de Situação e sua tabela
    @app.callback(
        [
            Output("tabela-situacao-container", "children"),
            Output("grafico-situacao-barras", "figure")
        ],
        [
            Input("grafico-situacao-barras", "clickData")
        ],
        [
            State("grafico-situacao-barras", "figure"),
            State("selected-data", "data")
        ]
    )
    def update_situacao_table(situacao_click_data, situacao_figure, data):
        if not situacao_click_data:
            return no_update, no_update
        
        try:
            # Verificar se data contém os dados necessários
            if not data or 'df_analise_curva_cobertura' not in data:
                return html.Div([
                    html.P("Dados necessários não encontrados", className="text-danger text-center my-4"),
                    html.I(className="fas fa-database fa-3x text-danger d-block text-center mb-3"),
                    html.P("Os dados de análise não estão disponíveis.", className="text-center text-muted")
                ]), no_update
            
            # Carregar dados com tratamento de erro
            try:
                df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
                if df_curva_cobertura.empty:
                    raise ValueError("DataFrame está vazio")
            except Exception as e:
                return html.Div([
                    html.P(f"Erro ao carregar os dados: {str(e)}", className="text-danger text-center my-4"),
                    html.I(className="fas fa-file-excel fa-3x text-danger d-block text-center mb-3")
                ]), no_update
            
            # Extrair o filtro com base no clique
            filtro_situacao = None
            if situacao_click_data and 'points' in situacao_click_data and situacao_click_data['points']:
                filtro_situacao = situacao_click_data['points'][0]['x']
            
            # Aplicar filtro ao DataFrame
            df_filtrado = df_curva_cobertura.copy()
            if filtro_situacao:
                df_filtrado = df_filtrado[df_filtrado['Situação do Produto'] == filtro_situacao]
            
            # Atualizar o gráfico de situação
            atualizar_grafico_situacao(situacao_figure, filtro_situacao)
            
            # Selecionar colunas relevantes para exibição na tabela
            colunas_base = [
                'SKU', 
                'ID Categoria',
                'EAN',
                'Descrição do Produto', 
                'Categoria', 
                'Estoque Total', 
                'Situação do Produto', 
                'Curva ABC',
                'Data Última Venda'
            ]
            
            # Identificar e adicionar colunas de estoque por loja disponíveis
            colunas_estoque_loja = [col for col in df_curva_cobertura.columns if col.startswith('Estoque Loja')]
            
            # Combinar colunas base com colunas de estoque de loja
            colunas_exibir = colunas_base + colunas_estoque_loja
            # Verificar se todas as colunas existem no DataFrame
            colunas_existentes = [col for col in colunas_exibir if col in df_filtrado.columns]
            
            if not colunas_existentes:
                return html.Div([
                    html.P("Nenhuma coluna válida encontrada nos dados", className="text-warning text-center my-4"),
                    html.I(className="fas fa-columns fa-3x text-warning d-block text-center mb-3")
                ]), situacao_figure
            
            df_exibir = df_filtrado[colunas_existentes].copy()
            
            # Formatar a data
            if 'Data Última Venda' in df_exibir.columns:
                df_exibir['Data Última Venda'] = pd.to_datetime(df_exibir['Data Última Venda'], errors='coerce').dt.strftime('%d/%m/%Y')
            
            # Criar componente da tabela
            table = dash_table.DataTable(
                id='datatable-situacao',
                columns=[{"name": col, "id": col} for col in df_exibir.columns],
                data=df_exibir.reset_index().to_dict("records"),
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
                        "if": {"column_id": "Situação do Produto"},
                        "fontWeight": "bold",
                        "color": color['accent']
                    },
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ]
            )
            
            titulo_filtro = f"Situação: {filtro_situacao}" if filtro_situacao else "Todos os produtos"
            
            if len(df_exibir) > 0:
                return html.Div([
                    html.P([
                        "Exibindo ", 
                        html.Strong(f"{len(df_exibir)}"), 
                        f" produtos - {titulo_filtro}"
                    ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"}),
                    table
                ]), situacao_figure
            else:
                return html.Div([
                    html.P(f"Nenhum produto encontrado para {titulo_filtro}", className="text-center text-muted my-4"),
                    html.I(className="fas fa-box-open fa-3x text-muted d-block text-center mb-3")
                ]), situacao_figure
            
        except Exception as e:
            print(f"Erro ao processar dados da tabela Situação: {e}")
            return html.Div([
                html.P(f"Erro ao processar dados: {str(e)}", className="text-danger text-center my-4"),
                html.I(className="fas fa-exclamation-triangle fa-3x text-danger d-block text-center mb-3")
            ]), no_update

    def atualizar_grafico_curva_abc(figura, filtro_curva):
        if not filtro_curva:
            # Restaurar a opacidade de todas as barras
            for i in range(len(figura['data'])):
                figura['data'][i]['marker']['opacity'] = 0.8
        else:
            # Diminuir a opacidade das barras não selecionadas
            for i in range(len(figura['data'])):
                if figura['data'][i]['x'][0] == filtro_curva:
                    figura['data'][i]['marker']['opacity'] = 0.8
                else:
                    figura['data'][i]['marker']['opacity'] = 0.3
        return figura

    def atualizar_grafico_situacao(figura, filtro_situacao):
        if not filtro_situacao:
            # Restaurar a opacidade de todas as barras
            for i in range(len(figura['data'])):
                figura['data'][i]['marker']['opacity'] = 0.8
        else:
            # Diminuir a opacidade das barras não selecionadas
            for i in range(len(figura['data'][0]['x'])):
                if figura['data'][0]['x'][i] == filtro_situacao:
                    figura['data'][0]['marker']['opacity'] = [0.8 if x == filtro_situacao else 0.3 for x in figura['data'][0]['x']]
        return figura