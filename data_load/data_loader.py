import os
import pandas as pd
import time
from .client_data import (
    get_client_context, 
    get_client_segmentos, 
    validate_client_data,
    get_file_paths
)

def load_data(client, data_type, app_cache=None, cache_version="v1.0"):
    """
    Carrega dados para um cliente e tipo específicos
    
    Args:
        client (str): Nome do cliente (ex: 'BENY', 'CLIENTE2')
        data_type (str): Tipo de dados ('PF' ou 'PJ')
        app_cache: Instância de cache do Flask (opcional)
        cache_version (str): Versão do cache para invalidação
    """
    print(f"[CACHE] Verificando cache para {client}_{data_type}")
    print("Carrega dados para um cliente e tipo específicos")

    # Adicionar chave de versão para invalidar cache quando necessário
    cache_key = f"{client}_{data_type}_{cache_version}"

    # Verificar se já existe em cache com esta chave específica
    if app_cache is not None:
        cached_data = app_cache.get(cache_key)
        if cached_data is not None:
            print(f"[CACHE] Encontrado no cache: {cache_key}")
            # Verificar se os dados em cache estão válidos e não têm erro
            if cached_data.get("error", False):
                print(f"[CACHE] Dados com erro encontrados no cache. Recarregando...")
            else:
                return cached_data
    
    print(f"[CACHE] Cache não encontrado para {cache_key}, carregando dados...")
    
    # Verificar se existem os arquivos necessários
    valid, missing_files = validate_client_data(client, data_type)
    if not valid:
        error_result = {
            "error": True,
            "message": f"Arquivos necessários ausentes para {client} - {data_type}: {', '.join(missing_files)}",
            "titulo": f"{client} - {data_type}",
            "company_context": get_client_context(client),
            "segmentos_context": get_client_segmentos(client)
        }
        return error_result
    
    # Obter caminhos dos arquivos
    file_paths = get_file_paths(client, data_type)
    if file_paths is None:
        error_result = {
            "error": True,
            "message": f"Não foram encontrados dados para {client} - {data_type}",
            "titulo": f"{client} - {data_type}",
            "company_context": get_client_context(client),
            "segmentos_context": get_client_segmentos(client)
        }
        return error_result
    
    # Inicializar dicionário de resultados e erros
    result = {
        "df_analytics": None,
        "df_RC_Mensal": None,
        "df_RC_Trimestral": None,
        "df_RC_Anual": None,
        # "df_Previsoes": None,
        "df_RT_Anual": None,
        "df_fat_Anual": None,
        "df_fat_Anual_Geral": None,
        "df_fat_Mensal": None,
        "df_fat_Mensal_lojas": None,
        "df_fat_Diario": None,
        "df_fat_Diario_lojas": None,
        "df_Vendas_Atipicas": None,
        "df_relatorio_produtos": None,
        "df_previsao_retorno": None,
        "df_analise_giro": None,
        "df_analise_curva_cobertura": None,
        "df_metricas_compra": None,
        "errors": []
    }
    
    # Lista de arquivos essenciais (sem os quais o carregamento deve falhar)
    essential_files = ["analytics_path", "rc_mensal_path", "rc_trimestral_path", "rc_anual_path"]
    essential_errors = []
    
    # Carregar arquivos com tratamento individual de erros
    try:
        if file_paths["analytics_path"]:
            try:
                result["df_analytics"] = pd.read_csv(file_paths["analytics_path"][0])
            except Exception as e:
                error_msg = f"Erro ao carregar analytics_path: {str(e)}"
                essential_errors.append(error_msg)
                result["errors"].append(error_msg)
        else:
            essential_errors.append("analytics_path não disponível")
            result["errors"].append("analytics_path não disponível")
        # Carregar cada arquivo individualmente com tratamento de erros
        for file_key, df_key in [
            ("rc_mensal_path", "df_RC_Mensal"),
            ("rc_trimestral_path", "df_RC_Trimestral"),
            ("rc_anual_path", "df_RC_Anual"),
            # ("previsoes_path", "df_Previsoes"),
            ("rt_anual_path", "df_RT_Anual"),
            ("fat_anual_path", "df_fat_Anual"),
            ("fat_anual_geral_path", "df_fat_Anual_Geral"),
            ("fat_mensal_path", "df_fat_Mensal"),
            ("fat_mensal_lojas_path", "df_fat_Mensal_lojas"),
            ("fat_diario_path", "df_fat_Diario"),
            ("fat_diario_lojas_path", "df_fat_Diario_lojas"),
            ("vendas_atipicas_path", "df_Vendas_Atipicas")
        ]:
            if os.path.exists(file_paths[file_key]):
                try:
                    result[df_key] = pd.read_excel(file_paths[file_key])
                except Exception as e:
                    error_msg = f"Erro ao carregar {file_key}: {str(e)}"
                    result["errors"].append(error_msg)
                    if file_key in essential_files:
                        essential_errors.append(error_msg)
            elif file_key in essential_files:
                error_msg = f"{file_key} não encontrado"
                essential_errors.append(error_msg)
                result["errors"].append(error_msg)
        
        # Tratamento especial para arquivos com sheet_name
        for file_key, df_key in [
            ("relatorio_produtos_path", "df_relatorio_produtos"),
            ("analise_giro_path", "df_analise_giro")
        ]:
            if os.path.exists(file_paths[file_key]):
                try:
                    result[df_key] = pd.read_excel(file_paths[file_key], sheet_name=0)
                except Exception as e:
                    result["errors"].append(f"Erro ao carregar {file_key}: {str(e)}")
        
        # Tratamento especial para df_analise_curva_cobertura
        if os.path.exists(file_paths.get("analise_curva_cobertura_path", "")):
            try:
                result["df_analise_curva_cobertura"] = pd.read_excel(file_paths["analise_curva_cobertura_path"], sheet_name=0)
            except Exception as e:
                result["errors"].append(f"Erro ao carregar analise_curva_cobertura: {str(e)}")
        
        # Tratamento especial para df_previsao_retorno
        if os.path.exists(file_paths.get("previsao_retorno_path", "")):
            try:
                excel_file = pd.ExcelFile(file_paths["previsao_retorno_path"])
                sheet_names = excel_file.sheet_names
                sheet_to_use = "Resumo_por_Cliente" if "Resumo_por_Cliente" in sheet_names else 0
                result["df_previsao_retorno"] = pd.read_excel(file_paths["previsao_retorno_path"], sheet_name=sheet_to_use)
            except Exception as e:
                result["errors"].append(f"Erro ao carregar previsao_retorno: {str(e)}")

        # Tratamento especial para df_metricas_compra
        if file_paths["metricas_de_compra_path"]:
            try:
                result["df_metricas_compra"] = pd.read_csv(file_paths["metricas_de_compra_path"][0])
            except Exception as e:
                result["errors"].append(f"Erro ao carregar metricas_de_compra_path: {str(e)}")
        # else:
            # result["errors"].append("metricas_de_compra_path não disponível")


    except Exception as e:
        return {
            "error": True,
            "message": f"Erro geral ao carregar arquivos: {str(e)}",
            "titulo": f"{client} - {data_type}",
            "company_context": get_client_context(client),
            "segmentos_context": get_client_segmentos(client)
        }

    # Se houver erros em arquivos essenciais, retorne erro
    if essential_errors:
        return {
            "error": True,
            "message": f"Erros em arquivos essenciais: {'; '.join(essential_errors)}",
            "titulo": f"{client} - {data_type}",
            "company_context": get_client_context(client),
            "segmentos_context": get_client_segmentos(client)
        }

    titulo = f"{client} - {data_type}"

    # =============================================================================
    # Processamento dos dados
    # =============================================================================
    if result["df_RC_Mensal"] is not None:
        result["df_RC_Mensal"]['retention_rate'] = result["df_RC_Mensal"]['retention_rate'].round(2)
    
    if result["df_RC_Trimestral"] is not None:
        result["df_RC_Trimestral"]['recurrence_rate'] = result["df_RC_Trimestral"]['recurrence_rate'].round(2)
    
    if result["df_RC_Anual"] is not None:
        result["df_RC_Anual"]['new_rate'] = result["df_RC_Anual"]['new_rate'].round(2)
        result["df_RC_Anual"]['returning_rate'] = result["df_RC_Anual"]['returning_rate'].round(2)
        result["df_RC_Anual"]['retention_rate'] = result["df_RC_Anual"]['retention_rate'].round(2)
    
    # Obter contexto específico do cliente
    company_context = get_client_context(client)
    segmentos_context = get_client_segmentos(client)

    # Adicionar informações ao resultado
    result["titulo"] = titulo
    result["company_context"] = company_context
    result["segmentos_context"] = segmentos_context
    result["error"] = len(result["errors"]) > 0
    
    # Mostrar warnings para arquivos não-essenciais com erro
    if result["errors"] and not essential_errors:
        print(f"[AVISO] Alguns arquivos não-essenciais não puderam ser carregados: {result['errors']}")
    
    # Salvar no cache antes de retornar
    if app_cache is not None and not essential_errors:
        try:
            # Salvar no cache do Flask com um timeout específico (15 minutos = 900 segundos)
            app_cache.set(cache_key, result, timeout=900)
            print(f"[CACHE] Dados salvos em cache com chave: {cache_key}")
        except Exception as e:
            print(f"[CACHE] Erro ao salvar no cache: {str(e)}")
    
    print(f"[CACHE] Dados carregados para {client}_{data_type}")
    return result