"""Run the full pipeline: scrape -> clean -> store.

Usage:
    python run_books.py          # all pages, saves to the database
    python run_books.py 2        # only 2 pages (quick test)
    python run_books.py 2 --dry  # 2 pages, print results, skip the database
"""
import logging
import sys

from scrapers.books import scrape_all
from pipeline.clean import clean_all
from pipeline.db import get_conn, init_db, save_books

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    max_pages = int(args[0]) if args else None

    cleaned = clean_all(scrape_all(max_pages=max_pages))
    if dry:
        for book in cleaned[:5]:
            print(book)
        print(f"Dry run: {len(cleaned)} clean records, nothing saved.")
        return

    with get_conn() as conn:
        init_db(conn)
        save_books(conn, cleaned)
    logging.info("Saved %d books to the database", len(cleaned))


if __name__ == "__main__":
    main()
