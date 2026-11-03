"""Scraper for quotes.toscrape.com/js - a page whose content is rendered by JavaScript.

A plain requests.get() would see an empty page here, so we load it in a real
(headless) browser with Playwright, then parse the rendered HTML with BeautifulSoup.
"""
import logging
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

BASE_URL = "https://quotes.toscrape.com/js/"
DELAY_SECONDS = 1

# All CSS selectors live here, so a layout change only needs edits in one place.
SELECTORS = {
    "item": "div.quote",
    "text": "span.text",
    "author": "small.author",
    "tag": "div.tags a.tag",
    "next": "li.next a",
}


class StructureChangedError(Exception):
    """Raised when the page renders but the expected elements are missing."""


def parse_quotes(html):
    """Return (list of quote dicts, href of the next page or None) from rendered HTML."""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(SELECTORS["item"])
    if not items:
        raise StructureChangedError("No quotes found - selectors may be outdated")

    quotes = []
    for item in items:
        text_el = item.select_one(SELECTORS["text"])
        author_el = item.select_one(SELECTORS["author"])
        if not text_el or not author_el:
            log.warning("Skipping a malformed quote block")
            continue
        quotes.append({
            "text": text_el.get_text(strip=True).strip('\u201c\u201d"'),
            "author": author_el.get_text(strip=True),
            "tags": [t.get_text(strip=True) for t in item.select(SELECTORS["tag"])],
        })

    nxt = soup.select_one(SELECTORS["next"])
    return quotes, (nxt["href"] if nxt else None)


def scrape_all(max_pages=None):
    """Load each page in headless Chromium, wait for the JS to render, and parse it."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    url, page_no, all_quotes = BASE_URL, 1, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            while url and (max_pages is None or page_no <= max_pages):
                log.info("Scraping page %d: %s", page_no, url)
                page.goto(url, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector(SELECTORS["item"], timeout=15000)
                except PlaywrightTimeout:
                    raise StructureChangedError(f"Quotes never rendered on {url}")
                quotes, next_href = parse_quotes(page.content())
                all_quotes.extend(quotes)
                url = urljoin(BASE_URL, next_href) if next_href else None
                page_no += 1
                time.sleep(DELAY_SECONDS)
        finally:
            browser.close()
    log.info("Scraped %d quotes from %d pages", len(all_quotes), page_no - 1)
    return all_quotes


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    for q in scrape_all(max_pages=1)[:3]:
        print(q)
