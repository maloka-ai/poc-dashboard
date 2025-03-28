def formatar_moeda(valor):
    """Formata um valor monetário no padrão brasileiro: R$ 1.234,56"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formatar_percentual(valor):
    """Formata um valor percentual no padrão brasileiro: 12,5%"""
    return f"{valor:.2f}%".replace(".", ",")

def formatar_numero(valor, decimais=0):
    """Formata um número com separador de milhares no padrão brasileiro"""
    formato = f"{{:,.{decimais}f}}"
    return formato.format(valor).replace(",", "X").replace(".", ",").replace("X", ".")

# Função específica para lidar com o formato ISO que você está recebendo
def format_iso_date(date_str):
    if date_str == '-' or not date_str:
        return '-'
    
    try:
        # Específico para o formato que você está recebendo: 2025-01-06T00:00:00.000
        if isinstance(date_str, str) and 'T' in date_str:
            # Pega apenas a parte da data (antes do T)
            date_part = date_str.split('T')[0]
            # Divide por traços para obter ano, mês e dia
            year, month, day = date_part.split('-')
            return f"{day}/{month}/{year}"
            
        # Se for uma string de data em outro formato
        elif isinstance(date_str, str):
            from datetime import datetime
            try:
                # Tenta vários formatos comuns
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        return date_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        continue
            except:
                return date_str
                
        # Se for um objeto datetime
        elif hasattr(date_str, 'strftime'):
            return date_str.strftime('%d/%m/%Y')
            
        # Retorna o original se nenhum método funcionar
        return date_str
    except Exception as e:
        # Em caso de qualquer erro, retorne o original
        return f"{date_str}"