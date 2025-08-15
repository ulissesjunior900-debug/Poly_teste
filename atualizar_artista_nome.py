import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db  # Importa o objeto app e db do seu app.py
from models import PagamentoRealizado
from utils import buscar_nome_artista

with app.app_context():
    pagamentos = PagamentoRealizado.query.all()
    count = 0
    for p in pagamentos:
        if not p.artista_nome:
            p.artista_nome = buscar_nome_artista(p.artista_id, p.tabela_artista) or "Artista não identificado"
            count += 1
    db.session.commit()
    print(f"{count} registros atualizados com artista_nome")
