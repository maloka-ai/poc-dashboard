import diskcache
from dash.long_callback import DiskcacheLongCallbackManager
from flask_caching import Cache

def setup_diskcache():
    """Configura e retorna o gerenciador de cache do diskcache"""
    cache = diskcache.Cache("./cache")
    
    # Otimize as configurações do diskcache
    cache.reset('size', int(1e9))  # Limite de 1GB para o cache
    
    # Adicione configurações adicionais para melhor performance
    cache.set('cull_limit', 0)     # Desabilita culling automático para melhor performance
    cache.set('statistics', True)   # Habilita estatísticas para monitoramento
    
    # Criar o gerenciador de longo callback
    long_callback_manager = DiskcacheLongCallbackManager(cache)
    
    return cache, long_callback_manager

def setup_flask_cache(server):
    """Configura e retorna o cache do Flask para a aplicação"""
    app_cache = Cache(server, config={
        'CACHE_TYPE': 'filesystem',
        'CACHE_DIR': './flask_cache_dir',
        'CACHE_DEFAULT_TIMEOUT': 900,  # 15 minutos de timeout padrão
        'CACHE_THRESHOLD': 1000,       # Número máximo de itens no cache
        'CACHE_OPTIONS': {'mode': 0o755}  # Permissões de diretório
    })
    
    return app_cache

def clear_client_cache(cache, app_cache, cliente):
    """
    Limpa o cache específico para um cliente
    
    Args:
        cache: Instância do diskcache
        app_cache: Instância do Flask cache
        cliente: Nome do cliente cujo cache deve ser limpo
    """
    cache_keys = []
    
    # Limpar do diskcache
    try:
        for key in cache.iterkeys():
            key_str = str(key)
            if cliente in key_str:
                cache.delete(key)
                cache_keys.append(key_str)
    except Exception as e:
        print(f"Erro ao limpar diskcache: {str(e)}")
    
    # Limpar do Flask cache
    try:
        with app_cache.app.app_context():
            for key in list(app_cache.cache._cache.keys()):
                key_str = str(key)
                if cliente in key_str:
                    app_cache.delete(key)
                    cache_keys.append(key_str)
    except Exception as e:
        print(f"Erro ao limpar Flask cache: {str(e)}")
    
    print(f"Cache limpo para {cliente}. Chaves afetadas: {len(cache_keys)}")
    
    return len(cache_keys)