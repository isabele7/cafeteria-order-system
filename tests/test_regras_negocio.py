from app.models import Cupom, Pedido, StatusPedido, TipoPedido
from app.services.pedido_service import OperacoesPedido

# Verifica se o limite de uso do cupom por cliente é respeitado na finalização do pedido
def test_limite_de_cupom_por_cliente_vale_na_finalizacao(db, produtos_base):
    cupom = Cupom(
        codigo="LIMIT1",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        max_usos_por_cliente=1,
    )
    db.add(cupom)
    db.commit()
    db.refresh(cupom)

    pedido_anterior = Pedido(
        cliente_id="123",
        cupom_id=cupom.id,
        subtotal=50.0,
        status=StatusPedido.PAGO,
    )
    db.add(pedido_anterior)
    db.commit()

    pedido = OperacoesPedido.criar_pedido(db, cliente_id="123")
    ok, item, msg = OperacoesPedido.adicionar_item(
        pedido.id,
        produtos_base["cafe"].id,
        10,
        db,
    )
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db, codigo_cupom="LIMIT1")

    assert ok is False
    assert msg == "Limite de uso por cliente atingido"
    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    db.refresh(cupom)
    assert pedido_after.status == StatusPedido.CRIADO
    assert cupom.usos == 0

# Verifica se o número de usos do cupom é incrementado quando o cupom já estava aplicado no pedido
def test_usos_incrementa_quando_cupom_ja_estava_aplicado(db, produtos_base, cupons_base):
    pedido = OperacoesPedido.criar_pedido(db, cliente_id="123")
    ok, item, msg = OperacoesPedido.adicionar_item(
        pedido.id,
        produtos_base["cafe"].id,
        10,
        db,
    )
    assert ok, msg
    assert item is not None
    
    ok, msg = OperacoesPedido.aplicar_cupom(pedido.id, "DESC10", db)
    assert ok, msg

    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    cupom = cupons_base["desc10"]
    before_usos = cupom.usos or 0

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db)

    assert ok, msg
    db.refresh(cupom)
    assert cupom.usos == before_usos + 1

# Verifica se o cupom é aplicado corretamente e o número de usos é incrementado quando o pedido é finalizado
def test_finalizar_com_codigo_cupom_aplica_desconto_e_incrementa_usos(
    db,
    produtos_base,
    cupons_base,
):
    pedido = OperacoesPedido.criar_pedido(db, cliente_id="123")
    cafe = produtos_base["cafe"]
    cupom = cupons_base["desc10"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, 10, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    before_usos = cupom.usos or 0

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db, codigo_cupom="DESC10")

    assert ok is True
    assert msg == "Pedido finalizado. Total: R$45.00"

    db.refresh(cupom)
    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()

    assert pedido_after.status == StatusPedido.PAGO
    assert pedido_after.desconto == 5.0
    assert pedido_after.total == 45.0
    assert cupom.usos == before_usos + 1
