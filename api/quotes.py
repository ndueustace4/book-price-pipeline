"""Quote endpoints. Included into the main app with app.include_router(router)."""
from typing import Optional

from fastapi import APIRouter, Query
from psycopg.rows import dict_row

from pipeline.db import get_conn

router = APIRouter(prefix="/quotes", tags=["quotes"])


def query(sql, params=()):
    with get_conn() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@router.get("")
def list_quotes(
    search: Optional[str] = Query(None, max_length=100),
    author: Optional[str] = Query(None, max_length=100),
    tag: Optional[str] = Query(None, max_length=50),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    conditions, params = [], []
    if search:
        conditions.append("text ILIKE %s")
        params.append(f"%{search}%")
    if author:
        conditions.append("author = %s")
        params.append(author)
    if tag:
        conditions.append("%s = ANY(tags)")
        params.append(tag)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = query(f"SELECT COUNT(*) AS n FROM quotes {where}", params)[0]["n"]
    rows = query(
        f"SELECT id, text, author, tags FROM quotes {where} ORDER BY author, id LIMIT %s OFFSET %s",
        params + [limit, offset],
    )
    return {"total": total, "limit": limit, "offset": offset, "results": rows}


@router.get("/authors")
def list_authors():
    return query("SELECT author, COUNT(*) AS quotes FROM quotes GROUP BY author ORDER BY quotes DESC, author")
