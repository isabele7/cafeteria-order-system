import pytest
from app.models import Cupom, Pedido, Produto, StatusPedido, TipoPedido
from app.services.pedido_service import OperacoesPedido

# Itens não podem ser adicionados a pedidos inexistentes
def test_adicionar_item_pedido_inexistente_rejeita(db, produtos_base):
    cafe = produtos_base["cafe"]
    ok, item, msg = OperacoesPedido.adicionar_item(999, cafe.id, 1, db)
    assert (ok, item, msg) == (False, None, "Pedido não encontrado")

# Itens não podem ser adicionados com produtos inexistentes
def test_adicionar_item_produto_inexistente_rejeita(db):
    pedido = OperacoesPedido.criar_pedido(db)
    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, 999, 1, db)
    assert (ok, item, msg) == (False, None, "Produto não encontrado")

# Itens não podem ser removidos se não existirem
def test_remover_item_inexistente_rejeita(db):
    ok, msg = OperacoesPedido.remover_item(999, db)
    assert (ok, msg) == (False, "Item não encontrado")

# Itens removidos devem restaurar o estoque do produto e atualizar o subtotal do pedido
def test_remover_item_com_sucesso_restaura_estoque_e_subtotal(db, produtos_base):
    pedido = OperacoesPedido.criar_pedido(db)
    cafe = produtos_base["cafe"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, 2, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.remover_item(item.id, db, pedido_id=pedido.id)

    assert (ok, msg) == (True, "Item removido com sucesso")

    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    produto_after = db.query(type(cafe)).filter(type(cafe).id == cafe.id).first()
    itens = OperacoesPedido.listar_itens_pedido(pedido.id, db)

    assert (pedido_after.subtotal, produto_after.estoque, itens) == (0, 100, [])

# Itens só podem ser removidos do pedido ao qual pertencem
def test_nao_remove_item_de_outro_pedido(db, produtos_base):
    pedido_com_item = OperacoesPedido.criar_pedido(db)
    outro_pedido = OperacoesPedido.criar_pedido(db)
    produto = produtos_base["cafe"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido_com_item.id, produto.id, 2, db)
    assert ok, msg
    assert item is not None

    ok, msg = OperacoesPedido.remover_item(item.id, db, pedido_id=outro_pedido.id)

    assert (ok, msg) == (False, "Item não pertence ao pedido informado")

    itens = OperacoesPedido.listar_itens_pedido(pedido_com_item.id, db)
    produto_after = db.query(type(produto)).filter(type(produto).id == produto.id).first()
    assert (len(itens), produto_after.estoque) == (1, 98)

# Cupom no pedido
def test_aplicar_cupom_pedido_inexistente_rejeita(db):
    assert OperacoesPedido.aplicar_cupom(999, "DESC10", db) == (False, "Pedido não encontrado")

def test_remover_cupom_pedido_inexistente_rejeita(db):
    assert OperacoesPedido.remover_cupom(999, db) == (False, "Pedido não encontrado")

def test_remover_cupom_com_sucesso(db, produtos_base, cupons_base):
    pedido = OperacoesPedido.criar_pedido(db)
    cafe = produtos_base["cafe"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, 10, db)
    assert ok, msg
    assert item is not None
    ok, msg = OperacoesPedido.aplicar_cupom(pedido.id, "DESC10", db)
    assert ok, msg

    ok, msg = OperacoesPedido.remover_cupom(pedido.id, db)

    assert (ok, msg) == (True, "Cupom removido")

    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()
    assert (pedido_after.cupom_id, pedido_after.desconto) == (None, 0.0)