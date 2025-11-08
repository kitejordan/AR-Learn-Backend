# app/managers/rag_manager.py

from typing import List, Dict, Optional

from neo4j.exceptions import Neo4jError, ServiceUnavailable

from app.infra.doc_repository import ann_search
from app.managers.graph_manager import GraphManager
from app.clients.openai_client import llm, client
from app.config.settings import settings

graph = GraphManager()


def _embed_query(q: str) -> List[float]:
    """Create an embedding for the user question."""
    res = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=[q],
    )
    return res.data[0].embedding


def _rrf(ch: List[Dict], gh: List[Dict], k: int = 60) -> List[Dict]:
    """
    Reciprocal Rank Fusion to combine:
      - ch: document hits (pgvector)
      - gh: graph hits (Neo4j)
    """
    ranks: Dict[str, float] = {}
    ordered: List[Dict] = []

    # rank document hits
    for rank, it in enumerate(sorted(ch, key=lambda x: x["score"], reverse=True), 1):
        rid = it["id"]
        ranks[rid] = ranks.get(rid, 0.0) + 1.0 / (k + rank)
        ordered.append(it)

    # rank graph hits
    for rank, it in enumerate(sorted(gh, key=lambda x: x["score"], reverse=True), 1):
        rid = it["id"]
        ranks[rid] = ranks.get(rid, 0.0) + 1.0 / (k + rank)
        ordered.append(it)

    # dedupe by id, preserve first occurrence
    uniq: Dict[str, Dict] = {}
    for it in ordered:
        uniq.setdefault(it["id"], it)

    result = list(uniq.values())
    result.sort(key=lambda x: ranks.get(x["id"], 0.0), reverse=True)

    # attach RRF score (mainly for debugging)
    for it in result:
        it["rrf"] = ranks[it["id"]]

    return result


def _normalize_part_name(raw: Optional[str]) -> Optional[str]:
    """
    Make the system tolerant to garbage / placeholder part names.
    Treat things like "null", "", "undefined" as no part selected.
    """
    if raw is None:
        return None
    val = raw.strip()
    if not val:
        return None
    low = val.lower()
    if low in {"null", "none", "undefined"}:
        return None
    return val


def ask_hybrid(
    question: str,
    model_id: Optional[str] = None,
    model_name: Optional[str] = None,
    part_name: Optional[str] = None,
    scene: Optional[str] = None,
) -> str:
    """
    Hybrid RAG pipeline:

      1. Dense retrieval from Postgres/pgvector (doc_chunk table),
         optionally filtered by meta (model_id, scene).

      2. Structured retrieval from Neo4j:
         - If part_name is provided, resolve it tolerantly.
         - Otherwise, infer a part via function mapping from the user question.

      3. Reciprocal Rank Fusion of doc + graph hits.

      4. LLM answer constrained to retrieved context.
    """

    # ---------- 1) dense retrieval from pgvector ----------
    filters: Dict[str, str] = {}
    if model_id:
        filters["model_id"] = model_id
    if scene:
        filters["scene"] = scene

    q_emb = _embed_query(question)
    doc_hits = ann_search(
        question_embedding=q_emb,
        n_results=settings.TOP_K_CHROMA,
        filters=filters or None,
    )

    # ---------- 2) graph facts (robust & tolerant) ----------
    graph_hits: List[Dict] = []
    try:
        chosen: Optional[str] = None

        # (a) normalize any incoming part_name
        norm_part = _normalize_part_name(part_name)

        # (b) if we have a candidate part, try to resolve context
        if norm_part:
            ctx = graph.get_part_context(
                part_name=norm_part,
                model_id=model_id,
            )
            if ctx:
                chosen = ctx["name"]  # canonical name from graph

        # (c) if no chosen part yet, infer from question via functions/processes
        if not chosen:
            chosen = graph.find_part_by_function(
                user_question=question,
                model_id=model_id,
                model_name=model_name,
            )

        # (d) fetch final context for chosen part
        if chosen:
            ctx = graph.get_part_context(
                part_name=chosen,
                model_id=model_id,
            )
            if ctx:
                snippet = (
                    f"Part: {ctx['name']}. "
                    f"Functions: {', '.join(ctx['functions'])}. "
                    f"Processes: {', '.join(ctx['processes'])}. "
                    f"Connects to: {', '.join(ctx['connects_to'])}. "
                    f"Description: {ctx['description']}"
                )
                graph_hits.append(
                    {
                        "id": f"graph::{chosen}",
                        "text": snippet,
                        "meta": {
                            "source": "graph",
                            "part": chosen,
                            "model_id": model_id,
                        },
                        "score": 1.0,
                    }
                )

    except (Neo4jError, ServiceUnavailable, OSError):
        # If Neo4j misbehaves, we gracefully fall back to pure doc RAG.
        graph_hits = []

    # ---------- 3) fuse results ----------
    fused = _rrf(doc_hits, graph_hits)[: settings.MAX_CHUNKS]

    # ---------- 4) build context blocks ----------
    blocks: List[str] = []
    if graph_hits:
        blocks.append("[GRAPH] " + graph_hits[0]["text"])

    for i, c in enumerate(fused):
        # avoid repeating the graph snippet
        if c.get("meta", {}).get("source") == "graph":
            continue
        blocks.append(f"[DOC-{i+1}] {c['text']}")

    # ---------- 5) construct prompt ----------
    if not blocks:
        prompt = (
            "You are an honest tutor. The system could not retrieve any useful "
            "context from documents or the knowledge graph for this question. "
            "Explain briefly that you don't have enough information.\n"
            f"Question: {question}\n"
        )
    else:
        prompt = (
            "You are a concise AR tutor embedded in a 3D learning app. "
            "Use only the context below. If the information is incomplete or "
            "you are unsure, say so explicitly instead of guessing.\n\n"
            f"Question: {question}\n\n"
            "Context:\n" + "\n\n".join(blocks) + "\n\n"
            "Answer in 3–6 short, clear sentences."
        )

    msg = llm.invoke(prompt)
    return msg.content
