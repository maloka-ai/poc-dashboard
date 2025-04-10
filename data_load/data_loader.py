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
            return cached_data
    
    print(f"[CACHE] Cache não encontrado para {cache_key}, carregando dados...")
    
    # Verificar se existem os arquivos necessários
    valid, missing_files = validate_client_data(client, data_type)
    if not valid:
        return {
            "error": True,
            "message": f"Arquivos necessários ausentes para {client} - {data_type}: {', '.join(missing_files)}"
        }
    
    # Obter caminhos dos arquivos
    file_paths = get_file_paths(client, data_type)
    if file_paths is None:
        return {
            "error": True,
            "message": f"Não foram encontrados dados para {client} - {data_type}"
        }
    
    # Carregar arquivos
    try:
        df = pd.read_csv(file_paths["analytics_path"][0]) if file_paths["analytics_path"] else None
        df_RC_Mensal = pd.read_excel(file_paths["rc_mensal_path"]) if os.path.exists(file_paths["rc_mensal_path"]) else None
        df_RC_Trimestral = pd.read_excel(file_paths["rc_trimestral_path"]) if os.path.exists(file_paths["rc_trimestral_path"]) else None
        df_RC_Anual = pd.read_excel(file_paths["rc_anual_path"]) if os.path.exists(file_paths["rc_anual_path"]) else None
        df_Previsoes = pd.read_excel(file_paths["previsoes_path"]) if os.path.exists(file_paths["previsoes_path"]) else None
        df_RT_Anual = pd.read_excel(file_paths["rt_anual_path"]) if os.path.exists(file_paths["rt_anual_path"]) else None
        df_fat_Anual = pd.read_excel(file_paths["fat_anual_path"]) if os.path.exists(file_paths["fat_anual_path"]) else None
        df_fat_Anual_Geral = pd.read_excel(file_paths["fat_anual_geral_path"]) if os.path.exists(file_paths["fat_anual_geral_path"]) else None
        df_fat_Mensal = pd.read_excel(file_paths["fat_mensal_path"]) if os.path.exists(file_paths["fat_mensal_path"]) else None
        df_Vendas_Atipicas = pd.read_excel(file_paths["vendas_atipicas_path"]) if os.path.exists(file_paths["vendas_atipicas_path"]) else None
        df_relatorio_produtos = pd.read_excel(file_paths["relatorio_produtos_path"], sheet_name=0) if os.path.exists(file_paths["relatorio_produtos_path"]) else None
        # Log adicional para diagnóstico do problema com df_previsao_retorno
        previsao_retorno_path = file_paths.get("previsao_retorno_path", "caminho não definido")
        # print(f"Caminho do arquivo de previsão de retorno: {previsao_retorno_path}")
        # print(f"O arquivo existe? {os.path.exists(previsao_retorno_path) if previsao_retorno_path != 'caminho não definido' else False}")
        
        if previsao_retorno_path != "caminho não definido" and os.path.exists(previsao_retorno_path):
            try:
                # Tentar ler todas as planilhas para verificar os nomes disponíveis
                excel_file = pd.ExcelFile(previsao_retorno_path)
                sheet_names = excel_file.sheet_names
                # print(f"Planilhas disponíveis no arquivo: {sheet_names}")
                
                # Tentar carregar a planilha específica
                df_previsao_retorno = pd.read_excel(
                    previsao_retorno_path, 
                    sheet_name="Resumo_por_Cliente"
                )
                # print(f"DataFrame carregado com {len(df_previsao_retorno)} linhas e {len(df_previsao_retorno.columns)} colunas.")
            except Exception as e:
                print(f"Erro específico ao carregar df_previsao_retorno: {str(e)}")
                df_previsao_retorno = None
        else:
            df_previsao_retorno = None
            print("Arquivo de previsão de retorno não encontrado ou caminho não definido.")
        # if df_previsao_retorno is not None:
        #     print(f"DataFrame carregado com {len(df_previsao_retorno)} linhas e {len(df_previsao_retorno.columns)} colunas.")
    except Exception as e:
        return {
            "error": True,
            "message": f"Erro ao carregar arquivos: {str(e)}"
        }

    titulo = f"{client} - {data_type}"

    # =============================================================================
    # Processamento dos dados
    # =============================================================================
    if df_RC_Mensal is not None:
        df_RC_Mensal['retention_rate'] = df_RC_Mensal['retention_rate'].round(2)
    
    if df_RC_Trimestral is not None:
        df_RC_Trimestral['recurrence_rate'] = df_RC_Trimestral['recurrence_rate'].round(2)
    
    if df_RC_Anual is not None:
        df_RC_Anual['new_rate'] = df_RC_Anual['new_rate'].round(2)
        df_RC_Anual['returning_rate'] = df_RC_Anual['returning_rate'].round(2)
        df_RC_Anual['retention_rate'] = df_RC_Anual['retention_rate'].round(2)
    
    # Obter contexto específico do cliente
    company_context = get_client_context(client)
    segmentos_context = get_client_segmentos(client)

    # Preparar o resultado final
    result = {
        "df": df,
        "df_RC_Mensal": df_RC_Mensal,
        "df_RC_Trimestral": df_RC_Trimestral,
        "df_RC_Anual": df_RC_Anual,
        "df_Previsoes": df_Previsoes,
        "df_RT_Anual": df_RT_Anual,
        "df_fat_Anual": df_fat_Anual,
        "df_fat_Anual_Geral": df_fat_Anual_Geral,
        "df_fat_Mensal": df_fat_Mensal,
        "df_Vendas_Atipicas": df_Vendas_Atipicas,
        "df_relatorio_produtos": df_relatorio_produtos,
        "df_previsao_retorno": df_previsao_retorno,
        "titulo": titulo,
        "company_context": company_context,
        "segmentos_context": segmentos_context,
        "error": False
    }
    
    # Salvar no cache antes de retornar
    if app_cache is not None:
        try:
            # Salvar no cache do Flask com um timeout específico (15 minutos = 900 segundos)
            app_cache.set(cache_key, result, timeout=900)
            print(f"[CACHE] Dados salvos em cache com chave: {cache_key}")
        except Exception as e:
            print(f"[CACHE] Erro ao salvar no cache: {str(e)}")
    
    print(f"[CACHE] Dados carregados para {client}_{data_type}")
    return result