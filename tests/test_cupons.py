from datetime import datetime, timedelta
from app.models import Cupom, Pedido, Produto, StatusPedido, TipoPedido
from app.services.cupom_service import OperacoesCupom
from app.services.pedido_service import OperacoesPedido
from app.services import cupom_service

# Criação e listagem de cupons

def test_criar_cupom_pelo_servico_salva_no_banco(db):
    cupom = OperacoesCupom.criar_cupom("NOVO10", 10.0, minimo=30.0, db=db)

    assert (cupom.id is not None, cupom.codigo, cupom.desconto, cupom.minimo) == (
        True, "NOVO10", 10.0, 30.0,
    )

def test_criar_cupom_aplica_valores_padrao():
    cupom = OperacoesCupom.criar_cupom("PADRAO", 10.0)

    assert (cupom.minimo, cupom.ativo) == (50.0, True)

def test_listar_cupons_retorna_apenas_ativos(db):
    ativo = Cupom(codigo="ATIVO", desconto=10.0, minimo=0.0, ativo=True)
    inativo = Cupom(codigo="INATIVO_LISTA", desconto=10.0, minimo=0.0, ativo=False)
    db.add_all([ativo, inativo])
    db.commit()

    cupons = OperacoesCupom.listar_cupons(db)

    assert [cupom.codigo for cupom in cupons] == ["ATIVO"]

# Validade temporal do cupom

# Cupons fora do período de validade não devem ser aplicáveis
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

    assert (ok, msg) == (False, "Cupom expirado")

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

    assert (ok, msg) == (False, "Cupom ainda não válido")

def test_cupom_valido_exatamente_no_inicio(db, monkeypatch):
    inicio = datetime(2026, 6, 20, 15, 0)

    cupom = Cupom(
        codigo="INICIO",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        ativo_de=inicio,
    )
    db.add(cupom)
    db.commit()
    
    class FrozenDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return inicio

    monkeypatch.setattr(cupom_service, "datetime", FrozenDatetime)

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "INICIO", 100.0, db
    )

    assert (valido, desconto, msg) == (True, 10.0, "Cupom aplicado com sucesso")

def test_cupom_futuro_retorna_desconto_zero(db):
    cupom = Cupom(
        codigo="FUTURO_ZERO",
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        ativo_de=datetime.utcnow() + timedelta(days=1),
    )
    db.add(cupom)
    db.commit()

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "FUTURO_ZERO",
        100.0,
        db,
    )

    assert (valido, desconto, msg) == (False, 0, "Cupom ainda não válido")

# Limite de uso por cliente 

# Criando cupom para testar limite de uso por cliente
def criar_cupom_limitado(db, codigo="CPF_OBRIGATORIO"):
    cupom = Cupom(
        codigo=codigo,
        desconto=10.0,
        minimo=0.0,
        ativo=True,
        max_usos_por_cliente=1,
    )
    db.add(cupom)
    db.commit()
    db.refresh(cupom)
    return cupom

def test_cupom_com_limite_exige_cliente_identificado_na_validacao(db):
    criar_cupom_limitado(db)

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "CPF_OBRIGATORIO",
        100.0,
        db,
        customer_id=None,
    )

    assert (valido, desconto, msg) == (
        False, 0, "Cliente deve ser identificado para usar este cupom",
    )

def test_pedido_sem_cliente_nao_aplica_cupom_limitado(db):
    criar_cupom_limitado(db, codigo="LIMITADO_SEM_CPF")
    pedido = OperacoesPedido.criar_pedido(db)

    ok, msg = OperacoesPedido.aplicar_cupom(pedido.id, "LIMITADO_SEM_CPF", db)

    assert (ok, msg) == (False, "Cliente deve ser identificado para usar este cupom")

def test_pedido_sem_cliente_nao_finaliza_com_cupom_limitado(db, produtos_base):
    criar_cupom_limitado(db, codigo="FINALIZA_SEM_CPF")
    pedido = OperacoesPedido.criar_pedido(db)

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

    ok, msg = OperacoesPedido.finalizar_pedido(
        pedido.id,
        db,
        codigo_cupom="FINALIZA_SEM_CPF",
    )

    pedido_after = db.query(Pedido).filter(Pedido.id == pedido.id).first()

    assert (ok, msg, pedido_after.status) == (
        False, "Cliente deve ser identificado para usar este cupom", StatusPedido.CRIADO,
    )

def test_pedido_com_cliente_aplica_cupom_limitado_se_ainda_nao_usou(db):
    criar_cupom_limitado(db, codigo="LIMITADO_COM_CPF")

    produto = Produto(nome="Cafe", preco=10.0, estoque=10)
    db.add(produto)
    db.commit()
    db.refresh(produto)

    pedido = OperacoesPedido.criar_pedido(db, cliente_id="12345678900")

    ok_item, item, msg_item = OperacoesPedido.adicionar_item(
        pedido.id,
        produto.id,
        5,
        db,
    )

    assert (ok_item, item is not None, msg_item) == (
        True, True, "Item adicionado com sucesso",
    )

    ok, msg = OperacoesPedido.aplicar_cupom(
        pedido.id,
        "LIMITADO_COM_CPF",
        db,
    )

    assert (ok, msg) == (True, "Cupom aplicado: R$5.00 de desconto")

def test_cupom_usado_por_outro_cliente_continua_valido(db):
    cupom = criar_cupom_limitado(db, codigo="OUTRO_CLIENTE")
    pedido_outro_cliente = Pedido(
        cliente_id="11111111111",
        cupom_id=cupom.id,
        subtotal=100.0,
        status=StatusPedido.PAGO,
    )
    db.add(pedido_outro_cliente)
    db.commit()

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "OUTRO_CLIENTE",
        100.0,
        db,
        customer_id="22222222222",
    )

    assert (valido, desconto, msg) == (True, 10.0, "Cupom aplicado com sucesso")

def test_pedido_nao_pago_nao_conta_para_limite_de_uso(db):
    cupom = criar_cupom_limitado(db, codigo="NAO_PAGO_NAO_CONTA")
    pedido_criado = Pedido(
        cliente_id="12345678900",
        cupom_id=cupom.id,
        subtotal=100.0,
        status=StatusPedido.CRIADO,
    )
    db.add(pedido_criado)
    db.commit()

    valido, desconto, msg = OperacoesCupom.validar_cupom(
        "NAO_PAGO_NAO_CONTA",
        100.0,
        db,
        customer_id="12345678900",
    )
    
    assert (valido, desconto, msg) == (True, 10.0, "Cupom aplicado com sucesso")