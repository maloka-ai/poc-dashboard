# Contexto padrão - caso não haja contexto específico para um cliente
import openai

CONTEXTO_PADRAO = """
Este é um sistema de análise de clientes para varejo. O sistema fornece insights sobre segmentação de clientes,
métrica RFMA (Recência, Frequência, Valor Monetário e Antiguidade), análises de retenção, recorrência e previsão de compras.

As políticas de atendimento, entrega, pagamento e garantia são específicas para cada cliente.

Este contexto é utilizado para orientar análises e respostas sobre clientes, entregas, pagamentos e garantias.
"""

SEGMENTOS_PADRAO = """ 
    cond_novos = (df_seg['Recency'] <= 30) & (df_seg['Age'] <= 30) 
    
    cond_campeoes = (df_seg['Recency'] <= 180) & \
                    (df_seg['Frequency'] >= 7) & (df_seg['M_decil'] == 10) 
                    
    cond_fieis_baixo_valor = (df_seg['Recency'] <= 180) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 4) & (df_seg['M_decil'] <= 8) #
    
    cond_fieis_alto_valor = (df_seg['Recency'] <= 180) & (df_seg['Age'] >= 730) & \
                 (df_seg['Frequency'] >= 4) & (df_seg['M_decil'] > 8) 
                 
    cond_recentes_alto = (df_seg['Recency'] <= 180) & \
                         (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] > 6) 
                         
    cond_recentes_baixo = (df_seg['Recency'] <= 180) & \
                          (df_seg['Frequency'] >= 1) & (df_seg['M_decil'] <= 6)
    
    # Clientes menos ativos
    cond_sumidos = (df_seg['Recency'] >= 180) & (df_seg['Recency'] < 365) 
    cond_inativos = (df_seg['Recency'] >= 365)

    # Segmentação de Clientes

    Nossa estratégia de segmentação divide os clientes em 8 grupos distintos, baseados em comportamento de compra e valor:

    ## Clientes Ativos

    *Novos*: Clientes recentes (últimos 30 dias) e novos na base (menos de 30 dias).

    *Campeões*: Alto valor (top 10% em gastos) com frequência elevada (7+ compras) e compra nos últimos 6 meses.

    *Fiéis de Alto Valor*: Relacionamento longo (mais de 2 anos), frequência regular (4+ compras), alto valor (top 20% em gastos) e compra nos últimos 6 meses.

    *Fiéis de Baixo Valor*: Relacionamento longo (mais de 2 anos), frequência regular (4+ compras), valor moderado a baixo (até 80% em gastos) e compra nos últimos 6 meses.

    *Recentes de Alto Valor*: Compra nos últimos 6 meses, pelo menos 1 compra e valor significativo (top 40% em gastos).

    *Recentes de Baixo Valor*: Compra nos últimos 6 meses, pelo menos 1 compra e valor moderado a baixo (abaixo dos 60% em gastos).

    ## Clientes Menos Ativos

    *Sumidos*: Sem atividade entre 6 meses e 1 ano.

    *Inativos*: Sem atividade há mais de 1 ano.
"""

DATAFRAME_KEYS = """
{'DF': Index(['id_cliente', 'Recency', 'Frequency', 'Monetary', 'Age', 'R_range',
        'F_range', 'M_range', 'A_range', 'R_decil', 'F_decil', 'M_decil',
        'A_decil', 'Segmento', 'nome', 'cpf', 'email', 'telefone'],
       dtype='object'),
 'DF_RC_MENSAL': Index(['yearmonth', 'retained_customers', 'prev_total_customers',
        'retention_rate'],
       dtype='object'),
 'DF_RC_TRIMESTRAL': Index(['trimestre', 'trimestre_obj', 'total_customers', 'returning_customers',
        'new_customers', 'recurrence_rate'],
       dtype='object'),
 'DF_RC_ANUAL': Index(['ano', 'ano_obj', 'total_customers', 'returning_customers',
        'new_customers', 'retention_rate', 'new_rate', 'returning_rate'],
       dtype='object'),
 'DF_RT_ANUAL': Index(['cohort_year', 'period_index', 'num_customers', 'cohort_size',
        'retention_rate'],
       dtype='object'),
 'DF_PREVISOES': Index(['id_cliente', 'Recency', 'Frequency', 'Monetary', 'Age', 'R_range',
        'F_range', 'M_range', 'A_range', 'R_decil', 'F_decil', 'M_decil',
        'A_decil', 'Segmento', 'nome', 'cpf', 'email', 'telefone',
        'frequency_adjusted', 'recency_bg', 'T', 'predicted_purchases_30d',
        'categoria_previsao'],
"""

def classificar_pergunta(pergunta):
    prompt = f"""
    Você é um assistente que classifica perguntas sobre análise de clientes do varejo.
    Classifique a seguinte pergunta em uma das categorias de análise: 
    - "RFMA" (Recência, Frequência, Valor Monetário, Tempo de Primeira Compra)
    - "Recorrência" (Mensal, Trimestral ou Anual)
    - "Retenção Anual"
    - "Previsão de Retorno"
    - "Fora do Escopo" (caso não se encaixe nas categorias acima)

    Qualquer pergunta sobre clientes deve ser encaixada numa categoria que não "Fora do Escopo"

    Pergunta: "{pergunta}"
    Se "Fora do Escopo" for uma categoria, não deve haver nenhuma outra. Caso contrário, é possível ter uma ou mais categorias
    Formato de saída: categoria1 (obrigatória), categoria2 (opcional)... 
    """
    
    response = openai.chat.completions.create(
        model="gpt-4o", 
        messages=[{"role": "system", "content": prompt}],
        temperature=0.2
    )
    return [elemento.strip() for elemento in response.choices[0].message.content.split(",")]

def selecionar_dataframes(pergunta, categorias_pergunta):
    prompt = f"""
    Você é um assistente que seleciona DataFrames para responder perguntas sobre clientes no varejo.  
    Temos os seguintes DataFrames disponíveis e suas chaves:  

    {DATAFRAME_KEYS}

    Abaixo está uma lista de categorias extraídas das perguntas:
    {str(categorias_pergunta)}

    Abaixo está a pergunta que foi feita:
    {pergunta}

    Com base nisso, retorne uma lista dos nomes dos DataFrames que contêm informações relevantes.  
    Responda apenas com os nomes dos DataFrames, separados por vírgula.
    """

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}], 
        temperature=0.2
    )

    dataframes_usados = [df.strip() for df in response.choices[0].message.content.split(",")]
    return dataframes_usados