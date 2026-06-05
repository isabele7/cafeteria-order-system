from sqlalchemy.orm import Session
from app.models import Pedido, ItemPedido, Produto, StatusPedido, TipoPedido, Cupom
from app.services.cupom_service import OperacoesCupom
from typing import Any, cast

class OperacoesPedido:
    @staticmethod
    def criar_pedido(db: Session) -> Pedido:
        """Cria um novo pedido vazio"""
        pedido = Pedido()
        db.add(pedido)
        db.commit()
        db.refresh(pedido)
        return pedido

    @staticmethod
    def adicionar_item(
        pedido_id: int,
        produto_id: int,
        quantidade: int,
        db: Session
    ) -> tuple[bool, ItemPedido | None, str]:
        """ Adiciona um item ao pedido, validando estoque e status do pedido"""
        # Validar se pedido existe
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            return False, None, "Pedido não encontrado"
        pedido = cast(Any, pedido)

        # Validar se pedido ainda pode receber itens
        if pedido.status == StatusPedido.PAGO:
            return False, None, "Não é possível adicionar itens a um pedido pago"

        if pedido.status == StatusPedido.CANCELADO:
            return False, None, "Não é possível adicionar itens a um pedido cancelado"

        # Validar produto
        produto = db.query(Produto).filter(Produto.id == produto_id).first()
        if not produto:
            return False, None, "Produto não encontrado"
        produto = cast(Any, produto)

        # Validar quantidade
        if quantidade <= 0:
            return False, None, "Quantidade inválida"

        # Validar estoque
        if produto.estoque < quantidade:
            return (
                False,
                None,
                f"Estoque insuficiente. Disponível: {produto.estoque}"
            )

        # Reservar estoque e criar item do pedido em transação atômica
        try:
            produto_query = db.query(Produto).filter(Produto.id == produto_id)
            try:
                produto = produto_query.with_for_update().first()  # type: ignore[attr-defined]
            except Exception:
                produto = produto_query.first()

            if produto is None:
                return False, None, "Produto não encontrado"

            if produto.estoque < quantidade:
                return (
                    False,
                    None,
                    f"Estoque insuficiente. Disponível: {produto.estoque}"
                )

            # Reservar (decrementar estoque imediatamente)
            produto.estoque -= quantidade
            db.add(produto)

            # Criar item do pedido
            item = ItemPedido(
                pedido_id=pedido_id,
                produto_id=produto_id,
                quantidade=quantidade,
                preco_unitario=produto.preco,
                subtotal=produto.preco * quantidade
            )
            db.add(item)

            # Commit atômico
            db.commit()
            db.refresh(item)

            # Recalcular subtotal do pedido
            OperacoesPedido._recalcular_subtotal(pedido_id, db)

            return True, item, "Item adicionado com sucesso"
        except Exception as e:
            db.rollback()
            return False, None, f"Erro ao adicionar item: {str(e)}"

    @staticmethod
    def remover_item(item_id: int, db: Session) -> tuple[bool, str]:
        """Remove um item do pedido"""
        item = db.query(ItemPedido).filter(ItemPedido.id == item_id).first()
        if not item:
            return False, "Item não encontrado"
        pedido = db.query(Pedido).filter(Pedido.id == item.pedido_id).first()
        if not pedido:
            return False, "Pedido não encontrado"
        pedido = cast(Any, pedido)
        if pedido.status != StatusPedido.CRIADO:
            return False, "Não é possível remover itens de um pedido que não está em criação"

        pedido_id = int(item.pedido_id)

        # Restaurar estoque do produto reservado
        produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
        if produto:
            produto = cast(Any, produto)
            produto.estoque += int(item.quantidade)
            db.add(produto)

        db.delete(item)
        db.commit()

        # Recalcular subtotal
        OperacoesPedido._recalcular_subtotal(pedido_id, db)

        return True, "Item removido com sucesso"

    @staticmethod
    def _recalcular_subtotal(pedido_id: int, db: Session):
        """Recalcula o subtotal de um pedido baseado em seus itens"""
        itens = db.query(ItemPedido).filter(ItemPedido.pedido_id == pedido_id).all()
        subtotal = sum(item.subtotal for item in itens)

        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            return
        pedido = cast(Any, pedido)
        pedido.subtotal = subtotal
        db.commit()

    @staticmethod
    def aplicar_cupom(pedido_id: int, codigo_cupom: str, db: Session) -> tuple[bool, str]:
        """Aplica um cupom ao pedido"""
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            return False, "Pedido não encontrado"
        pedido = cast(Any, pedido)

        if pedido.status != StatusPedido.CRIADO:
            return False, "Cupom só pode ser aplicado a pedido em criação"

        valido, desconto, mensagem = OperacoesCupom.validar_cupom(
            codigo_cupom, pedido.subtotal, db
        )

        if not valido:
            return False, mensagem

        # Encontrar o cupom para guardar o ID
        cupom = db.query(Cupom).filter(Cupom.codigo == codigo_cupom).first()
        if not cupom:
            return False, "Cupom não encontrado"
        cupom = cast(Any, cupom)
        pedido.cupom_id = cupom.id
        pedido.desconto = desconto
        db.commit()

        return True, f"Cupom aplicado: R${desconto:.2f} de desconto"

    @staticmethod
    def remover_cupom(pedido_id: int, db: Session) -> tuple[bool, str]:
        """Remove o cupom do pedido"""
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            return False, "Pedido não encontrado"
        pedido = cast(Any, pedido)

        if pedido.status != StatusPedido.CRIADO:
            return False, "Cupom só pode ser removido de pedido em criação"

        pedido.cupom_id = None
        pedido.desconto = 0.0
        db.commit()

        return True, "Cupom removido"

    @staticmethod
    def definir_tipo_pedido(pedido_id: int, tipo: TipoPedido, db: Session) -> tuple[bool, str]:
        """Define o tipo do pedido e calcula a taxa de entrega"""
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            return False, "Pedido não encontrado"
        pedido = cast(Any, pedido)

        if pedido.status != StatusPedido.CRIADO:
            return False, "Tipo só pode ser definido para pedido em criação"

        # Calcular taxa de entrega
        taxa_entrega = OperacoesPedido._calcular_taxa_entrega(
            tipo, pedido.subtotal - pedido.desconto
        )

        pedido.tipo = tipo
        pedido.taxa_entrega = taxa_entrega

        # Recalcular total
        pedido.total = (pedido.subtotal - pedido.desconto) + taxa_entrega
        db.commit()

        return True, f"Tipo definido para {tipo.value}, taxa: R${taxa_entrega:.2f}"

    @staticmethod
    def _calcular_taxa_entrega(tipo: TipoPedido, subtotal_com_desconto: float) -> float:
        """
        Calcula a taxa de entrega baseado no tipo de pedido e subtotal com desconto aplicado
        As regras são:
        - Retirada ou consumo local: R$0
        - Entrega: R$10 (grátis se subtotal >= R$50)
        """
        if tipo == TipoPedido.RETIRADA or tipo == TipoPedido.CONSUMO_LOCAL:
            return 0.0

        if tipo == TipoPedido.ENTREGA:
            if subtotal_com_desconto >= 50.0:
                return 0.0
            return 10.0

        return 0.0

    @staticmethod
    def finalizar_pedido(pedido_id: int, db: Session, codigo_cupom: str | None = None) -> tuple[bool, str]:
        """ Finaliza o pedido (muda status para PAGO) e decrementa o estoque dos produtos """
        # Executar validações e alterações em transação atômica
        try:
            with db.begin():
                pedido_query = db.query(Pedido).filter(Pedido.id == pedido_id)
                try:
                    pedido = pedido_query.with_for_update().first() 
                except Exception:
                    pedido = pedido_query.first()

                if not pedido:
                    return False, "Pedido não encontrado"
                pedido = cast(Any, pedido)

                if pedido.status != StatusPedido.CRIADO:
                    return False, "Pedido não está em criação"

                if pedido.tipo is None:
                    return False, "Defina o tipo do pedido antes de finalizar"

                # Revalidar/aplicar cupom dentro da transação
                if codigo_cupom:
                    valido, desconto, mensagem = OperacoesCupom.validar_cupom(
                        codigo_cupom, pedido.subtotal, db
                    )
                    if not valido:
                        return False, mensagem

                    cupom = db.query(Cupom).filter(Cupom.codigo == codigo_cupom).first()
                    if not cupom:
                        return False, "Cupom não encontrado"
                    cupom = cast(Any, cupom)
                    pedido.cupom_id = cupom.id
                    pedido.desconto = desconto
                elif pedido.cupom_id:
                    # Revalidar cupom previamente aplicado
                    cupom = db.query(Cupom).filter(Cupom.id == pedido.cupom_id).first()
                    if not cupom:
                        return False, "Cupom não encontrado"
                    valido, desconto, mensagem = OperacoesCupom.validar_cupom(cupom.codigo, pedido.subtotal, db)
                    if not valido:
                        return False, mensagem
                    pedido.desconto = desconto

                # Recalcular taxa de entrega se necessário
                if pedido.tipo is not None:
                    pedido.taxa_entrega = OperacoesPedido._calcular_taxa_entrega(pedido.tipo, pedido.subtotal - pedido.desconto)

                # Recalcular total
                pedido.total = (pedido.subtotal - pedido.desconto) + pedido.taxa_entrega

                # Marcar como pago
                pedido.status = StatusPedido.PAGO

            return True, f"Pedido finalizado. Total: R${pedido.total:.2f}"
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            return False, f"Erro ao finalizar pedido: {str(e)}"

    @staticmethod
    def cancelar_pedido(pedido_id: int, db: Session) -> tuple[bool, str]:
        """Cancela um pedido (só se ainda não foi pago)"""
        pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
        if not pedido:
            return False, "Pedido não encontrado"
        pedido = cast(Any, pedido)

        if pedido.status == StatusPedido.PAGO:
            return False, "Não é possível cancelar um pedido já pago"

        if pedido.status == StatusPedido.CANCELADO:
            return False, "Pedido já foi cancelado"

        # Restaurar estoque reservado por itens do pedido
        itens = db.query(ItemPedido).filter(ItemPedido.pedido_id == pedido_id).all()
        for item in itens:
            produto = db.query(Produto).filter(Produto.id == item.produto_id).first()
            if not produto:
                continue
            produto = cast(Any, produto)
            produto.estoque += item.quantidade
            db.add(produto)

        pedido.status = StatusPedido.CANCELADO
        db.commit()

        return True, "Pedido cancelado com sucesso"

    @staticmethod
    def obter_pedido(pedido_id: int, db: Session) -> Pedido | None:
        """Obtém um pedido com todos seus detalhes"""
        return db.query(Pedido).filter(Pedido.id == pedido_id).first()

    @staticmethod
    def listar_itens_pedido(pedido_id: int, db: Session):
        """Lista todos os itens de um pedido"""
        return db.query(ItemPedido).filter(ItemPedido.pedido_id == pedido_id).all()
