import io
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from dash.dependencies import Input, Output, State
from dash import callback_context

from utils import formatar_moeda, color, gradient_colors

def register_faturamento_anual_callbacks(app):
    """
    Registra os callbacks para o gráfico de faturamento anual.
    """
    @app.callback(
        Output('grafico-lojas-mensal', 'figure'),
        [Input('dropdown-ano-lojas', 'value'),
        Input('dropdown-loja-mensal', 'value')],
        [State('store-faturamento-data', 'data')]
    )
    def update_grafico_lojas(ano_selecionado, lojas_selecionadas, data):
        if not data or not ano_selecionado:
            # Retorna figura vazia se não houver dados
            return {}
        
        try:
            df_mensal_lojas = pd.read_json(io.StringIO(data["df_fat_Mensal_lojas"]), orient='split')
            
            # Converter valores de faturamento para numérico (caso estejam como string)
            df_mensal_lojas['total_venda'] = pd.to_numeric(df_mensal_lojas['total_venda'].astype(str).str.replace(',', '.'), errors='coerce')
            
            # Filtrar os dados pelo ano selecionado
            df_filtrado = df_mensal_lojas[df_mensal_lojas['Ano'] == ano_selecionado]

            # Verificar se existem valores duplicados na combinação Mês/Loja
            if not df_filtrado.empty:
                duplicated = df_filtrado.duplicated(subset=['Mês', 'id_loja'], keep=False)
                if duplicated.any():
                    df_filtrado = df_filtrado.groupby(['Mês', 'id_loja'], as_index=False).agg({'total_venda': 'sum'})
            

            # Aplicar filtro por loja APENAS se houver lojas selecionadas
            # Se lojas_selecionadas estiver vazio, mostrar todas as lojas
            if lojas_selecionadas and len(lojas_selecionadas) > 0 and not df_filtrado.empty:
                df_filtrado = df_filtrado[df_filtrado['id_loja'].isin(lojas_selecionadas)]
                
                # Se após o filtro não houver dados, retorne um gráfico vazio
                if df_filtrado.empty:
                    fig = go.Figure()
                    fig.add_annotation(
                        text="Não há dados para as lojas selecionadas neste ano",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16)
                    )
                    fig.update_layout(height=500)
                    return fig
            
            cores_fixas_lojas = {
                1: "orange",
                2: "darkred",
                3: gradient_colors['blue_gradient'][0],
                4: gradient_colors['green_gradient'][0],
                5: color['accent'],
                6: gradient_colors['blue_gradient'][2],
                7: gradient_colors['green_gradient'][2],
            }
            
            # Usar cores fixas se a loja estiver no dicionário, ou gerar cores dinâmicas para outras lojas
            lojas_unicas = df_mensal_lojas['id_loja'].unique()
            cores_lojas = {}
            
            for loja in lojas_unicas:
                if isinstance(loja, (int, float)) and int(loja) in cores_fixas_lojas:
                    cores_lojas[loja] = cores_fixas_lojas[int(loja)]
                elif str(loja).isdigit() and int(str(loja)) in cores_fixas_lojas:
                    cores_lojas[loja] = cores_fixas_lojas[int(str(loja))]
                else:
                    # Usar um índice no conjunto de cores padrão do Plotly para lojas não mapeadas
                    indice_cor = list(lojas_unicas).index(loja) % len(px.colors.qualitative.Bold)
                    cores_lojas[loja] = px.colors.qualitative.Bold[indice_cor]
                
            # Criar figura para o gráfico de barras usando o Graph Objects para mais controle
            fig = go.Figure()
            
            # Adicionar barras para cada loja separadamente
            for loja in df_filtrado['id_loja'].unique():
                df_loja = df_filtrado[df_filtrado['id_loja'] == loja]
                
                # Verificar se a coluna 'nome' existe e usar o nome da loja
                if 'nome' in df_loja.columns and not df_loja.empty:
                    nome_loja = df_loja['nome'].iloc[0]
                else:
                    nome_loja = f"Loja {loja}"
                
                # Mantém os valores formatados para o hover, mas não mostra nas barras
                valores_formatados = [formatar_moeda(valor) for valor in df_loja['total_venda']]
                
                fig.add_trace(go.Bar(
                    x=df_loja['Mês'],
                    y=df_loja['total_venda'],
                    name=nome_loja,
                    marker_color=cores_lojas.get(loja, '#333333'),
                    textposition='none',  # Oculta o texto nas barras
                    customdata=valores_formatados,  # Mantém os dados formatados para o hover
                    hovertemplate='<b>Loja:</b> %{fullData.name}<br><b>Mês:</b> %{x}<br><b>Faturamento:</b> %{customdata}<extra></extra>'
                ))

            # Título dinâmico baseado na seleção
            if not lojas_selecionadas or len(lojas_selecionadas) == 0:
                titulo = f"Faturamento Mensal por Loja ({ano_selecionado})"
            elif len(lojas_selecionadas) > 1:
                titulo = f"Faturamento Mensal: {len(lojas_selecionadas)} Lojas Selecionadas ({ano_selecionado})"
            else:
                nome_loja_selecionada = df_filtrado['nome'].iloc[0] if not df_filtrado.empty else "Loja"
                titulo = f"Faturamento Mensal: {nome_loja_selecionada} ({ano_selecionado})"
            
            # Atualizar o título no layout
            fig.update_layout(title=titulo)
            
            # Configurar layout do gráfico
            fig.update_layout(
                barmode='group',  # Forçar agrupamento
                xaxis_title="Mês",
                yaxis_title="Faturamento (R$)",
                title=f"Faturamento Mensal por Loja ({ano_selecionado})",
                margin=dict(t=70, b=50, l=50, r=50),
                height=500,
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    title_text="Lojas:",
                    font=dict(size=12),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='rgba(0,0,0,0.1)',
                    borderwidth=1
                ),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                bargap=0.15,
                bargroupgap=0.05
            )
            
            # Definir rótulos dos meses no eixo x
            meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            
            fig.update_xaxes(
                range=[0.5, 12.5],
                tickmode='array',
                tickvals=list(range(1, 13)),
                ticktext=meses,
                title_font=dict(size=14, family="Montserrat"),
                gridcolor='rgba(0,0,0,0.05)'
            )
            
            fig.update_yaxes(
                title_font=dict(size=14, family="Montserrat"),
                gridcolor='rgba(0,0,0,0.05)',
                tickformat=",.2f"
            )
            
            return fig
        
        except Exception as e:
            # Em caso de erro, retorne um gráfico com mensagem de erro
            fig = go.Figure()
            fig.add_annotation(
                text=f"Erro ao carregar os dados: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16)
            )
            fig.update_layout(height=500)
            return fig
        
    @app.callback(
        Output('grafico-faturamento-diario', 'figure'),
        [Input('dropdown-periodo-diario', 'value'),
        Input('store-faturamento-data', 'data')]
    )
    def update_grafico_diario(periodo_selecionado, data):
        # Verificar se temos dados
        if data is None or 'df_fat_Diario' not in data:
            # Retornar figura vazia com mensagem de erro
            fig = go.Figure()
            fig.add_annotation(
                text="Dados não disponíveis",
                showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # Ler dados
        df_diario = pd.read_json(io.StringIO(data["df_fat_Diario"]), orient='split')
        
        # Converter valores com vírgula para ponto
        df_diario['total_venda'] = df_diario['total_venda'].astype(str).str.replace(',', '.').astype(float)
        
        # Filtrar pelo período selecionado
        df_filtrado = df_diario[df_diario['Período'] == periodo_selecionado] if periodo_selecionado else pd.DataFrame()
        
        # NOVA FUNCIONALIDADE: Filtrar para remover dias sem faturamento (zero ou nulos)
        df_filtrado = df_filtrado[df_filtrado['total_venda'] > 0]
        
        # Garantir que os dias estejam em ordem
        df_filtrado = df_filtrado.sort_values('Dia')
        
        # Calcular média apenas dos dias com faturamento
        media_diaria = df_filtrado['total_venda'].mean() if not df_filtrado.empty else 0
        
        # Criar figura
        fig = go.Figure()
        
        # Adicionar linha principal com pontos
        fig.add_trace(go.Scatter(
            x=df_filtrado['Dia'],
            y=df_filtrado['total_venda'],
            mode='lines+markers',
            name='Faturamento Diário',
            line=dict(color=color['accent'], width=3),
            marker=dict(size=8, color=color['accent'], line=dict(width=2, color='white')),
            hovertemplate='Dia %{x}: ' + '%{y:,.2f}'.replace(',', '.') + '<extra></extra>'
        ))
        
        # Adicionar rótulos de valores
        for dia, valor in zip(df_filtrado['Dia'], df_filtrado['total_venda']):
            fig.add_annotation(
                x=dia,
                y=valor,
                text=formatar_moeda(valor),
                showarrow=False,
                yshift=15,
                font=dict(size=10, family="Montserrat")
            )
        
        # Configuração do layout
        fig.update_layout(
            xaxis_title="Dia do Mês",
            yaxis_title="Faturamento (R$)",
            margin=dict(t=50, b=50, l=50, r=50),
            height=500,
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        # Configuração dos eixos
        fig.update_xaxes(
            # Mostrar apenas os dias que têm dados
            tickmode='array',
            tickvals=df_filtrado['Dia'].tolist(),
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        fig.update_yaxes(
            title_font=dict(size=14, family="Montserrat"),
            gridcolor='rgba(0,0,0,0.05)'
        )
        
        return fig