import dash_bootstrap_components as dbc
import html
from dash import html
from utils.formatters import formatar_percentual

# Define a base color palette with gradients
color = {
    'primary': '#001514',
    'secondary': '#0077B6',
    'accent': '#FF730e',
    'highlight': '#FFF8B0',
    'neutral': '#7A4E2D',
    'success': '#3CB371',
    'warning': '#f1c40f',
    'danger': '#e74c3c',
    'background': '#f9f9f9'
}

colors = [color['accent'], color['highlight'], color['neutral'], color['secondary']]

gradient_colors = {
    'blue_gradient': ['#0077B6', '#4DA6FF', '#89D2FF'],
    'orange_gradient': ['#FF730e', '#FF9E52', '#FFBD80'],
    'green_gradient': ['#2E8B57', '#3CB371', '#90EE90']
}

cores_segmento = {
    'Novos': color['highlight'],  
    'Recentes Baixo Valor': color['accent'],   
    'Recentes Alto Valor': color['warning'],    
    'Fiéis Baixo Valor': color['secondary'],    
    'Fiéis Alto Valor': gradient_colors['green_gradient'][2], 
    'Campeões': gradient_colors['green_gradient'][0],     
    'Inativos': color['primary'],    
    'Sumidos': color['neutral'] 
}

card_style = {
    "border-radius": "12px",
    "box-shadow": "0 4px 12px rgba(0, 0, 0, 0.05)",
    "border": "none",
    "background-color": "white",
    "overflow": "hidden",
    "transition": "transform 0.3s, box-shadow 0.3s",
}

card_header_style = {
    "background-color": "white",
    "border-bottom": f"1px solid rgba(0, 0, 0, 0.05)",
    "padding": "1rem 1.5rem",
    "font-weight": "600",
    "color": color['primary'],
    "font-size": "1.1rem"
}


card_body_style = {
    "padding": "1.5rem",
}

content_style = {
    "margin-left": "280px",
    "margin-right": "0",
    "padding": "2rem 2.5rem",
    "background-color": color['background'],
    "min-height": "100vh",
    "transition": "all 0.3s"
}

# Button styles
button_style = {
    "border-radius": "8px",
    "font-weight": "500",
    "box-shadow": "0 2px 5px rgba(0, 0, 0, 0.1)",
    "transition": "all 0.2s"
}

# Navigation link styles
nav_link_style = {
    "border-radius": "8px",
    "font-weight": "500",
    "transition": "all 0.2s",
    "color": "rgba(255, 255, 255, 0.8)",
    "padding": "0.8rem 1rem"
}

def create_card(header, body, className="mb-4 dashboard-card"):
    return dbc.Card(
        [
            dbc.CardHeader(header, style=card_header_style),
            dbc.CardBody(body, style=card_body_style)
        ],
        className=className,
        style=card_style
    )

def create_metric_tile(title, value, change=None, color=color['secondary']):
    change_component = None
    if change is not None:
        change_class = "change-positive" if change >= 0 else "change-negative"
        change_icon = "↑" if change >= 0 else "↓"
        
        # Formatar a mudança percentual com vírgula
        formatted_change = formatar_percentual(abs(change))
        
        change_component = html.Div([
            html.Span(f"{change_icon} {formatted_change}", className=change_class)
        ], className="metric-change")
    
    return html.Div([
        html.Div(title, className="metric-title"),
        html.Div(value, className="metric-value"),
        change_component
    ], className="metric-tile", style={"border-left-color": color})

def create_metric_row(metrics):
    return html.Div(
        [create_metric_tile(m["title"], m["value"], m.get("change"), m.get("color", color['secondary'])) for m in metrics],
        className="metric-container"
    )