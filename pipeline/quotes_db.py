"""Storage for scraped quotes (same Neon database as the books)."""
SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    author TEXT NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    first_seen TIMESTAMPTZ DEFAULT now(),
    last_seen TIMESTAMPTZ DEFAULT now(),
    UNIQUE (text, author)
);
"""


def init_quotes_table(conn):
    conn.execute(SCHEMA)
    conn.commit()


def dedupe(quotes):
    seen, unique = set(), []
    for q in quotes:
        key = (q["text"], q["author"])
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


def save_quotes(conn, quotes):
    quotes = dedupe(quotes)
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO quotes (text, author, tags) VALUES (%s, %s, %s)
            ON CONFLICT (text, author) DO UPDATE SET tags = EXCLUDED.tags, last_seen = now()
            """,
            [(q["text"], q["author"], q["tags"]) for q in quotes],
        )
    conn.commit()
    return len(quotes)
