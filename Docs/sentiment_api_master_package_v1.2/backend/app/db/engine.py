from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from ..settings import settings

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine

def db_ping() -> tuple[bool, str | None]:
    try:
        eng = get_engine()
        with eng.connect() as conn:
            conn.execute(text("select 1"))
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, str(e)
