from callbacks.estoque.produtos import register_produtos_callbacks

def register_callbacks(app):
    register_produtos_callbacks(app)

__all__ = ['register_callbacks']