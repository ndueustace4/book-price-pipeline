"""FastAPI service exposing the scraped book data.

Run locally:  uvicorn api.main:app --reload
Docs:         http://127.0.0.1:8000/docs
"""
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row

from api.quotes import router as quotes_router
from pipeline.db import get_conn

app = FastAPI(title="Book Price Pipeline API", version="1.0.0")
app.include_router(quotes_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://localhost:8080",
    ).split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Only these values can reach the ORDER BY clause (prevents SQL injection).
SORT_COLUMNS = {"price": "ph.price", "rating": "b.rating", "title": "b.title"}

LATEST_PRICE_JOIN = """
    FROM books b
    JOIN LATERAL (
        SELECT price FROM price_history
        WHERE book_id = b.id ORDER BY scraped_at DESC, id DESC LIMIT 1
    ) ph ON true
"""


def query(sql, params=()):
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/books")
def list_books(
    search: Optional[str] = Query(None, max_length=100, description="Match part of the title"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    in_stock: Optional[bool] = None,
    sort: str = Query("title", pattern="^(price|rating|title)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conditions, params = [], []
    if search:
        conditions.append("b.title ILIKE %s")
        params.append(f"%{search}%")
    if min_price is not None:
        conditions.append("ph.price >= %s")
        params.append(min_price)
    if max_price is not None:
        conditions.append("ph.price <= %s")
        params.append(max_price)
    if min_rating is not None:
        conditions.append("b.rating >= %s")
        params.append(min_rating)
    if in_stock is not None:
        conditions.append("b.in_stock = %s")
        params.append(in_stock)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = query(f"SELECT COUNT(*) AS n {LATEST_PRICE_JOIN} {where}", params)[0]["n"]
    rows = query(
        f"""SELECT b.id, b.title, b.url, b.rating, b.in_stock, ph.price::float AS price
            {LATEST_PRICE_JOIN} {where}
            ORDER BY {SORT_COLUMNS[sort]} {order.upper()}, b.id
            LIMIT %s OFFSET %s""",
        params + [limit, offset],
    )
    return {"total": total, "limit": limit, "offset": offset, "results": rows}


@app.get("/books/{book_id}")
def get_book(book_id: int):
    rows = query(
        f"""SELECT b.id, b.title, b.url, b.rating, b.in_stock, ph.price::float AS price,
                   b.first_seen, b.last_seen
            {LATEST_PRICE_JOIN} WHERE b.id = %s""",
        [book_id],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Book not found")
    return rows[0]


@app.get("/books/{book_id}/price-history")
def price_history(book_id: int):
    rows = query(
        "SELECT price::float AS price, scraped_at FROM price_history WHERE book_id = %s ORDER BY scraped_at",
        [book_id],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No price history for this book")
    return rows


@app.get("/stats")
def stats():
    summary = query(
        f"""SELECT COUNT(*) AS books,
                   ROUND(AVG(ph.price), 2)::float AS avg_price,
                   MIN(ph.price)::float AS min_price,
                   MAX(ph.price)::float AS max_price,
                   COUNT(*) FILTER (WHERE b.in_stock) AS in_stock
            {LATEST_PRICE_JOIN}"""
    )[0]
    by_rating = query(
        f"""SELECT b.rating, COUNT(*) AS books, ROUND(AVG(ph.price), 2)::float AS avg_price
            {LATEST_PRICE_JOIN} GROUP BY b.rating ORDER BY b.rating"""
    )
    return {**summary, "by_rating": by_rating}
