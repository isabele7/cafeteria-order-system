from typing import List, Optional
from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime as SQLDateTime, Enum as SQLEnum, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from app.database import Base

class StatusPedido(str, Enum):
    CRIADO = "criado"
    PAGO = "pago"
    CANCELADO = "cancelado"

class TipoPedido(str, Enum):
    RETIRADA = "retirada"
    CONSUMO_LOCAL = "consumo_local"
    ENTREGA = "entrega"

# Colunas de produto: id, nome, preco, estoque, criado_em, atualizado_em
class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    preco: Mapped[float] = mapped_column(Float, nullable=False)
    estoque: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    criado_em: Mapped[SQLDateTime] = mapped_column(SQLDateTime, server_default=func.now())
    atualizado_em: Mapped[SQLDateTime] = mapped_column(SQLDateTime, server_default=func.now(), onupdate=func.now())

    itens: Mapped[List["ItemPedido"]] = relationship("ItemPedido", back_populates="produto")

    def __repr__(self):
        return f"<Produto(id={self.id}, nome={self.nome}, preco={self.preco}, estoque={self.estoque})>"

# Colunas de cupom: id, codigo, desconto, minimo, ativo, criado_em
class Cupom(Base):
    __tablename__ = "cupons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    codigo: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    desconto: Mapped[float] = mapped_column(Float, nullable=False)  # Percentual 
    minimo: Mapped[float] = mapped_column(Float, default=50.0)  # Mínimo de subtotal
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)  # True = ativo, False = inativo
    criado_em: Mapped[SQLDateTime] = mapped_column(SQLDateTime, server_default=func.now())
    ativo_de: Mapped[SQLDateTime] = mapped_column(SQLDateTime, nullable=True)  # Data de ativação
    ativo_ate: Mapped[SQLDateTime] = mapped_column(SQLDateTime, nullable=True)  # Data de expiração
    usos: Mapped[int] = mapped_column(Integer, default=0)  # Quantidade de vezes que o cupom foi usado
    max_usos_por_cliente: Mapped[int] = mapped_column(Integer, nullable=True)  # Limite de usos por cliente

    pedidos: Mapped[List["Pedido"]] = relationship("Pedido", back_populates="cupom")

    def __repr__(self):
        return f"<Cupom(codigo={self.codigo}, desconto={self.desconto}% )>"

# Colunas de pedido: id, status, tipo, subtotal, desconto, taxa_entrega, total, cupom_id, criado_em, atualizado_em
class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cliente_id: Mapped[str] = mapped_column(String, nullable=True, index=True)  # CPF do cliente (opcional)
    status: Mapped[StatusPedido] = mapped_column(SQLEnum(StatusPedido), default=StatusPedido.CRIADO, nullable=False)
    tipo: Mapped[Optional[TipoPedido]] = mapped_column(SQLEnum(TipoPedido), nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    desconto: Mapped[float] = mapped_column(Float, default=0.0)
    taxa_entrega: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    cupom_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cupons.id"), nullable=True)
    criado_em: Mapped[SQLDateTime] = mapped_column(SQLDateTime, server_default=func.now())
    atualizado_em: Mapped[SQLDateTime] = mapped_column(SQLDateTime, server_default=func.now(), onupdate=func.now())

    itens: Mapped[List["ItemPedido"]] = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    cupom: Mapped[Optional["Cupom"]] = relationship("Cupom", back_populates="pedidos")

    def __repr__(self):
        return f"<Pedido(id={self.id}, status={self.status}, total={self.total})>"

# Colunas de item_pedido: id, pedido_id, produto_id, quantidade, preco_unitario, subtotal, criado_em
class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False, index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    criado_em: Mapped[SQLDateTime] = mapped_column(SQLDateTime, server_default=func.now())

    pedido: Mapped["Pedido"] = relationship("Pedido", back_populates="itens")
    produto: Mapped["Produto"] = relationship("Produto", back_populates="itens")

    def __repr__(self):
        return f"<ItemPedido(pedido_id={self.pedido_id}, produto_id={self.produto_id}, qtd={self.quantidade})>"