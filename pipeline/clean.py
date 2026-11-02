"""Turn raw scraped strings into clean, typed records."""
import logging
import re

log = logging.getLogger(__name__)

RATING_MAP = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def clean_book(raw):
    """Convert one raw dict into a clean dict, or return None if it is unusable."""
    match = re.search(r"\d+(?:\.\d+)?", raw.get("price_raw", ""))
    if not match or not raw.get("title"):
        log.warning("Dropping unusable record: %s", raw)
        return None
    rating = next((RATING_MAP[w] for w in raw.get("rating_raw", "").split() if w in RATING_MAP), None)
    return {
        "title": raw["title"].strip(),
        "url": raw["url"],
        "price": float(match.group()),
        "in_stock": "in stock" in raw.get("availability_raw", "").lower(),
        "rating": rating,
    }


def clean_all(raw_books):
    """Clean every record and remove duplicates (by URL)."""
    seen, cleaned = set(), []
    for raw in raw_books:
        book = clean_book(raw)
        if book and book["url"] not in seen:
            seen.add(book["url"])
            cleaned.append(book)
    log.info("Cleaned %d of %d records", len(cleaned), len(raw_books))
    return cleaned
