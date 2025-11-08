# app/managers/rag_manager.py
from typing import List, Dict, Optional
from app.infra.doc_repository import ann_search
from app.managers.graph_manager import GraphManager
from app.clients.openai_client import llm, client
from app.config.settings import settings

graph = GraphManager()

def _embed_query(q: str) -> List[float]:
    r = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=[q]
    )
    return r.data[0].embedding

def _rrf(ch: List[Dict], gh: List[Dict], k: int = 60) -> List[Dict]:
    ranks, ordered = {}, []

    for rank, it in enumerate(sorted(ch, key=lambda x: x["score"], reverse=True), 1):
        rid = it["id"]
        ranks[rid] = ranks.get(rid, 0.0) + 1.0/(k+rank)
        ordered.append(it)

    for rank, it in enumerate(sorted(gh, key=lambda x: x["score"], reverse=True), 1):
        rid = it["id"]
        ranks[rid] = ranks.get(rid, 0.0) + 1.0/(k+rank)
        ordered.append(it)

    uniq = {}

    for it in ordered:
        uniq.setdefault(it["id"], it)
    result = list(uniq.values())
    result.sort(key=lambda x: ranks.get(x["id"], 0.0), reverse=True)

    for it in result:
        it["rrf"] = ranks[it["id"]]
    return result


def ask_hybrid(
    question: str,
    model_id: Optional[str] = None,
    model_name: Optional[str] = None,
    part_name: Optional[str] = None,
    scene: Optional[str] = None,
) -> str:
    # 1) dense retrieval from pgvector, scoped by meta filters
    filters: Dict[str,str] = {}
    if model_id:
        filters["model_id"] = model_id
    if scene:
        filters["scene"] = scene

    q_emb = _embed_query(question)
    doc_hits = ann_search(
        question_embedding=q_emb,
        n_results=settings.TOP_K_CHROMA,
        filters=filters if filters else None,
    )

    # 2) graph facts, also scoped
    chosen = part_name or graph.find_part_by_function(question, model_id=model_id)
    graph_hits: List[Dict] = []
    if chosen:
        ctx = graph.get_part_context(chosen, model_id=model_id)
        if ctx:
            snippet = (
                f"Part: {ctx['name']}. "
                f"Functions: {', '.join(ctx['functions'])}. "
                f"Processes: {', '.join(ctx['processes'])}. "
                f"Connects to: {', '.join(ctx['connects_to'])}. "
                f"Description: {ctx['description']}"
            )
            graph_hits.append({
                "id": f"graph::{chosen}",
                "text": snippet,
                "meta": {"source": "graph", "part": chosen, "model_id": model_id},
                "score": 1.0,
            })

    fused = _rrf(doc_hits, graph_hits)[: settings.MAX_CHUNKS]

    # 3) compose context
    blocks = []
    if model_name:
        blocks.append(f"[MODEL] {model_name}")
    if graph_hits:
        blocks.append("[GRAPH] " + graph_hits[0]["text"])

    for i, c in enumerate(fused):
        if c.get("meta", {}).get("source") == "graph":
            continue
        blocks.append(f"[DOC-{i+1}] {c['text']}")

    # 4) generic AR tutor prompt
    prompt = (
        "You are an AR learning assistant embedded inside a 3D model viewer. "
        "Use ONLY the provided context. If the context is insufficient, say so honestly "
        "instead of guessing.\n\n"
        f"User question: {question}\n\n"
        "Context:\n" + "\n\n".join(blocks) + "\n\n"
        "Answer in 3–6 clear, concise sentences."
    )

    msg = llm.invoke(prompt)
    return msg.content
