from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

import models  # noqa: F401
from database import Base, engine, get_db
from models import Task, User
from schemas import TaskCreate, TaskOut, UserCreate, UserOut
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

Base.metadata.create_all(engine)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Welcome to the Task API"}

@app.get("/health")
def health():
    return {"status": "ok"}

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


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalars(select(User).where(User.username == form.username)).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {"access_token": create_access_token(user.username), "token_type": "bearer"}


@app.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@app.get("/tasks", response_model=list[TaskOut])
def list_all_tasks(db: Session = Depends(get_db)):
    """Public on purpose: anyone can see every task, no login needed."""
    return db.scalars(select(Task)).all()


@app.get("/tasks/mine", response_model=list[TaskOut])
def list_my_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Protected AND filtered: only this user's own tasks."""
    return db.scalars(select(Task).where(Task.owner_id == current_user.id)).all()


@app.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Protected. The owner is the logged-in user, the client can't choose it."""
    task = Task(title=task_in.title, owner_id=current_user.id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Protected and ownership-checked: only the owner can delete."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your task")
    db.delete(task)
    db.commit()