"""Scraper for books.toscrape.com (a sandbox site built for scraping practice)."""
import logging
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE_URL = "https://books.toscrape.com/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PortfolioScraper/1.0)"}
DELAY_SECONDS = 1  # be polite: pause between requests
MAX_RETRIES = 3

# All CSS selectors live here. If the site changes its layout, only this dict changes.
SELECTORS = {
    "item": "article.product_pod",
    "title": "h3 a",
    "price": "p.price_color",
    "availability": "p.availability",
    "rating": "p.star-rating",
    "next": "li.next a",
}


class StructureChangedError(Exception):
    """Raised when a page loads but the expected elements are missing."""


def fetch(url):
    """GET a page with retries and a timeout."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            resp.encoding = "utf-8"  # avoids the broken pound sign in prices
            return resp.text
        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, url, exc)
            time.sleep(2 * attempt)
    raise RuntimeError(f"Could not fetch {url} after {MAX_RETRIES} attempts")


def parse_page(html, page_url):
    """Return (list of raw book dicts, url of next page or None)."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(SELECTORS["item"])
    if not items:
        raise StructureChangedError(f"No books found on {page_url} - selectors may be outdated")

    books = []
    for item in items:
        try:
            link = item.select_one(SELECTORS["title"])
            books.append({
                "title": link["title"],
                "url": urljoin(page_url, link["href"]),
                "price_raw": item.select_one(SELECTORS["price"]).get_text(strip=True),
                "availability_raw": item.select_one(SELECTORS["availability"]).get_text(strip=True),
                "rating_raw": " ".join(item.select_one(SELECTORS["rating"])["class"]),
            })
        except (AttributeError, KeyError, TypeError) as exc:
            log.warning("Skipping a malformed item on %s: %s", page_url, exc)

    nxt = soup.select_one(SELECTORS["next"])
    next_url = urljoin(page_url, nxt["href"]) if nxt else None
    return books, next_url


def scrape_all(max_pages=None):
    """Walk through every page of the catalogue and return raw book dicts."""
    url, page, all_books = BASE_URL, 1, []
    while url and (max_pages is None or page <= max_pages):
        log.info("Scraping page %d: %s", page, url)
        books, url = parse_page(fetch(url), url)
        all_books.extend(books)
        page += 1
        time.sleep(DELAY_SECONDS)
    log.info("Scraped %d books from %d pages", len(all_books), page - 1)
    return all_books


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sample = scrape_all(max_pages=2)
    for book in sample[:3]:
        print(book)
