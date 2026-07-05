"""Engine and session plumbing for the platform (SQLite in dev)."""

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_DB = Path("fleet.db")


def make_engine(db_path: str | Path = DEFAULT_DB) -> Engine:
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
