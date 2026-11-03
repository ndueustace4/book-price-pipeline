"""Run the quotes pipeline: scrape -> deduplicate -> store."""
import logging
import sys

from pipeline.db import get_conn
from pipeline.quotes_db import dedupe, init_quotes_table, save_quotes
from scrapers.quotes_js import scrape_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    dry = "--dry" in sys.argv
    max_pages = int(args[0]) if args else None

    quotes = dedupe(scrape_all(max_pages=max_pages))
    if dry:
        for quote in quotes[:5]:
            print(quote)
        print(f"Dry run: {len(quotes)} unique quotes, nothing saved.")
        return

    with get_conn() as conn:
        init_quotes_table(conn)
        saved = save_quotes(conn, quotes)
    logging.info("Saved %d unique quotes to the database", saved)


if __name__ == "__main__":
    main()
