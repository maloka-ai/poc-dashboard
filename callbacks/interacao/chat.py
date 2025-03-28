from dash import Input, Output, State, html, dcc
import io
import pandas as pd
import time
import openai

from utils import classificar_pergunta, selecionar_dataframes, CONTEXTO_PADRAO, SEGMENTOS_PADRAO

def register_chat_callbacks(app):
    """
    Registra todos os callbacks relacionados ao chat.
    
    Args:
        app: A instância do aplicativo Dash
    """
    
    @app.callback(
    Output('chat-history', 'children'),
    Output('user-input', 'value'),
    Input('submit-button', 'n_clicks'),
    State('user-input', 'value'),
    State('chat-history', 'children'),
    State('selected-data', 'data'),
    State('selected-client', 'data'),
    prevent_initial_call=True
    )
    def responde(n_clicks, user_input, chat_history, data, selected_client):
        if n_clicks is None or not user_input:
            return chat_history, ''

        if chat_history is None:
            chat_history = []  # Define chat_history como uma lista vazia

        # Add user message with styled container
        user_message = html.Div([
            html.Div([
                html.Strong("Você: "),
                html.Span(user_input)
            ], className="chat-message user-message")
        ], style={"display": "flex", "justifyContent": "flex-end", "marginBottom": "1rem"})
        
        chat_history.append(user_message)
        
        # Add typing indicator while processing
        typing_indicator = html.Div([
            html.Div([
                html.Span("Pensando", style={"fontStyle": "italic"}),
                html.Span("...", id="typing-dots")
            ], className="chat-message bot-message", style={"backgroundColor": "#f0f0f0"})
        ], style={"display": "flex", "justifyContent": "flex-start", "marginBottom": "1rem"})
        
        chat_history.append(typing_indicator)

        # 1. Classificar a pergunta para extrair as categorias
        start_time = time.time()
        categorias = classificar_pergunta(user_input)
        
        # 2. Selecionar os DataFrames relevantes com base nas categorias
        dataframes = selecionar_dataframes(user_input, categorias)
        
        # 3. Importar dataframes
        if data:
            #segmentacao de clientes
            df = pd.read_json(io.StringIO(data["df"]), orient='split') if data.get("df") else None
            df_RC_Mensal = pd.read_json(io.StringIO(data["df_RC_Mensal"]), orient='split') if data.get("df_RC_Mensal") else None
            df_RC_Trimestral = pd.read_json(io.StringIO(data["df_RC_Trimestral"]), orient='split') if data.get("df_RC_Trimestral") else None
            df_RC_Anual = pd.read_json(io.StringIO(data["df_RC_Anual"]), orient='split') if data.get("df_RC_Anual") else None
            df_RT_Anual = pd.read_json(io.StringIO(data["df_RT_Anual"]), orient='split') if data.get("df_RT_Anual") else None
            df_Previsoes = pd.read_json(io.StringIO(data["df_Previsoes"]), orient='split') if data.get("df_Previsoes") else None

            #estoque
            df_Vendas_Atipicas = pd.read_json(io.StringIO(data["df_Vendas_Atipicas"]), orient='split') if data.get("df_Vendas_Atipicas") else None
            df_relatorio_produtos = pd.read_json(io.StringIO(data["df_relatorio_produtos"]), orient='split') if data.get("df_relatorio_produtos") else None

            #faturamento
            df_fat_Anual = pd.read_json(io.StringIO(data["df_fat_Anual"]), orient='split') if data.get("df_fat_Anual") else None
            df_fat_Anual_Geral = pd.read_json(io.StringIO(data["df_fat_Anual_Geral"]), orient='split') if data.get("df_fat_Anual_Geral") else None
            df_fat_Mensal = pd.read_json(io.StringIO(data["df_fat_Mensal"]), orient='split') if data.get("df_fat_Mensal") else None

            # Obter contexto específico do cliente
            company_context = data.get("company_context", CONTEXTO_PADRAO)
            segmentos_context = data.get("segmentos_context", SEGMENTOS_PADRAO)

            # 4. Construir o prompt com os dados disponíveis
            prompt = f"""
            Você é um assistente de análise de dados para um sistema de varejo.
            A pergunta é: "{user_input}"
            Dados disponíveis:
            - Contexto do negócio: {company_context}
            - Dataframes considerados úteis: {dataframes}
            - Categorias identificadas para a pergunta: {categorias}
            - Dataframes: {
                df, df_RC_Mensal, 
                df_RC_Trimestral, 
                df_RC_Anual, 
                df_RT_Anual, 
                df_Previsoes, 
                df_Vendas_Atipicas, 
                df_fat_Anual, 
                df_fat_Anual_Geral, 
                df_fat_Mensal, 
                df_relatorio_produtos
            }
            
            Perguntas sobre segmentos de clientes:
            - Para perguntas sobre os segmentos dos clientes, considere: {segmentos_context}
            
            Regras sobre a resposta final:
            - Responda de forma clara e objetiva com linguagem natural
            - Na resposta final, não deve haver nomes de dataframes, apenas a análise feita em cima dos dados disponíveis 
            - Considere que quem está falando com você é algum funcionário da empresa {selected_client}
            - Formate valores monetários com R$ e separadores de milhar
            - Evite respostas genéricas
            - Seja direto ao ponto e forneça números e insights específicos
            - Limite sua resposta a no máximo 4 parágrafos
            """
            
            # 4. Obter a resposta do modelo
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                temperature=0.4,
            )
            
            # Extrai a resposta do GPT-4
            gpt_response = response.choices[0].message.content
        else:
            # Resposta caso não existam dados disponíveis
            gpt_response = """
            Não há dados disponíveis para análise. Por favor, certifique-se de que:
            
            1. Você selecionou corretamente o cliente e tipo de dados no menu lateral
            2. Os arquivos necessários estão presentes para o cliente selecionado
            3. O sistema conseguiu carregar os dados sem erros
            
            Caso o problema persista, entre em contato com o suporte técnico.
            """
        
        # Calcular o tempo de resposta
        response_time = time.time() - start_time
        
        # Remove typing indicator and add the bot response with styled container
        chat_history = chat_history[:-1]  # Remove typing indicator
        
        bot_message = html.Div([
            html.Div([
                html.Strong("Assistente: "),
                html.Div(dcc.Markdown(gpt_response)),
                html.Div(f"Tempo de resposta: {response_time:.2f}s", 
                        style={"fontSize": "0.8rem", "color": "#888", "marginTop": "0.5rem", "textAlign": "right"})
            ], className="chat-message bot-message")
        ], style={"display": "flex", "justifyContent": "flex-start", "marginBottom": "1rem"})
        
        chat_history.append(bot_message)

        return chat_history, ''