import psycopg2
import psycopg2.extras
from psycopg2 import pool
from contextlib import contextmanager
from .config import settings

_pool = pool.ThreadedConnectionPool(
    minconn=2,
    maxconn=10,
    dsn=settings.database_url,
)

@contextmanager
def get_conn():
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)

def query(sql: str, params=None) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

def execute(sql: str, params=None) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount

def executemany(sql: str, params_list: list) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, params_list, page_size=500)
            return cur.rowcount
