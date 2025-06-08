from datetime import datetime
import pandas as pd
import dotenv
import os
import warnings
import psycopg2

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
        database="add",
        user= os.getenv("DB_USER"),
        password= os.getenv("DB_PASS"),
        port= os.getenv("DB_PORT")
    )
    
    print("Conexão estabelecida com sucesso!")
    
    ########################################################
    # consulta da tabela vendas
    ########################################################
    
    print("Consultando a tabela VENDAS...")
    query = "SELECT * FROM maloka_core.venda"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_vendas = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_vendas)
    num_colunas = len(df_vendas.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_vendas.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_vendas.head())
    
    # Exportar para Excel
    # df_vendas.to_excel("df_vendas_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela venda_itens
    ########################################################
    
    print("Consultando a tabela VENDA_ITEM...")
    query = "SELECT * FROM maloka_core.venda_item"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_venda_itens = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_venda_itens)
    num_colunas = len(df_venda_itens.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_venda_itens.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_venda_itens.head())
    
    # Exportar para Excel
    # df_venda_itens.to_excel("df_venda_itens_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela produto
    ########################################################
    
    print("Consultando a tabela PRODUTO...")
    query = "SELECT * FROM maloka_core.produto"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_produto = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_produto)
    num_colunas = len(df_produto.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_produto.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_produto.head())
    
    # Exportar para CSV
    # df_produto.to_csv("df_produto_BD.csv", index=False)

    ########################################################
    # consulta da tabela compra
    ########################################################
    
    print("Consultando a tabela COMPRA...")
    query = "SELECT * FROM maloka_core.compra"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_compra = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_compra)
    num_colunas = len(df_compra.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_compra.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_compra.head())
    
    # Exportar para Excel
    # df_compra.to_excel("df_compra_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela fornecedor
    ########################################################
    
    print("Consultando a tabela FORNECEDOR...")
    query = "SELECT * FROM maloka_core.fornecedor"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_fornecedor = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_fornecedor)
    num_colunas = len(df_fornecedor.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_fornecedor.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_fornecedor.head())
    
    # Exportar para Excel
    # df_fornecedor.to_excel("df_fornecedor_BD.xlsx", index=False)

    ########################################################
    # consulta da tabela estoque_movimento
    ########################################################
    
    print("Consultando a tabela ESTOQUE_MOVIMENTO...")
    query = "SELECT * FROM maloka_core.estoque_movimento"
    
    # Carregar os dados diretamente em um DataFrame do pandas
    df_estoque_movimento = pd.read_sql_query(query, conn)
    
    # Informações sobre os dados
    num_registros = len(df_estoque_movimento)
    num_colunas = len(df_estoque_movimento.columns)
    
    print(f"Dados obtidos com sucesso! {num_registros} registros e {num_colunas} colunas.")
    print(f"Colunas disponíveis: {', '.join(df_estoque_movimento.columns)}")
    
    # Exibir uma amostra dos dados
    print("\nPrimeiros 5 registros para verificação:")
    print(df_estoque_movimento.head())
    
    # Exportar para Excel
    # df_estoque_movimento.to_excel("df_estoque_movimento_BD.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")
