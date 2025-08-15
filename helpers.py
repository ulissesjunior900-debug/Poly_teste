import unicodedata
import os
import re
from flask import current_app
from werkzeug.utils import secure_filename
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

# ------------------- NORMALIZAÇÃO E NOMES -------------------

def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    texto = ''.join(c for c in texto if c.isalnum() or c.isspace())
    return texto.strip()

def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def sanitize_nome(nome):
    """Remove caracteres inválidos para nome de arquivo."""
    return ''.join(c if c.isalnum() or c in ('-', '_') else '_' for c in nome).strip('_')

# ------------------- FORMATOS E DATAS -------------------

def formatar_valor(valor, casas=2):
    """Formata valor com casas decimais e arredondamento financeiro."""
    return f"{Decimal(valor).quantize(Decimal('1.' + '0' * casas), rounding=ROUND_HALF_UP)}"

def calcular_data_cotacao(mes, ano):
    """Retorna a data de cotação no formato 15/MM/AAAA."""
    mes = int(mes)
    ano = int(ano)
    return f"15/{str(mes).zfill(2)}/{ano}"

def mes_nome(numero, abreviado=False):
    """Retorna o nome do mês por extenso ou abreviado (3 letras)."""
    nomes = [
        '', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
        'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
    ]
    if 1 <= numero <= 12:
        return nomes[numero][:3] if abreviado else nomes[numero]
    return ''

# ------------------- ARQUIVOS -------------------

def encontrar_coluna(df, nome_alvo):
    nome_alvo = normalizar_texto(nome_alvo)
    for col in df.columns:
        if normalizar_texto(col) == nome_alvo:
            return col
    return None

def salvar_arquivo_sp(arquivo, nome_arquivo):
    pasta_upload = current_app.config['UPLOAD_FOLDER']
    caminho_completo = os.path.join(pasta_upload, secure_filename(nome_arquivo))
    arquivo.save(caminho_completo)
    return caminho_completo

# ------------------- CÁLCULOS DISPONÍVEIS -------------------

def construir_calculos_disponiveis():
    from models import CalculoSalvo, CalculoEspecialSalvo, CalculoAssisaoSalvo

    nome_meses = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março',
        4: 'Abril', 5: 'Maio', 6: 'Junho',
        7: 'Julho', 8: 'Agosto', 9: 'Setembro',
        10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }

    calculos = []

    def processar_calculo(c, tipo):
        try:
            valor_eur = float(c.valor_eur or 0)
            valor_brl = float(c.valor_brl or 0)

            mes_int = None
            mes_str = str(c.mes).strip().capitalize() if c.mes else ''
            if mes_str.isdigit():
                mes_int = int(mes_str)
            else:
                mes_map = {
                    'Janeiro': 1, 'Fevereiro': 2, 'Março': 3,
                    'Abril': 4, 'Maio': 5, 'Junho': 6,
                    'Julho': 7, 'Agosto': 8, 'Setembro': 9,
                    'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
                }
                mes_int = mes_map.get(mes_str)

            mes_nome = nome_meses.get(mes_int, '-') if mes_int else '-'

            # Pega diretamente o nome do artista associado
            artista_nome = 'Artista desconhecido'
            if hasattr(c, 'artista') and c.artista:
                artista_nome = c.artista if isinstance(c.artista, str) else getattr(c.artista, 'nome', 'Artista desconhecido')
            elif hasattr(c, 'artista_especial') and c.artista_especial:
                artista_nome = getattr(c.artista_especial, 'nome', 'Artista desconhecido')

            herdeiros = []
            if hasattr(c, 'herdeiros') and isinstance(c.herdeiros, list):
                herdeiros = [
                    {'nome': h.get('nome', 'Herdeiro'), 'valor': float(h.get('valor', 0))}
                    for h in c.herdeiros
                ]

            return {
                'id': c.id,
                'tipo': tipo,
                'artista': artista_nome,
                'mes': mes_int,
                'mes_nome': mes_nome,
                'ano': str(c.ano or ''),
                'valor_eur': round(valor_eur, 4),
                'valor_brl': round(valor_brl, 2),
                'cotacao': float(getattr(c, 'cotacao', 0)),
                'status': getattr(c, 'status', 'aguardando').lower(),
                'data_pagamento': c.data_pagamento.strftime('%d/%m/%Y') if getattr(c, 'data_pagamento', None) else '',
                'herdeiros': herdeiros,
                'data_calculo': getattr(c, 'data_calculo', None)
            }

        except Exception as e:
            print(f"[ERRO] ao processar cálculo ID {getattr(c, 'id', '?')}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    for model, tipo in [
        (CalculoSalvo, 'normal'),
        (CalculoEspecialSalvo, 'especial'),
        (CalculoAssisaoSalvo, 'assisao')
    ]:
        try:
            registros = model.query.order_by(model.id.desc()).all()
            for c in registros:
                calc = processar_calculo(c, tipo)
                if calc:
                    calculos.append(calc)
        except Exception as e:
            print(f"[ERRO] ao consultar {model.__name__}: {str(e)}")

    print(f"[DEBUG] {len(calculos)} cálculos carregados.")
    return calculos