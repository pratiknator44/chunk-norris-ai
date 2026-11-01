"""Database session management with SQLite."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# Ensure sqlite parent directory exists
if settings.database_url.startswith("sqlite:///"):
    db_rel_path = settings.database_url.replace("sqlite:///", "")
    db_file_path = Path(db_rel_path)
    if not db_file_path.is_absolute():
        base = Path(__file__).resolve().parent.parent.parent
        db_file_path = (base / db_file_path).resolve()
    db_file_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}
    engine = create_engine(f"sqlite:///{db_file_path}", connect_args=connect_args)
else:
    engine = create_engine(settings.database_url)


def init_db() -> None:
    """Creates all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency providing a database session."""
    with Session(engine) as session:
        yield session
