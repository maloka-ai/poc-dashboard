import dash
from dash import Input, Output, html, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import io
from utils import formatar_moeda, formatar_numero
from utils.helpers import color, button_style

def register_predicao_callbacks(app):
    """
    Registra todos os callbacks relacionados à página de segmentação de clientes.
    
    Args:
        app: A instância do aplicativo Dash
    """

    @app.callback(
        [Output("predicao-client-list-header", "children"),
        Output("predicao-client-list", "children")],
        [Input("predicao-pie", "clickData"),
        Input("predicao-bar", "clickData")],
        Input("selected-data", "data")
    )
    def update_predicao_client_list(clickData_pie, clickData_bar, data):
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
        
        if trigger_id == 'predicao-pie' and clickData_pie:
            selected_category = clickData_pie['points'][0]['label']
        elif trigger_id == 'predicao-bar' and clickData_bar:
            selected_category = clickData_bar['points'][0]['x']
        else:
            return "Clientes da Categoria Selecionada", html.Div([
                html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4")
            ])
        
        header_text = f"Clientes da Categoria: {selected_category}"
        filtered_df = df_Previsoes[df_Previsoes["categoria_previsao"] == selected_category]
        
        if filtered_df.empty:
            return header_text, "Nenhum cliente encontrado para a categoria selecionada."
        
        # Verifica se a coluna 'nome_fantasia' existe
        if 'nome_fantasia' in df_Previsoes.columns:
            display_columns = ["id_cliente", "nome_fantasia", "predicted_purchases_30d", "Recency", "Frequency", "Monetary", "email", "telefone"]
            col_rename = {
                "id_cliente": "Código do Cliente",
                "nome_fantasia": "Cliente",
                "predicted_purchases_30d": "Previsão de Compras (30d)",
                "Recency": "Recência (dias)",
                "Frequency": "Frequência",
                "Monetary": "Valor Monetário (R$)",
                "email": "E-mail",
                "telefone": "Contato"
            }
        else:
            display_columns = ["id_cliente", "nome", "predicted_purchases_30d", "Recency", "Frequency", "Monetary", "email", "telefone"]
            col_rename = {
                "id_cliente": "Código do Cliente",
                "nome": "Cliente",
                "predicted_purchases_30d": "Previsão de Compras (30d)",
                "Recency": "Recência (dias)",
                "Frequency": "Frequência",
                "Monetary": "Valor Monetário (R$)",
                "email": "E-mail",
                "telefone": "Contato"
            }
        
        # Usar apenas colunas que existem no DataFrame
        existing_columns = [col for col in display_columns if col in filtered_df.columns]
        if not existing_columns:
            return header_text, "Estrutura de dados incompatível para exibição de detalhes."
        
        # Format monetary values and predictions
        filtered_df_display = filtered_df[existing_columns].copy()
        if 'Monetary' in filtered_df_display.columns:
            filtered_df_display['Monetary'] = filtered_df_display['Monetary'].apply(lambda x: formatar_moeda(x))
        
        if 'predicted_purchases_30d' in filtered_df_display.columns:
            filtered_df_display['predicted_purchases_30d'] = filtered_df_display['predicted_purchases_30d'].apply(
                lambda x: f"{x:.2f}".replace(".", ",")
            )
        
        # Enhanced modern table
        table = dash_table.DataTable(
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
                    "backgroundColor": "rgb(248, 248, 248)"
                }
            ],
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            export_format="xlsx"
        )
        
        # Add a summary row above the table
        avg_predicted = filtered_df['predicted_purchases_30d'].mean()
        avg_monetary = filtered_df['Monetary'].mean()
        
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
        
        # Action buttons for marketing campaigns
        action_buttons = html.Div([
            dbc.Button(
                [html.I(className="fas fa-envelope me-2"), "Preparar E-mail Marketing"],
                color="primary",
                className="me-2",
                style=button_style
            ),
            dbc.Button(
                [html.I(className="fas fa-mobile-alt me-2"), "Preparar SMS"],
                color="secondary",
                className="me-2",
                style=button_style
            ),
            dbc.Button(
                [html.I(className="fas fa-download me-2"), "Exportar Lista"],
                color="success",
                style=button_style
            )
        ], className="mb-3")
        
        return header_text, html.Div([summary, action_buttons, table])