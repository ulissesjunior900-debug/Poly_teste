from app import app, db
from retroativos_models import RetroativoCalculado, RetroativoArquivo, RetroativoTitulo, TituloPeriodoValor

with app.app_context():
    print("✅ Criando tabelas no banco retroativos...")

    # Acessa o engine correto pelo bind name
    engine = db.engines['retroativos']

    # Cria as tabelas no bind correto
    RetroativoCalculado.__table__.create(bind=engine, checkfirst=True)
    RetroativoArquivo.__table__.create(bind=engine, checkfirst=True)
    RetroativoTitulo.__table__.create(bind=engine, checkfirst=True)
    TituloPeriodoValor.__table__.create(bind=engine, checkfirst=True)

    print("✅ Tabelas criadas com sucesso no banco retroativos!")
