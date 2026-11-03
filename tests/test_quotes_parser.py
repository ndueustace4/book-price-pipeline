from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.quotes import router
from pipeline.quotes_db import dedupe
from scrapers.quotes_js import StructureChangedError, parse_quotes

FIXTURE = Path(__file__).parent / "quotes_page.html"


def test_parse_quotes_extracts_text_author_tags_and_next_link():
    quotes, next_href = parse_quotes(FIXTURE.read_text(encoding="utf-8"))
    assert len(quotes) == 2
    assert quotes[0] == {
        "text": "The world as we have created it is a process of our thinking.",
        "author": "Albert Einstein",
        "tags": ["change", "deep-thoughts"],
    }
    assert next_href == "/js/page/2/"


def test_parse_quotes_raises_when_structure_changes():
    changed = FIXTURE.read_text(encoding="utf-8").replace('class="quote"', 'class="card"')
    with pytest.raises(StructureChangedError):
        parse_quotes(changed)


def test_dedupe_removes_repeated_quotes():
    q = {"text": "a", "author": "b", "tags": []}
    assert len(dedupe([q, dict(q)])) == 1


def test_quotes_api_rejects_bad_limits():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    assert client.get("/quotes?limit=500").status_code == 422
    assert client.get("/quotes?offset=-1").status_code == 422
