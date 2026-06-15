from sqlalchemy.orm import Session
from app.models import Pagamento

class OperacoesPagamento:
    @staticmethod
    def processar_pagamento(pagamento: Pagamento, db: Session, sucesso: bool = True) -> bool:
        """
        Processa (simula) um pagamento.
        - `succeed=True` simula confirmação imediata.
        - `succeed=False` simula falha.
        """
        return bool(sucesso)
