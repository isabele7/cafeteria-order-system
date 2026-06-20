from app.models import Pagamento, Pedido, StatusPagamento, StatusPedido, TipoPedido
from app.services.pedido_service import OperacoesPedido
from app.services import pagamento_service

# Testa se o pagamento confirmado atualiza o status do pedido e do pagamento corretamente
def test_pagamento_confirmado(db, produtos_base, monkeypatch):
    pedido = OperacoesPedido.criar_pedido(db)
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produtos_base["cafe"].id, 2, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    def stub_sucesso(pagamento, db_session):
        return True

    monkeypatch.setattr(
        pagamento_service.OperacoesPagamento,
        "processar_pagamento",
        staticmethod(stub_sucesso),
    )

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db)
    assert ok, msg

    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    pagamento = db.query(Pagamento).filter(Pagamento.pedido_id == pedido.id).first()

    assert (pedido_after.status, pagamento is not None, pagamento.status, pagamento.valor) == (
        StatusPedido.PAGO, True, StatusPagamento.CONFIRMADO, pedido_after.total,
    )

# Testa se o pagamento falho mantém o status do pedido como criado e do pagamento como falhou
def test_pagamento_falho_mantem_pedido(db, produtos_base, monkeypatch):
    pedido = OperacoesPedido.criar_pedido(db)
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produtos_base["cafe"].id, 2, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    def stub_falha(pagamento, db_session):
        return False

    from app.services import pagamento_service

    monkeypatch.setattr(
        pagamento_service.OperacoesPagamento,
        "processar_pagamento",
        staticmethod(stub_falha),
    )

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db)
    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    pagamento = db.query(Pagamento).filter(Pagamento.pedido_id == pedido.id).first()

    assert (ok, msg, pedido_after.status, pagamento is not None, pagamento.status) == (
        False, "Pagamento falhou", StatusPedido.CRIADO, True, StatusPagamento.FALHOU,
    )

# Testa se o pagamento falho não incrementa o número de usos do cupom aplicado no pedido
def test_pagamento_falho_nao_incrementa_usos_do_cupom(
    db,
    produtos_base,
    cupons_base,
    monkeypatch,
):
    pedido = OperacoesPedido.criar_pedido(db, cliente_id="123")
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produtos_base["cafe"].id, 10, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.aplicar_cupom(pedido.id, "DESC10", db)
    assert ok, msg

    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    def stub_falha(pagamento, db_session):
        return False

    from app.services import pagamento_service

    monkeypatch.setattr(
        pagamento_service.OperacoesPagamento,
        "processar_pagamento",
        staticmethod(stub_falha),
    )

    cupom = cupons_base["desc10"]
    before_usos = cupom.usos or 0

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db)
    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    db.refresh(cupom)

    assert (ok, msg, pedido_after.status, cupom.usos) == (
        False, "Pagamento falhou", StatusPedido.CRIADO, before_usos,
    )