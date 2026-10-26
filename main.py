from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

import models  # noqa: F401
from database import Base, engine, get_db
from models import User
from schemas import TaskCreate, UserCreate, UserOut
from security import hash_password

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


@app.post("/signup", response_model=UserOut, status_code=201)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.scalars(select(User).where(User.username == user_in.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    user = User(
        username=user_in.username,
        password_hash=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user