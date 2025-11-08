# app/managers/quiz_manager.py
from typing import Dict, List, Optional, Any
from app.clients.neo4j_client import neo4j_client
from app.clients.openai_client import client
from app.config.settings import settings
import json
import uuid

class QuizManager:
    """
    Builds a model-scoped knowledge snapshot from Neo4j and asks the LLM
    to generate MCQs strictly from that context. No persistence.
    """

    def _fetch_model_snapshot(
        self,
        model_id: Optional[str],
        model_name: Optional[str],
        include_parts: Optional[List[str]] = None,
        limit_parts: int = 200,
    ) -> Dict[str, Any]:
        """
        Returns a compact snapshot of the model: parts + functions + processes.
        If include_parts is provided, narrows the parts to that set.
        """
        params: Dict[str, Any] = {
            "modelId": model_id,
            "modelName": model_name,
            "limitParts": limit_parts,
            "includeParts": include_parts or [],
        }

        if model_id:
            base_match = "MATCH (m:Model {id:$modelId})-[:HAS_PART]->(p:Part)"
        elif model_name:
            base_match = "MATCH (m:Model {name:$modelName})-[:HAS_PART]->(p:Part)"
        else:
            # Fallback to all parts (not recommended but still safe)
            base_match = "MATCH (p:Part)"

        # Optional narrowing
        filter_clause = ""
        if include_parts:
            filter_clause = "WHERE p.name IN $includeParts"

        q = f"""
        {base_match}
        {filter_clause}
        OPTIONAL MATCH (p)-[:PERFORMS]->(f:Function)
        OPTIONAL MATCH (p)-[:PART_OF]->(pr:Process)
        WITH p, collect(DISTINCT f.name) AS functions, collect(DISTINCT pr.name) AS processes
        RETURN
          collect({{
            name: p.name,
            description: coalesce(p.description, ""),
            functions: [fn IN functions WHERE fn IS NOT NULL],
            processes: [pn IN processes WHERE pn IS NOT NULL]
          }}) AS parts
        LIMIT $limitParts
        """

        recs = neo4j_client.run(q, params)
        parts = recs[0]["parts"] if recs else []
        return {"parts": parts}

    def _system_prompt(self) -> str:
        return (
            "You are an assessment generator for an AR tutoring app. "
            "Create concise, unambiguous multiple-choice questions ONLY from the provided context. "
            "No external knowledge. Avoid trick questions or ambiguity. "
            "Return STRICT JSON matching the provided schema."
        )

    def _user_prompt(self, snapshot: Dict[str, Any], num_q: int, difficulty: str) -> str:
        # Compact context — safe to inline because we're not persisting anywhere
        parts = snapshot.get("parts", [])
        # Keep it short: just names + key facts
        bullets: List[str] = []
        for p in parts:
            bullets.append(f"- Part: {p.get('name','')}")
            d = p.get("description") or ""
            if d:
                bullets.append(f"  Desc: {d[:220]}")
            fns = p.get("functions") or []
            if fns:
                bullets.append(f"  Functions: {', '.join(fns[:6])}")
            procs = p.get("processes") or []
            if procs:
                bullets.append(f"  Processes: {', '.join(procs[:6])}")

        ctx = "\n".join(bullets[:1200])  # cap to keep prompt tight
        return (
            f"CONTEXT (graph-derived, authoritative):\n{ctx}\n\n"
            f"Generate exactly {num_q} MCQs for difficulty='{difficulty}'. "
            "Each question must clearly reference info derivable from the context. "
            "Use varied coverage across parts/functions/processes. "
            "Avoid repeated stems; avoid negative-only patterns; keep options plausible."
        )

    def _response_schema_json(self) -> Dict[str, Any]:
        """
        JSON schema-like instructions for the model to follow.
        We rely on OpenAI's response_format json_object for stricter output.
        """
        example = {
            "questions": [
                {
                    "id": "uuid-string",
                    "stem": "Which component primarily ...?",
                    "options": ["A", "B", "C", "D"],
                    "correct_index": 1,
                    "explanation": "B is correct because ... (based on context).",
                    "sources": ["Compressor", "Air Intake"]
                }
            ]
        }
        return example

    def generate_quiz(
        self,
        model_id: Optional[str],
        model_name: Optional[str],
        num_questions: int,
        difficulty: str,
        include_parts: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        snapshot = self._fetch_model_snapshot(model_id, model_name, include_parts)
        sys_prompt = self._system_prompt()
        user_prompt = self._user_prompt(snapshot, num_questions, difficulty)

        # Use JSON mode for robust parsing
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,  # e.g., "gpt-4o-mini"
            temperature=0.6,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "system", "content": "Output must be a JSON object with a 'questions' array matching this example:"},
                {"role": "system", "content": json.dumps(self._response_schema_json())},
            ],
        )

        raw = completion.choices[0].message.content
        try:
            data = json.loads(raw)
        except Exception:
            # Fallback: try to coerce
            raw = raw.strip().strip("```json").strip("```").strip()
            data = json.loads(raw)

        questions = data.get("questions", [])
        # Normalize + inject UUIDs if missing, and clamp fields
        cleaned: List[Dict[str, Any]] = []
        for q in questions[:num_questions]:
            opts = q.get("options", []) or []
            # Ensure 2-6 options, fix indices if out of bounds
            if not (3 <= len(opts) <= 6):
                continue
            ci = int(q.get("correct_index", 0))
            if ci < 0 or ci >= len(opts):
                ci = 0
            cleaned.append({
                "id": q.get("id") or str(uuid.uuid4()),
                "stem": str(q.get("stem", "")).strip(),
                "options": [str(o) for o in opts],
                "correct_index": ci,
                "explanation": (q.get("explanation") or "").strip() or None,
                "sources": [str(s) for s in (q.get("sources") or [])],
            })

        return cleaned
