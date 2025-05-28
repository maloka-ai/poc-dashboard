import pandas as pd
import psycopg2
import dotenv
import os
import warnings
from datetime import datetime

warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

dotenv.load_dotenv()
# Nome do arquivo com timestamp para evitar sobrescrever arquivos anteriores
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
diretorio_atual = os.path.dirname(os.path.abspath(__file__))

# Configuração da conexão
try:
    # Conectar ao PostgreSQL
    print("Conectando ao banco de dados PostgreSQL...")
    conn = psycopg2.connect(
        host= os.getenv("DB_HOST"),
        database="demonstracao",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS"),
        port= os.getenv("DB_PORT")
    )
    
    print("Conexão estabelecida com sucesso!")
    
    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela vendas...")
    query = "SELECT * FROM maloka_analytics.segmentacao"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_segmentacao = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_segmentacao)
    num_colunas = len(df_segmentacao.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_segmentacao.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_segmentacao.head())
    
    # Exportar para Excel
    # df_segmentacao.to_excel("df_segmentacao.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")