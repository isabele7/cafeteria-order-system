from datetime import datetime, timedelta
from app.models import Cupom, Pedido, StatusPedido, TipoPedido
from app.services.pedido_service import OperacoesPedido

# Verifica se há itens antes de finalizar o pedido
def test_nao_finaliza_pedido_sem_itens(db):
    pedido = OperacoesPedido.criar_pedido(db)
    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db)

    assert ok is False
    assert "item" in msg.lower()
    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    assert pedido_after.status == StatusPedido.CRIADO
    
# Verifica se não é possível remover um item de um pedido diferente do que ele pertence
def test_nao_remove_item_de_outro_pedido(db, produtos_base):
    pedido_com_item = OperacoesPedido.criar_pedido(db)
    outro_pedido = OperacoesPedido.criar_pedido(db)
    produto = produtos_base["cafe"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido_com_item.id, produto.id, 2, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.remover_item(item.id, db, pedido_id=outro_pedido.id)

    assert ok is False
    assert "pedido" in msg.lower()
    itens = OperacoesPedido.listar_itens_pedido(pedido_com_item.id, db)
    produto_after = db.query(type(produto)).filter(type(produto).id == produto.id).first()
    assert len(itens) == 1
    assert produto_after.estoque == 98

# Testa rejeição de cupons fora de sua data de validade
def test_cupom_expirado_rejeitado(db):
    cupom = Cupom(
        codigo="EXP",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        ativo_ate=datetime.utcnow() - timedelta(days=1),
    )
    db.add(cupom)
    db.commit()

    pedido = OperacoesPedido.criar_pedido(db)

    ok, msg = OperacoesPedido.aplicar_cupom(pedido.id, "EXP", db)

    assert ok is False
    assert "expir" in msg.lower()

# Testa rejeição de cupons que ainda não estão válidos
def test_cupom_ainda_nao_valido_rejeitado(db):
    cupom = Cupom(
        codigo="FUT",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        ativo_de=datetime.utcnow() + timedelta(days=1),
    )
    db.add(cupom)
    db.commit()

    pedido = OperacoesPedido.criar_pedido(db)

    ok, msg = OperacoesPedido.aplicar_cupom(pedido.id, "FUT", db)

    assert ok is False
    assert "ainda" in msg.lower()

# Testa rejeição de cupons que atingiram o limite de uso por cliente
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
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produtos_base["cafe"].id, 10, db)
    assert ok, msg
    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg

    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db, codigo_cupom="LIMIT1")

    assert ok is False
    assert "limite" in msg.lower()
    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    db.refresh(cupom)
    assert pedido_after.status == StatusPedido.CRIADO
    assert cupom.usos == 0

# Testa se o número de usos do cupom é incrementado corretamente  
# quando um pedido é finalizado com um cupom aplicado
def test_usos_incrementa_quando_cupom_ja_estava_aplicado(db, produtos_base, cupons_base):
    pedido = OperacoesPedido.criar_pedido(db, cliente_id="123")
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produtos_base["cafe"].id, 10, db)
    assert ok, msg
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

# Verifica se um pedido com status PAGO não aceita alterações
def test_pedido_pago_nao_aceita_alteracoes(db, produtos_base, cupons_base):
    pedido = OperacoesPedido.criar_pedido(db)
    produto = produtos_base["cafe"]
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produto.id, 10, db)
    assert ok, msg
    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.RETIRADA, db)
    assert ok, msg
    ok, msg = OperacoesPedido.finalizar_pedido(pedido.id, db)
    assert ok, msg
    assert item is not None

    ok_item, _, _ = OperacoesPedido.adicionar_item(pedido.id, produto.id, 1, db)
    ok_remove, _ = OperacoesPedido.remover_item(item.id, db, pedido_id=pedido.id)
    ok_cupom, _ = OperacoesPedido.aplicar_cupom(pedido.id, "DESC10", db)
    ok_remover_cupom, _ = OperacoesPedido.remover_cupom(pedido.id, db)
    ok_tipo, _ = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.ENTREGA, db)
    ok_cancelar, _ = OperacoesPedido.cancelar_pedido(pedido.id, db)

    assert not any([ok_item, ok_remove, ok_cupom, ok_remover_cupom, ok_tipo, ok_cancelar])

# Verifica se um pedido com status CANCELADO não aceita alterações
def test_pedido_cancelado_nao_aceita_alteracoes(db, produtos_base, cupons_base):
    pedido = OperacoesPedido.criar_pedido(db)
    produto = produtos_base["cafe"]
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produto.id, 10, db)
    assert ok, msg
    ok, msg = OperacoesPedido.cancelar_pedido(pedido.id, db)
    assert ok, msg
    assert item is not None

    ok_item, _, _ = OperacoesPedido.adicionar_item(pedido.id, produto.id, 1, db)
    ok_remove, _ = OperacoesPedido.remover_item(item.id, db, pedido_id=pedido.id)
    ok_cupom, _ = OperacoesPedido.aplicar_cupom(pedido.id, "DESC10", db)
    ok_remover_cupom, _ = OperacoesPedido.remover_cupom(pedido.id, db)
    ok_tipo, _ = OperacoesPedido.definir_tipo_pedido(pedido.id, TipoPedido.ENTREGA, db)
    ok_finalizar, _ = OperacoesPedido.finalizar_pedido(pedido.id, db)

    assert not any([ok_item, ok_remove, ok_cupom, ok_remover_cupom, ok_tipo, ok_finalizar])
