# POC Dashboard

## Visão Geral
Este projeto implementa um dashboard interativo para análise e monitoramento de clientes, vendas, estoque e interações. Utilizando [Dash](https://plotly.com/dash/), [Flask](https://flask.palletsprojects.com/), e [Plotly](https://plotly.com/), o sistema integra dados de diversas fontes (arquivos, banco de dados PostgreSQL, etc.) para fornecer insights e auxiliar na tomada de decisões estratégicas.

## Funcionalidades Principais
- **Segmentação de Clientes**: Análise de padrões de compra, RFMA, recorrência, retenção e previsão.
- **Vendas**: Visualização do faturamento anual, vendas atípicas e evolução percentual.
- **Estoque**: Análise de criticidade, identificação de produtos inativos e recomendações de compra.
- **Interação**: Chat Assistente integrado para consultas e suporte analítico.
- **Autenticação**: Sistema de login/logout com gerenciamento de sessão e cache.

## Estrutura do Projeto
```
/poc-dashboard
├── application.py    # Arquivo principal com rotas e configuração do servidor
├── wsgi.py           # Arquivo para deploy com Gunicorn
├── README.md         # Documentação do projeto
├── requirements.txt  # Dependências do projeto
├── auth/             # Módulos de autenticação
├── dados/            # Processamento e carregamento de dados
├── layouts/          # Componentes e layouts do dashboard
├── callbacks/        # Callbacks do Dash para interatividade
├── utils/            # Funções utilitárias e helpers
└── assets/           # Arquivos estáticos (CSS, imagens)
```
