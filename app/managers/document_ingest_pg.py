import re
from typing import List, Tuple
from pypdf import PdfReader
from app.infra.doc_repository import create_document, insert_chunks
from app.clients.openai_client import client
from app.config.settings import settings

def _clean(t: str) -> str:
    return re.sub(r"\s+"," ", (t or "")).strip()

def _chunk(text: str,
           max_chars: int = 1200,
           min_chars: int = 600,
           overlap: int = 150) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, cur = [], ""
    for s in sentences:
        if len(cur) + len(s) + 1 <= max_chars:
            cur = (cur + " " + s).strip()
        else:
            if len(cur) >= min_chars:
                chunks.append(cur)
                cur = s
            else:
                cur = (cur + " " + s).strip()
    if cur:
        chunks.append(cur)

    if overlap and len(chunks) > 1:
        out = [chunks[0]]
        for i in range(1, len(chunks)):
            out.append((chunks[i-1][-overlap:] + " " + chunks[i]).strip())
        return out
    return chunks

def _embed_many(texts: List[str]) -> List[List[float]]:
    res = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts
    )
    return [d.embedding for d in res.data]


def ingest_pdf_to_pg(
    file_path: str,
    title: str | None = None,
    subject: str | None = None,
    tags: list[str] | None = None,
    model_id: str | None = None,
    model_name: str | None = None,
) -> dict:
    reader = PdfReader(file_path)
    title = title or (reader.metadata.title if reader.metadata else "Untitled")

    doc_id = create_document(
        title=title,
        source="pdf",
        subject=subject,
        tags=tags or []
    )

    rows: List[Tuple[int | None, int | None, str, dict, list[float]]] = []

    for i, page in enumerate(reader.pages):
        raw = page.extract_text() or ""
        text = _clean(raw)
        if not text:
            continue

        chunks = _chunk(text)
        if not chunks:
            continue

        embs = _embed_many(chunks)
        for j, ch in enumerate(chunks):
            meta = {
                "page": i + 1,
                "chunk_index": j,
                "model_id": model_id,
                "model_name": model_name,
                "subject": subject,
            }
            rows.append((i + 1, j, ch, meta, embs[j]))

    upserted = insert_chunks(doc_id, rows)
    return {"document_id": doc_id, "upserted_chunks": upserted}
