import os
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm  import DeclarativeBase, Session, sessionmaker

DATABASE_URL = oc.getenv(
    "DATABASE_URL",
    "postgres://postgres:postgres@localhost:5432/postgres"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_bd() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()