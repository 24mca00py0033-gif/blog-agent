from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


def _normalize(url: str) -> str:
    """Accept Neon's plain postgres:// or postgresql:// string and use the psycopg2 driver."""
    url = url.strip().strip('"').strip("'")
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg2://" + url[len(prefix):]
    return url


# pool_pre_ping handles Neon closing idle connections (scale-to-zero)
engine = create_engine(_normalize(get_settings().database_url), pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()