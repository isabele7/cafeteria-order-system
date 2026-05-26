from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
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

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, unique=True, index=True, nullable=False)
    preco = Column(Float, nullable=False)
    estoque = Column(Integer, nullable=False, default=0)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Produto(id={self.id}, nome={self.nome}, preco={self.preco}, estoque={self.estoque})>"

# Colunas de cupom: id, codigo, desconto, minimo, ativo, criado_em
class Cupom(Base):
    __tablename__ = "cupons"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False)
    desconto = Column(Float, nullable=False)  # Percentual (ex: 10 para 10%)
    minimo = Column(Float, default=50.0)  # Mínimo de subtotal
    ativo = Column(Integer, default=1)  # 1 = ativo, 0 = inativo
    criado_em = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Cupom(codigo={self.codigo}, desconto={self.desconto}%)>"

# Colunas de pedido: id, status, tipo, subtotal, desconto, taxa_entrega, total, cupom_id, criado_em, atualizado_em
class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(SQLEnum(StatusPedido), default=StatusPedido.CRIADO, nullable=False)
    tipo = Column(SQLEnum(TipoPedido), nullable=True)
    subtotal = Column(Float, default=0.0)
    desconto = Column(Float, default=0.0)
    taxa_entrega = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    cupom_id = Column(Integer, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Pedido(id={self.id}, status={self.status}, total={self.total})>"

# Colunas de item_pedido: id, pedido_id, produto_id, quantidade, preco_unitario, subtotal, criado_em
class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, nullable=False, index=True)
    produto_id = Column(Integer, nullable=False)
    quantidade = Column(Integer, nullable=False)
    preco_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    criado_em = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ItemPedido(pedido_id={self.pedido_id}, produto_id={self.produto_id}, qtd={self.quantidade})>"