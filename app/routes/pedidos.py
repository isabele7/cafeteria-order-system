from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Pedido, ItemPedido, TipoPedido
from app.services.pedido_service import PedidoService
from pydantic import BaseModel

router = APIRouter(prefix="/api/pedidos", tags=["pedidos"])

class CriarItemPedido(BaseModel):
    produto_id: int
    quantidade: int

class AplicarCupom(BaseModel):
    codigo: str

class AtualizarTipoPedido(BaseModel):
    tipo: TipoPedido

class ItemPedidoResposta(BaseModel):
    id: int
    produto_id: int
    quantidade: int
    preco_unitario: float
    subtotal: float

    class Config:
        from_attributes = True

class PedidoResposta(BaseModel):
    id: int
    status: str
    tipo: str | None
    subtotal: float
    desconto: float
    taxa_entrega: float
    total: float
    cupom_id: int | None

    class Config:
        from_attributes = True

class PedidoDetalhadoResposta(PedidoResposta):
    itens: list[ItemPedidoResposta]

@router.post("", response_model=PedidoResposta, status_code=201)
def criar_pedido(db: Session = Depends(get_db)):
    pedido = PedidoService.criar_pedido(db)
    return pedido

@router.post("/{pedido_id}/itens", response_model=ItemPedidoResposta, status_code=201)
def adicionar_item(
    pedido_id: int,
    item: CriarItemPedido,
    db: Session = Depends(get_db)
):
    sucesso, item_criado, mensagem = PedidoService.adicionar_item(
        pedido_id, item.produto_id, item.quantidade, db
    )

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return item_criado

@router.delete("/{pedido_id}/itens/{item_id}", status_code=204)
def remover_item(
    pedido_id: int,
    item_id: int,
    db: Session = Depends(get_db)
):
    sucesso, mensagem = PedidoService.remover_item(item_id, db)

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return None

@router.post("/{pedido_id}/cupom")
def aplicar_cupom(
    pedido_id: int,
    cupom: AplicarCupom,
    db: Session = Depends(get_db)
):
    sucesso, mensagem = PedidoService.aplicar_cupom(pedido_id, cupom.codigo, db)

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return {"mensagem": mensagem}

@router.delete("/{pedido_id}/cupom")
def remover_cupom(pedido_id: int, db: Session = Depends(get_db)):
    sucesso, mensagem = PedidoService.remover_cupom(pedido_id, db)

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return {"mensagem": mensagem}

@router.put("/{pedido_id}/tipo")
def definir_tipo_pedido(
    pedido_id: int,
    tipo_att: AtualizarTipoPedido,
    db: Session = Depends(get_db)
):
    sucesso, mensagem = PedidoService.definir_tipo_pedido(
        pedido_id, tipo_att.tipo, db
    )

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return {"mensagem": mensagem}

@router.post("/{pedido_id}/finalizar")
def finalizar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    sucesso, mensagem = PedidoService.finalizar_pedido(pedido_id, db)

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return {"mensagem": mensagem}

@router.post("/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    """Cancela o pedido"""
    sucesso, mensagem = PedidoService.cancelar_pedido(pedido_id, db)

    if not sucesso:
        raise HTTPException(status_code=400, detail=mensagem)

    return {"mensagem": mensagem}

@router.get("/{pedido_id}", response_model=PedidoDetalhadoResposta)
def obter_pedido(pedido_id: int, db: Session = Depends(get_db)):
    pedido = PedidoService.obter_pedido(pedido_id, db)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    itens = PedidoService.listar_itens_pedido(pedido_id, db)
    pedido_dict = {
        "id": pedido.id,
        "status": pedido.status.value,
        "tipo": pedido.tipo.value if pedido.tipo else None, 
        "subtotal": pedido.subtotal,
        "desconto": pedido.desconto,
        "taxa_entrega": pedido.taxa_entrega,
        "total": pedido.total,
        "cupom_id": pedido.cupom_id,
        "itens": itens
    }
    return pedido_dict

@router.get("", response_model=list[PedidoResposta])
def listar_pedidos(db: Session = Depends(get_db)):
    return db.query(Pedido).all()