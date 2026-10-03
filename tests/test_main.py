import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from database import Base, engine, SessionLocal
from main import app, hits
from models import Url

client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    hits.clear()


def shorten(url="https://example.com"):
    return client.post("/api/urls", json={"url": url}).json()["code"]


def test_create():
    res = client.post("/api/urls", json={"url": "https://example.com"})
    assert res.status_code == 201
    assert len(res.json()["code"]) == 7


def test_bad_url():
    res = client.post("/api/urls", json={"url": "hello"})
    assert res.status_code == 400
    assert "error" in res.json()


def test_redirect_counts_click():
    code = shorten()
    res = client.get(f"/{code}")
    assert res.status_code == 302
    assert res.headers["location"] == "https://example.com"
    assert client.get(f"/api/urls/{code}/stats").json()["totalClicks"] == 1


def test_unknown_code():
    assert client.get("/nope123").status_code == 404


def test_expired_link():
    db = SessionLocal()
    db.add(Url(code="old1234", original_url="https://example.com", expires_at=datetime(2020, 1, 1)))
    db.commit()
    db.close()
    assert client.get("/old1234").status_code == 410


def test_list_newest_first():
    shorten("https://a.com")
    newest = shorten("https://b.com")
    items = client.get("/api/urls?limit=1").json()["items"]
    assert items[0]["code"] == newest


def test_delete():
    code = shorten()
    assert client.delete(f"/api/urls/{code}").status_code == 204
    assert client.get(f"/{code}").status_code == 404


def test_rate_limit():
    for i in range(10):
        shorten()
    res = client.post("/api/urls", json={"url": "https://example.com"})
    assert res.status_code == 429