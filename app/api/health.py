# app/api/health.py

from fastapi import APIRouter
from app.clients.postgres_client import get_conn
from app.clients.neo4j_client import neo4j_client

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health():
    services = {
        "app": "ok",
        "postgres": "unknown",
        "neo4j": "unknown",
    }
    details = {}

    # --- Postgres / Supabase check ---
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        services["postgres"] = "ok"
    except Exception as e:
        services["postgres"] = "error"
        details["postgres"] = str(e)

    # --- Neo4j check ---
    try:
        # lightweight no-op query
        neo4j_client.run("RETURN 1 AS ok")
        services["neo4j"] = "ok"
    except Exception as e:
        services["neo4j"] = "error"
        details["neo4j"] = str(e)

    # --- overall status ---
    overall_ok = all(val == "ok" for val in services.values())
    status = "ok" if overall_ok else "degraded"

    return {
        "status": status,
        "services": services,
        "details": details,  # empty if everything is ok
    }
