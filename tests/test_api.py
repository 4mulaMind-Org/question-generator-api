"""
Basic API tests using FastAPI TestClient.
Note: uses a fresh in-memory DB per test session via dependency override.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    # cleanup after tests: drop all tables
    Base.metadata.drop_all(bind=engine)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_add_and_list_questions():
    r = client.post("/questions", json={"content": "What is force?", "tags": "physics"})
    assert r.status_code == 200
    assert r.json()["content"] == "What is force?"

    r = client.get("/questions")
    assert r.status_code == 200
    assert any(q["content"] == "What is force?" for q in r.json())


def test_exact_duplicate():
    r = client.post("/detect-duplicate", json={"content": "What is force?"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_duplicate"] is True
    assert body["match_type"] == "exact"
    assert body["top_match"]["similarity"] == 1.0


def test_semantic_duplicate():
    r = client.post("/detect-duplicate", json={"content": "What is meant by force?"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_duplicate"] is True
    assert body["match_type"] == "semantic"
    assert body["top_match"]["similarity"] >= 0.85


def test_different_topic():
    r = client.post("/detect-duplicate", json={"content": "What is photosynthesis?"})
    assert r.status_code == 200
    body = r.json()
    assert body["is_duplicate"] is False
    assert body["match_type"] == "none"


def test_generation_succeeds():
    r = client.post("/generate", json={"topic": "energy"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["question"] is not None
    assert body["total_attempts"] >= 1