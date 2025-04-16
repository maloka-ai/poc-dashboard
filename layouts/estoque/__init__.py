from layouts.estoque.produtos import get_produtos_layout
from layouts.estoque.produtos_inativos import get_produtos_inativos_layout
from layouts.estoque.giro_estoque import get_giro_estoque_layout

# Exporta todas as funções de layout
__all__ = [
    'get_produtos_layout',
    'get_produtos_inativos_layout',
    'get_giro_estoque_layout',
]