import os
import glob
import zipfile
import base64
from utils import CONTEXTO_PADRAO, SEGMENTOS_PADRAO

def get_available_clients():
    """Lista todos os clientes disponíveis na pasta de dados"""
    clients = []
    if os.path.exists("dados"):
        clients = [d for d in os.listdir("dados") if os.path.isdir(os.path.join("dados", d))]
    
    return clients

def get_available_data_types(client):
    """Lista tipos de dados disponíveis para um cliente"""
    data_types = []
    
    # Verificar no novo formato onde os diretórios estão dentro de dados/{cliente}
    client_path = os.path.join("dados", client)
    if os.path.exists(client_path):
        # Procurar pastas que seguem o padrão Dados_{cliente}_{PF/PJ}
        for item in os.listdir(client_path):
            item_path = os.path.join(client_path, item)
            if os.path.isdir(item_path):
                # Verificar se segue o padrão Dados_{cliente}_{tipo}
                if item.startswith(f"Dados_{client}_"):
                    # Extrair o tipo (PF ou PJ)
                    tipo = item.split("_")[-1]
                    if tipo in ["PF", "PJ"] and tipo not in data_types:
                        data_types.append(tipo)
    
    # Verificar também o formato original (Dados_Cliente_PF) se estiver na raiz
    for tipo in ["PF", "PJ"]:
        path = f"Dados_{client}_{tipo}"
        if os.path.exists(path) and tipo not in data_types:
            data_types.append(tipo)
    
    return data_types

def get_client_context(client):
    """Obter o contexto de um cliente específico"""
    # Verifica a pasta contexts
    context_path = f"contexts/{client.lower()}.txt"
    if os.path.exists(context_path):
        with open(context_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Retorna o contexto padrão caso não exista um contexto específico
    return CONTEXTO_PADRAO

def get_client_segmentos(client):
    """Obter a definição de segmentos para um cliente específico"""
    # Verifica a pasta contexts
    segmentos_path = f"contexts/{client.lower()}_segmentos.txt"
    if os.path.exists(segmentos_path):
        with open(segmentos_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # Retorna a definição padrão de segmentos
    return SEGMENTOS_PADRAO

def validate_client_data(client, data_type):
    """Valida se os arquivos necessários existem para um cliente e tipo de dados"""
    # Verificar formato esperado: dados/{cliente}/Dados_{cliente}_{data_type}
    expected_path = os.path.join("dados", client, f"Dados_{client}_{data_type}")
    
    # Verificar formato antigo na raiz
    old_format_path = f"Dados_{client}_{data_type}"
    
    # Determinar qual caminho usar
    if os.path.exists(expected_path):
        base_path = expected_path
    elif os.path.exists(old_format_path):
        base_path = old_format_path
    else:
        return False, [f"Diretório não encontrado: nem {expected_path} nem {old_format_path} existem"]
    
    # Lista de arquivos requeridos
    required_files = [
        "analytics_cliente_*.csv",  # Usando glob pattern
        "metricas_recorrencia_mensal.xlsx",
        "metricas_recorrencia_trimestral.xlsx",
        "metricas_recorrencia_anual.xlsx"
    ]
    
    missing_files = []
    
    for req_file in required_files:
        if "*" in req_file:
            # Para arquivos com wildcard
            matches = glob.glob(f"{base_path}/{req_file}")
            if not matches:
                missing_files.append(req_file)
        else:
            # Para arquivos com nome exato
            if not os.path.exists(f"{base_path}/{req_file}"):
                missing_files.append(req_file)
    
    return len(missing_files) == 0, missing_files

def process_upload(contents, filename, destination_folder):
    """Processa um arquivo enviado via upload"""
    if not contents:
        return "Nenhum arquivo enviado."
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    
    if filename.endswith('.zip'):
        # Salvar arquivo ZIP
        zip_path = os.path.join(destination_folder, filename)
        with open(zip_path, 'wb') as f:
            f.write(decoded)
        
        # Extrair ZIP
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(destination_folder)
        
        # Remover arquivo ZIP
        os.remove(zip_path)
        return f"Arquivos extraídos com sucesso em {destination_folder}"
    else:
        # Salvar arquivo individual
        file_path = os.path.join(destination_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(decoded)
        return f"Arquivo {filename} salvo em {destination_folder}"

def get_file_paths(client, data_type):
    """Retorna os caminhos dos arquivos para um cliente e tipo específico"""
    # Verificar formato esperado: dados/{cliente}/Dados_{cliente}_{data_type}
    expected_path = os.path.join("dados", client, f"Dados_{client}_{data_type}")
    
    # Verificar formato antigo na raiz
    old_format_path = f"Dados_{client}_{data_type}"
    
    # Determinar qual caminho usar
    if os.path.exists(expected_path):
        base_path = expected_path
    elif os.path.exists(old_format_path):
        base_path = old_format_path
    else:
        return None
        
    # Caminhos dinâmicos para arquivos
    file_paths = {
        "analytics_path": glob.glob(f"{base_path}/analytics_cliente_*.csv"),
        "rc_mensal_path": f"{base_path}/metricas_recorrencia_mensal.xlsx",
        "rc_trimestral_path": f"{base_path}/metricas_recorrencia_trimestral.xlsx",
        "rc_anual_path": f"{base_path}/metricas_recorrencia_anual.xlsx",
        "previsoes_path": f"{base_path}/rfma_previsoes_ajustado.xlsx",
        "rt_anual_path": f"{base_path}/metricas_retencao_anual.xlsx",
        "fat_anual_path": f"{base_path}/faturamento_anual.xlsx",
        "fat_anual_geral_path": f"{base_path}/faturamento_anual_geral.xlsx",
        "fat_mensal_path": f"{base_path}/faturamento_mensal.xlsx",
        "vendas_atipicas_path": f"{base_path}/vendas_atipicas_atual.xlsx",
        "relatorio_produtos_path": f"{base_path}/relatorio_produtos.xlsx",
        "previsao_retorno_path": f"{base_path}/previsao_retorno.xlsx",
        "analise_giro_path": f"{base_path}/analise_giro_completa.xlsx",
    }
    
    return file_paths