from datetime import datetime, timedelta
from app.database import SessionLocal, init_db
from app.models import Produto, Cupom

def seed_database():
    init_db()
    db = SessionLocal()

    try:
        if db.query(Produto).count() > 0 or db.query(Cupom).count() > 0:
            print("Banco já contém dados. Abortando seed.")
            return

        produtos = [
            Produto(nome="Café Coado", preco=3.5, estoque=50),
            Produto(nome="Café Expresso", preco=4.0, estoque=50),
            Produto(nome="Cappuccino", preco=7.0, estoque=40),
            Produto(nome="Latte", preco=8.0, estoque=40),
            Produto(nome="Bolo de Chocolate", preco=12.0, estoque=20),
            Produto(nome="Bolo de Cenoura", preco=10.0, estoque=20),
            Produto(nome="Croissant", preco=8.5, estoque=30),
            Produto(nome="Pão de Queijo", preco=5.0, estoque=35),
            Produto(nome="Suco Natural", preco=7.0, estoque=25),
            Produto(nome="Refrigerante", preco=5.0, estoque=50),
            Produto(nome="Produto Sem Estoque", preco=6.0, estoque=0),
        ]

        agora = datetime.utcnow()

        cupons = [
            Cupom(
                codigo="DESC10",
                desconto=10.0,
                minimo=50.0,
                ativo=True,
            ),
            Cupom(
                codigo="DESC20",
                desconto=20.0,
                minimo=100.0,
                ativo=True,
            ),
            Cupom(
                codigo="CPF10",
                desconto=10.0,
                minimo=30.0,
                ativo=True,
                max_usos_por_cliente=1,
            ),
            Cupom(
                codigo="PROMO15",
                desconto=15.0,
                minimo=75.0,
                ativo=True,
                ativo_de=agora - timedelta(days=1),
                ativo_ate=agora + timedelta(days=7),
            ),
            Cupom(
                codigo="EXPIRADO",
                desconto=10.0,
                minimo=30.0,
                ativo=True,
                ativo_ate=agora - timedelta(days=1),
            ),
            Cupom(
                codigo="FUTURO",
                desconto=10.0,
                minimo=30.0,
                ativo=True,
                ativo_de=agora + timedelta(days=1),
            ),
            Cupom(
                codigo="INATIVO",
                desconto=10.0,
                minimo=30.0,
                ativo=False,
            ),
        ]

        db.add_all(produtos)
        db.add_all(cupons)
        db.commit()

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()