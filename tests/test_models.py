import pytest
from sqlalchemy.exc import IntegrityError
from app.models import Produto, Cupom, Pedido, ItemPedido, StatusPedido, TipoPedido

def test_criar_produto(db):
    produto = Produto(nome="Café", preco=5.0, estoque=10)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    assert produto.id is not None
    assert produto.nome == "Café"
    assert produto.preco == 5.0
    assert produto.estoque == 10

def test_criar_cupom(db):
    cupom = Cupom(codigo="DESC10", desconto=10.0, minimo=50.0, ativo=1)
    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    assert cupom.id is not None
    assert cupom.codigo == "DESC10"
    assert cupom.desconto == 10.0
    assert cupom.minimo == 50.0

def test_criar_pedido(db):
    pedido = Pedido()
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    assert pedido.id is not None
    assert pedido.status == StatusPedido.CRIADO
    assert pedido.subtotal == 0.0
    assert pedido.desconto == 0.0
    assert pedido.taxa_entrega == 0.0
    assert pedido.total == 0.0

def test_criar_item_pedido(db, produtos_base):
    pedido = Pedido()
    db.add(pedido)
    db.commit()

    cafe = produtos_base["cafe"]
    item = ItemPedido(
        pedido_id=pedido.id,
        produto_id=cafe.id,
        quantidade=2,
        preco_unitario=5.0,
        subtotal=10.0
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    assert item.id is not None
    assert item.quantidade == 2
    assert item.subtotal == 10.0

def test_produto_nome_unico(db):
    produto1 = Produto(nome="Café", preco=5.0, estoque=10)
    db.add(produto1)
    db.commit()

    produto2 = Produto(nome="Café", preco=6.0, estoque=5)
    db.add(produto2)
    # O commit deve falhar porque não pode haver dois produtos com o mesmo nome
    with pytest.raises(IntegrityError):  
        db.commit()
    db.rollback()

def test_cupom_codigo_unico(db):
    cupom1 = Cupom(codigo="DESC10", desconto=10.0)
    db.add(cupom1)
    db.commit()
    
    cupom2 = Cupom(codigo="DESC10", desconto=20.0)
    db.add(cupom2)
    # O commit deve falhar porque não pode haver dois cupons com o mesmo código
    with pytest.raises(IntegrityError):  
        db.commit()
    db.rollback()

def test_produto_estoque_padrao_zero(db):
    produto = Produto(nome="Café", preco=5.0)
    db.add(produto)
    db.commit()
    db.refresh(produto)
    assert produto.estoque == 0