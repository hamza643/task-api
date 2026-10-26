from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

engine = create_engine(
    "sqlite:///tasks.db",
    connect_args={"check_same_thread": False},
)


class Base(DeclarativeBase):
    pass


def get_db():
    """Give each request its own session and always close it afterwards."""
    with Session(engine) as session:
        yield session