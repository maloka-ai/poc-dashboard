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

    
    # Ajuste apenas na função load_data_callback

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
        
        # Se já temos dados em cache para este cliente/tipo, verificar a idade e se não há erro
        if (current_data and 'client_info' in current_data and 
                current_data['client_info'] == cache_key and 
                last_load_time and current_time - last_load_time < 3600 and
                not current_data.get("error", False)):  # Não usar cache se houver erro
            return current_data
        
        # Senão, carregue os dados usando a função modularizada
        print(f"**************** Cache vazio ou inválido: Carregando dados para {selected_client} - {selected_data_type}")
        data = load_data(selected_client, selected_data_type, app_cache)
        
        if data.get("error", False):
            error_data = {
                "client_info": cache_key, 
                "error": True, 
                "message": data.get("message", "Erro desconhecido no carregamento de dados")
            }
            return error_data
        
        # Crie um objeto com os dados serializados e a informação do cliente
        result = {
            "client_info": cache_key,
            "error": False,  # Explicitamente marcar como sem erro
        }
        
        # Adicionar cada dataframe ao resultado apenas se estiver presente e não for None
        dataframes = [
            "df_analytics", 
            "df_RC_Mensal", 
            "df_RC_Trimestral", 
            "df_RC_Anual", 
            # "df_Previsoes", 
            "df_RT_Anual", 
            "df_fat_Anual", 
            "df_fat_Anual_Geral",
            "df_fat_Mensal", 
            "df_fat_Mensal_lojas", 
            "df_fat_Diario", 
            "df_fat_Diario_lojas", 
            "df_Vendas_Atipicas", 
            "df_relatorio_produtos",
            "df_previsao_retorno", 
            "df_analise_giro", 
            "df_analise_curva_cobertura"
        ]
        
        for df_name in dataframes:
            if df_name in data and data[df_name] is not None:
                result[df_name] = data[df_name].to_json(date_format='iso', orient='split')
                print(f"DataFrame {df_name} carregado com sucesso.")
            else:
                result[df_name] = None
                print(f"DataFrame {df_name} não encontrado ou vazio.")
        
        # Adicionar os outros campos não-DataFrame
        result["company_context"] = data["company_context"]
        result["segmentos_context"] = data["segmentos_context"]
        
        print(f"Dados carregados com sucesso para {selected_client} - {selected_data_type}")
        return result

    