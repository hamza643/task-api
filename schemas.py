from typing import List, Optional

from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator("password")
    @classmethod
    def password_long_enough(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        if len(value.encode()) > 72:
            raise ValueError("password is too long (max 72 bytes)")
        return value


class UserOut(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip().lower()  # "Urgent" and "urgent" are the same tag
        if not value:
            raise ValueError("tag name cannot be blank")
        if len(value) > 50:
            raise ValueError("tag name is too long (max 50 characters)")
        return value


class TagOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title cannot be blank")
        return value


class TaskOut(BaseModel):
    id: int
    title: str
    done: bool
    project_id: Optional[int] = None
    tags: List[TagOut] = []

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("project name cannot be blank")
        return value


class ProjectOut(BaseModel):
    id: int
    name: str
    owner_id: int

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("comment cannot be blank")
        return value


class CommentOut(BaseModel):
    id: int
    text: str
    task_id: int
    author_id: int

    model_config = {"from_attributes": True}