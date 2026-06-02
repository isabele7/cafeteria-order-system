from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cupom
from app.services.cupom_service import CupomService
from pydantic import BaseModel

router = APIRouter(prefix="/api/cupons", tags=["cupons"])
class CriarCupom(BaseModel):
    codigo: str
    desconto: float  # percentual
    minimo: float = 50.0
class CupomResposta(BaseModel):
    id: int
    codigo: str
    desconto: float
    minimo: float
    ativo: int
    class Config:
        from_attributes = True

@router.post("", response_model=CupomResposta, status_code=201)
def criar_cupom(cupom: CriarCupom, db: Session = Depends(get_db)):
    novo_cupom = CupomService.criar_cupom(
        codigo=cupom.codigo,
        desconto=cupom.desconto,
        minimo=cupom.minimo,
        db=db
    )
    return novo_cupom

@router.get("", response_model=list[CupomResposta])
def listar_cupons(db: Session = Depends(get_db)):
    """Lista todos os cupons ativos"""
    return CupomService.listar_cupons(db)

@router.get("/{cupom_id}", response_model=CupomResposta)
def obter_cupom(cupom_id: int, db: Session = Depends(get_db)):
    """Obtém um cupom pelo ID"""
    cupom = db.query(Cupom).filter(Cupom.id == cupom_id).first()
    if not cupom:
        raise HTTPException(status_code=404, detail="Cupom não encontrado")
    return cupom
