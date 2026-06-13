from datetime import datetime
from typing import cast
from sqlalchemy.orm import Session
from app.models import Cupom, Pedido, StatusPedido

class OperacoesCupom:
    @staticmethod
    def validar_cupom(
        codigo: str,
        subtotal: float,
        db: Session,
        customer_id: str | None = None,
    ) -> tuple[bool, float, str]:
        """Valida um cupom e retorna se é válido, o desconto e a mensagem"""
        if not codigo:
            return False, 0, "Cupom não fornecido"

        cupom = db.query(Cupom).filter(Cupom.codigo == codigo).first()

        if not cupom:
            return False, 0, "Cupom não encontrado"

        if not cupom.ativo:
            return False, 0, "Cupom inativo"

        if subtotal < cupom.minimo:
            return False, 0, f"Subtotal mínimo de R${cupom.minimo:.2f} para usar este cupom"

        now = datetime.utcnow()
        ativo_de = cast(datetime | None, cupom.ativo_de)
        ativo_ate = cast(datetime | None, cupom.ativo_ate)
        if ativo_de is not None and now < ativo_de:
            return False, 0, "Cupom ainda não valido"
        if ativo_ate is not None and now > ativo_ate:
            return False, 0, "Cupom expirado"

        if cupom.max_usos_por_cliente and customer_id is not None:
            usos_cliente = (
                db.query(Pedido)
                .filter(
                    Pedido.cupom_id == cupom.id,
                    Pedido.cliente_id == customer_id,
                    Pedido.status == StatusPedido.PAGO,
                )
                .count()
            )
            if usos_cliente >= cupom.max_usos_por_cliente:
                return False, 0, "Limite de uso por cliente atingido"

        desconto_valor = (subtotal * cupom.desconto) / 100
        return True, desconto_valor, "Cupom aplicado com sucesso"

    @staticmethod
    def criar_cupom(
        codigo: str,
        desconto: float,
        minimo: float = 50.0,
        db: Session | None = None,
        ativo_de=None,
        ativo_ate=None,
        max_usos_por_cliente: int | None = None,
    ) -> Cupom:
        """Cria um novo cupom e o salva no banco de dados"""
        cupom = Cupom(
            codigo=codigo,
            desconto=desconto,
            minimo=minimo,
            ativo=True,
            ativo_de=ativo_de,
            ativo_ate=ativo_ate,
            max_usos_por_cliente=max_usos_por_cliente,
        )
        if db is not None:
            db.add(cupom)
            db.commit()
            db.refresh(cupom)
        return cupom

    @staticmethod
    def listar_cupons(db: Session):
        """Lista todos os cupons ativos"""
        return db.query(Cupom).filter(Cupom.ativo == True).all()
