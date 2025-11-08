# app/clients/postgres_client.py
import psycopg
from contextlib import contextmanager
from app.config.settings import settings

@contextmanager
def get_conn():
    """
    Get a Postgres connection.

    Prefers SUPABASE_DB_URL (e.g. transaction pooler DSN).
    Falls back to PG_HOST/... for local development.
    """
    if settings.SUPABASE_DB_URL:
        dsn = settings.SUPABASE_DB_URL

        # Ensure sslmode=require for Supabase if not already present
        if "sslmode=" not in dsn:
            joiner = "&" if "?" in dsn else "?"
            dsn = f"{dsn}{joiner}sslmode=require"

        conn = psycopg.connect(dsn, autocommit=False)
    else:
        # Local dev Postgres
        conn = psycopg.connect(
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            dbname=settings.PG_DATABASE,
            user=settings.PG_USER,
            password=settings.PG_PASSWORD,
            autocommit=False,
        )

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
