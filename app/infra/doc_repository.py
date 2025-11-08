from typing import Any, Dict, List, Optional, Tuple
from app.clients.postgres_client import get_conn
import json
from uuid import UUID

def create_document(title: str, source: str | None, subject: str | None, tags: list[str] | None) -> str:
    q = """
    INSERT INTO document (title, source, subject, tags)
    VALUES (%s, %s, %s, %s) RETURNING id::text
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, (title, source, subject, tags))
        return cur.fetchone()[0]


def insert_chunks(document_id: str, rows: List[Tuple[int|None, int|None, str, dict, list[float]]]) -> int:
    """
    rows: list of (page, chunk_index, text, meta, embedding)
    """
    q = """
    INSERT INTO doc_chunk (document_id, page, chunk_index, text, meta, embedding)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    with get_conn() as conn, conn.cursor() as cur:
        for page, idx, text, meta, emb in rows:
            cur.execute(q, (document_id, page, idx, text, json.dumps(meta), emb))
        return len(rows)


def ann_search(
    question_embedding: List[float],
    n_results: int,
    filters: Optional[Dict[str, Optional[str]]] = None,
) -> List[Dict]:
    """
    ANN search over doc_chunk.embedding with optional exact-match filters
    on meta JSONB (e.g. model_id, scene).
    `filters` is a dict like {"model_id": "jet-engine-v1", "scene": "overview"}.
    """
    base = """
    WITH q AS (SELECT %s::vector AS emb)
    SELECT id::text,
           text,
           meta,
           1 - (embedding <=> (SELECT emb FROM q)) AS score
    FROM doc_chunk
    WHERE 1=1
    """
    params: List = [question_embedding]

    if filters:
        for key, value in filters.items():
            if value is None:
                continue
            # meta->>'key' = value
            base += " AND meta->>%s = %s"
            params.extend([key, value])

    base += """
    ORDER BY embedding <=> (SELECT emb FROM q)
    LIMIT %s
    """
    params.append(n_results)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(base, params)
        rows = cur.fetchall()

    return [
        {"id": rid, "text": text, "meta": meta, "score": float(score)}
        for (rid, text, meta, score) in rows
    ]


def delete_document(doc_id: str) -> int:
    q = "DELETE FROM document WHERE id = %s"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(q, (doc_id,))
        return cur.rowcount
