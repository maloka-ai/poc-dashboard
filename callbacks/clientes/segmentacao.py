from dash import Input, Output, State, html, dash_table
import pandas as pd
import io
from utils import formatar_moeda, formatar_numero

def register_segmentacao_callbacks(app):
    """
    Registra todos os callbacks relacionados à página de segmentação de clientes.
    
    Args:
        app: A instância do aplicativo Dash
    """
    
    @app.callback(
        [Output("client-list-header", "children"),
         Output("client-list", "children")],
        Input("segment-distribution", "clickData"),
        State("selected-data", "data"),
        prevent_initial_call=True
    )
    def update_client_list(clickData, data):
        if clickData is None:
            return "Clientes do Segmento Selecionado", html.Div([
                html.P("Selecione um segmento no gráfico acima para ver os clientes.", className="text-center text-muted my-4"),
                html.Div(className="text-center", children=[
                    html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                    html.P("Clique em uma barra para visualizar detalhes", className="text-muted mt-2")
                ])
            ])
        
        if data is None or data.get("df_analytics") is None:
            return "Clientes do Segmento Selecionado", "Dados não disponíveis."
        
        df_analytics = pd.read_json(io.StringIO(data["df_analytics"]), orient='split')
        
        # Extrair o segmento selecionado do clickData
        selected_segment = clickData["points"][0]["x"]
        header_text = f"Clientes do Segmento: {selected_segment}"
        
        # Filtrar o DataFrame para o segmento selecionado ou mostrar todos
        if selected_segment == "Todos":
            filtered_df = df_analytics  # Não filtra, usa todos os registros
            header_text = "Todos os Clientes"
        else:
            filtered_df = df_analytics[df_analytics["Segmento"] == selected_segment]
        
        if filtered_df.empty:
            return header_text, "Nenhum cliente encontrado para o segmento selecionado."
        
        # Determinar colunas de exibição
        display_columns = ["id_cliente", "nome", "Recency", "Frequency", "Monetary", "Age", "cpf", "cnpj", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome": "Cliente",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "Age": "Antiguidade (dias)",
            "cpf": "CPF",
            "cnpj": "CNPJ",
            "email": "E-mail",
            "telefone": "Contato"
        }
        
        # Usar apenas colunas que existem no DataFrame
        existing_columns = [col for col in display_columns if col in filtered_df.columns]
        if not existing_columns:
            return header_text, "Estrutura de dados incompatível para exibição de detalhes."
        
        # Formatar valores monetários
        filtered_df_display = filtered_df[existing_columns].copy()
        if 'Monetary' in filtered_df_display.columns:
            filtered_df_display['Monetary'] = filtered_df_display['Monetary'].apply(lambda x: formatar_moeda(x))
        
        # Criar tabela aprimorada
        table = dash_table.DataTable(
            id='client-segment-table',  # ID único para a tabela
            columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
            data=filtered_df_display.to_dict("records"),
            page_size=10,
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
                    "if": {"column_id": "Monetary"},
                    "fontWeight": "bold"
                },
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": "rgb(248, 248, 248)"
                },
                {
                    "if": {"column_id": "id_cliente"},
                    "width": "100px"
                }
            ],
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            export_format="xlsx"
        )
        
        # Adicionar resumo acima da tabela
        summary = html.Div([
            html.P([
                f"Exibindo ", 
                html.Strong(formatar_numero(len(filtered_df))), 
                f" clientes do segmento ", 
                html.Strong(selected_segment),
                f". Valor monetário médio: ",
                html.Strong(formatar_moeda(filtered_df['Monetary'].mean())),
                f". Frequência média: ",
                html.Strong(f"{filtered_df['Frequency'].mean():.1f}".replace(".", ",") + " compras")
            ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
        ])
        
        return header_text, html.Div([summary, table])