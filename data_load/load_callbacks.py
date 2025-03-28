import time
from dash import Input, Output, State
import dash
from dash.exceptions import PreventUpdate

from data_load.data_loader import load_data

def register_data_callbacks(app, app_cache=None):
    """
    Registra todos os callbacks relacionados ao carregamento de dados
    
    Args:
        app: Instância do aplicativo Dash
        app_cache: Instância de cache do Flask (opcional)
    """
    
    @app.callback(
        Output("selected-data", "data", allow_duplicate=True),
        Input("data-type-selection", "value"),
        State("selected-client", "data"),
        State("selected-data", "data"),
        prevent_initial_call=True
    )
    def update_data_type(selected_type, selected_client, current_data):
        if selected_type is None or selected_client is None:
            return dash.no_update
        
        # Crie a chave de cache
        cache_key = f"{selected_client}_{selected_type}"
        
        # Se já temos os dados e são do mesmo tipo, não recarregue
        if current_data and 'client_info' in current_data and current_data['client_info'] == cache_key:
            print(f"Usando cache existente para {cache_key}")
            return dash.no_update
        
        # Caso contrário, retorne None para forçar o carregamento dos dados corretos
        print(f"Cache inválido para {cache_key}. Forçando recarregamento.")
        return None

    
    @app.callback(
        Output("selected-data", "data"),
        Input("selected-client", "data"),
        Input("selected-data-type", "data"),
        State("selected-data", "data"),
        State("last-data-load-time", "data"),
        prevent_initial_call=True
    )
    def load_data_callback(selected_client, selected_data_type, current_data, last_load_time):
        # Verificar se os inputs são válidos
        if not selected_client or not selected_data_type:
            return None
        
        # Criar uma chave de cache consistente
        cache_key = f"{selected_client}_{selected_data_type}"
        current_time = time.time()
        
        # Se já temos dados em cache para este cliente/tipo, verificar a idade
        if (current_data and 'client_info' in current_data and 
                current_data['client_info'] == cache_key and 
                last_load_time and current_time - last_load_time < 3600):  # Cache de 1 hora
            return current_data
        
        # Senão, carregue os dados usando a função modularizada
        print(f"**************** Cache vazio: Carregando dados para {selected_client} - {selected_data_type}")
        data = load_data(selected_client, selected_data_type, app_cache)
        
        if data.get("error", False):
            error_data = {"client_info": cache_key, "error": True, "message": data.get("message")}
            return error_data
        
        # Crie um objeto com os dados serializados e a informação do cliente
        result = {
            "client_info": cache_key,
            "df": data["df"].to_json(date_format='iso', orient='split') if data["df"] is not None else None,
            "df_RC_Mensal": data["df_RC_Mensal"].to_json(date_format='iso', orient='split') if data["df_RC_Mensal"] is not None else None,
            "df_RC_Trimestral": data["df_RC_Trimestral"].to_json(date_format='iso', orient='split') if data["df_RC_Trimestral"] is not None else None,
            "df_RC_Anual": data["df_RC_Anual"].to_json(date_format='iso', orient='split') if data["df_RC_Anual"] is not None else None,
            "df_Previsoes": data["df_Previsoes"].to_json(date_format='iso', orient='split') if data["df_Previsoes"] is not None else None,
            "df_RT_Anual": data["df_RT_Anual"].to_json(date_format='iso', orient='split') if data["df_RT_Anual"] is not None else None,
            "df_fat_Anual": data["df_fat_Anual"].to_json(date_format='iso', orient='split') if data["df_fat_Anual"] is not None else None,
            "df_fat_Anual_Geral": data["df_fat_Anual_Geral"].to_json(date_format='iso', orient='split') if data["df_fat_Anual_Geral"] is not None else None,
            "df_fat_Mensal": data["df_fat_Mensal"].to_json(date_format='iso', orient='split') if data["df_fat_Mensal"] is not None else None,
            "df_Vendas_Atipicas": data["df_Vendas_Atipicas"].to_json(date_format='iso', orient='split') if data["df_Vendas_Atipicas"] is not None else None,
            "df_relatorio_produtos": data["df_relatorio_produtos"].to_json(date_format='iso', orient='split') if "df_relatorio_produtos" in data and data["df_relatorio_produtos"] is not None else None,
            "company_context": data["company_context"],
            "segmentos_context": data["segmentos_context"]
        }
        
        print(f"Dados carregados com sucesso para {selected_client} - {selected_data_type}")
        return result

    