from layouts.clientes.segmentacao import get_segmentacao_layout
from layouts.clientes.rfma import get_rfma_layout
from layouts.clientes.recorrencia_mensal import get_recorrencia_mensal_layout
from layouts.clientes.recorrencia_trimestral import get_recorrencia_trimestral_layout
from layouts.clientes.recorrencia_anual import get_recorrencia_anual_layout
from layouts.clientes.retencao import get_retencao_layout
from layouts.clientes.predicao import get_predicao_layout

# Exporta todas as funções de layout
__all__ = [
    'get_segmentacao_layout',
    'get_rfma_layout',
    'get_recorrencia_mensal_layout',
    'get_recorrencia_trimestral_layout',
    'get_recorrencia_anual_layout',
    'get_retencao_layout',
    'get_predicao_layout'
]