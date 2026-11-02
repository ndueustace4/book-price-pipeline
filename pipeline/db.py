"""PostgreSQL storage (works with Neon). Reads DATABASE_URL from the .env file."""
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    rating INT,
    in_stock BOOLEAN,
    first_seen TIMESTAMPTZ DEFAULT now(),
    last_seen TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    book_id INT REFERENCES books(id),
    price NUMERIC(8, 2) NOT NULL,
    scraped_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_price_history_book ON price_history (book_id, scraped_at DESC);
"""


def get_conn():
    return psycopg.connect(os.environ["DATABASE_URL"])


def init_db(conn):
    conn.execute(SCHEMA)
    conn.commit()


def save_books(conn, books):
    """Upsert every book, then add one price-history row each, using batched statements.

    executemany sends many statements per network round trip (psycopg pipeline mode),
    which is far faster than one round trip per row on a remote database like Neon.
    """
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO books (url, title, rating, in_stock)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (url) DO UPDATE
            SET title = EXCLUDED.title, rating = EXCLUDED.rating,
                in_stock = EXCLUDED.in_stock, last_seen = now()
            """,
            [(b["url"], b["title"], b["rating"], b["in_stock"]) for b in books],
        )
        cur.executemany(
            "INSERT INTO price_history (book_id, price) SELECT id, %s FROM books WHERE url = %s",
            [(b["price"], b["url"]) for b in books],
        )
    conn.commit()
