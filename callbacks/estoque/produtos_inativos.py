import dash
from dash import Input, Output, html, dash_table
import plotly.graph_objects as go
import pandas as pd
import io
import datetime
from utils import formatar_numero
from utils.helpers import color

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
        if data is None or data.get("df_relatorio_produtos") is None:
            return (
                "Dados não disponíveis.",
                "Sem dados de produtos",
                go.Figure(),
                "Nenhum produto encontrado"
            )
            
        # Carregar os dados do DataFrame
        df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')
        
        # Garantir que a coluna 'recencia' esteja no formato de data
        if 'recencia' in df_produtos.columns and df_produtos['recencia'].dtype == 'object':
            # Usar errors='coerce' para tratar valores problemáticos como "0" ou vazios
            df_produtos['recencia'] = pd.to_datetime(df_produtos['recencia'], errors='coerce')
            
            # Definir uma data padrão para valores que não puderam ser convertidos (NULL/NaT)
            # Usando a data atual para calcular corretamente os dias de inatividade
            data_atual = datetime.datetime.now()
            df_produtos['recencia'].fillna(data_atual, inplace=True)
        df_produtos['antiguidade'] = pd.to_datetime(df_produtos['antiguidade'], errors='coerce')
        
        # Calcular os dias de inatividade
        data_atual = datetime.datetime.now()
        df_produtos['dias_inativo'] = (data_atual - df_produtos['recencia']).dt.days
        
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
        
        # Formatamos as datas e valores para a tabela
        df_filtrado['recencia_formatada'] = df_filtrado['recencia'].dt.strftime('%d/%m/%Y')
        df_filtrado['antiguidade_formatada'] = df_filtrado['antiguidade'].dt.strftime('%d/%m/%Y')
        df_filtrado['dias_inativo_formatado'] = df_filtrado['dias_inativo'].apply(lambda x: formatar_numero(x, 0))
        
        # Determinamos quais colunas mostrar (adaptando se certas colunas existirem)
        columns = [
            {"name": "Código", "id": "cd_produto"},
            {"name": "Produto", "id": "desc_produto"},
            {"name": "Estoque Atual", "id": "estoque_atualizado"},
            {"name": "Reposição Não-Local (Crítico)", "id": "critico"},
            {"name": "Última Venda", "id": "recencia_formatada"},
            {"name": "Dias Inativo", "id": "dias_inativo_formatado"},
            {"name": "Antiguidade", "id": "antiguidade_formatada"},
        ]

        # Criamos a tabela com os dados filtrados
        table = dash_table.DataTable(
            id='tabela-interna-produtos-inativos',
            columns=columns,
            data=df_filtrado.reset_index().to_dict("records"),
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            page_size=10,
            export_format="xlsx",
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