from pathlib import Path

import pytest

from pipeline.clean import clean_all, clean_book
from scrapers.books import StructureChangedError, parse_page

FIXTURE = Path(__file__).parent / "books_page.html"
PAGE_URL = "https://books.toscrape.com/"


def test_parse_page_extracts_books_and_next_link():
    books, next_url = parse_page(FIXTURE.read_text(encoding="utf-8"), PAGE_URL)
    assert len(books) == 2
    assert books[0]["title"] == "A Light in the Attic"
    assert books[0]["url"] == "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"


def test_parse_page_raises_when_site_structure_changes():
    # Simulates the site renaming its CSS classes: the page loads but nothing matches.
    changed = FIXTURE.read_text(encoding="utf-8").replace("product_pod", "book-card")
    with pytest.raises(StructureChangedError):
        parse_page(changed, PAGE_URL)


def test_clean_book_converts_types():
    raw = {"title": " A Light in the Attic ", "url": "u1", "price_raw": "£51.77",
           "availability_raw": "In stock", "rating_raw": "star-rating Three"}
    assert clean_book(raw) == {"title": "A Light in the Attic", "url": "u1",
                               "price": 51.77, "in_stock": True, "rating": 3}


def test_clean_book_detects_out_of_stock():
    raw = {"title": "X", "url": "u", "price_raw": "£10.00",
           "availability_raw": "Out of stock", "rating_raw": "star-rating Five"}
    assert clean_book(raw)["in_stock"] is False


def test_clean_book_drops_records_without_a_price():
    assert clean_book({"title": "X", "url": "u", "price_raw": "n/a"}) is None


def test_clean_all_removes_duplicates():
    raw = {"title": "X", "url": "same", "price_raw": "£1.00",
           "availability_raw": "In stock", "rating_raw": "star-rating One"}
    assert len(clean_all([raw, dict(raw)])) == 1
