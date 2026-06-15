from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import Produto
from pydantic import BaseModel

router = APIRouter(prefix="/api/produtos", tags=["produtos"])

class CriarProduto(BaseModel):
    nome: str
    preco: float
    estoque: int = 0

class AtualizarProduto(BaseModel):
    nome: str | None = None
    preco: float | None = None
    estoque: int | None = None

class RespostaProduto(BaseModel):
    id: int
    nome: str
    preco: float
    estoque: int

    class Config:
        from_attributes = True

@router.post("", response_model=RespostaProduto, status_code=201)
def criar_produto(produto: CriarProduto, db: Session = Depends(get_db)):
    """Cria um novo produto"""
    # Verificar se já existe
    existente = db.query(Produto).filter(Produto.nome == produto.nome).first()
    if existente:
        raise HTTPException(status_code=409, detail="Produto já existe.")

    novo_produto = Produto(
        nome=produto.nome,
        preco=produto.preco,
        estoque=produto.estoque
    )
    db.add(novo_produto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Produto já existe.")

    db.refresh(novo_produto)
    return novo_produto

@router.get("/{produto_id}", response_model=RespostaProduto)
def obter_produto(produto_id: int, db: Session = Depends(get_db)):
    """Obtém um produto pelo ID"""
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return produto

@router.get("", response_model=list[RespostaProduto])
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(Produto).all()

@router.put("/{produto_id}", response_model=RespostaProduto)
def atualizar_produto(
    produto_id: int,
    produto_update: AtualizarProduto,
    db: Session = Depends(get_db)
):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    if produto_update.nome is not None:
        produto.nome = produto_update.nome
    if produto_update.preco is not None:
        produto.preco = produto_update.preco
    if produto_update.estoque is not None:
        produto.estoque = produto_update.estoque

    db.commit()
    db.refresh(produto)
    return produto

@router.delete("/{produto_id}", status_code=204)
def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(Produto).filter(Produto.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    db.delete(produto)
    db.commit()
    return None