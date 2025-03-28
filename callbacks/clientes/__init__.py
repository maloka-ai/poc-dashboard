from callbacks.clientes.segmentacao import register_segmentacao_callbacks
from callbacks.clientes.predicao import register_predicao_callbacks

# Função para registrar todos os callbacks deste pacote
def register_callbacks(app):
    register_segmentacao_callbacks(app)
    register_predicao_callbacks(app)

# Lista de funções exportadas
__all__ = ['register_callbacks']