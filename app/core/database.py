import os
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm  import DeclarativeBase, Session, sessionmaker

DB_USER = os.getenv("POSTGRES_USER", "app_user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "supersecretpassword")
DB_NAME = os.getenv("POSTGRES_DB", "app_db")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
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