# Importe e exporte todas as funções de layout para facilitar o acesso
from layouts.clientes import *
from layouts.vendas import *
from layouts.estoque import *
from layouts.interacao import *

__all__ = [
    # Clientes
    'get_segmentacao_layout',
    'get_rfma_layout',
    'get_recorrencia_mensal_layout',
    'get_recorrencia_trimestral_layout',
    'get_recorrencia_anual_layout',
    'get_retencao_layout',
    'get_predicao_layout',
    
    # Vendas
    'get_faturamento_anual_layout',
    'get_vendas_atipicas_layout',
    
    # Estoque
    'get_produtos_layout',
    'get_produtos_inativos_layout',
    
    # Interação
    'get_chat_layout'
]