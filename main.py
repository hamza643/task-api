from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class TaskCreate(BaseModel):
    title: str


@app.get("/")
def root():
    return {"message": "Welcome to the Task API"}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    return {"task_id": task_id}


@app.post("/tasks")
def create_task(task_in: TaskCreate):
    return {"title": task_in.title}