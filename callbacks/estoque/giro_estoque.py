import io
import pandas as pd
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table
from utils import color
from dash import no_update

def register_giro_estoque_callbacks(app):
    @app.callback(
        Output("tabela-produtos-container", "children"),
        Input("grafico-situacao-barras", "clickData"),
        State("selected-data", "data")
    )
    def display_produtos_por_situacao(clickData, data):
        print("Clickdata:", clickData)
        print("Data:", data)
        if clickData is None:
            return no_update
        
        try:
            # Verificar a estrutura do clickData antes de tentar acessar os índices
            if not clickData or 'points' not in clickData or not clickData['points'] or 'x' not in clickData['points'][0]:
                return html.Div([
                    html.P("Dados do clique inválidos ou incompletos", className="text-warning text-center my-4"),
                    html.I(className="fas fa-exclamation-circle fa-3x text-warning d-block text-center mb-3"),
                    html.P("Por favor, tente clicar novamente na barra desejada.", className="text-center text-muted")
                ])
            
            # Verificar se data contém os dados necessários
            if not data or 'df_analise_curva_cobertura' not in data:
                return html.Div([
                    html.P("Dados necessários não encontrados", className="text-danger text-center my-4"),
                    html.I(className="fas fa-database fa-3x text-danger d-block text-center mb-3"),
                    html.P("Os dados de análise não estão disponíveis.", className="text-center text-muted")
                ])
            
            # Extrair a situação selecionada do clique
            situacao = clickData['points'][0]['x']
            
            # Carregar dados com tratamento de erro
            try:
                df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
                if df_curva_cobertura.empty:
                    raise ValueError("DataFrame está vazio")
            except Exception as e:
                return html.Div([
                    html.P(f"Erro ao carregar os dados: {str(e)}", className="text-danger text-center my-4"),
                    html.I(className="fas fa-file-excel fa-3x text-danger d-block text-center mb-3")
                ])
            
            # Filtrar por situação selecionada
            df_filtrado = df_curva_cobertura[df_curva_cobertura['Situação do Produto'] == situacao]
            
            # Selecionar colunas relevantes para exibição
            colunas_exibir = [
                'SKU', 
                'ID Categoria',
                'Descrição do Produto', 
                'Categoria', 
                'Estoque Total', 
                'Situação do Produto', 
                'Curva ABC',
                #estoque loja 1, 2, 3 e 4
                # 
                'Data Última Venda'
            ]

            # Verificar se todas as colunas existem no DataFrame
            colunas_existentes = [col for col in colunas_exibir if col in df_curva_cobertura.columns]
            
            if not colunas_existentes:
                return html.Div([
                    html.P("Nenhuma coluna válida encontrada nos dados", className="text-warning text-center my-4"),
                    html.I(className="fas fa-columns fa-3x text-warning d-block text-center mb-3")
                ])
            
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
            
            # Adicionar informações sobre como usar a tabela
            if len(df_exibir) > 0:
                return html.Div([
                    html.P([
                        "Exibindo ", 
                        html.Strong(f"{len(df_exibir)}"), 
                        f" produtos com situação: {situacao}"
                    ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"}),
                    table
                ])
            else:
                return html.Div([
                    html.P(f"Nenhum produto com situação '{situacao}' encontrado.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-box-open fa-3x text-muted d-block text-center mb-3"),
                    html.P("Tente selecionar outra categoria no gráfico.", className="text-center text-muted")
                ])
            
        except Exception as e:
            print(f"Erro ao processar dados da tabela: {e}")
            return html.Div([
                html.P(f"Erro ao processar dados: {str(e)}", className="text-danger text-center my-4"),
                html.I(className="fas fa-exclamation-triangle fa-3x text-danger d-block text-center mb-3"),
                html.P("Por favor, tente novamente ou contate o suporte.", className="text-muted text-center")
            ])