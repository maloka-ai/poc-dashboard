from callbacks.vendas.faturamento_anual import register_faturamento_anual_callbacks

def register_callbacks(app):
    register_faturamento_anual_callbacks(app)   

__all__ = ['register_callbacks']