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