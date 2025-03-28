# Importar as funções principais para facilitar o acesso
from data_load.client_data import (
    get_available_clients,
    get_available_data_types,
    get_client_context,
    get_client_segmentos,
    validate_client_data,
    process_upload
)
from data_load.data_loader import load_data