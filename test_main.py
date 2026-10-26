import pytest
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from security import create_access_token


@pytest.fixture()
def client():
    """Har test ko apni khali, alag database milti hai (tasks.db ko haath nahi lagta)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def signup(client, username, password="password123"):
    return client.post("/signup", json={"username": username, "password": password})


def auth_headers(client, username, password="password123"):
    r = client.post("/login", data={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_signup_same_username_twice_fails(client):
    assert signup(client, "ali").status_code == 201
    assert signup(client, "ali").status_code == 400


def test_login_with_wrong_password_fails(client):
    signup(client, "ali")
    r = client.post("/login", data={"username": "ali", "password": "wrongpass"})
    assert r.status_code == 401


def test_create_task_without_token_fails(client):
    r = client.post("/tasks", json={"title": "no auth"})
    assert r.status_code == 401


def test_users_only_see_their_own_tasks(client):
    signup(client, "ali")
    signup(client, "sara")
    ali = auth_headers(client, "ali")
    sara = auth_headers(client, "sara")

    client.post("/tasks", json={"title": "ali task"}, headers=ali)
    client.post("/tasks", json={"title": "sara task"}, headers=sara)

    ali_titles = [t["title"] for t in client.get("/tasks/mine", headers=ali).json()]
    sara_titles = [t["title"] for t in client.get("/tasks/mine", headers=sara).json()]
    assert ali_titles == ["ali task"]
    assert sara_titles == ["sara task"]

    # /tasks is public on purpose: it shows everyone's tasks
    assert len(client.get("/tasks").json()) == 2


def test_user_cannot_delete_another_users_task(client):
    signup(client, "ali")
    signup(client, "sara")
    ali = auth_headers(client, "ali")
    sara = auth_headers(client, "sara")

    task_id = client.post("/tasks", json={"title": "ali task"}, headers=ali).json()["id"]

    assert client.delete(f"/tasks/{task_id}", headers=sara).status_code == 403
    # the task must still exist, and its owner can delete it
    assert len(client.get("/tasks/mine", headers=ali).json()) == 1
    assert client.delete(f"/tasks/{task_id}", headers=ali).status_code == 204


def test_expired_token_is_rejected(client):
    signup(client, "ali")
    expired = create_access_token("ali", expires_delta=timedelta(minutes=-5))
    r = client.get("/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401