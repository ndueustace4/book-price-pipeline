from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_invalid_sort_is_rejected_before_touching_the_database():
    assert client.get("/books?sort=title;DROP TABLE books").status_code == 422


def test_invalid_rating_is_rejected():
    assert client.get("/books?min_rating=9").status_code == 422


def test_limit_is_capped():
    assert client.get("/books?limit=1000").status_code == 422
