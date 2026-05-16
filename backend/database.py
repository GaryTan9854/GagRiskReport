from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
import os

DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), "db", "gagrisk", "gag_risk.db")
DB_PATH = os.getenv("DB_PATH", DEFAULT_DB_PATH if os.path.exists(os.path.join(os.path.expanduser("~"), "db")) else "./gag_risk.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
