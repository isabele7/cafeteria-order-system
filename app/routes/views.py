from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Cupom, ItemPedido, Pagamento, Pedido, Produto, StatusPedido, TipoPedido
from app.services.cupom_service import OperacoesCupom
from app.services.pedido_service import OperacoesPedido

BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/painel", tags=["interface"])

def _redirect(path: str, mensagem: str | None = None, erro: str | None = None) -> RedirectResponse:
    params = []
    if mensagem:
        params.append(f"mensagem={quote(mensagem)}")
    if erro:
        params.append(f"erro={quote(erro)}")
    suffix = f"?{'&'.join(params)}" if params else ""
    return RedirectResponse(f"{path}{suffix}", status_code=303)

def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)

def _status_cupom(cupom: Cupom) -> str:
    agora = datetime.utcnow()
    if not cupom.ativo:
        return "inativo"
    if cupom.ativo_de and agora < cupom.ativo_de:
        return "agendado"
    if cupom.ativo_ate and agora > cupom.ativo_ate:
        return "expirado"
    return "ativo"

@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    pedidos = db.query(Pedido).order_by(Pedido.id.desc()).all()
    hoje = date.today()
    pagos_hoje = [
        pedido for pedido in pedidos
        if pedido.status == StatusPedido.PAGO
        and pedido.atualizado_em is not None
        and pedido.atualizado_em.date() == hoje
    ]
    produtos_baixo_estoque = (
        db.query(Produto)
        .filter(Produto.estoque <= 3)
        .order_by(Produto.estoque.asc(), Produto.nome.asc())
        .all()
    )
    cupons = db.query(Cupom).all()
    cupons_ativos = [cupom for cupom in cupons if _status_cupom(cupom) == "ativo"]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active": "dashboard",
            "pedidos_criados": len([p for p in pedidos if p.status == StatusPedido.CRIADO]),
            "pedidos_pagos_hoje": len(pagos_hoje),
            "cupons_ativos": len(cupons_ativos),
            "produtos_baixo_estoque": produtos_baixo_estoque,
            "pedidos_recentes": pedidos[:6],
        },
    )

@router.get("/produtos", response_class=HTMLResponse)
def produtos(request: Request, db: Session = Depends(get_db)):
    lista = db.query(Produto).order_by(Produto.nome.asc()).all()
    return templates.TemplateResponse(
        "produtos.html",
        {"request": request, "active": "produtos", "produtos": lista},
    )

@router.post("/produtos")
def criar_produto(
    nome: str = Form(...),
    preco: float = Form(...),
    estoque: int = Form(...),
    db: Session = Depends(get_db),
):
    existente = db.query(Produto).filter(Produto.nome == nome).first()
    if existente:
        return _redirect("/painel/produtos", erro="Produto já existe.")
    produto = Produto(nome=nome.strip(), preco=preco, estoque=estoque)
    db.add(produto)
    db.commit()
    return _redirect("/painel/produtos", mensagem="Produto cadastrado com sucesso.")

@router.post("/produtos/{produto_id}/editar")
def editar_produto(
    produto_id: int,
    nome: str = Form(...),
    preco: float = Form(...),
    estoque: int = Form(...),
    db: Session = Depends(get_db),
):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        return _redirect("/painel/produtos", erro="Produto não encontrado.")

    nome_normalizado = nome.strip()
    produto_com_mesmo_nome = (
        db.query(Produto)
        .filter(
            Produto.nome == nome_normalizado,
            Produto.id != produto_id,
        )
        .first()
    )
    if produto_com_mesmo_nome:
        return _redirect(
            "/painel/produtos",
            erro="Já existe outro produto com esse nome.",
        )

    produto.nome = nome_normalizado
    produto.preco = preco
    produto.estoque = estoque

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _redirect(
            "/painel/produtos",
            erro="Já existe outro produto com esse nome.",
        )

    return _redirect("/painel/produtos", mensagem="Produto atualizado.")

@router.post("/produtos/{produto_id}/excluir")
def excluir_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        return _redirect("/painel/produtos", erro="Produto não encontrado.")
    db.delete(produto)
    db.commit()
    return _redirect("/painel/produtos", mensagem="Produto removido.")

@router.get("/cupons", response_class=HTMLResponse)
def cupons(request: Request, db: Session = Depends(get_db)):
    lista = db.query(Cupom).order_by(Cupom.id.desc()).all()
    status = {cupom.id: _status_cupom(cupom) for cupom in lista}
    return templates.TemplateResponse(
        "cupons.html",
        {"request": request, "active": "cupons", "cupons": lista, "status_cupons": status},
    )

@router.post("/cupons")
def criar_cupom(
    codigo: str = Form(...),
    desconto: float = Form(...),
    minimo: float = Form(50.0),
    ativo_de: str | None = Form(None),
    ativo_ate: str | None = Form(None),
    max_usos_por_cliente: int | None = Form(None),
    ativo: bool = Form(False),
    db: Session = Depends(get_db),
):
    existente = db.query(Cupom).filter(Cupom.codigo == codigo).first()
    if existente:
        return _redirect("/painel/cupons", erro="Cupom já existe.")
    cupom = OperacoesCupom.criar_cupom(
        codigo=codigo.strip().upper(),
        desconto=desconto,
        minimo=minimo,
        db=db,
        ativo_de=_dt(ativo_de),
        ativo_ate=_dt(ativo_ate),
        max_usos_por_cliente=max_usos_por_cliente,
    )
    cupom.ativo = ativo
    db.commit()
    return _redirect("/painel/cupons", mensagem="Cupom cadastrado com sucesso.")

@router.post("/cupons/{cupom_id}/editar")
def editar_cupom(
    cupom_id: int,
    codigo: str = Form(...),
    desconto: float = Form(...),
    minimo: float = Form(50.0),
    ativo_de: str | None = Form(None),
    ativo_ate: str | None = Form(None),
    max_usos_por_cliente: int | None = Form(None),
    ativo: bool = Form(False),
    db: Session = Depends(get_db),
):
    cupom = db.query(Cupom).filter(Cupom.id == cupom_id).first()
    if not cupom:
        return _redirect("/painel/cupons", erro="Cupom não encontrado.")
    cupom.codigo = codigo.strip().upper()
    cupom.desconto = desconto
    cupom.minimo = minimo
    cupom.ativo_de = _dt(ativo_de)
    cupom.ativo_ate = _dt(ativo_ate)
    cupom.max_usos_por_cliente = max_usos_por_cliente
    cupom.ativo = ativo
    db.commit()
    return _redirect("/painel/cupons", mensagem="Cupom atualizado.")

@router.get("/pedidos", response_class=HTMLResponse)
def pedidos(request: Request, status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Pedido)
    if status:
        try:
            query = query.filter(Pedido.status == StatusPedido(status))
        except ValueError:
            status = None
    lista = query.order_by(Pedido.id.desc()).all()
    return templates.TemplateResponse(
        "pedidos.html",
        {"request": request, "active": "pedidos", "pedidos": lista, "status_atual": status},
    )

@router.get("/novo-pedido", response_class=HTMLResponse)
def novo_pedido(request: Request):
    return templates.TemplateResponse(
        "novo_pedido.html",
        {"request": request, "active": "novo_pedido"},
    )

@router.post("/pedidos")
def criar_pedido(cliente_id: str | None = Form(None), db: Session = Depends(get_db)):
    cliente = cliente_id.strip() if cliente_id else None
    pedido = OperacoesPedido.criar_pedido(db, cliente_id=cliente or None)
    return _redirect(f"/painel/pedidos/{pedido.id}/montar", mensagem="Pedido iniciado.")

@router.get("/pedidos/{pedido_id}", response_class=HTMLResponse)
def detalhe_pedido(request: Request, pedido_id: int, db: Session = Depends(get_db)):
    pedido = OperacoesPedido.obter_pedido(pedido_id, db)
    if not pedido:
        return _redirect("/painel/pedidos", erro="Pedido não encontrado.")
    itens = OperacoesPedido.listar_itens_pedido(pedido_id, db)
    pagamentos = db.query(Pagamento).filter(Pagamento.pedido_id == pedido_id).order_by(Pagamento.id.desc()).all()
    return templates.TemplateResponse(
        "pedido_detalhe.html",
        {
            "request": request,
            "active": "pedidos",
            "pedido": pedido,
            "itens": itens,
            "pagamentos": pagamentos,
        },
    )

@router.get("/pedidos/{pedido_id}/montar", response_class=HTMLResponse)
def montar_pedido(request: Request, pedido_id: int, db: Session = Depends(get_db)):
    pedido = OperacoesPedido.obter_pedido(pedido_id, db)
    if not pedido:
        return _redirect("/painel/pedidos", erro="Pedido não encontrado.")
    itens = OperacoesPedido.listar_itens_pedido(pedido_id, db)
    produtos = db.query(Produto).order_by(Produto.nome.asc()).all()
    cupom = db.query(Cupom).filter(Cupom.id == pedido.cupom_id).first() if pedido.cupom_id else None
    return templates.TemplateResponse(
        "novo_pedido.html",
        {
            "request": request,
            "active": "novo_pedido",
            "pedido": pedido,
            "itens": itens,
            "produtos": produtos,
            "cupom": cupom,
        },
    )

@router.post("/pedidos/{pedido_id}/itens")
def adicionar_item_pedido(
    pedido_id: int,
    produto_id: int = Form(...),
    quantidade: int = Form(1),
    db: Session = Depends(get_db),
):
    ok, _, msg = OperacoesPedido.adicionar_item(pedido_id, produto_id, quantidade, db)
    if not ok:
        return _redirect(f"/painel/pedidos/{pedido_id}/montar", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}/montar", mensagem=msg)

@router.post("/pedidos/{pedido_id}/itens/{item_id}/remover")
def remover_item_pedido(pedido_id: int, item_id: int, db: Session = Depends(get_db)):
    ok, msg = OperacoesPedido.remover_item(item_id, db, pedido_id=pedido_id)
    if not ok:
        return _redirect(f"/painel/pedidos/{pedido_id}/montar", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}/montar", mensagem=msg)

@router.post("/pedidos/{pedido_id}/cupom")
def aplicar_cupom_pedido(pedido_id: int, codigo: str = Form(...), db: Session = Depends(get_db)):
    ok, msg = OperacoesPedido.aplicar_cupom(pedido_id, codigo.strip().upper(), db)
    if not ok:
        if msg == "Cliente deve ser identificado para usar este cupom":
            msg = "Informe o CPF para usar este cupom."
        return _redirect(f"/painel/pedidos/{pedido_id}/montar", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}/montar", mensagem=msg)

@router.post("/pedidos/{pedido_id}/cupom/remover")
def remover_cupom_pedido(pedido_id: int, db: Session = Depends(get_db)):
    ok, msg = OperacoesPedido.remover_cupom(pedido_id, db)
    if not ok:
        return _redirect(f"/painel/pedidos/{pedido_id}/montar", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}/montar", mensagem=msg)

@router.post("/pedidos/{pedido_id}/tipo")
def definir_tipo_pedido(pedido_id: int, tipo: TipoPedido = Form(...), db: Session = Depends(get_db)):
    ok, msg = OperacoesPedido.definir_tipo_pedido(pedido_id, tipo, db)
    if not ok:
        return _redirect(f"/painel/pedidos/{pedido_id}/montar", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}/montar", mensagem=msg)

@router.post("/pedidos/{pedido_id}/finalizar")
def finalizar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    ok, msg = OperacoesPedido.finalizar_pedido(pedido_id, db)
    if not ok:
        if msg == "Cliente deve ser identificado para usar este cupom":
            msg = "Informe o CPF para usar este cupom."
        return _redirect(f"/painel/pedidos/{pedido_id}/montar", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}", mensagem=msg)

@router.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: int, db: Session = Depends(get_db)):
    ok, msg = OperacoesPedido.cancelar_pedido(pedido_id, db)
    if not ok:
        return _redirect(f"/painel/pedidos/{pedido_id}", erro=msg)
    return _redirect(f"/painel/pedidos/{pedido_id}", mensagem=msg)
