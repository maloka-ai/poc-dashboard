from callbacks.estoque.produtos import register_produtos_callbacks
from callbacks.estoque.produtos_inativos import register_produtos_inativos_callbacks
from callbacks.estoque.giro_estoque import register_giro_estoque_callbacks

def register_callbacks(app):
    register_produtos_callbacks(app)
    register_produtos_inativos_callbacks(app)
    register_giro_estoque_callbacks(app)

__all__ = ['register_callbacks']