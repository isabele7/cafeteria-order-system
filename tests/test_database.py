from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as database

def configurar_banco_temporario(tmp_path):
    caminho_banco = tmp_path / "cafeteria_order_system_test.db"
    database_url_temporaria = f"sqlite:///{caminho_banco}"
    engine_temporario = create_engine(
        database_url_temporaria,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    session_local_temporaria = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine_temporario,
    )
    return engine_temporario, session_local_temporaria, database_url_temporaria, caminho_banco

def test_criar_arquivo_do_banco(tmp_path):
    engine_anterior = database.engine
    session_local_anterior = database.SessionLocal
    database_url_anterior = database.DATABASE_URL

    engine_temporario, session_local_temporaria, database_url_temporaria, caminho_banco = (
        configurar_banco_temporario(tmp_path)
    )

    database.engine = engine_temporario
    database.SessionLocal = session_local_temporaria
    database.DATABASE_URL = database_url_temporaria

    try:
        database.init_db()

        assert caminho_banco.exists() is True
    finally:
        engine_temporario.dispose()
        database.engine = engine_anterior
        database.SessionLocal = session_local_anterior
        database.DATABASE_URL = database_url_anterior


def test_abrir_fechar_sessao(tmp_path):
    engine_anterior = database.engine
    session_local_anterior = database.SessionLocal
    database_url_anterior = database.DATABASE_URL

    engine_temporario, session_local_temporaria, database_url_temporaria, _ = (
        configurar_banco_temporario(tmp_path)
    )

    database.engine = engine_temporario
    database.SessionLocal = session_local_temporaria
    database.DATABASE_URL = database_url_temporaria

    try:
        gerador = database.get_db()

        sessao = next(gerador)

        assert sessao is not None
        assert hasattr(sessao, "execute")

        try:
            next(gerador)
        except StopIteration:
            pass
    finally:
        engine_temporario.dispose()
        database.engine = engine_anterior
        database.SessionLocal = session_local_anterior
        database.DATABASE_URL = database_url_anterior