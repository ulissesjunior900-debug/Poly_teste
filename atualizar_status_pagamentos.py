import pytz
from datetime import datetime
from app import db
from app.models import PagamentoRealizado
from utils import buscar_nome_artista

def atualizar_status_pagamentos():
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    agora_brasil = datetime.now(tz_brasil)
    hoje_brasil = agora_brasil.date()

    pagamentos_agendados = PagamentoRealizado.query.filter_by(status='agendado').all()

    atualizados = []
    mensagens = []

    print(f"[INÍCIO] Data atual Brasil: {agora_brasil} (hoje: {hoje_brasil})")
    print(f"Pagamentos agendados encontrados: {len(pagamentos_agendados)}")

    for p in pagamentos_agendados:
        print(f"Verificando pagamento ID {p.id} com vencimento {p.vencimento} e status {p.status}")

        if p.vencimento and p.vencimento <= hoje_brasil:
            duplicados = PagamentoRealizado.query.filter(
                PagamentoRealizado.artista_id == p.artista_id,
                PagamentoRealizado.tabela_artista == p.tabela_artista,
                PagamentoRealizado.mes == p.mes,
                PagamentoRealizado.ano == p.ano,
                PagamentoRealizado.status == 'pago'
            ).all()

            nome_artista = buscar_nome_artista(p.artista_id, p.tabela_artista) or "Artista não identificado"
            print(f"Duplicados encontrados para {nome_artista}: {len(duplicados)}")

            if duplicados:
                msg = f"Duplicidade: {nome_artista} - {p.mes}/{p.ano} já possui pagamento registrado"
                mensagens.append(msg)
                print(msg)
            else:
                p.status = 'pago'
                p.data_pagamento = agora_brasil
                atualizados.append(p.id)
                print(f"Atualizado para PAGO: ID {p.id}")

    db.session.commit()
    print(f"Total de pagamentos atualizados: {len(atualizados)}")

    if mensagens:
        print("Mensagens:")
        for msg in mensagens:
            print(msg)

if __name__ == '__main__':
    atualizar_status_pagamentos()
