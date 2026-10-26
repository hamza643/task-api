from pydantic import BaseModel, field_validator


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

    model_config = {"from_attributes": True}