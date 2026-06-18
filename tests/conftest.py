import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import Cupom, Produto

# Banco de dados em memória para testes
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """Fixture que fornece uma sessão de banco de dados limpa para cada teste"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    """Fixture que fornece TestClient usando o banco em memoria dos testes"""
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

@pytest.fixture
def produtos_base(db):
    """Cria produtos padrão para testes"""
    cafe = Produto(nome="Café", preco=5.0, estoque=100)
    bolo = Produto(nome="Bolo", preco=8.0, estoque=5)
    suco = Produto(nome="Suco", preco=7.0, estoque=0)
    db.add(cafe)
    db.add(bolo)
    db.add(suco)
    db.commit()
    db.refresh(cafe)
    db.refresh(bolo)
    db.refresh(suco)
    return {"cafe": cafe, "bolo": bolo, "suco": suco}

@pytest.fixture
def cupons_base(db):
    """Cria cupons padrão para testes"""
    cupom_10 = Cupom(codigo="DESC10", desconto=10.0, minimo=50.0, ativo=1)
    cupom_20 = Cupom(codigo="DESC20", desconto=20.0, minimo=100.0, ativo=1)
    cupom_inativo = Cupom(codigo="INATIVO", desconto=5.0, minimo=30.0, ativo=0)
    db.add(cupom_10)
    db.add(cupom_20)
    db.add(cupom_inativo)
    db.commit()
    db.refresh(cupom_10)
    db.refresh(cupom_20)
    db.refresh(cupom_inativo)
    return {"desc10": cupom_10, "desc20": cupom_20, "inativo": cupom_inativo}