from typing import List, Optional

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

# Association table: it only holds pairs (task_id, tag_id).
# One row = "this task has this tag". This is how many-to-many works.
task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # one project -> many tasks
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))

    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    # deleting a task also deletes its comments
    comments: Mapped[List["Comment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    tags: Mapped[List["Tag"]] = relationship(secondary=task_tags, back_populates="tasks")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    # two foreign keys: the task it is on, and the user who wrote it
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    task: Mapped["Task"] = relationship(back_populates="comments")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

    tasks: Mapped[List["Task"]] = relationship(secondary=task_tags, back_populates="tags")