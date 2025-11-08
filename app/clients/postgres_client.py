import os
import psycopg
from contextlib import contextmanager
from app.config.settings import settings

def _conn_kwargs():
    return {
        "host": settings.PG_HOST,
        "port": settings.PG_PORT,
        "dbname": settings.PG_DATABASE,
        "user": settings.PG_USER,
        "password": settings.PG_PASSWORD,
        "autocommit": False,
    }

@contextmanager
def get_conn():
    conn = psycopg.connect(**_conn_kwargs())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
