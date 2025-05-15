import io
import pandas as pd
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table

from utils import create_card
# Adicione esta função de callback após a função get_giro_estoque_layout
def register_giro_estoque_callbacks(app):
    @app.callback(
        Output("tabela-produtos-container", "children"),
        Output("tabela-produtos-container", "style"),
        Input("grafico-situacao-barras", "clickData"),
        State("store-data", "data")
    )
    def display_produtos_por_situacao(clickData, data):
        if clickData is None:
            return html.Div(), {'display': 'none'}
        
        try:
            # Extrair a situação selecionada do clique
            situacao = clickData['points'][0]['x']
            
            # Carregar dados
            df_curva_cobertura = pd.read_json(io.StringIO(data["df_analise_curva_cobertura"]), orient='split')
            
            # Filtrar por situação selecionada
            df_filtrado = df_curva_cobertura[df_curva_cobertura['situacao'] == situacao]
            
            # Selecionar colunas relevantes para exibição
            colunas_exibir = ['SKU', 'Descrição do Produto', 'Categoria', 'Estoque Total', 
                              'Curva ABC', 'Data Última Venda', 'Recência (dias)', 'situacao']
            
            df_exibir = df_filtrado[colunas_exibir].copy()
            
            # Formatar a data
            if 'Data Última Venda' in df_exibir.columns:
                df_exibir['Data Última Venda'] = pd.to_datetime(df_exibir['Data Última Venda']).dt.strftime('%d/%m/%Y')
            
            # Criar o componente da tabela
            tabela = create_card(
                f"Produtos com Situação: {situacao} ({len(df_exibir)} produtos)",
                dash_table.DataTable(
                    data=df_exibir.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in df_exibir.columns],
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'fontWeight': 'bold'
                    },
                    style_cell={
                        'textAlign': 'left',
                        'padding': '8px',
                        'minWidth': '100px', 'width': '150px', 'maxWidth': '300px',
                        'whiteSpace': 'normal',
                        'height': 'auto',
                    },
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': 'rgb(248, 248, 248)'
                        }
                    ],
                    sort_action='native',
                    filter_action='native'
                )
            )
            
            return tabela, {'display': 'block'}
            
        except Exception as e:
            print(f"Erro ao processar dados da tabela: {e}")
            return html.Div(f"Erro ao processar dados: {e}"), {'display': 'block'}