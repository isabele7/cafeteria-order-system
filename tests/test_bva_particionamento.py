import pytest
from app.models import Cupom, Pedido, Produto, StatusPedido, TipoPedido
from app.services.cupom_service import OperacoesCupom
from app.services.pedido_service import OperacoesPedido

def criar_cupom(db, codigo="BVA10", desconto=10.0, minimo=50.0, ativo=True):
    cupom = Cupom(codigo=codigo, desconto=desconto, minimo=minimo, ativo=ativo)
    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    return cupom

# BVA - valor mínimo do cupom: abaixo, no limite e acima.
def test_bva_cupom_minimo_49_99_rejeita(db):
    criar_cupom(db, codigo="MIN4999", minimo=50.0)

    valido, desconto, msg = OperacoesCupom.validar_cupom("MIN4999", 49.99, db)

    assert valido is False
    assert desconto == 0
    assert msg == "Subtotal mínimo de R$50.00 para usar este cupom"

def test_bva_cupom_minimo_50_00_aceita(db):
    criar_cupom(db, codigo="MIN5000", minimo=50.0)

    valido, desconto, msg = OperacoesCupom.validar_cupom("MIN5000", 50.00, db)

    assert valido is True
    assert desconto == pytest.approx(5.0)
    assert msg == "Cupom aplicado com sucesso"

def test_bva_cupom_minimo_50_01_aceita(db):
    criar_cupom(db, codigo="MIN5001", minimo=50.0)

    valido, desconto, msg = OperacoesCupom.validar_cupom("MIN5001", 50.01, db)

    assert valido is True
    assert desconto == pytest.approx(5.001)
    assert msg == "Cupom aplicado com sucesso"

# Particionamento de equivalência - classes válidas e inválidas de cupom.
def test_cupom_valido_representativo(db):
    criar_cupom(db, codigo="VALIDO", minimo=50.0, ativo=True)

    valido, desconto, msg = OperacoesCupom.validar_cupom("VALIDO", 100.0, db)

    assert valido is True
    assert desconto == pytest.approx(10.0)
    assert msg == "Cupom aplicado com sucesso"

def test_cupom_inexistente_rejeita(db):
    valido, desconto, msg = OperacoesCupom.validar_cupom("NAO_EXISTE", 100.0, db)

    assert valido is False
    assert desconto == 0
    assert msg == "Cupom não encontrado"

def test_cupom_inativo_rejeita(db):
    criar_cupom(db, codigo="INATIVO_BVA", minimo=50.0, ativo=False)

    valido, desconto, msg = OperacoesCupom.validar_cupom("INATIVO_BVA", 100.0, db)

    assert valido is False
    assert desconto == 0
    assert msg == "Cupom inativo"

def test_cupom_sem_codigo_rejeita(db):
    valido, desconto, msg = OperacoesCupom.validar_cupom("", 100.0, db)

    assert valido is False
    assert desconto == 0
    assert msg == "Cupom não fornecido"

# BVA - frete grátis: abaixo, no limite e acima do limite de R$50.
def test_bva_entrega_49_99_tem_taxa():
    taxa = OperacoesPedido._calcular_taxa_entrega(TipoPedido.ENTREGA, 49.99)
    assert taxa == 10.0

def test_bva_entrega_50_00_sem_taxa():
    taxa = OperacoesPedido._calcular_taxa_entrega(TipoPedido.ENTREGA, 50.00)
    assert taxa == 0.0

def test_bva_entrega_50_01_sem_taxa():
    taxa = OperacoesPedido._calcular_taxa_entrega(TipoPedido.ENTREGA, 50.01)
    assert taxa == 0.0

# Particionamento de equivalência - tipos sem entrega não têm taxa.
def test_retirada_sem_taxa():
    taxa = OperacoesPedido._calcular_taxa_entrega(TipoPedido.RETIRADA, 10.0)
    assert taxa == 0.0

def test_consumo_local_sem_taxa():
    taxa = OperacoesPedido._calcular_taxa_entrega(TipoPedido.CONSUMO_LOCAL, 10.0)
    assert taxa == 0.0

# BVA e particionamento - estoque e quantidade.
def test_equivalence_estoque_zero_rejeita_item(db, produtos_base):
    pedido = OperacoesPedido.criar_pedido(db)
    suco = produtos_base["suco"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, suco.id, 1, db)

    assert ok is False
    assert item is None
    assert msg == "Estoque insuficiente. Disponível: 0"

def test_bva_estoque_um_aceita_uma_unidade(db):
    produto = Produto(nome="Cookie", preco=3.0, estoque=1)
    db.add(produto)
    db.commit()
    db.refresh(produto)

    pedido = OperacoesPedido.criar_pedido(db)

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, produto.id, 1, db)

    assert ok is True
    assert item is not None
    assert msg == "Item adicionado com sucesso"

    produto_after = db.query(Produto).filter(Produto.id == produto.id).first()
    assert produto_after is not None
    assert produto_after.estoque == 0

def test_bva_estoque_exato_n_aceita(db, produtos_base):
    pedido = OperacoesPedido.criar_pedido(db)
    cafe = produtos_base["cafe"]
    estoque = int(cafe.estoque)

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, estoque, db)

    assert ok is True
    assert item is not None
    assert msg == "Item adicionado com sucesso"

    produto_after = db.query(Produto).filter(Produto.id == cafe.id).first()
    assert produto_after is not None
    assert produto_after.estoque == 0

def test_bva_estoque_n_mais_um_rejeita(db, produtos_base):
    pedido = OperacoesPedido.criar_pedido(db)
    cafe = produtos_base["cafe"]
    estoque = int(cafe.estoque)

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, estoque + 1, db)

    assert ok is False
    assert item is None
    assert msg == f"Estoque insuficiente. Disponível: {estoque}"

def test_bva_quantidade_zero_rejeita(db, produtos_base):
    pedido = OperacoesPedido.criar_pedido(db)
    cafe = produtos_base["cafe"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, 0, db)

    assert ok is False
    assert item is None
    assert msg == "Quantidade inválida"

def test_bva_quantidade_negativa_rejeita(db, produtos_base):
    pedido = OperacoesPedido.criar_pedido(db)
    cafe = produtos_base["cafe"]

    ok, item, msg = OperacoesPedido.adicionar_item(pedido.id, cafe.id, -1, db)

    assert ok is False
    assert item is None
    assert msg == "Quantidade inválida"

# Particionamento - limite de uso por cliente.
def test_cliente_abaixo_do_limite_pode_usar_cupom(db):
    cupom = Cupom(
        codigo="LIMITE_OK",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        max_usos_por_cliente=1,
    )
    db.add(cupom)
    db.commit()

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "LIMITE_OK",
        100.0,
        db,
        customer_id="123",
    )

    assert valido is True
    assert desconto == pytest.approx(10.0)
    assert msg == "Cupom aplicado com sucesso"

def test_cliente_no_limite_nao_pode_usar_cupom(db):
    cupom = Cupom(
        codigo="LIMITE_FAIL",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        max_usos_por_cliente=1,
    )
    db.add(cupom)
    db.commit()
    db.refresh(cupom)

    pedido_pago = Pedido(
        cliente_id="123",
        cupom_id=cupom.id,
        subtotal=100.0,
        status=StatusPedido.PAGO,
    )
    db.add(pedido_pago)
    db.commit()

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "LIMITE_FAIL",
        100.0,
        db,
        customer_id="123",
    )

    assert valido is False
    assert desconto == 0
    assert msg == "Limite de uso por cliente atingido"