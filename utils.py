# utils.py

import unicodedata
from flask import current_app
from sqlalchemy.orm import Session

from models import (
    db,
    Artista,
    ArquivoImportado,
    CalculoSalvo,
    ArtistaEspecial,
    TituloEspecial,
    Cotacao,
    CalculoEspecialSalvo,
    CalculoAssisaoSalvo,
    SPImportada,
    SolicitacaoPagamento,
    PagamentoRealizado,
    Herdeiro,
    Usuario,
    Transacao,
    ArtistaInfo,
)


def remover_acentos(texto):
    """
    Remove acentos e normaliza a string.
    Exemplo: "São João" → "Sao Joao"
    """
    if not isinstance(texto, str):
        return texto
    return ''.join(
        c for c in unicodedata.normalize('NFKD', texto)
        if not unicodedata.combining(c)
    )

def buscar_nome_artista(artista_id, tabela):
    if not artista_id:
        return None
    try:
        artista_id_int = int(artista_id)
    except (ValueError, TypeError):
        return None

    try:
        if tabela in ['norm', 'normal']:
            artista = Artista.query.get(artista_id_int)
        elif tabela in ['esp', 'especial']:
            artista = ArtistaEspecial.query.get(artista_id_int)
        elif tabela in ['ass', 'assisao']:
            artista = ArtistaEspecial.query.get(artista_id_int)
        else:
            return None
        return artista.nome if artista else None
    except Exception as e:
        print(f"[ERRO buscar_nome_artista] ID: {artista_id}, tabela: {tabela} → {e}")
        return None

def atualizar_historico_pagamentos():
    from datetime import datetime
    import pytz
    from app import db
    from models import PagamentoRealizado
    from utils import buscar_nome_artista

    tz_brasil = pytz.timezone('America/Sao_Paulo')
    hoje = datetime.now(tz_brasil).date()

    pagamentos = PagamentoRealizado.query.all()
    atualizados_nome = 0
    atualizados_status = 0

    print(f"[DEBUG] Pagamentos encontrados: {len(pagamentos)}")

    for p in pagamentos:
        nome_correto = buscar_nome_artista(p.artista_id, p.tabela_artista)
        if nome_correto and p.artista_nome != nome_correto:
            print(f"[DEBUG] Atualizando nome ID {p.id}: '{p.artista_nome}' → '{nome_correto}'")
            p.artista_nome = nome_correto
            atualizados_nome += 1

        if p.status.strip().lower() == 'agendado' and p.vencimento and p.vencimento <= hoje:
            print(f"[DEBUG] Atualizando status para PAGO ID {p.id} (venc: {p.vencimento})")
            p.status = 'pago'
            p.data_pagamento = datetime.now(tz_brasil)
            atualizados_status += 1

    try:
        db.session.commit()
        print(f"[DEBUG] Commit realizado com {atualizados_nome} nomes e {atualizados_status} status atualizados")
    except Exception as e:
        db.session.rollback()
        print(f"[ERRO] Commit falhou: {e}")
        raise e

    return atualizados_nome, atualizados_status

