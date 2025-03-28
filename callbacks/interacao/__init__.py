from callbacks.interacao.chat import register_chat_callbacks

def register_callbacks(app):
    register_chat_callbacks(app)

__all__ = ['register_callbacks']