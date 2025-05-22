import io
import dash
import pandas as pd
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table
from utils import color
from dash import no_update

def register_giro_estoque_callbacks(app):
    @app.callback(
        [
            Output("tabela-produtos-container", "children"),
            Output("grafico-curva-abc-barras", "figure"),
            Output("grafico-situacao-barras", "figure")
        ],
        [
            Input("grafico-curva-abc-barras", "clickData"),
            Input("grafico-situacao-barras", "clickData")
        ],
        [
            State("grafico-curva-abc-barras", "figure"),
            State("grafico-situacao-barras", "figure"),
            State("selected-data", "data")
        ]
    )
    def update_dashboard(curva_click_data, situacao_click_data, curva_figure, situacao_figure, data):
        ctx = dash.callback_context
        if not ctx.triggered:
            return no_update, no_update, no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        try:
            # Verificar se data contém os dados necessários
            if not data or 'df_analise_curva_cobertura' not in data:
                return html.Div([
                    html.P("Dados necessários não encontrados", className="text-danger text-center my-4"),
                    html.I(className="fas fa-database fa-3x text-danger d-block text-center mb-3"),
                    html.P("Os dados de análise não estão disponíveis.", className="text-center text-muted")
                ]), no_update, no_update
            
            # Carregar dados com tratamento de erro
            try:
                df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
                if df_curva_cobertura.empty:
                    raise ValueError("DataFrame está vazio")
            except Exception as e:
                return html.Div([
                    html.P(f"Erro ao carregar os dados: {str(e)}", className="text-danger text-center my-4"),
                    html.I(className="fas fa-file-excel fa-3x text-danger d-block text-center mb-3")
                ]), no_update, no_update
            
            # Filtros padrão (sem filtros)
            filtro_curva = None
            filtro_situacao = None
            
            # Extrair os filtros com base nos cliques
            if curva_click_data and 'points' in curva_click_data and curva_click_data['points']:
                filtro_curva = curva_click_data['points'][0]['x']
            
            if situacao_click_data and 'points' in situacao_click_data and situacao_click_data['points']:
                filtro_situacao = situacao_click_data['points'][0]['x']
            
            # Aplicar filtros ao DataFrame
            df_filtrado = df_curva_cobertura.copy()
            
            if filtro_curva:
                df_filtrado = df_filtrado[df_filtrado['Curva ABC'] == filtro_curva]
            
            if filtro_situacao:
                df_filtrado = df_filtrado[df_filtrado['Situação do Produto'] == filtro_situacao]
            
            # Atualizar o gráfico de curva ABC
            atualizar_grafico_curva_abc(curva_figure, filtro_curva)
            
            # Atualizar o gráfico de situação
            atualizar_grafico_situacao(situacao_figure, filtro_situacao)
            
            # Selecionar colunas relevantes para exibição na tabela
            colunas_base = [
                'SKU', 
                'ID Categoria',
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
                ]), curva_figure, situacao_figure
            
            df_exibir = df_filtrado[colunas_existentes].copy()
            
            # Formatar a data
            if 'Data Última Venda' in df_exibir.columns:
                df_exibir['Data Última Venda'] = pd.to_datetime(df_exibir['Data Última Venda'], errors='coerce').dt.strftime('%d/%m/%Y')
            
            # Criar componente da tabela
            table = dash_table.DataTable(
                id='datatable-situacao-produtos',
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
            
            # Cria o título da tabela com base nos filtros aplicados
            titulo_filtros = []
            if filtro_curva:
                titulo_filtros.append(f"Curva ABC: {filtro_curva}")
            if filtro_situacao:
                titulo_filtros.append(f"Situação: {filtro_situacao}")
            
            filtro_texto = " e ".join(titulo_filtros) if titulo_filtros else "Todos os produtos"
            
            # Adicionar informações sobre como usar a tabela
            if len(df_exibir) > 0:
                return html.Div([
                    html.P([
                        "Exibindo ", 
                        html.Strong(f"{len(df_exibir)}"), 
                        f" produtos - Filtros: {filtro_texto}"
                    ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"}),
                    table
                ]), curva_figure, situacao_figure
            else:
                return html.Div([
                    html.P(f"Nenhum produto encontrado para os filtros: {filtro_texto}", className="text-center text-muted my-4"),
                    html.I(className="fas fa-box-open fa-3x text-muted d-block text-center mb-3"),
                    html.P("Tente selecionar outros filtros nos gráficos.", className="text-center text-muted")
                ]), curva_figure, situacao_figure
            
        except Exception as e:
            print(f"Erro ao processar dados da tabela: {e}")
            return html.Div([
                html.P(f"Erro ao processar dados: {str(e)}", className="text-danger text-center my-4"),
                html.I(className="fas fa-exclamation-triangle fa-3x text-danger d-block text-center mb-3"),
                html.P("Por favor, tente novamente ou contate o suporte.", className="text-muted text-center")
            ]), no_update, no_update

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