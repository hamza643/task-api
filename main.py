from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

import models  # noqa: F401
from database import Base, engine, get_db
from models import Comment, Project, Tag, Task, User
from schemas import (
    CommentCreate,
    CommentOut,
    ProjectCreate,
    ProjectOut,
    TagCreate,
    TagOut,
    TaskCreate,
    TaskOut,
    UserCreate,
    UserOut,
)
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

Base.metadata.create_all(engine)

app = FastAPI()


def get_owned_task(db: Session, task_id: int, user: User) -> Task:
    """Load a task and make sure it belongs to this user (404 or 403 otherwise)."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your task")
    return task


def get_owned_project(db: Session, project_id: int, user: User) -> Project:
    """Load a project and make sure it belongs to this user (404 or 403 otherwise)."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not your project")
    return project


# ---------- basics ----------


@app.get("/")
def root():
    return {"message": "Welcome to the Task API"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- auth ----------


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


# ---------- tasks ----------


@app.get("/tasks", response_model=list[TaskOut])
def list_all_tasks(tag: Optional[str] = None, db: Session = Depends(get_db)):
    """Public on purpose: anyone can see every task. Optional ?tag=urgent filter."""
    stmt = select(Task)
    if tag:
        stmt = stmt.join(Task.tags).where(Tag.name == tag.strip().lower())
    return db.scalars(stmt).all()


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


# ---------- projects (one project -> many tasks) ----------


@app.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = Project(name=project_in.name, owner_id=current_user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects/mine", response_model=list[ProjectOut])
def list_my_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(select(Project).where(Project.owner_id == current_user.id)).all()


@app.post("/projects/{project_id}/tasks/{task_id}", response_model=TaskOut)
def attach_task_to_project(
    project_id: int,
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Both the project and the task must belong to the logged-in user."""
    project = get_owned_project(db, project_id, current_user)
    task = get_owned_task(db, task_id, current_user)
    task.project_id = project.id
    db.commit()
    db.refresh(task)
    return task


@app.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_project_tasks(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_owned_project(db, project_id, current_user)
    return project.tasks


# ---------- comments (a comment has TWO owners: its task and its author) ----------


@app.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    task_id: int,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Any logged-in user can comment on any task. The author is the current user."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    comment = Comment(text=comment_in.text, task_id=task.id, author_id=current_user.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@app.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
def list_comments(task_id: int, db: Session = Depends(get_db)):
    """Public, like /tasks."""
    task = db.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.comments


@app.delete("/comments/{comment_id}", status_code=204)
def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The comment's author OR the owner of the task it is on can delete it."""
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    if current_user.id not in (comment.author_id, comment.task.owner_id):
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(comment)
    db.commit()


# ---------- tags (many tasks <-> many tags) ----------


@app.post("/tasks/{task_id}/tags", response_model=TaskOut)
def tag_task(
    task_id: int,
    tag_in: TagCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only the task's owner can tag it. A tag is created the first time it is used."""
    task = get_owned_task(db, task_id, current_user)
    tag = db.scalars(select(Tag).where(Tag.name == tag_in.name)).first()
    if tag is None:
        tag = Tag(name=tag_in.name)
        db.add(tag)
    if tag not in task.tags:
        task.tags.append(tag)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tags", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db)):
    return db.scalars(select(Tag)).all()