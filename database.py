from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from settings import DATABASE_URL

# check_same_thread is a SQLite-only option, Postgres would reject it.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)


class Base(DeclarativeBase):
    pass


def get_db():
    """Give each request its own session and always close it afterwards."""
    with Session(engine) as session:
        yield session