from fastapi import FastAPI

import models  # noqa: F401  (tables ko Base mein register karne ke liye)
from database import Base, engine
from schemas import TaskCreate

Base.metadata.create_all(engine)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Welcome to the Task API"}


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    return {"task_id": task_id}


@app.post("/tasks")
def create_task(task_in: TaskCreate):
    return {"title": task_in.title}