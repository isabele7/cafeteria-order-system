from sqlalchemy.orm import Session
from app.models import Cupom

class OperacoesCupom:
    @staticmethod
    def validar_cupom(codigo: str, subtotal: float, db: Session) -> tuple[bool, float, str]:
        """Valida um cupom e retorna se é válido, o desconto e mensagem"""
        if not codigo:
            return False, 0, "Cupom não fornecido"

        cupom = db.query(Cupom).filter(Cupom.codigo == codigo).first()

        if not cupom:
            return False, 0, "Cupom não encontrado"

        if not cupom.ativo:
            return False, 0, "Cupom inativo"

        if subtotal < cupom.minimo:
            return (False, 0, f"Subtotal mínimo de R${cupom.minimo:.2f} para usar este cupom")

        # Desconto percentual
        desconto_valor = (subtotal * cupom.desconto) / 100
        return True, desconto_valor, "Cupom aplicado com sucesso"

    @staticmethod
    def criar_cupom(codigo: str, desconto: float, minimo: float = 50.0, db: Session | None = None,) -> Cupom:
        """Cria um novo cupom e o salva no banco de dados"""
        cupom = Cupom(codigo=codigo, desconto=desconto, minimo=minimo, ativo=1)
        if db is not None:
            db.add(cupom)
            db.commit()
            db.refresh(cupom)
        return cupom

    @staticmethod
    def listar_cupons(db: Session):
        """Lista todos os cupons ativos"""
        return db.query(Cupom).filter(Cupom.ativo == 1).all()
