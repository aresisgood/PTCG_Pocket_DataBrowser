import warnings

from fastapi.testclient import TestClient
from sqlalchemy import event

from api import db


def test_get_database_url_uses_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///custom.db")
    assert db.get_database_url() == "sqlite:///custom.db"


def test_sqlite_engine_options_enable_cross_thread_access():
    assert db.engine_options("sqlite:///data/decks.db") == {
        "connect_args": {"check_same_thread": False}
    }


def test_non_sqlite_engine_options_are_empty():
    assert db.engine_options("postgresql+psycopg://user:secret@db/app") == {}


def test_create_app_uses_environment_database_url(monkeypatch, tmp_path):
    database_url = f"sqlite:///{tmp_path / 'configured.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    from api.main import create_app

    app = create_app()
    assert str(app.state.db_engine.url) == database_url


def test_lifespan_disposes_app_database_engine(tmp_path):
    from api.main import create_app

    app = create_app(f"sqlite:///{tmp_path / 'lifespan.db'}")
    engine_disposed = False

    @event.listens_for(app.state.db_engine, "engine_disposed")
    def observe_engine_disposal(engine):
        nonlocal engine_disposed
        engine_disposed = True

    with warnings.catch_warnings():
        warnings.simplefilter("error", ResourceWarning)
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200

    assert engine_disposed
