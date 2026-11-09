from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_connect_args = {}
if settings.DB_SSL:
    _ssl: dict = {}
    if settings.DB_SSL_CA:
        _ssl["ca"] = settings.DB_SSL_CA
    _connect_args["ssl"] = _ssl if _ssl else {"ssl": {}}

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import app.models  # noqa: F401
    verify_database_connection()


def verify_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
