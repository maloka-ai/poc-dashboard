import io
import os
import glob
import zipfile
import base64
import dash
import dash_bootstrap_components as dbc
import dotenv
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import openai
from dash.long_callback import DiskcacheLongCallbackManager
import diskcache
from flask_caching import Cache
import time
from dash_bootstrap_templates import load_figure_template
from flask import Flask, redirect, url_for, session, request

# =============================================================================
# Setup caching for improved performance
# =============================================================================
cache = diskcache.Cache("./cache")
long_callback_manager = DiskcacheLongCallbackManager(cache)

cache.reset('size', int(1e9))  # Limite de 1GB para o cache


# =============================================================================
# Funções auxiliares pro chat
# =============================================================================
openai.api_key = os.getenv("chatKey")

# Contexto padrão - caso não haja contexto específico para um cliente
CONTEXTO_PADRAO = """
Este é um sistema de análise de clientes para varejo. O sistema fornece insights sobre segmentação de clientes,
métrica RFMA (Recência, Frequência, Valor Monetário e Antiguidade), análises de retenção, recorrência e previsão de compras.

As políticas de atendimento, entrega, pagamento e garantia são específicas para cada cliente.

Este contexto é utilizado para orientar análises e respostas sobre clientes, entregas, pagamentos e garantias.
"""

SEGMENTOS_PADRAO = """ 
    cond_novos = (df_seg['Recency'] <= 30) & (df_seg['Age'] <= 30) 
    
    cond_campeoes = (df_seg['Recency'] <= 180) & \
                    (df_seg['Frequency'] >= 7) & (df_seg['M_decil'] == 10) 
                    
    cond_fieis_baixo_valor = (df_seg['Recency'] <= 180) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 4) & (df_seg['M_decil'] <= 8) #
    
    cond_fieis_alto_valor = (df_seg['Recency'] <= 180) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 4) & (df_seg['M_decil'] > 8) 
                 
    cond_recentes_alto = (df_seg['Recency'] <= 180) & \
                         (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] > 6) 
                         
    cond_recentes_baixo = (df_seg['Recency'] <= 180) & \
                          (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] <= 6)
    
    # Clientes menos ativos
    cond_sumidos = (df_seg['Recency'] >= 180) & (df_seg['Recency'] < 365) 
    cond_inativos = (df_seg['Recency'] >= 365)

    # Segmentação de Clientes

    Nossa estratégia de segmentação divide os clientes em 8 grupos distintos, baseados em comportamento de compra e valor:

    ## Clientes Ativos

    *Novos*: Clientes recentes (últimos 30 dias) e novos na base (menos de 30 dias).

    *Campeões*: Alto valor (top 10% em gastos) com frequência elevada (7+ compras) e compra nos últimos 6 meses.

    *Fiéis de Alto Valor*: Relacionamento longo (mais de 2 anos), frequência regular (4+ compras), alto valor (top 20% em gastos) e compra nos últimos 6 meses.

    *Fiéis de Baixo Valor*: Relacionamento longo (mais de 2 anos), frequência regular (4+ compras), valor moderado a baixo (até 80% em gastos) e compra nos últimos 6 meses.

    *Recentes de Alto Valor*: Compra nos últimos 6 meses, pelo menos 1 compra e valor significativo (top 40% em gastos).

    *Recentes de Baixo Valor*: Compra nos últimos 6 meses, pelo menos 1 compra e valor moderado a baixo (abaixo dos 60% em gastos).

    ## Clientes Menos Ativos

    *Sumidos*: Sem atividade entre 6 meses e 1 ano.

    *Inativos*: Sem atividade há mais de 1 ano.
"""

DATAFRAME_KEYS = """
{'DF': Index(['id_cliente', 'Recency', 'Frequency', 'Monetary', 'Age', 'R_range',
        'F_range', 'M_range', 'A_range', 'R_decil', 'F_decil', 'M_decil',
        'A_decil', 'Segmento', 'nome', 'cpf', 'email', 'telefone'],
       dtype='object'),
 'DF_RC_MENSAL': Index(['yearmonth', 'retained_customers', 'prev_total_customers',
        'retention_rate'],
       dtype='object'),
 'DF_RC_TRIMESTRAL': Index(['trimestre', 'trimestre_obj', 'total_customers', 'returning_customers',
        'new_customers', 'recurrence_rate'],
       dtype='object'),
 'DF_RC_ANUAL': Index(['ano', 'ano_obj', 'total_customers', 'returning_customers',
        'new_customers', 'retention_rate', 'new_rate', 'returning_rate'],
       dtype='object'),
 'DF_RT_ANUAL': Index(['cohort_year', 'period_index', 'num_customers', 'cohort_size',
        'retention_rate'],
       dtype='object'),
 'DF_PREVISOES': Index(['id_cliente', 'Recency', 'Frequency', 'Monetary', 'Age', 'R_range',
        'F_range', 'M_range', 'A_range', 'R_decil', 'F_decil', 'M_decil',
        'A_decil', 'Segmento', 'nome', 'cpf', 'email', 'telefone',
        'frequency_adjusted', 'recency_bg', 'T', 'predicted_purchases_30d',
        'categoria_previsao'],
"""

# Estado das collapses da sidebar
INITIAL_COLLAPSE_STATE = False  # False = iniciar fechados, True = iniciar abertos
collapse_states = {
    "clientes": INITIAL_COLLAPSE_STATE,
    "faturamento": INITIAL_COLLAPSE_STATE,
    "estoque": INITIAL_COLLAPSE_STATE
}

def classificar_pergunta(pergunta):
    prompt = f"""
    Você é um assistente que classifica perguntas sobre análise de clientes do varejo.
    Classifique a seguinte pergunta em uma das categorias de análise: 
    - "RFMA" (Recência, Frequência, Valor Monetário, Tempo de Primeira Compra)
    - "Recorrência" (Mensal, Trimestral ou Anual)
    - "Retenção Anual"
    - "Previsão de Retorno"
    - "Fora do Escopo" (caso não se encaixe nas categorias acima)

    Qualquer pergunta sobre clientes deve ser encaixada numa categoria que não "Fora do Escopo"

    Pergunta: "{pergunta}"
    Se "Fora do Escopo" for uma categoria, não deve haver nenhuma outra. Caso contrário, é possível ter uma ou mais categorias
    Formato de saída: categoria1 (obrigatória), categoria2 (opcional)... 
    """
    
    response = openai.chat.completions.create(
        model="gpt-4o", 
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2
    )
    return [elemento.strip() for elemento in response.choices[0].message.content.split(",")]

def selecionar_dataframes(pergunta, categorias_pergunta):
    prompt = f"""
    Você é um assistente que seleciona DataFrames para responder perguntas sobre clientes no varejo.  
    Temos os seguintes DataFrames disponíveis e suas chaves:  

    {DATAFRAME_KEYS}

    Abaixo está uma lista de categorias extraídas das perguntas:
    {str(categorias_pergunta)}

    Abaixo está a pergunta que foi feita:
    {pergunta}

    Com base nisso, retorne uma lista dos nomes dos DataFrames que contêm informações relevantes.  
    Responda apenas com os nomes dos DataFrames, separados por vírgula.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}], 
        temperature=0.2
    )

    dataframes_usados = [df.strip() for df in response.choices[0].message.content.split(",")]
    return dataframes_usados

# =============================================================================
# Funções para gerenciar clientes e bases de dados
# =============================================================================
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

# =============================================================================
# Função para carregar os dados conforme o cliente e base escolhidos
# =============================================================================
@cache.memoize(expire=3600)  # Cache for 1 hour
def load_data(client, data_type):
    """
    Carrega dados para um cliente e tipo específicos
    
    Args:
        client (str): Nome do cliente (ex: 'BENY', 'CLIENTE2')
        data_type (str): Tipo de dados ('PF' ou 'PJ')
    """
    print(f"[CACHE] Verificando cache para {client}_{data_type}")
    print("Carrega dados para um cliente e tipo específicos")
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
        return {
            "error": True,
            "message": f"Não foram encontrados dados para {client} - {data_type} nos caminhos:\n- {expected_path}\n- {old_format_path}"
        }
        
    # Verificar se existem os arquivos necessários
    valid, missing_files = validate_client_data(client, data_type)
    if not valid:
        return {
            "error": True,
            "message": f"Arquivos necessários ausentes para {client} - {data_type}: {', '.join(missing_files)}"
        }
        
    # Caminhos dinâmicos para arquivos
    analytics_path = glob.glob(f"{base_path}/analytics_cliente_*.csv")
    rc_mensal_path = f"{base_path}/metricas_recorrencia_mensal.xlsx"
    rc_trimestral_path = f"{base_path}/metricas_recorrencia_trimestral.xlsx"
    rc_anual_path = f"{base_path}/metricas_recorrencia_anual.xlsx"
    previsoes_path = f"{base_path}/rfma_previsoes_ajustado.xlsx"
    rt_anual_path = f"{base_path}/metricas_retencao_anual.xlsx"
    fat_anual_path = f"{base_path}/faturamento_anual.xlsx"
    fat_anual_geral_path = f"{base_path}/faturamento_anual_geral.xlsx"
    fat_mensal_path = f"{base_path}/faturamento_mensal.xlsx"
    vendas_atipicas_path = f"{base_path}/vendas_atipicas_atual.xlsx"
    relatorio_produtos_path = f"{base_path}/relatorio_produtos.xlsx"
    
    # Carregar arquivos
    df = pd.read_csv(analytics_path[0])
    df_RC_Mensal = pd.read_excel(rc_mensal_path) if os.path.exists(rc_mensal_path) else None
    df_RC_Trimestral = pd.read_excel(rc_trimestral_path) if os.path.exists(rc_trimestral_path) else None
    df_RC_Anual = pd.read_excel(rc_anual_path) if os.path.exists(rc_anual_path) else None
    df_Previsoes = pd.read_excel(previsoes_path) if os.path.exists(previsoes_path) else None
    df_RT_Anual = pd.read_excel(rt_anual_path) if os.path.exists(rt_anual_path) else None
    df_fat_Anual = pd.read_excel(fat_anual_path) if os.path.exists(fat_anual_path) else None
    df_fat_Anual_Geral = pd.read_excel(fat_anual_geral_path) if os.path.exists(fat_anual_geral_path) else None
    df_fat_Mensal = pd.read_excel(fat_mensal_path) if os.path.exists(fat_mensal_path) else None
    df_Vendas_Atipicas = pd.read_excel(vendas_atipicas_path) if os.path.exists(vendas_atipicas_path) else None
    df_relatorio_produtos = pd.read_excel(relatorio_produtos_path, sheet_name=0) if os.path.exists(relatorio_produtos_path) else None

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
    print(f"[CACHE] Dados carregados para {client}_{data_type}")
    return {
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
        "titulo": titulo,
        "company_context": company_context,
        "segmentos_context": segmentos_context,
        "error": False
    }

# =============================================================================
# Funções auxiliares de formatação de números
# =============================================================================
def formatar_moeda(valor):
    """Formata um valor monetário no padrão brasileiro: R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_percentual(valor):
    """Formata um valor percentual no padrão brasileiro: 12,5%"""
    return f"{valor:.2f}%".replace(".", ",")

def formatar_numero(valor, decimais=0):
    """Formata um número com separador de milhares no padrão brasileiro"""
    formato = f"{{:,.{decimais}f}}"
    return formato.format(valor).replace(",", "X").replace(".", ",").replace("X", ".")

# Função específica para lidar com o formato ISO que você está recebendo
def format_iso_date(date_str):
    if date_str == '-' or not date_str:
        return '-'
    
    try:
        # Específico para o formato que você está recebendo: 2025-01-06T00:00:00.000
        if isinstance(date_str, str) and 'T' in date_str:
            # Pega apenas a parte da data (antes do T)
            date_part = date_str.split('T')[0]
            # Divide por traços para obter ano, mês e dia
            year, month, day = date_part.split('-')
            return f"{day}/{month}/{year}"
            
        # Se for uma string de data em outro formato
        elif isinstance(date_str, str):
            from datetime import datetime
            try:
                # Tenta vários formatos comuns
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        return date_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        continue
            except:
                return date_str
                
        # Se for um objeto datetime
        elif hasattr(date_str, 'strftime'):
            return date_str.strftime('%d/%m/%Y')
            
        # Retorna o original se nenhum método funcionar
        return date_str
    except Exception as e:
        # Em caso de qualquer erro, retorne o original
        return f"{date_str}"

# Define a base color palette with gradients
color = {
    'primary': '#001514',
    'secondary': '#0077B6',
    'accent': '#FF730e',
    'highlight': '#FFF8B0',
    'neutral': '#7A4E2D',
    'success': '#3CB371',
    'warning': '#f1c40f',
    'danger': '#e74c3c',
    'background': '#f9f9f9'
}

gradient_colors = {
    'blue_gradient': ['#0077B6', '#4DA6FF', '#89D2FF'],
    'orange_gradient': ['#FF730e', '#FF9E52', '#FFBD80'],
    'green_gradient': ['#2E8B57', '#3CB371', '#90EE90']
}

# Loading custom figure template based on our color scheme
load_figure_template('bootstrap')

cluster_colors = ['#66B2FF', '#99FF99', '#FF9999', '#FFCC99', '#FF99CC']

cluster_metrics = {
    "Recência": "R_decil",
    "Frequencia": "F_decil",
    "Valor Monetário": "M_decil",
    "Antiguidade": "A_decil",
}

colors = [color['accent'], color['highlight'], color['neutral'], color['secondary']]

rfma_metrics = {
    "Recency": ("R_range", colors[0]),
    "Frequency": ("F_range", colors[1]),
    "Monetary": ("M_range", colors[2]),
    "Age": ("A_range", colors[3]),
}

cores_segmento = {
    'Novos': color['highlight'],  
    'Recentes Baixo Valor': color['accent'],   
    'Recentes Alto Valor': color['warning'],    
    'Fiéis Baixo Valor': color['secondary'],    
    'Fiéis Alto Valor': gradient_colors['green_gradient'][2], 
    'Campeões': gradient_colors['green_gradient'][0],     
    'Inativos': color['primary'],    
    'Sumidos': color['neutral'] 
}

# =============================================================================
# Inicializar o application
# =============================================================================
server = Flask(__name__)
server.secret_key = 'maloka_ai_secret_key_2025'  # Mesma chave do sistema de login

application = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap'],
    suppress_callback_exceptions=True,
    long_callback_manager=long_callback_manager,
    server=server,  # Associar ao servidor Flask
    url_base_pathname='/app/'
)

# Configure caching for app
app_cache = Cache(server, config={
    'CACHE_TYPE': 'filesystem',
    'CACHE_DIR': './flask_cache_dir'
})

# Adicione isto na seção dos estilos
ESTILO_CUSTOMIZADO = {
    'login-container': {
        'background': f"linear-gradient(135deg, {gradient_colors['blue_gradient'][0]} 0%, {gradient_colors['blue_gradient'][2]} 100%)",
        'height': '100vh',
        'display': 'flex',
        'alignItems': 'center',
        'justifyContent': 'center'
    },
    'login-card': {
        'backgroundColor': 'rgba(255, 255, 255, 0.9)',
        'borderRadius': '15px',
        'boxShadow': '0 10px 25px rgba(0,0,0,0.1)',
        'padding': '30px',
        'width': '350px'
    },
    'login-title': {
        'color': gradient_colors['blue_gradient'][0],
        'textAlign': 'center',
        'marginBottom': '25px',
        'fontWeight': 'bold'
    },
    'login-button': {
        'background': f"linear-gradient(135deg, {gradient_colors['blue_gradient'][0]} 0%, {gradient_colors['blue_gradient'][1]} 100%)",
        'border': 'none',
        'borderRadius': '25px'
    },
    'logo': {
        'maxWidth': '200px',
        'marginBottom': '20px',
        'display': 'block',
        'margin': '0 auto'
    }
}
# =============================================================================
# Estilos de layout
# =============================================================================
# Modern sidebar style
sidebar_style = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "280px",
    "padding": "2rem 1.5rem",
    "background": f"linear-gradient(180deg, {color['primary']} 0%, #033B4A 100%)",
    "overflow-y": "auto",
    "height": "100vh",
    "box-shadow": "4px 0px 10px rgba(0, 0, 0, 0.1)",
    "z-index": "1000",
    "transition": "all 0.3s"
}

# Content style with more spacing
content_style = {
    "margin-left": "280px",
    "margin-right": "0",
    "padding": "2rem 2.5rem",
    "background-color": color['background'],
    "min-height": "100vh",
    "transition": "all 0.3s"
}

# Card styles
card_style = {
    "border-radius": "12px",
    "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.05)",
    "border": "none",
    "background-color": "white",
    "overflow": "hidden",
    "transition": "transform 0.3s, box-shadow 0.3s",
}

card_header_style = {
    "background-color": "white",
    "border-bottom": f"1px solid rgba(0, 0, 0, 0.05)",
    "padding": "1rem 1.5rem",
    "font-weight": "600",
    "color": color['primary'],
    "font-size": "1.1rem"
}

card_body_style = {
    "padding": "1.5rem",
}

# Button styles
button_style = {
    "border-radius": "8px",
    "font-weight": "500",
    "box-shadow": "0 2px 5px rgba(0, 0, 0, 0.1)",
    "transition": "all 0.2s"
}

# Navigation link styles
nav_link_style = {
    "border-radius": "8px",
    "font-weight": "500",
    "transition": "all 0.2s",
    "color": "rgba(255, 255, 255, 0.8)",
    "padding": "0.8rem 1rem"
}



# =============================================================================
# Custom components for improved UI
# =============================================================================
def create_card(header, body, className="mb-4 dashboard-card"):
    return dbc.Card(
        [
            dbc.CardHeader(header, style=card_header_style),
            dbc.CardBody(body, style=card_body_style)
        ],
        className=className,
        style=card_style
    )

def create_metric_tile(title, value, change=None, color=color['secondary']):
    change_component = None
    if change is not None:
        change_class = "change-positive" if change >= 0 else "change-negative"
        change_icon = "↑" if change >= 0 else "↓"
        
        # Formatar a mudança percentual com vírgula
        formatted_change = formatar_percentual(abs(change))
        
        change_component = html.Div([
            html.Span(f"{change_icon} {formatted_change}", className=change_class)
        ], className="metric-change")
    
    return html.Div([
        html.Div(title, className="metric-title"),
        html.Div(value, className="metric-value"),
        change_component
    ], className="metric-tile", style={"border-left-color": color})

def create_metric_row(metrics):
    return html.Div(
        [create_metric_tile(m["title"], m["value"], m.get("change"), m.get("color", color['secondary'])) for m in metrics],
        className="metric-container"
    )

loading_component = dcc.Loading(
    id="loading",
    type="dot",
    children=html.Div(id="loading-output"),
    color=color['secondary']
)

# =============================================================================
# Sidebar com seleção dinâmica de cliente e tipo de dados
# =============================================================================
def create_sidebar(client=None, available_data_types=None):
    # Se client não foi fornecido, tentar obter um cliente padrão
    if client is None:
        clients = get_available_clients()
        if clients:
            client = clients[0]

    # Se available_data_types não foi fornecido, buscar com base no cliente
    if available_data_types is None:
        available_data_types = get_available_data_types(client)

    if not available_data_types:
        available_data_types = ["PF", "PJ"]

    # Mostrar a seleção de tipo de dados apenas se houver mais de um tipo disponível
    show_data_type_selection = len(available_data_types) > 1

    
    sidebar = html.Div(
        [
            html.Div(
                [
                    html.Img(src="assets/maloka_logo.png", style={"width": "60px", "height": "auto"}),
                    html.H3("MALOKA'AI", style={"color": "white", "margin": "0 0 0 10px", "font-weight": "700", "letter-spacing": "1px"})
                ],
                style={"display": "flex", "alignItems": "center", "paddingBottom": "1.5rem"}
            ),
            # App title that will be updated based on the selected data source
            html.H4(client, style={
                "color": "white", 
                "textAlign": "center", 
                "font-weight": "700",
                "marginBottom": "1rem",
                "letter-spacing": "0.5px"
            }),
            html.H5("Dashboard de Análise", style={
                "color": "rgba(255, 255, 255, 0.8)", 
                "textAlign": "center",
                "marginBottom": "1.5rem",
                "font-weight": "400",
                "letter-spacing": "0.5px"
            }),
            html.Hr(style={"borderColor": "rgba(255, 255, 255, 0.2)", "margin": "1.5rem 0"}),
            
            # Navigation sections with icons and improved styling
            html.Div([
                html.P("INTERAÇÃO", style={"color": "rgba(255, 255, 255, 0.5)", "fontSize": "0.8rem", "letterSpacing": "1px", "marginBottom": "0.5rem", "marginLeft": "0.5rem"}),
                dbc.Nav(
                    [
                        dbc.NavLink(
                            [html.I(className="fas fa-comments me-2"), "Chat Assistente"], 
                            href="/chat", 
                            active="exact",
                            style=nav_link_style,
                            className="my-1"
                        ),
                    ],
                    vertical=True,
                    pills=True,
                ),
            ], style={"marginBottom": "1.5rem"}),
            
            # Primeiro Collapse: "Meus Clientes" - Análises de cliente
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-users me-2"), "Relacionamento com Clientes"],
                    id="clientes-collapse-button",
                    color="link",
                    style={
                        "color": "rgba(255, 255, 255, 0.8)",
                        "fontWeight": "500",
                        "fontSize": "0.9rem",
                        "textDecoration": "none",
                        "width": "100%",
                        "textAlign": "left",
                        "padding": "0.5rem 0.8rem",
                        "marginBottom": "0rem"
                    }
                ),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="fas fa-users me-2"), "Segmentação de Clientes"], 
                                href="/segmentacao", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-user-tag me-2"), "Clientes por RFMA"], 
                                href="/", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-sync me-2"), "Recorrência Mensal"], 
                                href="/recorrencia/mensal", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-calendar-check me-2"), "Recorrência Trimestral"], 
                                href="/recorrencia/trimestral", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="far fa-calendar-alt me-2"), "Recorrência Anual"], 
                                href="/recorrencia/anual", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-user-clock me-2"), "Retenção Anual"], 
                                href="/retencao", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-chart-pie me-2"), "Previsão de Retorno"], 
                                href="/predicao", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="clientes-collapse",
                    is_open=collapse_states["clientes"],
                    style={"paddingLeft": "1rem"}
                ),
            ], style={"marginBottom": "1.5rem"}),
            
            # Segunda Collapse: "Faturamento" - Análise financeira
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-chart-line me-2"), "Vendas"],
                    id="faturamento-collapse-button",
                    color="link",
                    style={
                        "color": "rgba(255, 255, 255, 0.8)",
                        "fontWeight": "500",
                        "fontSize": "0.9rem",
                        "textDecoration": "none",
                        "width": "100%",
                        "textAlign": "left",
                        "padding": "0.5rem 0.8rem",
                        "marginBottom": "0rem"
                    }
                ),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="fas fa-chart-line me-2"), "Crescimento do Negócio"], 
                                href="/faturamento/anual", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                            dbc.NavLink(
                                [html.I(className="fas fa-exclamation-triangle me-2"), "Vendas Atípicas"], 
                                href="/estoque/vendas-atipicas", 
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="faturamento-collapse",
                    is_open=collapse_states["faturamento"],
                    style={"paddingLeft": "1rem"}
                ),
            ], style={"marginBottom": "1.5rem"}),

            # Terceira Collapse: "Estoque" - Gestão de estoque
            html.Div([
                dbc.Button(
                    [html.I(className="fas fa-boxes me-2"), "Gestão do Estoque"],
                    id="estoque-collapse-button",
                    color="link",
                    style={
                        "color": "rgba(255, 255, 255, 0.8)",
                        "fontWeight": "500",
                        "fontSize": "0.9rem",
                        "textDecoration": "none",
                        "width": "100%",
                        "textAlign": "left",
                        "padding": "0.5rem 0.8rem",
                        "marginBottom": "0rem"
                    }
                ),
                dbc.Collapse(
                    dbc.Nav(
                        [
                            dbc.NavLink(
                                [html.I(className="fas fa-exclamation-circle me-2"), "Recomendação de Compras"], 
                                href="/estoque/produtos",
                                active="exact",
                                style=nav_link_style,
                                className="my-1"
                            ),
                        ],
                        vertical=True,
                        pills=True,
                    ),
                    id="estoque-collapse",
                    is_open=collapse_states["estoque"],
                    style={"paddingLeft": "1rem"}
                ),
            ], style={"marginBottom": "1.5rem"}),

            html.Hr(style={"borderColor": "rgba(255, 255, 255, 0.2)", "margin": "1.5rem 0"}),
            
            # Data type selection dropdown
            html.Div([
                html.H5("Selecione a Base de Dados:", style={"color": "white", "fontSize": "1rem", "marginBottom": "1rem", "textAlign": "center"}),
                dcc.Dropdown(
                    id="data-type-selection",
                    options=[{"label": data_type, "value": data_type} for data_type in available_data_types],
                    value=available_data_types[0] if available_data_types else None,
                    clearable=False,
                    style={"color": "black", "backgroundColor": "white"}
                )
            ], style={
                "marginTop": "1rem",
                "background": "rgba(255, 255, 255, 0.05)",
                "padding": "1.5rem",
                "borderRadius": "12px",
                "display": "block" if show_data_type_selection else "none"  # Mostrar apenas se necessário
            }),


            # Botão de logout
            html.Div([
                html.A(  # Link HTML direto
                    html.Button(
                        [html.I(className="fas fa-sign-out-alt me-2"), "Sair"],
                        className="btn btn-danger w-100 mt-4"
                    ),
                    href="/logout/",  # Link direto para a rota de logout
                    style={"textDecoration": "none"}
                )
            ]),


            # Time last updated indicator
            html.Div([
                html.P("Última atualização:", style={"color": "rgba(255, 255, 255, 0.5)", "fontSize": "0.8rem", "marginBottom": "0.2rem"}),
                html.P(id="last-updated", children=time.strftime("%d/%m/%Y %H:%M:%S"), style={"color": "white", "fontSize": "0.9rem", "fontWeight": "600"})
            ], style={
                "marginTop": "2rem", 
                "textAlign": "center"
            })
        ],
        className="sidebar"
    )
    
    return sidebar

# =============================================================================
# Callbacks para controlar os collapses da sidebar
# =============================================================================

# dashboard.py - Callback para inicializar sidebar
@application.callback(
    Output("sidebar-container", "children"),
    Output("selected-client", "data"),
    Input("url", "search")
)
def initialize_sidebar(search):
    # Extrair cliente da URL (passado pelo sistema de login)
    if search and 'cliente=' in search:
        # Extrair o cliente do parâmetro de consulta (ex: ?cliente=BENY)
        cliente = search.split('cliente=')[1].split('&')[0]
    else:
        # Verificar se há um cliente na sessão
        if 'cliente' in session:
            cliente = session['cliente']
        else:
            # Se não tiver cliente na URL nem na sessão, redirecionar para login
            return html.Div("Redirecionando para login..."), None
    
    # Obter tipos de dados disponíveis para o cliente
    available_data_types = get_available_data_types(cliente)
    
    # Criar sidebar com o cliente específico
    sidebar = create_sidebar(cliente, available_data_types)
    # print("sidebar gerada:", sidebar)
    
    return sidebar, cliente

# Callbacks das collapses
@application.callback(
    Output("clientes-collapse", "is_open"),
    [Input("clientes-collapse-button", "n_clicks")],
    [State("clientes-collapse", "is_open")],
)
def toggle_clientes_collapse(n, is_open):
    global collapse_states  # Acessa a variável global
    if n:
        # Atualiza a variável global com o novo estado
        collapse_states["clientes"] = not is_open
        return not is_open
    return is_open

@application.callback(
    Output("faturamento-collapse", "is_open"),
    [Input("faturamento-collapse-button", "n_clicks")],
    [State("faturamento-collapse", "is_open")],
)
def toggle_faturamento_collapse(n, is_open):
    global collapse_states  # Acessa a variável global
    if n:
        # Atualiza a variável global com o novo estado
        collapse_states["faturamento"] = not is_open
        return not is_open
    return is_open

@application.callback(
    Output("estoque-collapse", "is_open"),
    [Input("estoque-collapse-button", "n_clicks")],
    [State("estoque-collapse", "is_open")],
)
def toggle_estoque_collapse(n, is_open):
    global collapse_states  # Acessa a variável global
    if n:
        # Atualiza a variável global com o novo estado
        collapse_states["estoque"] = not is_open
        return not is_open
    return is_open

@application.callback(
    Output("titulo-app", "children"),
    [Input("selected-client", "data"),
     Input("selected-data-type", "data")]
)
def update_sidebar_title(selected_client):
    if selected_client is None:
        return "Client"
    return f"{selected_client}"

# =============================================================================
# Layout principal (layout condicional baseado na autenticação)
# =============================================================================
application.layout = html.Div([
    dcc.Location(id='url', refresh=True),  # refresh=True para permitir recarregar após login
    html.Div(id='page-content')
])

# Definir uma página de login específica com IDs corretos
login_layout = html.Div([
    html.H2("Login MALOKA'AI", style={"textAlign": "center", "marginTop": "50px", "color": gradient_colors['blue_gradient'][0]}),
    html.Div([
        html.Label("Email:"),
        dcc.Input(id="input-email", type="email", placeholder="Digite seu email", style={"width": "100%", "marginBottom": "10px"}),
        html.Label("Senha:"),
        dcc.Input(id="input-senha", type="password", placeholder="Digite sua senha", style={"width": "100%", "marginBottom": "20px"}),
        dbc.Button("Entrar", id="botao-login", style={"width": "100%"}, className="mb-3"),
        html.Div(id="output-login")  # Este é o ID que o callback vai usar
    ], style={"width": "300px", "margin": "0 auto", "padding": "20px", "border": "1px solid #ddd", "borderRadius": "5px", "backgroundColor": "white"})
], style={"height": "100vh", "background": f"linear-gradient(135deg, {gradient_colors['blue_gradient'][0]} 0%, {gradient_colors['blue_gradient'][2]} 100%)", "paddingTop": "10vh"})

@application.callback(
    [Output("output-login", "children"),
     Output("url", "pathname")],
    Input("botao-login", "n_clicks"),
    [State("input-email", "value"),
     State("input-senha", "value")],
    prevent_initial_call=True
)

def validar_login(n_clicks, email, senha):
    if n_clicks is None:
        return dash.no_update, dash.no_update
    
    # Verificação básica de preenchimento
    if not email or not senha:
        return dbc.Alert("Por favor, preencha email e senha.", color="warning"), dash.no_update
    
    # Verificar se a senha está correta - com trim
    SENHA_PADRAO = os.getenv("senhaLogin")
    if senha.strip() != SENHA_PADRAO:
        return dbc.Alert("Senha incorreta.", color="danger"), dash.no_update
    
    # Extrair domínio do email - método mais robusto
    email = email.strip().lower()
    dominio = None
    
    try:
        if '@' in email:
            # Obter a parte após o @
            dominio = '@' + email.split('@')[1]
            
            # Listar os domínios válidos com mais casos
            DOMINIOS_VALIDOS = {
                '@bibi': 'BIBI',
                '@bibi.com': 'BIBI',
                '@beny': 'BENY',
                '@beny.com': 'BENY',
                '@espantalho': 'ESPANTALHO',
                '@espantalho.com': 'ESPANTALHO',
                '@add': 'ADD',
                '@add.com': 'ADD'
            }
            
            # Verificar se o domínio está na lista
            if dominio in DOMINIOS_VALIDOS:
                empresa = DOMINIOS_VALIDOS[dominio]
                
                # Tentar armazenar na sessão com tratamento de erro
                try:
                    session['cliente'] = empresa
                    # Verificar se foi armazenado corretamente
                    if session.get('cliente') == empresa:
                        return dbc.Alert(f"Login bem-sucedido! Redirecionando...", color="success"), "/"
                    else:
                        return dbc.Alert("Erro ao armazenar na sessão. Tente novamente.", color="danger"), dash.no_update
                except Exception as e:
                    return dbc.Alert(f"Erro na sessão: {str(e)}", color="danger"), dash.no_update
            else:
                return dbc.Alert(f"Domínio '{dominio}' não está cadastrado.", color="danger"), dash.no_update
        else:
            return dbc.Alert("Email inválido. Use o formato usuario@dominio.com", color="danger"), dash.no_update
    except Exception as e:
        return dbc.Alert(f"Erro ao processar login: {str(e)}", color="danger"), dash.no_update
         
          
# Callback para mostrar conteúdo baseado na URL/autenticação
@application.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')]
)
def display_page(pathname):
    # Log para rastreamento
    print(f"Callback display_page executado - URL: {pathname} - Cliente na sessão: {'sim' if 'cliente' in session else 'não'}")
    
    # Verificar se não está autenticado
    if 'cliente' not in session:
        print("Usuário não autenticado, exibindo login_layout")
        # Retornar a página de login
        return login_layout
    
    # Se estiver autenticado
    try:
        cliente = session['cliente']
        available_data_types = get_available_data_types(cliente)
        print(f"Usuário autenticado, carregando dashboard para cliente: {cliente}")
        
        # Layout do dashboard
        return html.Div([
            dcc.Store(id='selected-data', storage_type='session'),
            dcc.Store(id='selected-client', data=cliente),
            dcc.Store(id='selected-data-type', data="PF"),
            dcc.Store(id='last-data-load-time', data=time.time()),
            dcc.Loading(
                id="loading-overlay",
                type="circle",
                children=html.Div(id="loading-output-overlay"),
                style={"position": "fixed", "top": "50%", "left": "50%", 
                    "transform": "translate(-50%, -50%)", "zIndex": "9999"}
            ),
            html.Div(id="sidebar-container", children=create_sidebar(cliente, available_data_types)),
            html.Div(id="page-content-dashboard", children=[])
        ])
    except Exception as e:
        print(f"ERRO no callback display_page: {str(e)}")
        # Em caso de erro, mostrar mensagem de erro
        return html.Div([
            html.H3("Erro ao renderizar a página", style={"color": "red"}),
            html.Pre(f"Pathname: {pathname}"),
            html.Pre(f"Erro: {str(e)}"),
            html.Button("Voltar para o início", id="error-redirect-button")
        ])

# Rota raiz
@server.route('/')
def index():
    # Log para rastreamento
    print("Acessando rota raiz '/'")
    try:
        # Redirecionar para a aplicação Dash
        return redirect('/app/')
    except Exception as e:
        print(f"ERRO na rota '/': {str(e)}")
        return f"Erro no redirecionamento: {str(e)}"

# Rota principal da aplicação
@server.route('/app/')
def app_index():
    # Log para rastreamento
    print(f"Acessando rota '/app/' - Cliente na sessão: {'sim' if 'cliente' in session else 'não'}")
    return application.index()  # Sempre retornar o app.index() - o Dash decidirá o que mostrar

# Rota de login específica
@server.route('/app/login/')
def login_page():
    # Log para rastreamento
    print(f"Acessando rota '/app/login/'")
    # Se já estiver autenticado, redirecionar para o dashboard
    if 'cliente' in session:
        return redirect('/app/')
    # Caso contrário, mostrar a aplicação Dash que decidirá mostrar o login_layout
    return application.index()

# Atualize a rota de logout para ser mais direta:
@server.route('/logout/')
def logout():
    # Limpar a sessão
    session.clear()
    # Redirecionar diretamente para a raiz que mostrará o login
    return redirect('/')  # Redirecionamento mais direto

@server.route('/debug-session/')
def debug_session():
    # Retorna informações sobre a sessão atual
    print("Acessando rota de debug '/debug-session/'")
    session_info = {
        'has_session': 'sim' if 'cliente' in session else 'não',
        'cliente': session.get('cliente', 'nenhum')
    }
    return f"Informações da sessão: {session_info}"
      

def update_data_source(selected_data_type, last_load_time, selected_client):
    # Validar entradas
    if not selected_client or not selected_data_type:
        return None, None, "Selecione o tipo de dados", time.strftime("%d/%m/%Y %H:%M:%S"), last_load_time, None
    
    # Calculate if we need to reload data (every hour)
    current_time = time.time()
    time_diff = current_time - last_load_time
    
    # Verificar se o contexto da chamada foi por mudança de cliente/data-type
    if dash.callback_context.triggered_id not in ['client-selection', 'data-type-selection'] and time_diff < 3600:
        # Just update the last updated time
        formatted_time = time.strftime("%d/%m/%Y %H:%M:%S")
        titulo = f"{selected_client} - {selected_data_type}"
        
        return dash.no_update, selected_client, selected_data_type, titulo, formatted_time, last_load_time, None
    
    # Carregar dados para o cliente e tipo selecionados
    data = load_data(selected_client, selected_data_type)
    formatted_time = time.strftime("%d/%m/%Y %H:%M:%S")
    
    if data.get("error", False):
        error_message = data.get("message", "Erro ao carregar dados")
        return None, selected_client, selected_data_type, f"ERRO: {error_message}", formatted_time, current_time, error_message
    
    return {
        "df": data["df"].to_json(date_format='iso', orient='split') if data["df"] is not None else None,
        "df_RC_Mensal": data["df_RC_Mensal"].to_json(date_format='iso', orient='split') if data["df_RC_Mensal"] is not None else None,
        "df_RC_Trimestral": data["df_RC_Trimestral"].to_json(date_format='iso', orient='split') if data["df_RC_Trimestral"] is not None else None,
        "df_RC_Anual": data["df_RC_Anual"].to_json(date_format='iso', orient='split') if data["df_RC_Anual"] is not None else None,
        "df_Previsoes": data["df_Previsoes"].to_json(date_format='iso', orient='split') if data["df_Previsoes"] is not None else None,
        "df_RT_Anual": data["df_RT_Anual"].to_json(date_format='iso', orient='split') if data["df_RT_Anual"] is not None else None,
        "df_fat_Anual": data["df_fat_Anual"].to_json(date_format='iso', orient='split') if data["df_fat_Anual"] is not None else None,
        "df_fat_Anual_Geral": data["df_fat_Anual_Geral"].to_json(date_format='iso', orient='split') if data["df_fat_Anual_Geral"] is not None else None,
        "df_fat_Mensal": data["df_fat_Mensal"].to_json(date_format='iso', orient='split') if data["df_fat_Mensal"] is not None else None,
        "company_context": data["company_context"],
        "segmentos_context": data["segmentos_context"]
    }, selected_client, selected_data_type, data["titulo"], formatted_time, current_time, None

# =============================================================================
# Páginas do Dashboard
# =============================================================================

def get_faturamento_anual_layout(data, selected_client=None):
    try:
        # -------------------------------------------------------
        # --- Gráfico 1: Evolução Percentual Anual das Vendas ---
        # -------------------------------------------------------
        if data.get("df_fat_Anual") is None:
            return html.Div([
                html.H2("Crescimento do Negócio", className="dashboard-title"),
                create_card(
                    "Dados Indisponíveis",
                    html.Div([
                        html.P("Não foram encontrados dados de faturamento para este cliente.", className="text-center text-muted my-4"),
                        html.I(className="fas fa-chart-line fa-4x text-muted d-block text-center mb-3"),
                        html.P("Verifique se os arquivos necessários estão presentes: faturamento_anual.xlsx, faturamento_anual_geral.xlsx, faturamento_mensal.xlsx", 
                               className="text-muted text-center")
                    ])
                )
            ], style=content_style)
        
        df_fat = pd.read_json(io.StringIO(data["df_fat_Anual"]), orient='split')
        df_fat = df_fat.sort_values("Ano")
        
        # Verificar se já temos a coluna de evolução, senão calculá-la
        if 'Evolucao (%)' not in df_fat.columns:
            df_fat['Evolucao (%)'] = df_fat['total_item'].pct_change() * 100
        
        df_fat['label'] = df_fat.apply(lambda row: f"{formatar_percentual(row['Evolucao (%)'])}\n{formatar_moeda(row['total_item'])}" 
                                    if not pd.isna(row['Evolucao (%)']) else f"{formatar_moeda(row['total_item'])}", axis=1)
        
        # Calculate YoY growth for the metrics row
        last_year_growth = df_fat['Evolucao (%)'].iloc[-1] if len(df_fat) > 1 and not df_fat.empty else 0
        total_sales = df_fat['total_item'].iloc[-1] if not df_fat.empty else 0
        avg_growth = df_fat['Evolucao (%)'].mean() if len(df_fat) > 1 else 0
        
        # Handle NaN values
        if pd.isna(last_year_growth): last_year_growth = 0
        if pd.isna(avg_growth): avg_growth = 0
        
        # Create metrics row
        metrics = [
            {"title": "Faturamento Total (Último Ano)", "value": formatar_moeda(total_sales), "color": color['accent']},
            {"title": "Crescimento Anual", "value": formatar_percentual(last_year_growth), "change": last_year_growth, "color": color['secondary']},
            {"title": "Média de Crescimento", "value": formatar_percentual(avg_growth), "color": color['success']}
        ]
        
        metrics_row = create_metric_row(metrics)
        
        # Enhanced growth chart
        fig_fat = px.bar(
            df_fat,
            x='Ano',
            y='Evolucao (%)',
            text='label',
            color_discrete_sequence=[color['secondary']],
            template='plotly_white'
        )
        
        fig_fat.update_xaxes(
            tickmode='array', 
            tickvals=df_fat['Ano'].unique(),
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_fat.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_fat.update_layout(
            xaxis_title="Ano",
            yaxis_title="Crescimento (%)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig_fat.update_traces(
            textposition='outside', 
            textfont=dict(size=12, family="Montserrat"),
            selector=dict(type='bar')  # Aplicar apenas aos traces de tipo barra
        )

        # ------------------------------------------
        # --- Gráfico 2: Faturamento Anual ---------
        # ------------------------------------------

        df_ano = pd.read_json(io.StringIO(data["df_fat_Anual_Geral"]), orient='split')
        if df_ano.index.name == 'Ano' or (hasattr(df_ano.index, 'name') and df_ano.index.name is not None):
            # Se o índice for nomeado 'Ano', transforme-o em coluna
            df_ano = df_ano.reset_index()
        elif 'Ano' not in df_ano.columns:
            # Se não tiver coluna 'Ano', primeiro tente verificar se o índice tem valores que podem ser anos
            if df_ano.index.dtype in ['int64', 'float64'] and df_ano.index.min() >= 2000:
                # Parece que o índice contém anos, vamos usá-lo
                df_ano['Ano'] = df_ano.index
                df_ano = df_ano.reset_index(drop=True)
            else:
                # Ou tente criar uma sequência de anos com base no número de registros
                anos_desejados = [2021, 2022, 2023, 2024, 2025][:len(df_ano)]
                # Verificar se temos anos suficientes na nossa lista
                if len(anos_desejados) < len(df_ano):
                    # Adicionar mais anos se necessário
                    anos_extras = list(range(anos_desejados[-1] + 1, anos_desejados[-1] + 1 + (len(df_ano) - len(anos_desejados))))
                    anos_desejados.extend(anos_extras)
                df_ano['Ano'] = anos_desejados

        is_bibi_data = (
        'Cadastrado' in df_ano.columns and 
        'Sem Cadastro' in df_ano.columns
        )
        if is_bibi_data:
            # Para BIBI: gráfico de barras empilhadas Cadastrado vs Sem Cadastro
            fig_ano = px.bar(
                df_ano,
                x='Ano',
                y=['Cadastrado', 'Sem Cadastro'],
                barmode='stack',
                labels={"value": "Faturamento (R$)", "variable": "Tipo de Cliente"},
                color_discrete_map={
                    'Cadastrado': '#1f77b4',
                    'Sem Cadastro': '#ff7f0e'
                },
                template='plotly_white'
            )
            
            # Configurar texto dentro das barras
            # Update: Usar texttemplate para mostrar valores dentro das barras
            for i, bar in enumerate(fig_ano.data):
                # Formatar valores para mostrar dentro das barras
                text_values = []
                for val in bar.y:
                    if val is not None and val > 0:
                        text_values.append(formatar_moeda(val))
                    else:
                        text_values.append("")
                
                # Aplicar texto dentro das barras
                fig_ano.data[i].text = text_values
                fig_ano.data[i].textposition = 'inside'
                fig_ano.data[i].insidetextanchor = 'middle'
                fig_ano.data[i].textfont = dict(
                    family="Montserrat",
                    size=12,
                    color="white"
                )
            
            # Adicionar rótulos de total no topo das barras
            for i in range(len(df_ano)):
                total = df_ano.iloc[i]['Cadastrado'] + df_ano.iloc[i]['Sem Cadastro']
                fig_ano.add_annotation(
                    x=df_ano['Ano'].iloc[i],
                    y=total,
                    text=f"Total: {formatar_moeda(total)}",
                    showarrow=False,
                    yshift=10,
                    font=dict(size=12, color="black", family="Montserrat", weight="bold")
                )
            
            # Título específico para BIBI
            titulo_grafico2 = "Faturamento Anual - Clientes Cadastrados vs Sem Cadastro"
            
        else:
            # Para outros clientes: gráfico de barras simples com total_item
            # Verificar se temos a coluna total_item
            if 'total_item' not in df_ano.columns:
                # Se tiver Cadastrado e Sem Cadastro, podemos calcular o total
                if 'Cadastrado' in df_ano.columns and 'Sem Cadastro' in df_ano.columns:
                    df_ano['total_item'] = df_ano['Cadastrado'] + df_ano['Sem Cadastro']
                else:
                    # Procurar outras colunas numéricas
                    potential_total_columns = [col for col in df_ano.columns if col not in ['Ano', 'index']]
                    if not potential_total_columns:
                        return html.Div([
                            html.H2("Crescimento do Negócio", className="dashboard-title"),
                            create_card(
                                "Formato de Dados Incompatível",
                                html.Div([
                                    html.P("Não foi possível identificar a coluna de faturamento nos dados anuais.", className="text-center text-muted my-4"),
                                    html.I(className="fas fa-exclamation-triangle fa-4x text-warning d-block text-center mb-3")
                                ])
                            )
                        ], style=content_style)
                    
                    # Usar a primeira coluna numérica
                    for col in potential_total_columns:
                        if pd.api.types.is_numeric_dtype(df_ano[col]):
                            df_ano['total_item'] = df_ano[col]
                            break
            
            # Gráfico de barras padrão para outros clientes
            fig_ano = px.bar(
                df_ano,
                x='Ano',
                y='total_item',
                color_discrete_sequence=[gradient_colors['blue_gradient'][1]],
                template='plotly_white'
            )
            
            # Add value annotations
            for i, row in df_ano.iterrows():
                fig_ano.add_annotation(
                    x=row['Ano'],
                    y=row['total_item'],
                    text=formatar_moeda(row['total_item']),
                    showarrow=False,
                    yshift=10,
                    font=dict(size=12, color="black", family="Montserrat")
                )
            
            # Título padrão para outros clientes
            titulo_grafico2 = "Faturamento Anual"
        
        # Configurações comuns para o gráfico 2
        fig_ano.update_layout(
            xaxis_title="Ano",
            yaxis_title="Faturamento (R$)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig_ano.update_xaxes(
            tickmode='array', 
            tickvals=df_ano['Ano'].unique(),
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_ano.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )

        # ----------------------------------------------
        # --- Gráfico 3: Faturamento Mensal por Ano ----
        # ----------------------------------------------

        df_mensal = pd.read_json(io.StringIO(data["df_fat_Mensal"]), orient='split')
        if 'Mês' not in df_mensal.columns:
            df_mensal = df_mensal.reset_index(drop=True)
            # Se o número de linhas for 12, atribuimos os meses de 1 a 12; caso contrário, usamos o número de linhas existente
            if len(df_mensal) == 12:
                df_mensal['Mês'] = list(range(1, 13))
            else:
                df_mensal['Mês'] = list(range(1, len(df_mensal) + 1))
        
        df_mensal_long = df_mensal.melt(id_vars="Mês", var_name="Ano", value_name="Faturamento")
        
        # Enhanced monthly sales chart with custom colors
        custom_colors = ["orange", "darkred", color['secondary'], color['accent'], gradient_colors['green_gradient'][1], color['warning']]
        
        fig_mensal = px.bar(
            df_mensal_long,
            x="Mês",
            y="Faturamento",
            color="Ano",
            barmode="group",
            color_discrete_sequence=custom_colors,
            template='plotly_white'
        )
        
        # Define os rótulos dos meses e ajusta o range do eixo x para evitar que a primeira barra seja cortada
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        
        fig_mensal.update_layout(
            xaxis_title="Mês",
            yaxis_title="Faturamento (R$)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        fig_mensal.update_xaxes(
            range=[0.5, 12.5],
            tickmode='array',
            tickvals=list(range(1, 13)),
            ticktext=meses,
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig_mensal.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        # --- Layout final: três cards com os gráficos ---
        layout = html.Div([
            html.H2("Crescimento do Negócio", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # Card for annual growth rate
            create_card(
                "Evolução Percentual Anual das Vendas",
                dcc.Graph(figure=fig_fat, config={"responsive": True}),
            ),
            
            # Card for annual sales
            create_card(
                titulo_grafico2,
                dcc.Graph(figure=fig_ano, config={"responsive": True}),
            ),
            
            # Card for monthly sales by year
            create_card(
                "Faturamento Mensal por Ano",
                dcc.Graph(figure=fig_mensal, config={"responsive": True}),
            ),
        ], style=content_style)
        
        return layout
        
    except Exception as e:
        # Em caso de erro, exibir mensagem amigável e informações do erro
        return html.Div([
            html.H2("Crescimento do Negócio", className="dashboard-title"),
            
            create_card(
                "Erro ao carregar os dados",
                html.Div([
                    html.P("Ocorreu um problema ao carregar os dados de faturamento. Detalhes do erro:"),
                    html.Pre(str(e), style={"background": "#f8f9fa", "padding": "15px", "borderRadius": "5px", "whiteSpace": "pre-wrap"}),
                    html.P("Tente recarregar a página ou entre em contato com o suporte técnico.")
                ])
            )
        ], style=content_style)

def get_rfma_layout(data):
    if data.get("df") is None:
        return html.Div([
            html.H2("Análise RFMA de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados RFMA para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-user-tag fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo analytics_cliente está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df = pd.read_json(io.StringIO(data["df"]), orient='split')
    
    # Calculate metrics for the metrics row
    avg_recency = df['Recency'].mean()
    avg_frequency = df['Frequency'].mean()
    avg_monetary = df['Monetary'].mean()
    avg_age = df['Age'].mean()
    
    # Create metrics row
    metrics = [
        {"title": "Média de Recência (dias)", "value": formatar_numero(avg_recency, 1), "color": colors[0]},
        {"title": "Média de Frequência", "value": formatar_numero(avg_frequency, 1), "color": colors[1]},
        {"title": "Valor Médio (R$)", "value": formatar_moeda(avg_monetary), "color": colors[2]},
        {"title": "Média de Antiguidade (dias)", "value": formatar_numero(avg_age, 1), "color": colors[3]}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    figures = []
    x_axis_titles_rfma = {
        "Recency": "Intervalo de Recência (dias)",
        "Frequency": "Intervalo de Frequência (compras)",
        "Monetary": "Intervalo de Valor Monetário (R$)",
        "Age": "Intervalo de Idade (dias)"
    }
    
    rfma_metrics_order = [
        ("Recency", "R_range", colors[0]),
        ("Frequency", "F_range", colors[1]),
        ("Monetary", "M_range", colors[2]),
        ("Age", "A_range", colors[3]),
    ]
    
    for metric, col, color in rfma_metrics_order:
        if col in df.columns:
            counts = df[col].value_counts()
            ordered_index = sorted(counts.index, key=lambda x: float(x.split('-')[0].replace('+', '')))
            counts = counts.loc[ordered_index]
            
            # Add gradient colors for each bar
            color_scale = [color, f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.7)"]
            
            fig = px.bar(
                x=counts.index,
                y=counts.values,
                labels={'x': col, 'y': 'Número de Clientes'},
                color_discrete_sequence=[color],
                text=counts.values,
                category_orders={col: ordered_index},
                template='plotly_white'
            )
            
            x_title = x_axis_titles_rfma.get(metric, col)
            
            fig.update_layout(
                xaxis_title=x_title, 
                yaxis_title="Número de Clientes",
                margin=dict(t=20, b=50, l=50, r=50),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            fig.update_traces(
                textposition='outside',
                textfont=dict(size=12, family="Montserrat"),
                marker=dict(
                    color=color,
                    opacity=0.8,
                    line=dict(width=1, color=color)
                )
            )
            
            fig.update_xaxes(
                title_font=dict(size=12, family="Montserrat"),
                gridcolor='rgba(0,0,0,0.05)'
            )
            
            fig.update_yaxes(
                title_font=dict(size=12, family="Montserrat"),
                gridcolor='rgba(0,0,0,0.05)'
            )
            
            figures.append(fig)
    
    return html.Div(
        [
            html.H2("Análise RFMA de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # First row of charts
            dbc.Row(
                [
                    dbc.Col(
                        create_card(
                            "Distribuição de Recência",
                            dcc.Graph(id="recency-dist", figure=figures[0] if len(figures)>0 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                    dbc.Col(
                        create_card(
                            "Distribuição de Frequência",
                            dcc.Graph(id="frequency-dist", figure=figures[1] if len(figures)>1 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                ],
                className="mb-4",
            ),
            
            # Second row of charts
            dbc.Row(
                [
                    dbc.Col(
                        create_card(
                            "Distribuição de Valor Monetário",
                            dcc.Graph(id="monetary-dist", figure=figures[2] if len(figures)>2 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                    dbc.Col(
                        create_card(
                            "Distribuição de Antiguidade",
                            dcc.Graph(id="age-dist", figure=figures[3] if len(figures)>3 else {}, config={"responsive": True})
                        ),
                        lg=6, md=12,
                    ),
                ],
                className="mb-4",
            ),
        ],
        style=content_style,
    )

def get_segmentacao_layout(data):
    if data.get("df") is None:
        return html.Div([
            html.H2("Segmentação de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de segmentação para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-users fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo analytics_cliente está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df = pd.read_json(io.StringIO(data["df"]), orient='split')
    
    # Calculate metrics for the metrics row
    total_clients = len(df)
    active_clients = len(df[df['Segmento'].isin(['Novos', 'Campeões', 'Fiéis Alto Valor', 'Fiéis Baixo Valor', 'Recentes Alto Valor', 'Recentes Baixo Valor'])])
    inactive_clients = len(df[df['Segmento'].isin(['Sumidos', 'Inativos'])])
    champions = len(df[df['Segmento'] == 'Campeões'])
    
    # Create metrics row
    metrics = [
        {"title": "Total de Clientes", "value": formatar_numero(total_clients), "color": color['primary']},
        {"title": "Clientes Ativos", "value": formatar_numero(active_clients), "color": color['success']},
        {"title": "Clientes Inativos", "value": formatar_numero(inactive_clients), "color": color['danger']},
        {"title": "Clientes Campeões", "value": formatar_numero(champions), "color": gradient_colors['green_gradient'][0]}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Construir gráfico diretamente aqui, em vez de depender de um callback
    segment_counts = df['Segmento'].value_counts().reset_index()
    segment_counts.columns = ['Segmento', 'Quantidade de Clientes']

    # Calcular percentuais
    total_clients = segment_counts['Quantidade de Clientes'].sum()
    segment_counts['Percentual'] = segment_counts['Quantidade de Clientes'] / total_clients * 100
    
    # Criar o gráfico de barras diretamente na função
    fig_segments = px.bar(
        segment_counts, 
        x='Segmento', 
        y='Quantidade de Clientes', 
        color='Segmento', 
        labels={"Segmento": "Segmentos"},
        color_discrete_map=cores_segmento,
        template='plotly_white'
    )
    
    # Adicionar anotações de valores
    for i, row in segment_counts.iterrows():
        # Formatar percentual com 1 casa decimal
        formatted_pct = f"{row['Percentual']:.1f}%".replace('.', ',')
        
        fig_segments.add_annotation(
            x=row['Segmento'],
            y=row['Quantidade de Clientes'],
            text=f"{formatar_numero(row['Quantidade de Clientes'])} ({formatted_pct})",
            showarrow=False,
            yshift=10,
            font=dict(size=12, family="Montserrat")
        )
    
    fig_segments.update_layout(
        margin=dict(t=30, b=50, l=50, r=50),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=500,
        showlegend=False,
        yaxis=dict(
            title="Quantidade de Clientes",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        xaxis=dict(
            title="Segmentos",
            title_font=dict(size=14, family="Montserrat"),
            tickfont=dict(size=12),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        clickmode='event+select'
    )
    
    # Layout with cards
    layout = html.Div(
        [
            html.H2("Segmentação de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # Distribution row
            dbc.Row(
            [
                dbc.Col(
                    create_card(
                        "Distribuição de Segmentos",
                        dcc.Graph(
                            id="segment-distribution",
                            figure=fig_segments,
                            config={"responsive": True, "displayModeBar": False}
                        )
                    ),
                    width=12  # Ocupa toda a largura disponível
                ),
            ],
            className="mb-4",
        ),
            
            # Client list
            create_card(
                html.Div(id="client-list-header", children="Clientes do Segmento Selecionado"),
                html.Div(
                    id="client-list",
                    children=html.Div([
                        html.P("Selecione um segmento no gráfico acima para ver os clientes.", className="text-center text-muted my-4"),
                        html.Div(className="text-center", children=[
                            html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                            html.P("Clique em uma barra para visualizar detalhes", className="text-muted mt-2")
                        ])
                    ])
                )
            )
        ],
        style=content_style,
    )
    return layout

def get_recorrencia_mensal_layout(data):
    if data.get("df_RC_Mensal") is None:
        return html.Div([
            html.H2("Recorrência Mensal", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de recorrência mensal para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-sync fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo metricas_recorrencia_mensal.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_RC_Mensal = pd.read_json(io.StringIO(data["df_RC_Mensal"]), orient='split')
    
    # Calculate metrics for the metrics row
    current_retention = df_RC_Mensal['retention_rate'].iloc[-1] if not df_RC_Mensal.empty else 0
    avg_retention = df_RC_Mensal['retention_rate'].mean()
    max_retention = df_RC_Mensal['retention_rate'].max()
    min_retention = df_RC_Mensal['retention_rate'].min()
    
    retention_change = df_RC_Mensal['retention_rate'].iloc[-1] - df_RC_Mensal['retention_rate'].iloc[-2] if len(df_RC_Mensal) > 1 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Taxa de Retenção Atual", "value": formatar_percentual(current_retention), "change": retention_change, "color": color['accent']},
        {"title": "Média de Retenção", "value": formatar_percentual(avg_retention), "color": color['secondary']},
        {"title": "Maior Taxa", "value": formatar_percentual(max_retention), "color": color['success']},
        {"title": "Menor Taxa", "value": formatar_percentual(min_retention), "color": color['warning']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced monthly retention chart
    fig_mensal = px.line(
        df_RC_Mensal, 
        x='yearmonth', 
        y='retention_rate', 
        markers=True, 
        color_discrete_sequence=[color['secondary']],
        template='plotly_white'
    )
    
    # Add thicker line and bigger markers
    fig_mensal.update_traces(
        line=dict(width=3),
        marker=dict(size=10, line=dict(width=2, color='white'))
    )
    
    # Add a moving average line
    window_size = 3
    if len(df_RC_Mensal) >= window_size:
        df_RC_Mensal['moving_avg'] = df_RC_Mensal['retention_rate'].rolling(window=window_size).mean()
        
        fig_mensal.add_trace(
            go.Scatter(
                x=df_RC_Mensal['yearmonth'],
                y=df_RC_Mensal['moving_avg'],
                mode='lines',
                name=f'Média Móvel ({window_size} meses)',
                line=dict(color=color['accent'], width=2, dash='dash')
            )
        )
    
    # Add target line at 30%
    fig_mensal.add_shape(
        type="line",
        x0=df_RC_Mensal['yearmonth'].iloc[0],
        y0=30,
        x1=df_RC_Mensal['yearmonth'].iloc[-1],
        y1=30,
        line=dict(
            color=color['success'],
            width=2,
            dash="dot",
        )
    )
    
    fig_mensal.add_annotation(
        x=df_RC_Mensal['yearmonth'].iloc[-1],
        y=30,
        text="Meta (30%)",
        showarrow=False,
        yshift=10,
        xshift=30,
        font=dict(size=12, color=color['success'])
    )
    
    fig_mensal.update_layout(
        xaxis_title="Mês", 
        yaxis_title="Taxa de Retenção (%)", 
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig_mensal.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)',
        tickangle=-45
    )
    
    fig_mensal.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Enhanced table
    colunas_mensais = ["yearmonth", "retained_customers", "prev_total_customers", "retention_rate"]
    renomear_mensal = {
        "yearmonth": "Mês/Ano",
        "retained_customers": "Clientes Recorrentes",
        "prev_total_customers": "Total de Clientes",
        "retention_rate": "Taxa de Retenção (%)",
    }
    df_mensal_filtrado = df_RC_Mensal[colunas_mensais]
    
    # Create visualization for customer counts
    fig_customers = px.bar(
        df_RC_Mensal,
        x='yearmonth',
        y=['retained_customers', 'prev_total_customers'],
        barmode="group",
        labels={"value": "Número de Clientes", "variable": "Tipo de Cliente"},
        color_discrete_map={
            'retained_customers': color['accent'],
            'prev_total_customers': color['secondary']
        },
        template='plotly_white'
    )
    
    fig_customers.update_layout(
        xaxis_title="Mês",
        yaxis_title="Número de Clientes",
        margin=dict(t=50, b=50, l=50, r=50),
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig_customers.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)',
        tickangle=-45
    )
    
    fig_customers.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Rename traces
    for trace in fig_customers.data:
        if trace.name == 'retained_customers':
            trace.name = "Clientes Recorrentes"
        elif trace.name == 'prev_total_customers':
            trace.name = "Total de Clientes"
    
    # Layout with cards
    layout = html.Div([
        html.H2("Recorrência Mensal", className="dashboard-title"),
        
        # Summary metrics row
        metrics_row,
        
        # Retention rate chart
        create_card(
            "Taxa de Recorrência Mensal (%)",
            dcc.Graph(id='recorrencia-mensal-graph', figure=fig_mensal, config={"responsive": True})
        ),
        
        # Customer counts chart
        create_card(
            "Composição de Clientes por Mês",
            dcc.Graph(id='recorrencia-mensal-customers', figure=fig_customers, config={"responsive": True})
        ),
        
        # Table with metrics
        create_card(
            "Métricas Mensais Detalhadas",
            dash_table.DataTable(
                id='table-recorrencia-mensal',
                columns=[{"name": renomear_mensal.get(col, col), "id": col} for col in colunas_mensais],
                data=df_mensal_filtrado.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "center",
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
                        "if": {"column_id": "retention_rate"},
                        "fontWeight": "bold",
                        "color": color['secondary']
                    },
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ]
            )
        )
    ], style=content_style)
    
    return layout

def get_recorrencia_trimestral_layout(data):
    if data.get("df_RC_Trimestral") is None:
        return html.Div([
            html.H2("Recorrência Trimestral", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de recorrência trimestral para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-calendar-check fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo metricas_recorrencia_trimestral.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_RC_Trimestral = pd.read_json(io.StringIO(data["df_RC_Trimestral"]), orient='split')
    
    # Calculate metrics for the metrics row
    current_rate = df_RC_Trimestral['recurrence_rate'].iloc[-1] if not df_RC_Trimestral.empty else 0
    avg_rate = df_RC_Trimestral['recurrence_rate'].mean()
    max_rate = df_RC_Trimestral['recurrence_rate'].max()
    
    rate_change = df_RC_Trimestral['recurrence_rate'].iloc[-1] - df_RC_Trimestral['recurrence_rate'].iloc[-2] if len(df_RC_Trimestral) > 1 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Taxa de Recorrência Atual", "value": formatar_percentual(current_rate), "change": rate_change, "color": color['accent']},
        {"title": "Média de Recorrência", "value": formatar_percentual(avg_rate), "color": color['secondary']},
        {"title": "Maior Taxa", "value": formatar_percentual(max_rate), "color": color['success']},
        {"title": "Total de Clientes (Último Trimestre)", "value": formatar_numero(df_RC_Trimestral['total_customers'].iloc[-1]), "color": color['primary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced trimestral retention line chart
    fig_trimestral_line = px.line(
        df_RC_Trimestral, 
        x='trimestre', 
        y='recurrence_rate', 
        markers=True, 
        color_discrete_sequence=[color['secondary']],
        template='plotly_white'
    )
    
    # Add thicker line and bigger markers
    fig_trimestral_line.update_traces(
        line=dict(width=3),
        marker=dict(size=10, line=dict(width=2, color='white'))
    )
    
    # Add a target line
    fig_trimestral_line.add_shape(
        type="line",
        x0=df_RC_Trimestral['trimestre'].iloc[0],
        y0=35,
        x1=df_RC_Trimestral['trimestre'].iloc[-1],
        y1=35,
        line=dict(
            color=color['success'],
            width=2,
            dash="dot",
        )
    )
    
    fig_trimestral_line.add_annotation(
        x=df_RC_Trimestral['trimestre'].iloc[-1],
        y=35,
        text="Meta (35%)",
        showarrow=False,
        yshift=10,
        xshift=30,
        font=dict(size=12, color=color['success'])
    )
    
    fig_trimestral_line.update_layout(
        xaxis_title="Trimestre", 
        yaxis_title="Taxa de Recorrência (%)", 
        margin=dict(t=50, b=50, l=50, r=50),
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig_trimestral_line.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    fig_trimestral_line.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Enhanced customer composition chart
    fig_trimestral_bar = px.bar(
        df_RC_Trimestral, 
        x='trimestre', 
        y=['new_customers', 'returning_customers'], 
        barmode="stack",
        labels={"value": "Número de Clientes", "variable": "Tipo de Cliente"},
        color_discrete_map={
            'new_customers': color['accent'],
            'returning_customers': color['secondary']
        },
        template='plotly_white'
    )
    
    # Add percentages as text on the bars
    total_customers = df_RC_Trimestral['new_customers'] + df_RC_Trimestral['returning_customers']
    new_pct = (df_RC_Trimestral['new_customers'] / total_customers * 100).round(1)
    ret_pct = (df_RC_Trimestral['returning_customers'] / total_customers * 100).round(1)
    
    # Custom data for hover
    fig_trimestral_bar.update_traces(
        customdata=np.vstack((
            df_RC_Trimestral['new_customers'] if len(fig_trimestral_bar.data) > 0 and fig_trimestral_bar.data[0].name == 'new_customers' else df_RC_Trimestral['returning_customers'],
            new_pct if len(fig_trimestral_bar.data) > 0 and fig_trimestral_bar.data[0].name == 'new_customers' else ret_pct
        )).T,
        hovertemplate='%{y} clientes (%{customdata[1]:.1f}%)<extra>%{fullData.name}</extra>'
    )
    
    fig_trimestral_bar.update_layout(
        xaxis_title="Trimestre", 
        yaxis_title="Número de Clientes",
        margin=dict(t=50, b=50, l=50, r=50),
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig_trimestral_bar.update_xaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    fig_trimestral_bar.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Rename traces for better readability
    for trace in fig_trimestral_bar.data:
        if trace.name == 'new_customers':
            trace.name = "Novos Clientes"
        elif trace.name == 'returning_customers':
            trace.name = "Clientes Recorrentes"
        
        # Add count text
        text_values = []
        for value in trace.y:
            if value > 0:
                text_values.append(f"{int(value)}")
            else:
                text_values.append("")
        
        trace.text = text_values
        trace.textposition = 'inside'
        trace.textfont = dict(family="Montserrat", size=12, color="white")
    
    # Table with detailed metrics
    colunas_trimestrais = ["trimestre", "total_customers", "returning_customers", "new_customers", "recurrence_rate"]
    renomear_trimestral = {
        "trimestre": "Trimestre",
        "total_customers": "Total de Clientes",
        "returning_customers": "Clientes Recorrentes",
        "new_customers": "Novos Clientes",
        "recurrence_rate": "Taxa de Recorrência (%)",
    }
    df_trimestral_filtrado = df_RC_Trimestral[colunas_trimestrais]
    
    # Layout with cards
    layout = html.Div([
        html.H2("Recorrência Trimestral", className="dashboard-title"),
        
        # Summary metrics row
        metrics_row,
        
        # Charts in row
        dbc.Row([
            dbc.Col(
                create_card(
                    "Taxa de Recorrência Trimestral",
                    dcc.Graph(id='recorrencia-trimestral-line', figure=fig_trimestral_line, config={"responsive": True})
                ),
                lg=6, md=12
            ),
            dbc.Col(
                create_card(
                    "Composição de Clientes por Trimestre",
                    dcc.Graph(id='recorrencia-trimestral-bar', figure=fig_trimestral_bar, config={"responsive": True})
                ),
                lg=6, md=12
            )
        ], className="mb-4"),
        
        # Table with detailed metrics
        create_card(
            "Métricas Trimestrais Detalhadas",
            dash_table.DataTable(
                id='table-recorrencia-trimestral',
                columns=[
                    {"name": renomear_trimestral.get(col, col), "id": col}
                    for col in colunas_trimestrais
                ],
                data=df_trimestral_filtrado.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "center",
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
                        "if": {"column_id": "recurrence_rate"},
                        "fontWeight": "bold",
                        "color": color['secondary']
                    },
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ]
            )
        )
    ], style=content_style)
    
    return layout

def get_recorrencia_anual_layout(data):
    if data.get("df_RC_Anual") is None:
        return html.Div([
            html.H2("Recorrência Anual", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de recorrência anual para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="far fa-calendar-alt fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo metricas_recorrencia_anual.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_RC_Anual = pd.read_json(io.StringIO(data["df_RC_Anual"]), orient='split')
    
    # Calculate metrics for the metrics row
    current_retention = df_RC_Anual['retention_rate'].iloc[-1] if not df_RC_Anual.empty else 0
    current_new_rate = df_RC_Anual['new_rate'].iloc[-1] if not df_RC_Anual.empty else 0
    current_returning_rate = df_RC_Anual['returning_rate'].iloc[-1] if not df_RC_Anual.empty else 0
    
    retention_change = df_RC_Anual['retention_rate'].iloc[-1] - df_RC_Anual['retention_rate'].iloc[-2] if len(df_RC_Anual) > 1 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Taxa de Retenção Atual", "value": formatar_percentual(current_retention), "change": retention_change, "color": color['accent']},
        {"title": "Taxa de Novos Clientes", "value": formatar_percentual(current_new_rate), "color": color['secondary']},
        {"title": "Taxa de Recorrentes", "value": formatar_percentual(current_returning_rate), "color": color['success']},
        {"title": "Total de Clientes (Último Ano)", "value": formatar_numero(df_RC_Anual['total_customers'].iloc[-1]), "color": color['primary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced annual retention chart
    fig_anual = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bars for new and returning customer rates
    fig_anual.add_trace(
        go.Bar(
            x=df_RC_Anual['ano'],
            y=df_RC_Anual['new_rate'],
            name='Novos Clientes (%)',
            marker_color=color['accent'],
            text=df_RC_Anual['new_customers'],
            textposition='inside',
            textfont=dict(family="Montserrat", size=12, color="white")
        ),
        secondary_y=False
    )
    
    fig_anual.add_trace(
        go.Bar(
            x=df_RC_Anual['ano'],
            y=df_RC_Anual['returning_rate'],
            name='Clientes Recorrentes (%)',
            marker_color=color['secondary'],
            text=df_RC_Anual['returning_customers'],
            textposition='inside',
            textfont=dict(family="Montserrat", size=12, color="white")
        ),
        secondary_y=False
    )
    
    # Add line for retention rate
    fig_anual.add_trace(
        go.Scatter(
            x=df_RC_Anual['ano'],
            y=df_RC_Anual['retention_rate'],
            name='Taxa de Retenção',
            mode='lines+markers+text',
            text=df_RC_Anual['retention_rate'].apply(lambda x: f'{x:.1f}%'),
            textposition='top center',
            textfont=dict(family="Montserrat", size=12),
            line=dict(color=color['success'], width=3),
            marker=dict(size=10, line=dict(width=2, color='white'))
        ),
        secondary_y=True
    )
    
    # Update layout
    fig_anual.update_layout(
        barmode='stack',
        xaxis_title="Ano",
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        title_font=dict(family="Montserrat")
    )
    
    fig_anual.update_yaxes(
        title_text="Percentual de Clientes (%)", 
        secondary_y=False,
        gridcolor='rgba(0,0,0,0.05)',
        title_font=dict(size=14, family="Montserrat")
    )
    
    fig_anual.update_yaxes(
        title_text="Taxa de Retenção (%)", 
        secondary_y=True,
        gridcolor='rgba(0,0,0,0.05)',
        title_font=dict(size=14, family="Montserrat")
    )
    
    fig_anual.update_xaxes(
        tickmode='array', 
        tickvals=df_RC_Anual['ano'].unique(),
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Enhanced table
    colunas_anuais = ["ano", "total_customers", "returning_customers", "new_customers", "retention_rate", "new_rate", "returning_rate"]
    renomear_anual = {
        "ano": "Ano",
        "total_customers": "Total de Clientes",
        "returning_customers": "Clientes Recorrentes",
        "new_customers": "Novos Clientes",
        "retention_rate": "Taxa de Retenção (%)",
        "new_rate": "Taxa de Novos Clientes (%)",
        "returning_rate": "Taxa de Clientes Recorrentes (%)",
    }   
    df_anual_filtrado = df_RC_Anual[colunas_anuais]
    
    # Customer trending chart
    fig_customers = px.line(
        df_RC_Anual,
        x='ano',
        y=['total_customers', 'returning_customers', 'new_customers'],
        markers=True,
        labels={"value": "Número de Clientes", "variable": "Tipo"},
        color_discrete_map={
            'total_customers': color['primary'],
            'returning_customers': color['secondary'],
            'new_customers': color['accent']
        },
        template='plotly_white'
    )
    
    # Rename series
    for trace in fig_customers.data:
        if trace.name == 'total_customers':
            trace.name = "Total de Clientes"
        elif trace.name == 'returning_customers':
            trace.name = "Clientes Recorrentes"
        elif trace.name == 'new_customers':
            trace.name = "Novos Clientes"
    
    fig_customers.update_layout(
        xaxis_title="Ano",
        yaxis_title="Número de Clientes",
        margin=dict(t=50, b=50, l=50, r=50),
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    fig_customers.update_xaxes(
        tickmode='array', 
        tickvals=df_RC_Anual['ano'].unique(),
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    fig_customers.update_yaxes(
        title_font=dict(size=14, family="Montserrat"),
        gridcolor='rgba(0,0,0,0.05)'
    )
    
    # Layout with cards
    layout = html.Div([
        html.H2("Recorrência Anual", className="dashboard-title"),
        
        # Summary metrics row
        metrics_row,
        
        # Charts in row
        dbc.Row([
            dbc.Col(
                create_card(
                    "Composição de Clientes e Taxa de Retenção Anual",
                    dcc.Graph(id='recorrencia-anual-graph', figure=fig_anual, config={"responsive": True})
                ),
                lg=7, md=12
            ),
            dbc.Col(
                create_card(
                    "Evolução Anual de Clientes",
                    dcc.Graph(id='recorrencia-anual-customers', figure=fig_customers, config={"responsive": True})
                ),
                lg=5, md=12
            )
        ], className="mb-4"),
        
        # Table with detailed metrics
        create_card(
            "Métricas Anuais Detalhadas",
            dash_table.DataTable(
                id='table-recorrencia-anual',
                columns=[
                    {"name": renomear_anual.get(col, col), "id": col}
                    for col in colunas_anuais
                ],
                data=df_anual_filtrado.to_dict("records"),
                page_size=10,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "center",
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
                        "if": {"column_id": "retention_rate"},
                        "fontWeight": "bold",
                        "color": color['success']
                    },
                    {
                        "if": {"column_id": "new_rate"},
                        "color": color['accent']
                    },
                    {
                        "if": {"column_id": "returning_rate"},
                        "color": color['secondary']
                    },
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "rgb(248, 248, 248)"
                    }
                ]
            )
        )
    ], style=content_style)
    
    return layout

def get_retencao_layout(data):
    try:
        if data.get("df_RT_Anual") is None:
            return html.Div([
                html.H2("Análise de Retenção Anual", className="dashboard-title"),
                create_card(
                    "Dados Indisponíveis",
                    html.Div([
                        html.P("Não foram encontrados dados de retenção anual para este cliente.", className="text-center text-muted my-4"),
                        html.I(className="fas fa-user-clock fa-4x text-muted d-block text-center mb-3"),
                        html.P("Verifique se o arquivo metricas_retencao_anual.xlsx está presente", 
                              className="text-muted text-center")
                    ])
                )
            ], style=content_style)
        
        df_RT_Anual = pd.read_json(io.StringIO(data["df_RT_Anual"]), orient='split')
        
        # Calculate metrics for the metrics row - ajustado para calcular apenas após o primeiro ano
        avg_retention = df_RT_Anual[(df_RT_Anual['period_index'] > 0) & ~pd.isna(df_RT_Anual['retention_rate'])]['retention_rate'].mean() * 100  # Apenas períodos > 0
        first_year_retention = df_RT_Anual[df_RT_Anual['period_index'] == 1]['retention_rate'].mean() * 100 if 1 in df_RT_Anual['period_index'].values else 0
        second_year_retention = df_RT_Anual[df_RT_Anual['period_index'] == 2]['retention_rate'].mean() * 100 if 2 in df_RT_Anual['period_index'].values else 0
        
        # Handle NaN values
        if pd.isna(avg_retention): avg_retention = 0
        if pd.isna(first_year_retention): first_year_retention = 0
        if pd.isna(second_year_retention): second_year_retention = 0
        
        # Create metrics row
        metrics = [
            {"title": "Retenção Média", "value": formatar_percentual(avg_retention), "color": color['primary']},
            {"title": "Retenção Primeiro Ano", "value": formatar_percentual(first_year_retention), "color": color['secondary']},
            {"title": "Retenção Segundo Ano", "value": formatar_percentual(second_year_retention), "color": color['accent']},
            {"title": "Diferença 1º-2º Ano", "value": formatar_percentual(first_year_retention - second_year_retention), 
             "change": second_year_retention - first_year_retention, "color": color['success']}
        ]
        
        metrics_row = create_metric_row(metrics)
        
        # Enhanced retention heatmap
        cohort_pivot = df_RT_Anual.pivot(
            index='cohort_year',
            columns='period_index', 
            values='retention_rate'
        )
        cohort_pivot = cohort_pivot * 100
        
        # Ensure index is integer and filter for valid years
        cohort_pivot.index = cohort_pivot.index.astype(int)
        
        # Create enhanced heatmap
        fig_retention = px.imshow(
            cohort_pivot,
            text_auto=False,
            aspect="auto",
            labels={
                "x": "Período (Anos desde a Primeira Compra)",
                "y": "Coorte (Ano da Primeira Compra)",
                "color": "Taxa de Retenção (%)"
            },
            x=cohort_pivot.columns,
            y=cohort_pivot.index,
            color_continuous_scale="YlGnBu",
            template='plotly_white'
        )
        
        annotations = []
        for i, y_val in enumerate(cohort_pivot.index):
            for j, x_val in enumerate(cohort_pivot.columns):
                value = cohort_pivot.iloc[i, j]
                if not np.isnan(value) and value is not None:
                    text_color = 'white' if value >= 95 else 'black'
                    
                    annotations.append(dict(
                        x=x_val,
                        y=y_val,
                        text=f'{value:.1f}%'.replace(".", ","),
                        showarrow=False,
                        font=dict(color=text_color, size=12, family="Montserrat")
                    ))

        # Remover texto automático
        fig_retention.data[0].text = None
        fig_retention.data[0].texttemplate = None

        # Adicionar anotações personalizadas
        fig_retention.update_layout(annotations=annotations)
        
        # Update layout
        fig_retention.update_layout(
            height=600,
            margin=dict(t=30, b=50, l=50, r=50),
            coloraxis_colorbar=dict(
                title=dict(
                    text="Retenção (%)",
                    side="right",
                    font=dict(size=14, family="Montserrat")
                ),
                ticks="outside",
                tickfont=dict(size=12, family="Montserrat")
            ),
            xaxis=dict(
                title="Período (Anos desde a Primeira Compra)",
                title_font=dict(size=14, family="Montserrat"),
                tickfont=dict(size=12, family="Montserrat")
            ),
            yaxis=dict(
                title="Coorte (Ano da Primeira Compra)",
                title_font=dict(size=14, family="Montserrat"),
                tickfont=dict(size=12, family="Montserrat")
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Update axes to show only the valid years and integers
        fig_retention.update_yaxes(
            tickmode='array',
            tickvals=cohort_pivot.index.tolist(),
            ticktext=[str(year) for year in cohort_pivot.index.tolist()]
        )
        
        fig_retention.update_xaxes(
            tickmode='linear',
            dtick=1
        )
        
        # Update text appearance
        fig_retention.update_traces(
            textfont=dict(size=12, family="Montserrat", color="black")
        )
        
        # Create cohort analysis line chart - verificar se há dados suficientes
        if len(df_RT_Anual['period_index'].unique()) > 0:
            retention_by_period = df_RT_Anual.groupby('period_index')['retention_rate'].mean() * 100
            fig_retention_curve = px.line(
                x=retention_by_period.index,
                y=retention_by_period.values,
                labels={"x": "Período (Anos)", "y": "Taxa de Retenção Média (%)"},
                markers=True,
                template='plotly_white'
            )
            
            fig_retention_curve.update_traces(
                line=dict(width=3, color=color['secondary']),
                marker=dict(size=10, color=color['secondary']),
                mode='lines+markers+text',
                text=[f"{val:.1f}%".replace(".", ",") for val in retention_by_period.values],
                textposition='top center',
                textfont=dict(family="Montserrat", size=12)
            )
            
            fig_retention_curve.update_layout(
                title="Curva de Retenção Média por Período",
                title_font=dict(size=16, family="Montserrat", color=color['primary']),
                height=400,
                margin=dict(t=50, b=50, l=50, r=50),
                xaxis=dict(
                    title="Período (Anos desde a Primeira Compra)",
                    title_font=dict(size=14, family="Montserrat"),
                    tickvals=list(range(0, int(retention_by_period.index.max()) + 1)),
                    gridcolor='rgba(0,0,0,0.05)'
                ),
                yaxis=dict(
                    title="Taxa de Retenção Média (%)",
                    title_font=dict(size=14, family="Montserrat"),
                    gridcolor='rgba(0,0,0,0.05)'
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        else:
            # Se não tiver dados suficientes, cria um gráfico placeholder
            fig_retention_curve = go.Figure()
            fig_retention_curve.add_annotation(
                x=0.5, y=0.5,
                text="Dados insuficientes para gerar a curva de retenção",
                showarrow=False,
                font=dict(size=14, family="Montserrat")
            )
            fig_retention_curve.update_layout(
                height=400,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
        
        # Layout with cards
        layout = html.Div(
            [
                html.H2("Análise de Retenção Anual", className="dashboard-title"),
                
                # Summary metrics row
                metrics_row,
                
                # Retention Heatmap
                create_card(
                    "Cohort Analysis - Taxa de Retenção (Anual)",
                    dcc.Graph(
                        id='retention-heatmap',
                        figure=fig_retention,
                        config={"responsive": True}
                    )
                ),
                
                # Retention Curve
                create_card(
                    "Curva de Retenção",
                    dcc.Graph(
                        id='retention-curve',
                        figure=fig_retention_curve,
                        config={"responsive": True}
                    )
                ),
                
                # Explanation card
                create_card(
                    "Como interpretar a Cohort Analysis",
                    html.Div([
                        html.P("A análise de coortes mostra a taxa de retenção de clientes ao longo do tempo, agrupados pelo ano de sua primeira compra."),
                        html.Ul([
                            html.Li("Cada linha representa uma coorte (grupo de clientes que começaram no mesmo ano)"),
                            html.Li("Cada coluna representa o período de tempo desde a primeira compra"),
                            html.Li("As células mostram a porcentagem de clientes que continuam comprando após o período indicado"),
                            html.Li("Cores mais escuras indicam taxas de retenção mais altas")
                        ]),
                        html.P("Esta visualização permite identificar quais coortes têm melhor desempenho a longo prazo e como evolui a retenção com o passar do tempo.")
                    ])
                )
            ],
            style=content_style,
        )
        
        return layout
        
    except Exception as e:
        # Em caso de erro, exibir mensagem amigável e informações do erro
        return html.Div([
            html.H2("Análise de Retenção Anual", className="dashboard-title"),
            
            create_card(
                "Erro ao carregar os dados",
                html.Div([
                    html.P("Ocorreu um problema ao carregar os dados de retenção. Detalhes do erro:"),
                    html.Pre(str(e), style={"background": "#f8f9fa", "padding": "15px", "borderRadius": "5px", "whiteSpace": "pre-wrap"}),
                    html.P("Tente recarregar a página ou entre em contato com o suporte técnico.")
                ])
            )
        ], style=content_style)

def get_predicao_layout(data):
    if data.get("df_Previsoes") is None:
        return html.Div([
            html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de previsão para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-chart-pie fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo rfma_previsoes_ajustado.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split')
    
    # Calculate metrics for the metrics row
    total_customers = len(df_Previsoes)
    high_prob_customers = len(df_Previsoes[df_Previsoes['categoria_previsao'] == 'Alta Probabilidade de Compra'])
    low_prob_customers = len(df_Previsoes[df_Previsoes['categoria_previsao'] == 'Baixa Probabilidade de Compra'])
    high_prob_pct = (high_prob_customers / total_customers * 100) if total_customers > 0 else 0
    
    # Create metrics row
    metrics = [
        {"title": "Total de Clientes", "value": formatar_numero(total_customers), "color": color['primary']},
        {"title": "Alta Probabilidade", "value": formatar_numero(high_prob_customers), "color": color['secondary']},
        {"title": "Baixa Probabilidade", "value": formatar_numero(low_prob_customers), "color": color['accent']},
        {"title": "% Alta Probabilidade", "value": formatar_percentual(high_prob_pct), "color": color['success']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Enhanced prediction chart
    previsao_counts = df_Previsoes['categoria_previsao'].value_counts().reset_index()
    previsao_counts.columns = ['categoria_previsao', 'count']
    
    fig_pred = px.bar(
        previsao_counts,
        x='categoria_previsao',
        y='count',
        color='categoria_previsao',
        color_discrete_map={
            'Baixa Probabilidade de Compra': color['accent'],
            'Alta Probabilidade de Compra': color['secondary']
        },
        template='plotly_white'
    )
    
    # Add percentage labels
    for i, row in previsao_counts.iterrows():
        percentage = row['count'] / previsao_counts['count'].sum() * 100
        fig_pred.add_annotation(
            x=row['categoria_previsao'],
            y=row['count'],
            text=f"{formatar_numero(row['count'])} ({formatar_percentual(percentage)})",
            showarrow=False,
            yshift=10,
            font=dict(size=12, family="Montserrat")
        )
    
    fig_pred.update_layout(
        legend_title_text="Categoria de Previsão",
        margin=dict(t=30, b=50, l=50, r=50),
        height=500,
        xaxis=dict(
            title="Categoria de Previsão",
            title_font=dict(size=14, family="Montserrat"),
            tickfont=dict(size=12, family="Montserrat")
        ),
        yaxis=dict(
            title="Número de Clientes",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    
    # Create pie chart for prediction categories
    fig_pie = px.pie(
        previsao_counts,
        values='count',
        names='categoria_previsao',
        color='categoria_previsao',
        color_discrete_map={
            'Baixa Probabilidade de Compra': color['accent'],
            'Alta Probabilidade de Compra': color['secondary']
        },
        template='plotly_white',
        hole=0.4
    )
    
    fig_pie.update_layout(
        margin=dict(t=30, b=30, l=30, r=30),
        height=450,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    fig_pie.update_traces(
        textposition='inside',
        textinfo='percent',
        textfont=dict(size=14, family="Montserrat", color="white"),
        pull=[0.05, 0]
    )
    
    # Calculate average predicted purchases
    avg_predicted = df_Previsoes['predicted_purchases_30d'].mean()
    
    # Create distribution of predicted purchases
    fig_dist = px.histogram(
        df_Previsoes,
        x='predicted_purchases_30d',
        color='categoria_previsao',
        color_discrete_map={
            'Baixa Probabilidade de Compra': color['accent'],
            'Alta Probabilidade de Compra': color['secondary']
        },
        template='plotly_white',
        barmode='overlay',
        opacity=0.7,
        nbins=20
    )
    
    # Add vertical line for average
    fig_dist.add_shape(
        type="line",
        x0=avg_predicted,
        y0=0,
        x1=avg_predicted,
        y1=1,
        yref="paper",
        line=dict(
            color=color['primary'],
            width=2,
            dash="dash",
        )
    )
    
    fig_dist.add_annotation(
        x=avg_predicted,
        y=0.95,
        yref="paper",
        text=f"Média: {str(avg_predicted).replace('.', ',')}",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40,
        font=dict(size=12, family="Montserrat")
    )
    
    fig_dist.update_layout(
        title="Distribuição das Previsões de Compra",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        height=400,
        margin=dict(t=50, b=50, l=50, r=50),
        xaxis=dict(
            title="Previsão de Compras (30 dias)",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        yaxis=dict(
            title="Número de Clientes",
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Layout with cards
    layout = html.Div(
        [
            html.H2("Previsão de Retorno de Clientes", className="dashboard-title"),
            
            # Summary metrics row
            metrics_row,
            
            # Charts in row
            dbc.Row([
                dbc.Col(
                    create_card(
                        "Probabilidade de Compra nos Próximos 30 dias",
                        dcc.Graph(id="predicao-bar", figure=fig_pred, config={"responsive": True})
                    ),
                    lg=8, md=12
                ),
                dbc.Col(
                    create_card(
                        "Proporção de Probabilidade",
                        dcc.Graph(id="predicao-pie", figure=fig_pie, config={"responsive": True})
                    ),
                    lg=4, md=12
                )
            ], className="mb-4"),
            
            # Distribution chart
            create_card(
                "Distribuição de Previsões de Compra (30 dias)",
                dcc.Graph(id="predicao-dist", figure=fig_dist, config={"responsive": True})
            ),
            
            # Client list
            create_card(
                html.Div(id="predicao-client-list-header", children="Clientes da Categoria Selecionada"),
                html.Div(
                    id="predicao-client-list",
                    children=html.Div([
                        html.P("Selecione uma categoria nos gráficos acima para ver os clientes.", className="text-center text-muted my-4"),
                        html.Div(className="text-center", children=[
                            html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                            html.P("Clique em uma categoria para visualizar detalhes", className="text-muted mt-2")
                        ])
                    ])
                )
            )
        ],
        style=content_style,
    )
    
    return layout

def get_chat_layout(data):
    # Modern chat interface
    chat_layout = html.Div(
        [
            html.H2("Assistente de Análises", className="dashboard-title"),
            
            # Introduction card
            create_card(
                "Como posso ajudar?",
                html.Div([
                    html.P("O assistente de análises pode responder perguntas sobre seus dados de clientes. Por exemplo:"),
                    html.Ul([
                        html.Li("Quais são os segmentos com maior valor monetário?"),
                        html.Li("Como está a retenção anual dos clientes?"),
                        html.Li("Quais clientes têm maior probabilidade de compra nos próximos 30 dias?"),
                        html.Li("Qual foi a evolução das vendas desde 2021?")
                    ]),
                    html.P("Faça sua pergunta abaixo e ajudarei com insights e análises!")
                ])
            ),
            
            # Chat container
            create_card(
                "Chat",
                html.Div([
                    # Chat history
                    html.Div(
                        id='chat-history',
                        className="chat-history",
                        children=[]
                    ),
                    
                    # Input area
                    html.Div([
                        dbc.Input(
                            id='user-input',
                            placeholder="Digite sua pergunta sobre os dados...",
                            type="text",
                            className="dash-input",
                            style={"flex": "1"}
                        ),
                        dbc.Button(
                            html.I(className="fas fa-paper-plane"),
                            id='submit-button',
                            color="primary",
                            className="ms-2",
                            style=button_style
                        )
                    ], className="chat-input-container d-flex mt-3")
                ], className="chat-container")
            )
        ],
        style=content_style
    )
    
    return chat_layout

def get_vendas_atipicas_layout(data):
    """
    Cria o layout da página de vendas atípicas com gráficos e tabelas interativas
    para análise de comportamentos fora do padrão no estoque.
    """
    if data.get("df_Vendas_Atipicas") is None:
        return html.Div([
            html.H2("Vendas Atípicas", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de vendas atípicas para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P("Verifique se o arquivo vendas_atipicas_atual.xlsx está presente", 
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    # Carregamos os dados de vendas atípicas
    df_atipicas = pd.read_json(io.StringIO(data["df_Vendas_Atipicas"]), orient='split')
    
    # Convertemos a coluna 'Dia' para o formato de data, se ainda não estiver
    if df_atipicas['Dia'].dtype == 'object':
        df_atipicas['Dia'] = pd.to_datetime(df_atipicas['Dia'])

    df_atipicas['Dia_formatada'] = df_atipicas['Dia'].dt.strftime('%d/%m/%Y')

    
    # Calculamos métricas gerais para cards de resumo
    total_produtos_atipicos = len(df_atipicas)
    total_quantidade_atipica = df_atipicas['quantidade_atipica'].sum()
    media_por_produto = total_quantidade_atipica / total_produtos_atipicos if total_produtos_atipicos > 0 else 0
    
    # Criamos as métricas para a primeira linha de cards
    metrics = [
        {"title": "Total de Produtos Atípicos", "value": formatar_numero(total_produtos_atipicos), "color": color['primary']},
        {"title": "Quantidade Total Atípica", "value": formatar_numero(total_quantidade_atipica), "color": color['accent']},
        {"title": "Média por Produto", "value": formatar_numero(media_por_produto, 1), "color": color['secondary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Criamos um gráfico de barras para os produtos com maior quantidade atípica
    top_produtos = df_atipicas.sort_values('quantidade_atipica', ascending=False).head(10)
    
    fig_top_produtos = px.bar(
        top_produtos,
        y='produto',
        x='quantidade_atipica',
        orientation='h',
        color='quantidade_atipica',
        color_continuous_scale='Blues',
        labels={'quantidade_atipica': 'Quantidade Atípica', 'produto': 'Produto'},
        template='plotly_white'
    )
    
    fig_top_produtos.update_layout(
        title="Top 10 Produtos com Vendas Atípicas",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        xaxis_title="Quantidade",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),  # Para mostrar o maior valor no topo
        height=500,
        margin=dict(l=200, r=20, t=70, b=70),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Criamos uma tabela interativa com os dados completos
    table = dash_table.DataTable(
        id='table-vendas-atipicas',
        columns=[
            {"name": "Data", "id": "Dia_formatada"},
            {"name": "Quantidade Atípica", "id": "quantidade_atipica"},
            {"name": "Cliente", "id": "cliente"},
            {"name": "Produto", "id": "produto"},
            {"name": "Estoque Atual", "id": "estoque_atualizado"},
            {"name": "Reposição Não-Local (Crítico)", "id": "critico"}
        ],
        data=df_atipicas.reset_index().to_dict("records"),
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
                "if": {"column_id": "quantidade_atipica"},
                "fontWeight": "bold",
                "color": color['accent']
            },
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(248, 248, 248)"
            }
        ]
    )
    
    # Incluímos todos os elementos no layout
    layout = html.Div([
        html.H2("Análise de Vendas Atípicas", className="dashboard-title"),
        
        # Linha de cartões de métricas
        metrics_row,
        
        # Primeira linha de gráficos
        create_card(
            "Top Produtos com Vendas Atípicas",
            dcc.Graph(id="grafico-top-produtos", figure=fig_top_produtos, config={"responsive": True})
        ), 
        
        # Terceira linha - Tabela de dados
        create_card(
            "Detalhamento de Vendas Atípicas",
            html.Div([
                html.P("Esta tabela apresenta todos os produtos com vendas fora do padrão esperado. Utilize os filtros e ordenação para análise detalhada.", className="text-muted mb-3"),
                table
            ])
        ),
        
        # Quarta linha - Cartão explicativo
        create_card(
            "Interpretação dos Dados",
            html.Div([
                html.P("As vendas atípicas representam situações onde o volume de vendas foi significativamente diferente do padrão esperado para aquele produto, podendo indicar:"),
                html.Ul([
                    html.Li("Oportunidades de expansão para produtos com vendas acima do esperado"),
                    html.Li("Clientes com potencial para aumento de volume"),
                    html.Li("Produtos que podem precisar de ajuste no estoque ou previsão"),
                    html.Li("Possíveis problemas de registro ou cadastro quando extremamente fora do padrão")
                ]),
                html.P("Recomendamos a análise detalhada dos casos mais significativos para definir estratégias de negócio.")
            ])
        )
    ], style=content_style)
    
    return layout


def get_produtos_layout(data):
    """
    Cria o layout da página de criticidade de produtos com gráficos e tabelas interativas
    para análise completa de todos os níveis de criticidade do estoque.
    """
    if data.get("df_relatorio_produtos") is None:
        return html.Div([
            html.H2("Análise de Cobertura de Estoque", className="dashboard-title"),
            create_card(
                "Dados Indisponíveis",
                html.Div([
                    html.P("Não foram encontrados dados de produtos para este cliente.", className="text-center text-muted my-4"),
                    html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                    html.P(            "Verifique se o arquivo relatorio_produtos_criticos.xlsx está presente no diretório de dados",  
                           className="text-muted text-center")
                ])
            )
        ], style=content_style)
    
    # Carregamos os dados de produtos críticos
    df_criticos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')
    
    # Verificar se a coluna de criticidade existe, caso contrário, precisamos criá-la
    if 'criticidade' not in df_criticos.columns:
        # Verifica se tem a coluna percentual_cobertura
        if 'percentual_cobertura' in df_criticos.columns:
            # Definir categorias de criticidade
            df_criticos['criticidade'] = pd.cut(
                df_criticos['percentual_cobertura'],
                bins=[-float('inf'), 30, 50, 80, 100, float('inf')],
                labels=['Crítico', 'Muito Baixo', 'Baixo', 'Adequado', 'Excesso']
            )
        else:
            # Se não tiver percentual_cobertura, verifica se tem as colunas para calcular
            if 'estoque_atualizado' in df_criticos.columns and 'Media 3M' in df_criticos.columns:
                # Calcular percentual de cobertura
                df_criticos['percentual_cobertura'] = (df_criticos['estoque_atualizado'] / df_criticos['Media 3M'] * 100).round(1)
                # Definir categorias de criticidade
                df_criticos['criticidade'] = pd.cut(
                    df_criticos['percentual_cobertura'],
                    bins=[-float('inf'), 30, 50, 80, 100, float('inf')],
                    labels=['Crítico', 'Muito Baixo', 'Baixo', 'Adequado', 'Excesso']
                )
            else:
                return html.Div([
                    html.H2("Produtos Críticos", className="dashboard-title"),
                    create_card(
                        "Dados Insuficientes",
                        html.Div([
                            html.P("Os dados não contêm as colunas necessárias para análise de criticidade.", className="text-center text-muted my-4"),
                            html.I(className="fas fa-exclamation-triangle fa-4x text-muted d-block text-center mb-3"),
                            html.P("São necessárias as colunas: 'percentual_cobertura' ou 'estoque_atualizado' e 'Media 3M'", 
                                   className="text-muted text-center")
                        ])
                    )
                ], style=content_style)

    # Botão de filtro críticos (Toggle) - Adicionado
    filtro_criticos = html.Div([
        dbc.Button(
            [
                html.I(className="fas fa-filter me-2"), 
                "Mostrar Apenas Produtos Críticos"
            ],
            id="btn-filtro-criticos",
            color="danger",
            className="mb-3",
            style={"marginTop": "-2rem", "marginBottom": "1rem"}
        ),
        dcc.Store(id="filtro-criticos-ativo", data=False),
    ], className="d-flex justify-content-end")
    
    # Contar produtos por categoria de criticidade
    contagem_criticidade = df_criticos['criticidade'].value_counts().sort_index()
    
    # Calcular métricas para a primeira linha de cards
    total_produtos = len(df_criticos)

    # Criar uma Series com o total e concatenar com a contagem_criticidade
    total_series = pd.Series([total_produtos], index=['Todos'])
    contagem_criticidade = pd.concat([contagem_criticidade, total_series])

    produtos_criticos = len(df_criticos[df_criticos['criticidade'] == 'Crítico'])
    produtos_baixos = len(df_criticos[df_criticos['criticidade'].isin(['Muito Baixo', 'Baixo'])])
    
    # Calcular valor estimado para compra, se disponível
    valor_estimado = None
    if 'Sug 1M' in df_criticos.columns and 'custo1' in df_criticos.columns:
        df_criticos['valor_estimado'] = df_criticos['Sug 1M'] * df_criticos['custo1']
        valor_estimado = df_criticos['valor_estimado'].sum()
    
    # Contar produtos por cada categoria de criticidade para os cards de métrica
    produtos_criticos = len(df_criticos[df_criticos['criticidade'] == 'Crítico'])
    produtos_muito_baixos = len(df_criticos[df_criticos['criticidade'] == 'Muito Baixo'])
    produtos_baixos = len(df_criticos[df_criticos['criticidade'] == 'Baixo'])
    produtos_adequados = len(df_criticos[df_criticos['criticidade'] == 'Adequado'])
    produtos_excesso = len(df_criticos[df_criticos['criticidade'] == 'Excesso'])
    
    # Criar métricas para a primeira linha de cards - mostrando todas as categorias
    metrics = [
        {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
        {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
        {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
        {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
        {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
        {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
    ]
    
    metrics_row = create_metric_row(metrics)
    
    # Criar gráfico de barras para criticidade (similar ao do Jupyter)
    fig_criticidade = px.bar(
        x=contagem_criticidade.index,
        y=contagem_criticidade.values,
        color=contagem_criticidade.index,
        color_discrete_map={
            'Crítico': 'darkred',
            'Muito Baixo': 'orange',
            'Baixo': color['warning'],
            'Adequado': gradient_colors['green_gradient'][0],
            'Excesso': color['secondary'],
            'Todos': color['primary']
        },
        labels={'x': 'Nível de Criticidade', 'y': 'Quantidade de Produtos'},
        template='plotly_white'
    )
    total_produtos = contagem_criticidade.sum()
    porcentagens = (contagem_criticidade / total_produtos * 100).round(1)

    # Adicionar valores nas barras
    for i, v in enumerate(contagem_criticidade.values):
        percentage = porcentagens[contagem_criticidade.index[i]]
        fig_criticidade.add_annotation(
            x=contagem_criticidade.index[i],
            y=v,
            text=f"{str(v)} ({percentage:.1f}%)".replace(".", ","),
            showarrow=False,
            yshift=10,
            font=dict(size=14, color="black", family="Montserrat", weight="bold")
        )
    
    fig_criticidade.update_layout(
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        xaxis_title="Nível de Criticidade",
        yaxis_title="Quantidade de Produtos",
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    # Filtrar produtos críticos e ordenar pelo percentual de cobertura (do menor para o maior)
    df_produtos_criticos = df_criticos.sort_values('percentual_cobertura')

    if len(df_criticos[df_criticos['criticidade'] == 'Crítico']) > 0:
        top_20_criticos = df_criticos[df_criticos['criticidade'] == 'Crítico'].sort_values('percentual_cobertura').head(20)
    else:
        top_20_criticos = df_produtos_criticos.head(20)

    # Verificar a coluna de descrição do produto
    produto_col = 'desc_produto' if 'desc_produto' in df_criticos.columns else 'Produto' if 'Produto' in df_criticos.columns else None

    if produto_col:

        top_20_criticos['produto_display'] = top_20_criticos[produto_col].apply(lambda x: (x[:30] + '...') if len(str(x)) > 30 else x)
        
        fig_top_criticos = px.bar(
            top_20_criticos,
            y='produto_display',
            x='percentual_cobertura',
            orientation='h',
            color='percentual_cobertura',
            color_continuous_scale=['darkred', 'orange', color['warning']],
            range_color=[0, 50],
            labels={'percentual_cobertura': 'Cobertura (%)', 'produto_display': 'Produto'},
            template='plotly_white'
        )
        
        if 'cd_produto' in top_20_criticos.columns:
            fig_top_criticos.update_traces(
                hovertemplate='<b>%{y}</b><br>Código: %{customdata[0]}<br>Cobertura: %{x:.1f}%',
                customdata=top_20_criticos[['cd_produto']]
            )
        
        fig_top_criticos.update_layout(
            title_font=dict(size=16, family="Montserrat", color=color['primary']),
            yaxis_title="",
            xaxis_title="Percentual de Cobertura (%)",
            margin=dict(l=200, r=20, t=30, b=30),
            height=500,
            yaxis=dict(autorange="reversed"),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        
        fig_top_criticos.add_shape(
            type="line",
            x0=30, y0=-0.5,
            x1=30, y1=len(top_20_criticos) - 0.5,
            line=dict(color="darkred", width=2, dash="dash"),
        )
        
        
        for i, row in enumerate(top_20_criticos.itertuples()):
            fig_top_criticos.add_annotation(
                x=row.percentual_cobertura,
                y=row.produto_display,
                text=f"{row.percentual_cobertura:.1f}%".replace(".", ","),
                showarrow=False,
                xshift=15,
                font=dict(size=12, color="black", family="Montserrat")
            )

    # Layout final
    layout = html.Div([
        html.H2("Análise de Cobertura de Estoque", className="dashboard-title"),

        # Armazenamento para os dados de produtos
        dcc.Store(
            id="store-produtos-data", 
            data=data["df_relatorio_produtos"] if data and "df_relatorio_produtos" in data else None
        ),

        # Botão de filtro críticos adicionado abaixo do título
        filtro_criticos,
        
        # Linha de cartões de métricas
        html.Div(
            id="div-metrics-row",
            children=metrics_row
        ),
        
        # Primeira linha: Gráfico de criticidade e gráfico de pizza
        dbc.Row([
            dbc.Col(
                create_card(
                    "Produtos por Nível de Cobertura",
                    dcc.Graph(id="produtos-criticidade-bar", figure=fig_criticidade, config={"responsive": True})
                ),
                lg=6, md=12
            ),
            dbc.Col(
                create_card(
                    "Top 20 Produtos Mais Críticos",
                    dcc.Graph(id="produtos-criticidade-top20", figure=fig_top_criticos if produto_col else {}, config={"responsive": True})
                ),
                lg=6, md=12
            ),
        ], className="mb-4"),
        
        # Segunda linha: Tabela detalhada de produtos por criticidade
        create_card(
            html.Div(id="produtos-criticidade-header", children="Produtos do Nível de Cobertura Selecionado"),
            html.Div(
                id="produtos-criticidade-list",
                children=html.Div([
                    html.P("Selecione um nível de cobertura nos gráficos acima para ver os produtos.", className="text-center text-muted my-4"),
                    html.Div(className="text-center", children=[
                        html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                        html.P("Clique em uma fatia, barra ou ponto para visualizar detalhes", className="text-muted mt-2")
                    ])
                ])
            )
        ),

        # Terceira linha: detalhe de um produto específico
        create_card(
            html.Div(id="produto-consumo-header", children="Gráfico de Consumo do Produto Selecionado"),
            html.Div(
                id="produto-consumo-grafico",
                children=html.Div([
                    html.P("Selecione um produto na lista acima para visualizar o gráfico de consumo.", 
                        className="text-center text-muted my-4"),
                    html.Div(className="text-center", children=[
                        html.I(className="fas fa-chart-line fa-2x text-muted"),
                        html.P("O gráfico mostrará o histórico de consumo e sugestões de compra", 
                            className="text-muted mt-2")
                    ])
                ])
            )
        ),

        
        # Quarta linha: Card explicativo
        create_card(
            "Interpretação dos Níveis de Cobertura",
            html.Div([
                html.P("A análise de cobertura de estoque é baseada no percentual de cobertura, calculado como a relação entre o estoque atual e o consumo médio trimestral:"),
                html.Ul([
                    html.Li([html.Span("Crítico (0-30%): ", style={"color": "darkred", "fontWeight": "bold"}), 
                           "Necessidade urgente de reposição. Risco iminente de ruptura de estoque."]),
                    html.Li([html.Span("Muito Baixo (30-50%): ", style={"color": "red", "fontWeight": "bold"}), 
                           "Estoque baixo, reposição necessária em curto prazo."]),
                    html.Li([html.Span("Baixo (50-80%): ", style={"color": "orange", "fontWeight": "bold"}), 
                           "Estoque moderado, monitorar e planejar reposição."]),
                    html.Li([html.Span("Adequado (80-100%): ", style={"color": "green", "fontWeight": "bold"}), 
                           "Nível de estoque ideal, bem dimensionado para o consumo."]),
                    html.Li([html.Span("Excesso (>100%): ", style={"color": "blue", "fontWeight": "bold"}), 
                           "Estoque acima do necessário, possível capital imobilizado."])
                ]),
                html.P("Recomenda-se priorizar a reposição dos itens críticos e com muito baixa cobertura para evitar rupturas e garantir o atendimento ao cliente.")
            ])
        )
    ], style=content_style)
    
    return layout

@application.callback(
    [Output("produto-consumo-header", "children"),
     Output("produto-consumo-grafico", "children")],
    [Input("produtos-criticidade-table", "active_cell"),
     Input("produtos-criticidade-table", "derived_virtual_data"),
     Input("produtos-criticidade-table", "derived_virtual_selected_rows")],
    [State("selected-data", "data")]
)
def update_produto_consumo_grafico(active_cell, virtual_data, selected_rows, data):
    """
    Atualiza o gráfico de consumo quando um produto é selecionado na tabela.
    """
    # Verificar se temos seleção e dados válidos
    if active_cell is None or virtual_data is None or not virtual_data:
        return "Gráfico de Consumo do Produto Selecionado", html.Div([
            html.P("Selecione um produto na lista acima para visualizar o gráfico de consumo.", 
                   className="text-center text-muted my-4"),
            html.Div(className="text-center", children=[
                html.I(className="fas fa-chart-line fa-2x text-muted"),
                html.P("O gráfico mostrará o histórico de consumo e sugestões de compra", 
                       className="text-muted mt-2")
            ])
        ])
    
    if data is None or data.get("df_relatorio_produtos") is None:
        return "Dados não disponíveis", "Não foi possível carregar os dados dos produtos."
    
    try:
        # Obter o produto selecionado da tabela
        row_id = active_cell["row"]
        if row_id >= len(virtual_data):
            return "Erro de seleção", "A linha selecionada está fora dos limites da tabela."
            
        produto_selecionado = virtual_data[row_id]
        
        # Encontrar a coluna que contém o código do produto
        codigo_colunas = ['cd_produto', 'Código', 'codigo', 'ID']
        desc_colunas = ['desc_produto', 'Produto', 'Descrição', 'Nome', 'descricao']
        
        cd_produto = None
        for col in codigo_colunas:
            if col in produto_selecionado and produto_selecionado[col]:
                cd_produto = str(produto_selecionado[col])
                break
                
        if not cd_produto:
            return "Código não encontrado", "Não foi possível identificar o código do produto."
            
        # Obter a descrição do produto
        desc_produto = None
        for col in desc_colunas:
            if col in produto_selecionado and produto_selecionado[col]:
                desc_produto = produto_selecionado[col]
                break
                
        if not desc_produto:
            desc_produto = f"Produto {cd_produto}"
        
        # Carregar dados de produtos
        df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')
        
        # Verificar se o produto existe no dataframe
        # Tentar diferentes formatos de código para aumentar compatibilidade
        cd_produto_encontrado = False
        for valor in [cd_produto, int(cd_produto) if cd_produto.isdigit() else cd_produto]:
            if valor in df_produtos['cd_produto'].values:
                cd_produto = valor
                cd_produto_encontrado = True
                break
        
        if not cd_produto_encontrado:
            return f"Produto não encontrado: {cd_produto}", html.Div([
                html.P(f"O produto com código {cd_produto} não foi encontrado na base de dados.", 
                       className="text-center text-muted my-4")
            ])
        
        # Chamar a função para criar o gráfico
        fig = criar_grafico_produto(df_produtos, cd_produto)
        
        # Adicionar título legível e detalhes
        header = html.Div([
            # Informações de fornecedor 1
            html.Div([
                html.H6("Últimas 3 Compras", className="mt-4 mb-3"),
                html.Div([
                    # Usando blocos com grande espaçamento horizontal
                    html.Div([
                        html.Span("Data: ", className="font-weight-bold"),
                        html.Span(format_iso_date(produto_selecionado.get('Data1', '-')))
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Qtd: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Quantidade1', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Custo: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('custo1', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Fornecedor: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Fornecedor1', '-')}")
                    ], style={"display": "inline-block"})
                ], className="text-muted")
            ], className="mt-4 pb-3 border-bottom") if 'Data1' in produto_selecionado or 'Quantidade1' in produto_selecionado or 'custo1' in produto_selecionado or 'Fornecedor1' in produto_selecionado else None,
            
            # Informações de fornecedor 2
            html.Div([
                html.Div([
                    # Usando blocos com grande espaçamento horizontal
                    html.Div([
                        html.Span("Data: ", className="font-weight-bold"),
                        html.Span(format_iso_date(produto_selecionado.get('Data2', '-')))
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Qtd: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Quantidade2', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Custo: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('custo2', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Fornecedor: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Fornecedor2', '-')}")
                    ], style={"display": "inline-block"})
                ], className="text-muted")
            ], className="mt-4 pb-3 border-bottom") if 'Data2' in produto_selecionado or 'Quantidade2' in produto_selecionado or 'custo2' in produto_selecionado or 'Fornecedor2' in produto_selecionado else None,
            
            # Informações de fornecedor 3
            html.Div([
                html.Div([
                    # Usando blocos com grande espaçamento horizontal
                    html.Div([
                        html.Span("Data: ", className="font-weight-bold"),
                        html.Span(format_iso_date(produto_selecionado.get('Data3', '-')))
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Qtd: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Quantidade3', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Custo: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('custo3', '-')}")
                    ], style={"display": "inline-block", "marginRight": "60px"}),
                    
                    html.Div([
                        html.Span("Fornecedor: ", className="font-weight-bold"),
                        html.Span(f"{produto_selecionado.get('Fornecedor3', '-')}")
                    ], style={"display": "inline-block"})
                ], className="text-muted")
            ], className="mt-4") if 'Data3' in produto_selecionado or 'Quantidade3' in produto_selecionado or 'custo3' in produto_selecionado or 'Fornecedor3' in produto_selecionado else None
        ])
        
        # Adicionar o gráfico com legenda explicativa
        grafico_component = html.Div([
            dcc.Graph(
                figure=fig,
                config={"responsive": True},
                style={"height": "500px"}
            ),
            html.Div([
                html.P([
                    "O gráfico mostra o histórico de consumo nos últimos meses e a sugestão de compra.",
                    html.Br(),
                    html.Span("Sugestão 1M: ", className="font-weight-bold"),
                    "Quantidade sugerida para compra no próximo mês.", 
                    html.Br(),
                    html.Span("Sugestão 3M: ", className="font-weight-bold"),
                    "Quantidade sugerida para compra nos próximos três meses."
                ], className="text-muted small mt-2")
            ])
        ])
        
        return header, grafico_component
    
    except Exception as e:
        return "Erro ao gerar gráfico", html.Div([
            html.P(f"Ocorreu um erro ao gerar o gráfico: {str(e)}", 
                   className="text-center text-danger my-4"),
            html.Pre(str(e), className="bg-light p-3 text-danger")
        ])


# Callback para atualizar o estado do filtro e o texto do botão
@application.callback(
    [Output("filtro-criticos-ativo", "data"),
     Output("btn-filtro-criticos", "children"),
     Output("btn-filtro-criticos", "color")],
    Input("btn-filtro-criticos", "n_clicks"),
    State("filtro-criticos-ativo", "data"),
    prevent_initial_call=True
)
def toggle_filtro_criticos(n_clicks, filtro_ativo):
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update
    
    # Inverte o estado atual do filtro
    novo_estado = not filtro_ativo
    
    # Texto e cor do botão dependendo do estado
    if novo_estado:
        # Se o filtro estiver ativo (mostrando apenas críticos)
        texto_botao = [html.I(className="fas fa-filter me-2"), "Mostrar Todos os Produtos"]
        cor_botao = "primary"
    else:
        # Se o filtro estiver inativo (mostrando todos)
        texto_botao = [html.I(className="fas fa-filter me-2"), "Mostrar Produtos com Reposição Não-Local"]
        cor_botao = "danger"
    
    return novo_estado, texto_botao, cor_botao

# Callback para atualizar o gráfico de barras com base no filtro
@application.callback(
    Output("produtos-criticidade-bar", "figure"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
)
def update_grafico_barras(filtro_ativo, produtos_data):
    if produtos_data is None:
        return dash.no_update
    
    # Carregamos os dados
    df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
    
    # Se o filtro estiver ativo, filtrar para mostrar apenas produtos críticos
    if filtro_ativo:
        # Em vez de filtrar a contagem, vamos filtrar o dataframe original
        df_filtrado = df_criticos[df_criticos['critico'] == True]

        contagem_criticidade = df_filtrado['criticidade'].value_counts().sort_index()

        total_produtos = len(df_filtrado)
        total_series = pd.Series([total_produtos], index=['Todos'])
        contagem_criticidade = pd.concat([contagem_criticidade, total_series])
    else:
        # Contagem normal de todos os produtos por criticidade
        contagem_criticidade = df_criticos['criticidade'].value_counts().sort_index()
        # Adicionar o total
        total_produtos = len(df_criticos)
        total_series = pd.Series([total_produtos], index=['Todos'])
        contagem_criticidade = pd.concat([contagem_criticidade, total_series])
    
    # Calcular porcentagens para anotações
    porcentagens = (contagem_criticidade / total_produtos * 100).round(1)
    
    # Criar gráfico de barras
    fig = px.bar(
        x=contagem_criticidade.index,
        y=contagem_criticidade.values,
        color=contagem_criticidade.index,
        color_discrete_map={
            'Crítico': 'darkred',
            'Muito Baixo': 'orange',
            'Baixo': color['warning'],
            'Adequado': gradient_colors['green_gradient'][0],
            'Excesso': color['secondary'],
            'Todos': color['primary']
        },
        labels={'x': 'Nível de Criticidade', 'y': 'Quantidade de Produtos'},
        template='plotly_white'
    )
    
    # Adicionar valores nas barras
    for i, v in enumerate(contagem_criticidade.values):
        percentage = porcentagens[contagem_criticidade.index[i]]
        fig.add_annotation(
            x=contagem_criticidade.index[i],
            y=v,
            text=f"{str(v)} ({percentage:.1f}%)".replace(".", ","),
            showarrow=False,
            yshift=10,
            font=dict(size=14, color="black", family="Montserrat", weight="bold")
        )
    
    fig.update_layout(
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        xaxis_title="Nível de Criticidade",
        yaxis_title="Quantidade de Produtos",
        margin=dict(t=50, b=50, l=50, r=50),
        height=500,
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig

# Callback para atualizar o Top 20 produtos críticos com base no filtro
@application.callback(
    Output("produtos-criticidade-top20", "figure"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
)
def update_grafico_top20(filtro_ativo, produtos_data):
    if produtos_data is None:
        return dash.no_update
    
    # Carregamos os dados
    df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
    
    # Verificar a coluna de descrição do produto
    produto_col = 'desc_produto' if 'desc_produto' in df_criticos.columns else 'Produto' if 'Produto' in df_criticos.columns else None
    
    if not produto_col:
        # Se não tiver coluna de produto, retorna um gráfico vazio
        fig = go.Figure()
        fig.update_layout(
            title="Coluna de descrição de produto não encontrada",
            title_font=dict(size=16, family="Montserrat", color=color['primary'])
        )
        return fig
    
    # Filtrar os dados com base no estado do filtro
    if filtro_ativo:
        df_filtrado = df_criticos[df_criticos['critico'] == True]
    else:
        df_filtrado = df_criticos
    
    # Ordenar pelo percentual de cobertura
    df_ordenado = df_filtrado.sort_values('percentual_cobertura')
    
    # Selecionar os Top 20
    top_20 = df_ordenado.head(20)
    
    # Criar a coluna de exibição do produto
    top_20['produto_display'] = top_20[produto_col].apply(lambda x: (x[:30] + '...') if len(str(x)) > 30 else x)
    
    # Criar o gráfico
    fig = px.bar(
        top_20,
        y='produto_display',
        x='percentual_cobertura',
        orientation='h',
        color='percentual_cobertura',
        color_continuous_scale=['darkred', 'orange', color['warning']],
        range_color=[0, 50 if filtro_ativo else 100],  # Ajusta range de cores com base no filtro
        labels={'percentual_cobertura': 'Cobertura (%)', 'produto_display': 'Produto'},
        template='plotly_white'
    )
    
    if 'cd_produto' in top_20.columns:
        fig.update_traces(
            hovertemplate='<b>%{y}</b><br>Código: %{customdata[0]}<br>Cobertura: %{x:.1f}%',
            customdata=top_20[['cd_produto']]
        )
    
    fig.update_layout(
        title=f"Top 20 Produtos{' Críticos' if filtro_ativo else ''}",
        title_font=dict(size=16, family="Montserrat", color=color['primary']),
        yaxis_title="",
        xaxis_title="Percentual de Cobertura (%)",
        margin=dict(l=200, r=20, t=30, b=30),
        height=500,
        yaxis=dict(autorange="reversed"),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # Adicionar linha em 30% para referência de criticidade
    fig.add_shape(
        type="line",
        x0=30, y0=-0.5,
        x1=30, y1=len(top_20) - 0.5,
        line=dict(color="darkred", width=2, dash="dash"),
    )
    
    # Adicionar valores de percentual nas barras
    for i, row in enumerate(top_20.itertuples()):
        fig.add_annotation(
            x=row.percentual_cobertura,
            y=row.produto_display,
            text=f"{row.percentual_cobertura:.1f}%".replace(".", ","),
            showarrow=False,
            xshift=15,
            font=dict(size=12, color="black", family="Montserrat")
        )
    
    return fig

@application.callback(
    Output("div-metrics-row", "children"),
    [Input("filtro-criticos-ativo", "data"),
     Input("store-produtos-data", "data")],
    prevent_initial_call=True
)
def update_metricas(filtro_ativo, produtos_data):
    if produtos_data is None:
        return dash.no_update
    
    # Carregamos os dados
    df_criticos = pd.read_json(io.StringIO(produtos_data), orient='split')
    
    # Se o filtro estiver ativo, mostrar apenas informações de produtos críticos
    if filtro_ativo:
        df_filtrado = df_criticos[df_criticos['critico'] == True]
        
        # Contar produtos por cada categoria de criticidade
        total_produtos = len(df_filtrado)
        produtos_criticos = len(df_filtrado[df_filtrado['criticidade'] == 'Crítico'])
        produtos_muito_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'Muito Baixo'])
        produtos_baixos = len(df_filtrado[df_filtrado['criticidade'] == 'Baixo'])
        produtos_adequados = len(df_filtrado[df_filtrado['criticidade'] == 'Adequado'])
        produtos_excesso = len(df_filtrado[df_filtrado['criticidade'] == 'Excesso'])
        
        # Criar métricas para a primeira linha de cards - mostrando todas as categorias
        metrics = [
            {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
            {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
            {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
            {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
            {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
            {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
        ]
        
    else:
        # Contar produtos por cada categoria de criticidade
        total_produtos = len(df_criticos)
        produtos_criticos = len(df_criticos[df_criticos['criticidade'] == 'Crítico'])
        produtos_muito_baixos = len(df_criticos[df_criticos['criticidade'] == 'Muito Baixo'])
        produtos_baixos = len(df_criticos[df_criticos['criticidade'] == 'Baixo'])
        produtos_adequados = len(df_criticos[df_criticos['criticidade'] == 'Adequado'])
        produtos_excesso = len(df_criticos[df_criticos['criticidade'] == 'Excesso'])
        
        # Criar métricas para a primeira linha de cards - mostrando todas as categorias
        metrics = [
            {"title": "Total de Produtos", "value": formatar_numero(total_produtos), "color": color['primary']},
            {"title": "Crítico (0-30%)", "value": formatar_numero(produtos_criticos), "color": 'darkred'},
            {"title": "Muito Baixo (30-50%)", "value": formatar_numero(produtos_muito_baixos), "color": 'orange'},
            {"title": "Baixo (50-80%)", "value": formatar_numero(produtos_baixos), "color": color['warning']},
            {"title": "Adequado (80-100%)", "value": formatar_numero(produtos_adequados), "color": gradient_colors['green_gradient'][0]},
            {"title": "Excesso (>100%)", "value": formatar_numero(produtos_excesso), "color": color['secondary']}
        ]
    
    # Retornar a linha de métricas criada
    return create_metric_row(metrics)

@application.callback(
    [Output("produtos-criticidade-header", "children"),
     Output("produtos-criticidade-list", "children")],
    [Input("produtos-criticidade-bar", "clickData"),
     Input("filtro-criticos-ativo", "data")],
    [State("selected-data", "data")]
)
def update_produtos_criticidade_list(clickData_bar, filtro_ativo, data):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        # No clicks yet
        return "Produtos do Nível de Cobertura Selecionado", html.Div([
            html.P("Selecione um nível de criticidade nos gráficos acima para ver os produtos.", className="text-center text-muted my-4"),
            html.Div(className="text-center", children=[
                html.I(className="fas fa-mouse-pointer fa-2x text-muted"),
                html.P("Clique em uma fatia, barra ou ponto para visualizar detalhes", className="text-muted mt-2")
            ])
        ])
    
    if data is None or data.get("df_relatorio_produtos") is None:
        return "Produtos do Nível de Cobertura Selecionado", "Dados não disponíveis."
    
    df_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split')

    if filtro_ativo:
        df_produtos = df_produtos[df_produtos['critico'] == True]
    
    # Converta as colunas de string para lowercase para facilitar buscas case-insensitive
    string_columns = df_produtos.select_dtypes(include=['object']).columns
    for col in string_columns:
        try:
            # Tentar converter para lowercase, mas ignorar erros (se houver valores não-string)
            df_produtos[f"{col}_lower"] = df_produtos[col].str.lower()
        except:
            pass
    
    # Determine which chart was clicked
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Initialize default criticidade
    selected_criticidade = None
    
    if trigger_id == 'produtos-criticidade-bar' and clickData_bar:
        selected_criticidade = clickData_bar['points'][0]['x']
    
    if selected_criticidade is None:
        return "Produtos do Nível de Cobertura Selecionado", html.Div([
            html.P("Não foi possível identificar a cobertura selecionada.", className="text-center text-muted my-4")
        ])
    
    # Checar se foi selecionado "Todos"
    if selected_criticidade == 'Todos':
        header_text = "Todos os Produtos"
        filtered_df = df_produtos  # Usar todo o DataFrame
    else:
        header_text = f"Produtos com Criticidade: {selected_criticidade}"
        # Filtrar TODOS os produtos desta criticidade
        filtered_df = df_produtos[df_produtos["criticidade"] == selected_criticidade]
    
    if filtered_df.empty:
        return header_text, "Nenhum produto encontrado para a criticidade selecionada."
    
    # Determinar colunas de exibição
    display_columns = [
        "cd_produto", "desc_produto", "critico", "estoque_atualizado", "Media 3M", 
        "percentual_cobertura", "Sug 1M", "Sug 3M", 
        "Data1", "Quantidade1", "custo1", "Fornecedor1", 
        "Data2", "Quantidade2", "custo2", "Fornecedor2",
        "Data3", "Quantidade3", "custo3", "Fornecedor3"
    ]
    
    # Usar apenas colunas que existem no DataFrame
    existing_columns = [col for col in display_columns if col in filtered_df.columns]
    if not existing_columns:
        return header_text, "Estrutura de dados incompatível para exibição de detalhes."
    
    # Renomear colunas para melhor visualização
    col_rename = {
        "cd_produto": "Código",
        "desc_produto": "Produto",
        "critico": "Reposição Não-Local (Crítico)",
        "estoque_atualizado": "Estoque Atual",
        "Media 3M": "Consumo Médio (3M)",
        "percentual_cobertura": "Cobertura (%)",
        "Sug 1M": "Sugestão (1M)",
        "Sug 3M": "Sugestão (3M)",
        "Data1": "Data 1",
        "Quantidade1": "Quantidade 1",
        "custo1": "Custo Unitário 1",
        "Fornecedor1": "Fornecedor 1",
        "Data2": "Data 2",
        "Quantidade2": "Quantidade 2",
        "custo2": "Custo Unitário 2",
        "Fornecedor2": "Fornecedor 2",
        "Quantidade3": "Quantidade 3",
        "Data3": "Data 3",
        "custo3": "Custo Unitário 3",
        "Fornecedor3": "Fornecedor 3"
    }
    
    # Formatação especial para valores monetários e percentuais
    filtered_df_display = filtered_df[existing_columns].copy()
    
    if 'percentual_cobertura' in filtered_df_display.columns:
        filtered_df_display['percentual_cobertura'] = filtered_df_display['percentual_cobertura'].apply(
            lambda x: f"{x:.1f}%".replace(".", ",")
        )
    
    if 'custo1' in filtered_df_display.columns:
        filtered_df_display['custo1'] = filtered_df_display['custo1'].apply(
            lambda x: formatar_moeda(x) if not pd.isna(x) else ""
        )
    
    # Calcular valor total estimado, se possível
    valor_total = None
    if 'Sug 1M' in filtered_df.columns and 'custo1' in filtered_df.columns:
        # Tentar converter para numérico (pode já ser string formatada)
        filtered_df['Sug_1M_num'] = pd.to_numeric(filtered_df['Sug 1M'], errors='coerce')
        filtered_df['custo1_num'] = pd.to_numeric(filtered_df['custo1'], errors='coerce')
        
        # Calcular o valor total
        filtered_df['valor_estimado'] = filtered_df['Sug_1M_num'] * filtered_df['custo1_num']
        valor_total = filtered_df['valor_estimado'].sum()
    
    # Criar tabela aprimorada com filtro case-insensitive
    table = dash_table.DataTable(
        id='produtos-criticidade-table',  # ID único para a tabela
        columns=[{"name": col_rename.get(col, col), "id": col} for col in existing_columns],
        data=filtered_df_display.to_dict("records"),
        page_size=10,  # Aumentado para mostrar mais produtos por página
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
                "if": {"column_id": "percentual_cobertura"},
                "fontWeight": "bold",
                "color": "darkred" if selected_criticidade == "Crítico" else 
                        "orange" if selected_criticidade == "Muito Baixo" else
                        color['warning'] if selected_criticidade == "Baixo" else
                        "green" if selected_criticidade == "Adequado" else color['secondary']
            },
            {
                "if": {"column_id": "custo1"},
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
        export_format="xlsx",
        # Configuração para tornar o filtro case-insensitive
        filter_options={
            'case': 'insensitive'   # Ignora maiúsculas/minúsculas nos filtros
        }
    )
    
    # Adicionar resumo acima da tabela
    total_categoria = len(filtered_df)
    summary = html.Div([
        html.P([
            f"Exibindo todos os ", 
            html.Strong(formatar_numero(total_categoria)), 
            f" produtos com criticidade ", 
            html.Strong(selected_criticidade),
            valor_total and f". Valor estimado de compra: " or "",
            valor_total and html.Strong(formatar_moeda(valor_total)) or ""
        ], style={"marginBottom": "1rem", "fontSize": "0.9rem", "color": "#666"})
    ])
    
    return header_text, html.Div([summary, table])

# """"""""""""""""""""""""""""""""""""""""""""""""""""""
# Geração de gráficos de consumo de produtos
# """"""""""""""""""""""""""""""""""""""""""""""""""""""

def criar_grafico_simulado(produto, valores, meses_labels):
    """
    Cria um gráfico simulado quando as colunas não estão no formato esperado.
    
    Args:
        produto: Série com os dados do produto
        valores: Lista de valores mensais
        meses_labels: Lista de rótulos para os meses
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Obter as sugestões de compra
        sug_1m = float(produto['Sug 1M']) if 'Sug 1M' in produto else 0
        sug_3m = float(produto['Sug 3M']) if 'Sug 3M' in produto else 0
        
        # Nome do produto
        nome_produto = produto.get('desc_produto', produto.get('Produto', f"Produto {produto.get('cd_produto', '')}"))
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Adicionar linha de consumo mensal
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=valores,
                mode='lines+markers+text',
                name='Consumo',
                line=dict(color='#0077B6', width=3),
                marker=dict(size=8, color='#0077B6'),
                text=[str(int(v)) for v in valores],
                textposition='top center',
                textfont=dict(size=10)
            )
        )
        
        # Adicionar barras para Sugestão 1M e 3M
        x_all = meses_labels + ['Sugestão\n1M', 'Sugestão\n3M']
        
        # Adicionar barra para Sugestão 1M
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n1M'],
                y=[sug_1m],
                name='Sugestão 1M',
                marker_color='#0077B6',
                text=[str(int(sug_1m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Adicionar barra para Sugestão 3M 
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n3M'],
                y=[sug_3m],
                name='Sugestão 3M',
                marker_color='#0077B6',
                text=[str(int(sug_3m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Configurar layout
        fig.update_layout(
            title=f"Consumo Mensal - {nome_produto}",
            title_font=dict(size=16, family="Montserrat", color='#001514'),
            xaxis=dict(
                title="",
                tickmode='array',
                tickvals=x_all,
                ticktext=x_all,
                tickangle=-45,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title="Quantidade",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=80),
            height=500
        )
        
        # Adicionar linha horizontal no zero
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=len(x_all) - 1,
            y1=0,
            line=dict(color="black", width=1)
        )
        
        return fig
    
    except Exception as e:
        print(f"Erro ao gerar gráfico simulado: {str(e)}")
        # Retornar um gráfico de erro
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao gerar gráfico simulado: {str(e)}",
            showarrow=False,
            font=dict(size=12, color="red")
        )
        return fig

def criar_grafico_produto(df_produto, cd_produto):
    """
    Cria um gráfico de consumo mensal para um produto específico,
    similar ao da imagem de referência.
    
    Args:
        df_produto: DataFrame contendo os dados dos produtos
        cd_produto: Código do produto para gerar o gráfico
    
    Returns:
        Uma figura Plotly configurada
    """
    try:
        # Filtrar o produto específico
        produto = df_produto[df_produto['cd_produto'] == cd_produto].iloc[0]
        
        # Obter colunas que representam meses (formato: YYYY_MM)
        colunas_meses = [col for col in df_produto.columns if col.startswith('202')]
        
        # Se não houver colunas de meses no formato YYYY_MM, verificar outros formatos possíveis
        if not colunas_meses:
            # Tentar encontrar colunas numéricas que possam representar meses
            colunas_numericas = [col for col in df_produto.columns 
                                if isinstance(col, str) and col not in ['cd_produto', 'desc_produto', 'estoque_atualizado', 
                                                                       'Media 3M', 'Sug 1M', 'Sug 3M', 'custo1', 'Fornecedor1']]
            
            # Se tivermos pelo menos 12 colunas numéricas, podemos assumir que são meses
            if len(colunas_numericas) >= 12:
                colunas_meses = colunas_numericas[:14]  # Limitar a 14 meses como no exemplo
                
                # Criar rótulos simulados de meses (Jan-24, Fev-24, etc.)
                meses_labels = [
                    'Jan-24', 'Fev-24', 'Mar-24', 'Abr-24', 'Mai-24', 'Jun-24', 
                    'Jul-24', 'Ago-24', 'Set-24', 'Out-24', 'Nov-24', 'Dez-24', 
                    'Jan-25', 'Fev-25'
                ][:len(colunas_meses)]
                
                # Simular valores se estiverem faltando
                valores = []
                for col in colunas_meses:
                    try:
                        val = float(produto[col])
                        valores.append(val)
                    except:
                        valores.append(0)  # Valor padrão se não conseguir converter
                
                return criar_grafico_simulado(produto, valores, meses_labels)
        
        colunas_meses.sort()  # Garantir ordem cronológica
        
        # Extrair valores mensais de consumo
        valores = []
        for col in colunas_meses:
            try:
                valores.append(float(produto[col]))
            except (ValueError, TypeError):
                # Se não conseguir converter para float, usar 0
                valores.append(0)
        
        # Obter as sugestões de compra
        sug_1m = float(produto['Sug 1M']) if 'Sug 1M' in produto else 0
        sug_3m = float(produto['Sug 3M']) if 'Sug 3M' in produto else 0
        
        # Criar rótulos para os meses no formato "MMM-YY"
        meses_labels = []
        for col in colunas_meses:
            ano, mes = col.split('_')
            ano_curto = ano[2:]  # Pegar só os dois últimos dígitos do ano
            # Converter mês numérico para nome abreviado
            mes_nomes = {
                '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
                '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
                '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
            }
            mes_nome = mes_nomes.get(mes, mes)
            meses_labels.append(f"{mes_nome}-{ano_curto}")

        # Calcular a média móvel de 3 meses
        media_movel_3m = []
        for i in range(len(valores)):
            if i < 2:  # Para os dois primeiros meses, não temos 3 meses completos
                media_movel_3m.append(None)
            else:
                # Média dos 3 meses anteriores (incluindo o atual)
                media = sum(valores[i-2:i+1]) / 3
                media_movel_3m.append(media)
        
        # Criar o gráfico
        fig = make_subplots(specs=[[{"secondary_y": False}]])
        
        # Adicionar linha de consumo mensal
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=valores,
                mode='lines+markers+text',
                name='Consumo',
                line=dict(color='#0077B6', width=3),
                marker=dict(size=8, color='#0077B6'),
                text=[str(int(v)) for v in valores],
                textposition='top center',
                textfont=dict(size=10)
            )
        )

        # Adicionar linha de média móvel de 3 meses
        fig.add_trace(
            go.Scatter(
                x=meses_labels,
                y=media_movel_3m,
                mode='lines',
                name='Média Móvel 3M',
                line=dict(color='#FF8C00', width=2, dash='dash'),
                hoverinfo='text',
                hovertext=[f'Média 3M: {round(m, 1)}' if m is not None else '' for m in media_movel_3m]
            )
        )
        
        # Adicionar barras para Sugestão 1M e 3M
        x_all = meses_labels + ['Sugestão\n1M', 'Sugestão\n3M']
        
        # Adicionar barra para Sugestão 1M
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n1M'],
                y=[sug_1m],
                name='Sugestão 1M',
                marker_color='#0077B6',
                text=[str(int(sug_1m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Adicionar barra para Sugestão 3M 
        fig.add_trace(
            go.Bar(
                x=['Sugestão\n3M'],
                y=[sug_3m],
                name='Sugestão 3M',
                marker_color='#0077B6',
                text=[str(int(sug_3m))],
                textposition='outside',
                width=[0.6]
            )
        )
        
        # Configurar layout
        fig.update_layout(
            title=f"Consumo Mensal - {produto['desc_produto']}",
            title_font=dict(size=16, family="Montserrat", color='#001514'),
            xaxis=dict(
                title="",
                tickmode='array',
                tickvals=x_all,
                ticktext=x_all,
                tickangle=-45,
                gridcolor='rgba(0,0,0,0.1)'
            ),
            yaxis=dict(
                title="Quantidade",
                gridcolor='rgba(0,0,0,0.1)'
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=80, b=80),
            height=500
        )
        
        # Adicionar linha horizontal no zero
        fig.add_shape(
            type="line",
            x0=0,
            y0=0,
            x1=len(x_all) - 1,
            y1=0,
            line=dict(color="black", width=1)
        )
        
        return fig
    
    except Exception as e:
        print(f"Erro ao gerar gráfico para o produto {cd_produto}: {str(e)}")
        # Retornar um gráfico de erro
        fig = go.Figure()
        fig.add_annotation(
            text=f"Erro ao gerar gráfico: {str(e)}",
            showarrow=False,
            font=dict(size=12, color="red")
        )
        return fig

# =============================================================================
# Callback para renderizar o conteúdo conforme a URL
# =============================================================================
@application.callback(
    Output("page-content-dashboard", "children"),
    Output("loading-output-overlay", "children"),
    Input("url", "pathname"),
    Input("selected-data", "data"),
    prevent_initial_call=True
)
def render_page_content(pathname, data):       
    # Verificar se temos dados carregados e válidos
    if data is None:
        # Verificar se temos cliente e tipo de dados no store
        return html.Div([
            html.Div(className="text-center", style={"marginTop": "20%"},
                children=[
                    html.H4("Carregando dados...", className="mb-3"),
                    html.P("Aguarde enquanto os dados são preparados."),
                    html.Div(className="loading-spinner")
                ]
            )
        ], style=content_style), None
    
    # Verificar se os dados contêm a chave de identificação
    if 'client_info' not in data:
        return html.Div([
            html.Div(className="text-center", style={"marginTop": "20%"},
                children=[
                    html.H4("Dados incompletos", className="mb-3"),
                    html.P("Os dados carregados não contêm as informações necessárias."),
                    html.P("Tente selecionar novamente o cliente e o tipo de dados.")
                ]
            )
        ], style=content_style), None
    
    # Log para depuração
    print(f"Renderizando {pathname} com dados do cliente {data['client_info']}")
    
    # Se chegamos aqui, os dados estão disponíveis
    # Pequeno delay para melhor experiência do usuário
    time.sleep(0.2)
    
    # Renderizar a página apropriada com base no pathname
    if pathname == "/" or pathname == "/rfma":
        return get_rfma_layout(data), None
    elif pathname == "/segmentacao":
        return get_segmentacao_layout(data), None
    elif pathname == "/recorrencia/mensal":
        return get_recorrencia_mensal_layout(data), None
    elif pathname == "/recorrencia/trimestral":
        return get_recorrencia_trimestral_layout(data), None
    elif pathname == "/recorrencia/anual":
        return get_recorrencia_anual_layout(data), None
    elif pathname == "/retencao":
        return get_retencao_layout(data), None
    elif pathname == "/predicao":
        return get_predicao_layout(data), None
    elif pathname == "/faturamento/anual": 
        return get_faturamento_anual_layout(data), None
    elif pathname == "/estoque/vendas-atipicas":
        return get_vendas_atipicas_layout(data), None
    elif pathname == "/estoque/produtos":
        return get_produtos_layout(data), None
    elif pathname == "/chat" or pathname == "/app/": 
        return get_chat_layout(data), None
    
    # 404 Page Not Found com estilização
    return html.Div(
        [
            html.Div(
                className="text-center",
                children=[
                    html.H1("404", className="display-1 text-muted"),
                    html.H2("Página não encontrada", className="mb-4"),
                    html.P("A página que você tentou acessar não existe no dashboard.", className="mb-4"),
                    dbc.Button(
                        [html.I(className="fas fa-home me-2"), "Voltar para o início"],
                        href="/",
                        color="primary",
                        style=button_style
                    )
                ]
            )
        ],
        style={**content_style, "display": "flex", "alignItems": "center", "justifyContent": "center"}
    ), None

# =============================================================================
# Callback separado para carregar dados
# =============================================================================
@application.callback(
    Output("selected-data", "data"),
    Input("selected-client", "data"),
    Input("selected-data-type", "data"),
    State("selected-data", "data"),
    prevent_initial_call=True
)
def load_data_callback(selected_client, selected_data_type, current_data):
    # Verificar se os inputs são válidos
    if not selected_client or not selected_data_type:
        return None
    
    # Criar uma chave de cache consistente
    cache_key = f"{selected_client}_{selected_data_type}"
    
    # Se já temos dados em cache para este cliente/tipo, use-os
    if current_data and 'client_info' in current_data and current_data['client_info'] == cache_key:
        print(f"Usando dados em cache para {cache_key}")
        return current_data
    
    # Senão, carregue os dados
    print(f"**************** Carregando dados para {selected_client} - {selected_data_type}")
    data = load_data(selected_client, selected_data_type)
    
    if data.get("error", False):
        print(f"Erro ao carregar dados: {data.get('message', 'Erro desconhecido')}")
        return None
    
    # Crie um objeto com os dados serializados e a informação do cliente
    cached_data = {
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
    return cached_data

@application.callback(
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
# =============================================================================
# Callbacks específicos para atualizar componentes nas páginas
# =============================================================================

@application.callback(
    Output('chat-history', 'children'),
    Output('user-input', 'value'),
    Input('submit-button', 'n_clicks'),
    State('user-input', 'value'),
    State('chat-history', 'children'),
    State('selected-data', 'data'),
    State('selected-client', 'data'),
    prevent_initial_call=True
)
def responde(n_clicks, user_input, chat_history, data, selected_client):
    if n_clicks is None or not user_input:
        return chat_history, ''

    if chat_history is None:
        chat_history = []  # Define chat_history como uma lista vazia

    # Add user message with styled container
    user_message = html.Div([
        html.Div([
            html.Strong("Você: "),
            html.Span(user_input)
        ], className="chat-message user-message")
    ], style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "1rem"})
    
    chat_history.append(user_message)
    
    # Add typing indicator while processing
    typing_indicator = html.Div([
        html.Div([
            html.Span("Pensando", style={"fontStyle": "italic"}),
            html.Span("...", id="typing-dots")
        ], className="chat-message bot-message", style={"backgroundColor": "#f0f0f0"})
    ], style={"display": "flex", "justifyContent": "flex-start", "marginBottom": "1rem"})
    
    chat_history.append(typing_indicator)

    # 1. Classificar a pergunta para extrair as categorias
    start_time = time.time()
    categorias = classificar_pergunta(user_input)
    
    # 2. Selecionar os DataFrames relevantes com base nas categorias
    dataframes = selecionar_dataframes(user_input, categorias)
    
    # 3. Importar dataframes
    if data:
        #segmentacao de clientes
        df = pd.read_json(io.StringIO(data["df"]), orient='split') if data.get("df") else None
        df_RC_Mensal = pd.read_json(io.StringIO(data["df_RC_Mensal"]), orient='split') if data.get("df_RC_Mensal") else None
        df_RC_Trimestral = pd.read_json(io.StringIO(data["df_RC_Trimestral"]), orient='split') if data.get("df_RC_Trimestral") else None
        df_RC_Anual = pd.read_json(io.StringIO(data["df_RC_Anual"]), orient='split') if data.get("df_RC_Anual") else None
        df_RT_Anual = pd.read_json(io.StringIO(data["df_RT_Anual"]), orient='split') if data.get("df_RT_Anual") else None
        df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split') if data.get("df_Previsoes") else None

        #estoque
        df_Vendas_Atipicas = pd.read_json(io.StringIO(data["df_Vendas_Atipicas"]), orient='split') if data.get("df_Vendas_Atipicas") else None
        df_relatorio_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split') if data.get("df_relatorio_produtos") else None

        #faturamento
        df_fat_Anual = pd.read_json(io.StringIO(data["df_fat_Anual"]), orient='split') if data.get("df_fat_Anual") else None
        df_fat_Anual_Geral = pd.read_json(io.StringIO(data["df_fat_Anual_Geral"]), orient='split') if data.get("df_fat_Anual_Geral") else None
        df_fat_Mensal = pd.read_json(io.StringIO(data["df_fat_Mensal"]), orient='split') if data.get("df_fat_Mensal") else None

        # Obter contexto específico do cliente
        company_context = data.get("company_context", CONTEXTO_PADRAO)
        segmentos_context = data.get("segmentos_context", SEGMENTOS_PADRAO)

        # 4. Construir o prompt com os dados disponíveis
        prompt = f"""
        Você é um assistente de análise de dados para um sistema de varejo.
        A pergunta é: "{user_input}"
        Dados disponíveis:
        - Contexto do negócio: {company_context}
        - Dataframes considerados úteis: {dataframes}
        - Categorias identificadas para a pergunta: {categorias}
        - Dataframes: {
            df, df_RC_Mensal, 
            df_RC_Trimestral, 
            df_RC_Anual, 
            df_RT_Anual, 
            df_Previsoes, 
            df_Vendas_Atipicas, 
            df_fat_Anual, 
            df_fat_Anual_Geral, 
            df_fat_Mensal, 
            df_relatorio_produtos
        }
        
        Perguntas sobre segmentos de clientes:
        - Para perguntas sobre os segmentos dos clientes, considere: {segmentos_context}
        
        Regras sobre a resposta final:
        - Responda de forma clara e objetiva com linguagem natural
        - Na resposta final, não deve haver nomes de dataframes, apenas a análise feita em cima dos dados disponíveis 
        - Considere que quem está falando com você é algum funcionário da empresa {selected_client}
        - Formate valores monetários com R$ e separadores de milhar
        - Evite respostas genéricas
        - Seja direto ao ponto e forneça números e insights específicos
        - Limite sua resposta a no máximo 4 parágrafos
        """
        
        # 4. Obter a resposta do modelo
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.4,
        )
        
        # Extrai a resposta do GPT-4
        gpt_response = response.choices[0].message.content
    else:
        # Resposta caso não existam dados disponíveis
        gpt_response = """
        Não há dados disponíveis para análise. Por favor, certifique-se de que:
        
        1. Você selecionou corretamente o cliente e tipo de dados no menu lateral
        2. Os arquivos necessários estão presentes para o cliente selecionado
        3. O sistema conseguiu carregar os dados sem erros
        
        Caso o problema persista, entre em contato com o suporte técnico.
        """
    
    # Calcular o tempo de resposta
    response_time = time.time() - start_time
    
    # Remove typing indicator and add the bot response with styled container
    chat_history = chat_history[:-1]  # Remove typing indicator
    
    bot_message = html.Div([
        html.Div([
            html.Strong("Assistente: "),
            html.Div(dcc.Markdown(gpt_response)),
            html.Div(f"Tempo de resposta: {response_time:.2f}s", 
                     style={"fontSize": "0.8rem", "color": "#888", "marginTop": "0.5rem", "textAlign": "right"})
        ], className="chat-message bot-message")
    ], style={"display": "flex", "justifyContent": "flex-start", "marginBottom": "1rem"})
    
    chat_history.append(bot_message)

    return chat_history, ''

@application.callback(
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
    
    if data is None or data.get("df") is None:
        return "Clientes do Segmento Selecionado", "Dados não disponíveis."
    
    df = pd.read_json(io.StringIO(data["df"]), orient='split')
    
    # Extrair o segmento selecionado do clickData
    selected_segment = clickData["points"][0]["x"]
    header_text = f"Clientes do Segmento: {selected_segment}"
    
    # Filtrar o DataFrame para o segmento selecionado
    filtered_df = df[df["Segmento"] == selected_segment]
    
    if filtered_df.empty:
        return header_text, "Nenhum cliente encontrado para o segmento selecionado."
    
    # Determinar colunas de exibição
    if 'nome_fantasia' in df.columns:
        display_columns = ["id_cliente", "nome_fantasia", "Recency", "Frequency", "Monetary", "Age", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome_fantasia": "Cliente",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "Age": "Antiguidade (dias)",
            "email": "E-mail",
            "telefone": "Contato"
        }
    else:
        display_columns = ["id_cliente", "nome", "Recency", "Frequency", "Monetary", "Age", "email", "telefone"]
        col_rename = {
            "id_cliente": "Código do Cliente",
            "nome": "Cliente",
            "Recency": "Recência (dias)",
            "Frequency": "Frequência",
            "Monetary": "Valor Monetário (R$)",
            "Age": "Antiguidade (dias)",
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

@application.callback(
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

# =============================================================================
# Execução do servidor
# =============================================================================
if __name__ == "__main__":
    # Crie os diretórios necessários
    os.makedirs("dados", exist_ok=True)
    os.makedirs("contexts", exist_ok=True)
    os.makedirs("assets", exist_ok=True)
    
    print("Iniciando servidor Dashboard...")
    server.config['DEBUG'] = False
    server.secret_key = 'maloka_ai_secret_key_2025'
    
    # Rode na porta padrão (127.0.0.1:5000)
    server.run()

