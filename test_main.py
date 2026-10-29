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


def make_task(client, headers, title="a task"):
    r = client.post("/tasks", json={"title": title}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


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


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------- Project (one-to-many) ----------


def test_project_groups_tasks(client):
    signup(client, "ali")
    signup(client, "sara")
    ali = auth_headers(client, "ali")
    sara = auth_headers(client, "sara")

    project = client.post("/projects", json={"name": "Docker week"}, headers=ali)
    assert project.status_code == 201
    project_id = project.json()["id"]

    t1 = make_task(client, ali, "write Dockerfile")
    t2 = make_task(client, ali, "write compose file")
    make_task(client, ali, "unrelated task")

    r = client.post(f"/projects/{project_id}/tasks/{t1}", headers=ali)
    assert r.status_code == 200
    assert r.json()["project_id"] == project_id
    client.post(f"/projects/{project_id}/tasks/{t2}", headers=ali)

    titles = [t["title"] for t in client.get(f"/projects/{project_id}/tasks", headers=ali).json()]
    assert sorted(titles) == ["write Dockerfile", "write compose file"]

    # sara can neither look into ali's project nor attach her task to it
    assert client.get(f"/projects/{project_id}/tasks", headers=sara).status_code == 403
    sara_task = make_task(client, sara, "sara task")
    assert client.post(f"/projects/{project_id}/tasks/{sara_task}", headers=sara).status_code == 403


# ---------- Comment (two foreign keys: task + author) ----------


def test_comment_has_task_and_author(client):
    signup(client, "ali")
    signup(client, "sara")
    signup(client, "bob")
    ali = auth_headers(client, "ali")
    sara = auth_headers(client, "sara")
    bob = auth_headers(client, "bob")

    task_id = make_task(client, ali)

    # sara comments on ali's task: the comment is owned by sara, but sits on ali's task
    r = client.post(f"/tasks/{task_id}/comments", json={"text": "looks good"}, headers=sara)
    assert r.status_code == 201
    comment = r.json()
    assert comment["task_id"] == task_id
    assert comment["author_id"] == client.get("/me", headers=sara).json()["id"]

    # reading comments is public
    assert len(client.get(f"/tasks/{task_id}/comments").json()) == 1

    # a stranger cannot delete it, but the author and the task owner can
    assert client.delete(f"/comments/{comment['id']}", headers=bob).status_code == 403
    assert client.delete(f"/comments/{comment['id']}", headers=ali).status_code == 204

    again = client.post(f"/tasks/{task_id}/comments", json={"text": "second"}, headers=sara).json()
    assert client.delete(f"/comments/{again['id']}", headers=sara).status_code == 204


def test_comment_needs_login_and_existing_task(client):
    signup(client, "ali")
    ali = auth_headers(client, "ali")
    task_id = make_task(client, ali)
    assert client.post(f"/tasks/{task_id}/comments", json={"text": "hi"}).status_code == 401
    assert client.post("/tasks/999/comments", json={"text": "hi"}, headers=ali).status_code == 404


# ---------- Tag (many-to-many through task_tags) ----------


def test_tags_are_many_to_many(client):
    signup(client, "ali")
    signup(client, "sara")
    ali = auth_headers(client, "ali")
    sara = auth_headers(client, "sara")

    t1 = make_task(client, ali, "first")
    t2 = make_task(client, ali, "second")

    # the same tag on two tasks (names are case-insensitive) -> one tag row
    client.post(f"/tasks/{t1}/tags", json={"name": "Urgent"}, headers=ali)
    client.post(f"/tasks/{t2}/tags", json={"name": "urgent"}, headers=ali)
    # one task with two tags
    r = client.post(f"/tasks/{t1}/tags", json={"name": "home"}, headers=ali)
    assert sorted(t["name"] for t in r.json()["tags"]) == ["home", "urgent"]

    # tagging twice does not duplicate
    client.post(f"/tasks/{t1}/tags", json={"name": "home"}, headers=ali)

    assert sorted(t["name"] for t in client.get("/tags").json()) == ["home", "urgent"]
    assert len(client.get("/tasks", params={"tag": "urgent"}).json()) == 2
    assert [t["title"] for t in client.get("/tasks", params={"tag": "home"}).json()] == ["first"]
    assert client.get("/tasks", params={"tag": "nothing"}).json() == []

    # only the owner can tag a task
    assert client.post(f"/tasks/{t1}/tags", json={"name": "x"}, headers=sara).status_code == 403


def test_deleting_a_task_removes_its_comments_and_tag_links(client):
    signup(client, "ali")
    ali = auth_headers(client, "ali")
    task_id = make_task(client, ali)
    client.post(f"/tasks/{task_id}/comments", json={"text": "note"}, headers=ali)
    client.post(f"/tasks/{task_id}/tags", json={"name": "urgent"}, headers=ali)

    assert client.delete(f"/tasks/{task_id}", headers=ali).status_code == 204
    assert client.get(f"/tasks/{task_id}/comments").status_code == 404
    # the tag itself stays, only the link to the deleted task is gone
    assert [t["name"] for t in client.get("/tags").json()] == ["urgent"]
    assert client.get("/tasks", params={"tag": "urgent"}).json() == []