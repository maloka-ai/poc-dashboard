from datetime import datetime, timedelta
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
    
    print("Consultando a tabela vendas...")
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
    # df_vendas.to_excel("df_vendas.xlsx", index=False)

    ########################################################
    # consulta da tabela venda_itens
    ########################################################
    
    print("Consultando a tabela venda_item...")
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
    # df_venda_itens.to_excel("df_venda_itens.xlsx", index=False)

    ########################################################
    # consulta da tabela produto
    ########################################################
    
    print("Consultando a tabela venda_item...")
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
    
    # Exportar para Excel
    # df_produto.to_excel("df_produto.xlsx", index=False)

    ########################################################
    # consulta da tabela produto
    ########################################################
    
    print("Consultando a tabela venda_item...")
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
    df_compra.to_excel("df_compra.xlsx", index=False)

    # Fechar conexão
    conn.close()
    print("\nConexão com o banco de dados fechada.")

except Exception as e:
    print(f"Erro: {e}")
    print("\nVerifique se:")
    print("1. O PostgreSQL está rodando")
    print("2. O banco de dados existe")
    print("3. As credenciais de conexão estão corretas")

# ...existing code...

# Análise de vendas do último mês
print("\n" + "="*50)
print("ANÁLISE DE VENDAS DO ÚLTIMO MÊS")
print("="*50)

try:
    # Converter a coluna data_venda para datetime
    df_vendas['data_venda'] = pd.to_datetime(df_vendas['data_venda'])
    
    # Definir a data atual e a data de um mês atrás
    data_atual = datetime.now()
    data_um_mes_atras = data_atual - timedelta(days=15)
    
    print(f"Período: {data_um_mes_atras.strftime('%d/%m/%Y')} até {data_atual.strftime('%d/%m/%Y')}")
    
    # Filtrar vendas do último mês
    vendas_ultimo_mes = df_vendas[df_vendas['data_venda'] >= data_um_mes_atras]
    
    # Verificar se há vendas no período
    if len(vendas_ultimo_mes) == 0:
        print("Não foram encontradas vendas no último mês.")
    else:
        print(f"Total de vendas no último mês: {len(vendas_ultimo_mes)}")
        
        # Juntar as tabelas para obter as informações completas das vendas
        vendas_detalhadas = pd.merge(
            vendas_ultimo_mes, 
            df_venda_itens,
            on='id_venda',
            how='inner'
        )
        
        # Adicionar informações do produto
        vendas_completas = pd.merge(
            vendas_detalhadas,
            df_produto[['id_produto', 'nome']],
            on='id_produto',
            how='left'
        )
        
        # Criar um DataFrame resumido com as informações solicitadas
        resumo_vendas = vendas_completas[['id_venda', 'data_venda', 'id_produto', 'nome', 'quantidade', 
                                        'preco_bruto', 'desconto', 'total_item']]
        
        # Ordenar por data de venda
        resumo_vendas = resumo_vendas.sort_values('data_venda', ascending=False)
        
        # Resumo por produto
        resumo_por_produto = vendas_completas.groupby(['id_produto', 'nome']).agg({
            'quantidade': 'sum',
            'total_item': 'sum'
        }).reset_index().sort_values('total_item', ascending=False)
        
        # Resumo por dia
        resumo_por_dia = vendas_completas.groupby(vendas_completas['data_venda'].dt.date).agg({
            'id_venda': 'nunique',
            'quantidade': 'sum',
            'total_item': 'sum'
        }).reset_index()
        
        resumo_por_dia.columns = ['Data', 'Número de Vendas', 'Quantidade Itens', 'Valor Total']
        
        # Exibir resultados
        print("\nTop 10 Produtos Mais Vendidos (por valor total):")
        print(resumo_por_produto[['nome', 'quantidade', 'total_item']].head(10).to_string(index=False))
        
        print("\nResumo de Vendas por Dia:")
        print(resumo_por_dia.to_string(index=False))
        
        # Salvar os resultados em Excel
        nome_arquivo = f"vendas_ultimo_mes.xlsx"
        
        with pd.ExcelWriter(nome_arquivo) as writer:
            resumo_vendas.to_excel(writer, sheet_name='Vendas Detalhadas', index=False)
            resumo_por_produto.to_excel(writer, sheet_name='Resumo por Produto', index=False)
            resumo_por_dia.to_excel(writer, sheet_name='Resumo por Dia', index=False)
        
        print(f"\nResultados salvos no arquivo: {nome_arquivo}")

except Exception as e:
    print(f"Erro na análise de vendas: {e}")
