import pandas as pd
import psycopg2
import dotenv
import os
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dotenv.load_dotenv()

# ========================================================
# DEFINA AQUI O ID DO PRODUTO PARA ANÁLISE
# ========================================================
ID_PRODUTO = 16344342  # <-- Altere este valor para o ID desejado
# ========================================================

def analisar_produto_especifico(id_produto):
    """
    Analisa o estoque diário de um produto específico pelo ID
    
    Args:
        id_produto: ID do produto para análise
    
    Returns:
        DataFrame com evolução diária e gráficos gerados
    """
    print(f"Iniciando análise para o produto ID: {id_produto}")
    
    try:
        # Conectar ao PostgreSQL
        print("Conectando ao banco de dados...")
        conn = psycopg2.connect(
            host="maloka-application-db.cwlsoqygi6rc.us-east-1.rds.amazonaws.com",
            dbname="add_v1",
            user="adduser",
            password="maloka2025",
            port="5432",
        )
        
        # Consultar dados do produto
        query_produto = f"SELECT * FROM produtos WHERE id_produto = {id_produto}"
        df_produto = pd.read_sql_query(query_produto, conn)
        
        if len(df_produto) == 0:
            print(f"ERRO: Produto com ID {id_produto} não encontrado.")
            return None
            
        nome_produto = df_produto['nome'].iloc[0]
        print(f"Produto encontrado: {nome_produto}")
        
        # Consultar movimentos do produto
        query_estoque = f"""
        SELECT * FROM estoquemovimentos 
        WHERE id_produto = {id_produto}
        ORDER BY data_movimento ASC
        """
        
        df_movimentos = pd.read_sql_query(query_estoque, conn)
        
        # Fechar conexão
        conn.close()
        
        if len(df_movimentos) == 0:
            print(f"ERRO: Nenhum movimento de estoque encontrado para o produto {id_produto}.")
            return None
            
        print(f"Encontrados {len(df_movimentos)} registros de movimento.")
        
        # Processamento dos dados
        df_movimentos['data_movimento'] = pd.to_datetime(df_movimentos['data_movimento'])
        
        # Determinar período de análise
        data_inicial = df_movimentos['data_movimento'].min()
        data_final = df_movimentos['data_movimento'].max()
        
        # Limitar a análise apenas ao último ano
        data_um_ano_atras = data_final - timedelta(days=365)
        data_inicial_original = data_inicial
        data_inicial = max(data_inicial, data_um_ano_atras)
        
        # Filtrar movimentos apenas do último ano
        df_movimentos = df_movimentos[df_movimentos['data_movimento'] >= data_inicial]
        
        print(f"Período de análise: {data_inicial.strftime('%d/%m/%Y')} até {data_final.strftime('%d/%m/%Y')}")
        print(f"Nota: Análise limitada ao último ano (dados originais começam em {data_inicial_original.strftime('%d/%m/%Y')})")
        
        # Criar DataFrame com todas as datas no intervalo
        todas_datas = pd.date_range(start=data_inicial, end=data_final, freq='D')
        df_diario = pd.DataFrame({'data': todas_datas})
        
        # Para cada data, encontrar o estoque mais recente (último movimento até essa data)
        estoque_diario = []
        
        # Obter o estoque inicial (último movimento antes do período analisado)
        movimentos_anteriores = df_movimentos[df_movimentos['data_movimento'] < data_inicial]
        estoque_inicial = 0
        if len(movimentos_anteriores) > 0:
            estoque_inicial = movimentos_anteriores.iloc[-1]['estoque_depois']
        
        for data in df_diario['data']:
            # Filtrar movimentos até esta data
            movimentos_ate_data = df_movimentos[df_movimentos['data_movimento'] <= data]
            
            if len(movimentos_ate_data) > 0:
                # Último movimento
                ultimo_movimento = movimentos_ate_data.iloc[-1]
                estoque = ultimo_movimento['estoque_depois']
                ultima_movimentacao = ultimo_movimento['data_movimento']
                tipo_ultimo_movimento = ultimo_movimento['tipo']
            else:
                estoque = estoque_inicial
                ultima_movimentacao = None
                tipo_ultimo_movimento = None
            
            estoque_diario.append({
                'data': data,
                'estoque': estoque,
                'ultima_movimentacao': ultima_movimentacao,
                'tipo_ultimo_movimento': tipo_ultimo_movimento
            })
        
        # Criar DataFrame com evolução diária
        df_evolucao_diaria = pd.DataFrame(estoque_diario)
        
        # Calcular estatísticas
        estoque_medio = df_evolucao_diaria['estoque'].mean()
        estoque_mediano = df_evolucao_diaria['estoque'].median()
        estoque_min = df_evolucao_diaria['estoque'].min()
        estoque_max = df_evolucao_diaria['estoque'].max()
        estoque_atual = df_evolucao_diaria['estoque'].iloc[-1]
        desvio_padrao = df_evolucao_diaria['estoque'].std()
        
        # Calcular tendência (primeiros 10% vs últimos 10%)
        n_amostras = len(df_evolucao_diaria)
        n_amostras_10pct = max(1, int(n_amostras * 0.1))
        
        estoque_inicial = df_evolucao_diaria['estoque'].iloc[:n_amostras_10pct].mean()
        estoque_final = df_evolucao_diaria['estoque'].iloc[-n_amostras_10pct:].mean()
        
        if estoque_inicial > 0:
            variacao_pct = ((estoque_final - estoque_inicial) / estoque_inicial) * 100
        else:
            variacao_pct = float('inf') if estoque_final > 0 else 0
            
        # Determinar tendência
        if variacao_pct > 10:
            tendencia = "CRESCIMENTO"
        elif variacao_pct < -10:
            tendencia = "REDUÇÃO"
        else:
            tendencia = "ESTÁVEL"
            
        # Calcular dias com zero estoque
        dias_zerados = sum(df_evolucao_diaria['estoque'] <= 0)
        pct_dias_zerados = (dias_zerados / len(df_evolucao_diaria)) * 100
        
        # Adicionar média móvel para suavizar flutuações
        df_evolucao_diaria['media_movel_7d'] = df_evolucao_diaria['estoque'].rolling(window=7, min_periods=1).mean()
        
        # Calcular métricas de giro e cobertura de estoque
        # 1. Calcular total de saídas no período
        saidas = df_movimentos[df_movimentos['tipo'] == 'S']
        total_saidas = saidas['quantidade'].sum() if len(saidas) > 0 else 0
        
        # 2. Calcular média diária de saídas (demanda média diária)
        dias_periodo = (data_final - data_inicial).days + 1
        demanda_media_diaria = total_saidas / dias_periodo if dias_periodo > 0 else 0
        
        # 3. Calcular índice de giro de estoque (anualizado)
        # Giro = (Total de saídas no período / Estoque médio) * (365 / dias no período)
        if estoque_medio > 0:
            giro_estoque = (total_saidas / estoque_medio) * (365 / dias_periodo)
        else:
            giro_estoque = float('inf') if total_saidas > 0 else 0
        
        # 4. Calcular cobertura de estoque (em dias)
        # Cobertura = Estoque atual / demanda média diária
        if demanda_media_diaria > 0:
            cobertura_estoque = estoque_atual / demanda_media_diaria
        else:
            cobertura_estoque = float('inf') if estoque_atual > 0 else 0
        
        # # Visualização dos dados
        # plt.figure(figsize=(16, 10))
        
        # # Criar figura com dois subplots
        # fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # # Gráfico de evolução diária do estoque
        # ax1.plot(df_evolucao_diaria['data'], df_evolucao_diaria['estoque'], 
        #         color='#3498db', linewidth=1.5, label='Estoque Diário', alpha=0.7)
        
        # # Adicionar média móvel
        # ax1.plot(df_evolucao_diaria['data'], df_evolucao_diaria['media_movel_7d'], 
        #         color='#e74c3c', linewidth=2, label='Média Móvel (7 dias)')
        
        # # Linha de estoque médio
        # ax1.axhline(y=estoque_medio, color='#2ecc71', linestyle='--', alpha=0.7, 
        #            label=f'Estoque Médio: {estoque_medio:.1f}')
        
        # # Destacar estoque atual
        # ax1.scatter(df_evolucao_diaria['data'].iloc[-1], estoque_atual, 
        #            color='#9b59b6', s=100, zorder=5, label=f'Estoque Atual: {estoque_atual:.0f}')
        
        # # Destacar valores extremos
        idx_min = df_evolucao_diaria['estoque'].idxmin()
        idx_max = df_evolucao_diaria['estoque'].idxmax()
        
        # ax1.scatter(df_evolucao_diaria['data'][idx_min], estoque_min, 
        #            color='#e67e22', s=80, zorder=5, label=f'Mínimo: {estoque_min:.0f}')
        # ax1.scatter(df_evolucao_diaria['data'][idx_max], estoque_max, 
        #             color='#16a085', s=80, zorder=5, label=f'Máximo: {estoque_max:.0f}')
        
        # # Formatação do gráfico principal
        # ax1.set_title(f'Evolução Diária do Estoque - {nome_produto} (ID: {id_produto})', fontsize=16)
        # ax1.set_ylabel('Quantidade em Estoque', fontsize=12)
        # ax1.grid(True, alpha=0.3)
        # ax1.legend(loc='upper left')
        
        # # Melhorar exibição das datas no eixo x
        dias_totais = (data_final - data_inicial).days
        
        # if dias_totais > 180:
        #     # Para períodos longos, mostrar apenas o primeiro dia de cada mês
        #     locator = plt.matplotlib.dates.MonthLocator()
        #     formatter = plt.matplotlib.dates.DateFormatter('%b/%Y')
        #     ax1.xaxis.set_major_locator(locator)
        #     ax1.xaxis.set_major_formatter(formatter)
        # elif dias_totais > 60:
        #     # Para períodos médios, mostrar a cada 15 dias
        #     locator = plt.matplotlib.dates.DayLocator(interval=15)
        #     formatter = plt.matplotlib.dates.DateFormatter('%d/%m/%Y')
        #     ax1.xaxis.set_major_locator(locator)
        #     ax1.xaxis.set_major_formatter(formatter)
        # else:
        #     # Para períodos curtos, mostrar todos os dias
        #     locator = plt.matplotlib.dates.DayLocator(interval=5)
        #     formatter = plt.matplotlib.dates.DateFormatter('%d/%m')
        #     ax1.xaxis.set_major_locator(locator)
        #     ax1.xaxis.set_major_formatter(formatter)
        
        # plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # # Gráfico de movimentações
        # movimentos_entrada = df_movimentos[df_movimentos['tipo'] == 'E']
        # movimentos_saida = df_movimentos[df_movimentos['tipo'] == 'S']
        
        # if len(movimentos_entrada) > 0:
        #     ax2.bar(movimentos_entrada['data_movimento'], movimentos_entrada['quantidade'], 
        #             width=0.8, color='green', alpha=0.7, label='Entradas')
        
        # if len(movimentos_saida) > 0:
        #     ax2.bar(movimentos_saida['data_movimento'], -movimentos_saida['quantidade'], 
        #             width=0.8, color='red', alpha=0.7, label='Saídas')
        
        # ax2.set_title('Movimentações de Estoque', fontsize=14)
        # ax2.set_ylabel('Quantidade', fontsize=12)
        # ax2.set_xlabel('Data', fontsize=12)
        # ax2.grid(True, alpha=0.3)
        # ax2.legend()
        
        # # Usar a mesma formatação de datas
        # ax2.xaxis.set_major_locator(locator)
        # ax2.xaxis.set_major_formatter(formatter)
        # plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # plt.tight_layout()
        
        # # Salvar gráfico
        # # nome_arquivo = f'estoque_produto_{id_produto}.png'
        # plt.savefig(nome_arquivo, dpi=300, bbox_inches='tight')
        # plt.close()
        
        # Salvar dados em Excel
        nome_arquivo_excel = f'estoque_produto_{id_produto}.xlsx'
        with pd.ExcelWriter(nome_arquivo_excel) as writer:
            df_evolucao_diaria.to_excel(writer, sheet_name='Estoque Diário', index=False)
            df_movimentos.to_excel(writer, sheet_name='Movimentações', index=False)
            
            # Adicionar planilha com resumo estatístico
            resumo = pd.DataFrame({
                'Métrica': [
                    'ID Produto', 'Nome Produto', 'Período Inicial', 'Período Final',
                    'Dias Analisados', 'Estoque Médio', 'Estoque Mediano', 'Estoque Mínimo',
                    'Estoque Máximo', 'Estoque Atual', 'Desvio Padrão',
                    'Dias com Estoque Zero', '% Dias com Estoque Zero', 
                    'Tendência', 'Variação no Período (%)',
                    'Total Saídas no Período', 'Demanda Média Diária',
                    'Giro de Estoque (anual)', 'Cobertura de Estoque (dias)'
                ],
                'Valor': [
                    id_produto, nome_produto, data_inicial.strftime('%d/%m/%Y'), 
                    data_final.strftime('%d/%m/%Y'), dias_totais + 1,
                    f"{estoque_medio:.2f}", f"{estoque_mediano:.2f}", 
                    f"{estoque_min:.2f}", f"{estoque_max:.2f}", f"{estoque_atual:.2f}",
                    f"{desvio_padrao:.2f}", dias_zerados, f"{pct_dias_zerados:.2f}%",
                    tendencia, f"{variacao_pct:.2f}%",
                    f"{total_saidas:.2f}", f"{demanda_media_diaria:.2f}",
                    f"{giro_estoque:.2f}", f"{cobertura_estoque:.2f}"
                ]
            })
            
            resumo.to_excel(writer, sheet_name='Resumo', index=False)
        
        # Exibir resumo no console
        print("\n" + "="*80)
        print(f"RESUMO DE ESTOQUE - {nome_produto}")
        print("="*80)
        print(f"Período analisado: {data_inicial.strftime('%d/%m/%Y')} a {data_final.strftime('%d/%m/%Y')} ({dias_totais + 1} dias)")
        print(f"Estoque Atual: {estoque_atual:.0f} unidades")
        print(f"Estoque Médio: {estoque_medio:.2f} unidades")
        print(f"Estoque Mediano: {estoque_mediano:.2f} unidades")
        print(f"Estoque Mínimo: {estoque_min:.0f} unidades (em {df_evolucao_diaria['data'][idx_min].strftime('%d/%m/%Y')})")
        print(f"Estoque Máximo: {estoque_max:.0f} unidades (em {df_evolucao_diaria['data'][idx_max].strftime('%d/%m/%Y')})")
        
        if dias_zerados > 0:
            print(f"ALERTA: Estoque zerado por {dias_zerados} dias ({pct_dias_zerados:.1f}% do período)")
        
        print(f"\nTendência do período: {tendencia} ({variacao_pct:.1f}%)")
        
        # Exibir informações de giro e cobertura
        print(f"\nMétricas de gestão de estoque:")
        print(f"Total de saídas no período: {total_saidas:.0f} unidades")
        print(f"Demanda média diária: {demanda_media_diaria:.2f} unidades/dia")
        print(f"Giro de estoque (anualizado): {giro_estoque:.2f} vezes/ano")
        print(f"Cobertura de estoque atual: {cobertura_estoque:.1f} dias")
        
        # Alertas adicionais baseados em giro e cobertura
        if cobertura_estoque < 15 and estoque_atual > 0:
            print("ALERTA: Cobertura de estoque baixa (<15 dias)!")
        elif cobertura_estoque > 120 and estoque_atual > 0:
            print("ALERTA: Possível excesso de estoque (>120 dias de cobertura)!")
            
        if giro_estoque < 1 and estoque_medio > 0:
            print("ALERTA: Giro de estoque muito baixo (<1 vez/ano)!")
        
        if tendencia == "REDUÇÃO" and estoque_atual < estoque_medio * 0.5:
            print("ALERTA: Estoque em tendência de queda e abaixo de 50% da média!")
        elif tendencia == "CRESCIMENTO" and estoque_atual > estoque_medio * 1.5:
            print("ALERTA: Possível excesso de estoque se formando!")
        
        print(f"\nArquivos gerados:")
        # print(f"- Gráfico: {nome_arquivo}")
        print(f"- Dados: {nome_arquivo_excel}")
        
        return df_evolucao_diaria
        
    except Exception as e:
        print(f"Erro na análise: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

# Executar a análise para o ID definido no topo do arquivo
if __name__ == "__main__":
    resultado = analisar_produto_especifico(ID_PRODUTO)
    
    # Verificar o que está no resultado
    if resultado is not None:
        print("\n" + "="*80)
        print("ANÁLISE DO RESULTADO RETORNADO")
        print("="*80)
        
        # Informações sobre o DataFrame
        print(f"Tipo do resultado: {type(resultado)}")
        print(f"Tamanho do DataFrame: {resultado.shape}")
        print(f"Colunas disponíveis: {', '.join(resultado.columns)}")
        
        # Mostrar as primeiras linhas do DataFrame
        print("\nPrimeiras 5 linhas do DataFrame:")
        print(resultado.head())
        
        # Verificar arquivo Excel gerado
        nome_arquivo_excel = f'estoque_produto_{ID_PRODUTO}.xlsx'
        if os.path.exists(nome_arquivo_excel):
            # Listar as sheets do Excel
            excel = pd.ExcelFile(nome_arquivo_excel)
            sheets = excel.sheet_names
            print(f"\nO arquivo Excel '{nome_arquivo_excel}' contém {len(sheets)} planilhas:")
            print(f"- {', '.join(sheets)}")
            
            # Exibir as primeiras linhas de cada sheet
            for sheet in sheets:
                df = pd.read_excel(nome_arquivo_excel, sheet_name=sheet)
                print(f"\nPrimeiras 5 linhas da planilha '{sheet}':")
                print(df.head())
    