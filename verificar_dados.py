from app import app, db
from retroativos_models import TituloPeriodoValor

with app.app_context():
    registros = (
        db.session.query(TituloPeriodoValor)
        .filter(TituloPeriodoValor.artista == 'Accioly Neto')
        .order_by(TituloPeriodoValor.ano, TituloPeriodoValor.mes)
        .all()
    )
    for r in registros:
        print(f"{r.ano}-{r.mes:02d} | {r.titulo} | €{r.valor}")
