# retroativos_models.py
from extensions import db
from datetime import datetime


class RetroativoCalculado(db.Model):
    __tablename__ = 'retroativos_calculados'
    __bind_key__ = 'retroativos'

    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(255), nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)  # Corrigido
    titulo = db.Column(db.String(255), nullable=True)
    lucro_liquido = db.Column(db.Numeric(20, 8), nullable=False)
    origem_planilha = db.Column(db.String(255), nullable=True)


class RetroativoArquivo(db.Model):
    __tablename__ = 'retroativos_arquivos'
    __bind_key__ = 'retroativos'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255))
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)  # Corrigido
    registros_validos = db.Column(db.Integer, default=0)
    registros_invalidos = db.Column(db.Integer, default=0)
class RetroativoTitulo(db.Model):
    __tablename__ = "retroativos_titulos"

    id = db.Column(db.Integer, primary_key=True)
    artista_nome = db.Column(db.String(255), nullable=False)
    titulo = db.Column(db.String(255), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('artista_nome', 'titulo', name='uix_artista_titulo'),
    )

class TituloPeriodoValor(db.Model):
    __tablename__ = 'titulo_periodo_valor'

    id = db.Column(db.Integer, primary_key=True)
    artista = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    ano = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=True)
    origem_planilha = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
