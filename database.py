import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

# Postgres in Docker sets DATABASE_URL; without it we keep using SQLite.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///tasks.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


def get_db():
    """Give each request its own session and always close it afterwards."""
    with Session(engine) as session:
        yield session