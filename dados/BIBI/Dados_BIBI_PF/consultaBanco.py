import pandas as pd
import psycopg2
import dotenv
import os
import numpy as np
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dotenv.load_dotenv()
caminho_arquivo_completo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analise_curva_cobertura.xlsx")

try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("DB_HOST"),
        database="bibicell",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS"),
        port= os.getenv("DB_PORT"),
    )
    
    print("Conexão estabelecida com sucesso!")

    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela VENDAS...")
    query = "" \
    "select count (distinct id_produto) " \
    "as qt_produtos from " \
    "maloka_core.produto" \
    ""
    
    # Carregar os dados diretamente em um DataFrame do pandas
    teste = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(teste)
    num_colunas = len(teste.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(teste.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(teste.head())
    
    # EXPORTAR EXCEL
    # teste.to_excel("teste.xlsx", index=False)

    conn.close()
    print("\nConexão com o banco de dados fechada.")
except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")