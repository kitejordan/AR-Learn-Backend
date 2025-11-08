from typing import Dict, Any, Optional
from app.clients.neo4j_client import neo4j_client


class GraphManager:
    """
    Encapsulates Cypher queries used by other managers.
    Uses a Model node to support multiple 3D models.

    Key idea: we NEVER trust the raw part_name blindly.
    We first resolve it to a canonical Part.name via _resolve_part_name,
    which is tolerant to:
      - case differences
      - singular/plural (Divider vs Dividers)
      - unityId matches
      - simple substring overlaps
    """

    # ---------- internal: tolerant part resolver ----------

    def _resolve_part_name(
        self,
        raw_name: str,
        model_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Map a noisy part_name to a canonical Part.name, optionally scoped by model_id.

        Returns:
            str | None: resolved Part.name or None if no good candidate.
        """
        if not raw_name:
            return None

        name = raw_name.strip()
        if not name:
            return None

        name_lower = name.lower()

        # simple singular/plural flip
        if name_lower.endswith("s"):
            alt = name_lower[:-1]
        else:
            alt = name_lower + "s"

        q = """
        WITH
          $nameLower AS nameLower,
          $alt AS alt,
          $modelId AS modelId

        MATCH (p:Part)
        WHERE
          (modelId IS NULL OR p.modelId = modelId)
          AND (
                toLower(p.name) = nameLower
             OR toLower(p.name) = alt
             OR toLower(coalesce(p.unityId, '')) = nameLower
             OR nameLower CONTAINS toLower(p.name)
             OR toLower(p.name) CONTAINS nameLower
          )
        RETURN p.name AS name
        ORDER BY
          CASE
            WHEN toLower(p.name) = nameLower THEN 0          // exact
            WHEN toLower(p.name) = alt THEN 1                // plural/singular flip
            WHEN toLower(coalesce(p.unityId, '')) = nameLower THEN 2
            WHEN nameLower CONTAINS toLower(p.name)
              OR toLower(p.name) CONTAINS nameLower THEN 3   // substring-ish
            ELSE 4
          END,
          size(p.name) ASC
        LIMIT 1
        """

        params = {
            "nameLower": name_lower,
            "alt": alt,
            "modelId": model_id,
        }
        recs = neo4j_client.run(q, params)
        return recs[0]["name"] if recs else None

    # ---------- Part context ----------

    def get_part_context(
        self,
        part_name: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return details about a part, its functions, processes, and neighbors.
        Tolerant to minor naming issues via _resolve_part_name.
        """
        resolved = self._resolve_part_name(part_name, model_id=model_id)
        if not resolved:
            return {}

        if model_id:
            q = """
            MATCH (m:Model {id:$modelId})-[:HAS_PART]->(p:Part {name:$name})
            OPTIONAL MATCH (p)-[:PERFORMS]->(f:Function)
            OPTIONAL MATCH (p)-[:PART_OF]->(proc:Process)
            // Add CONNECTS_TO relationships later if you seed them
            RETURN p.name AS name,
                   coalesce(p.description,'') AS description,
                   collect(DISTINCT f.name) AS functions,
                   collect(DISTINCT proc.name) AS processes,
                   [] AS connects_to
            """
            params = {"modelId": model_id, "name": resolved}
        else:
            q = """
            MATCH (p:Part {name:$name})
            OPTIONAL MATCH (p)-[:PERFORMS]->(f:Function)
            OPTIONAL MATCH (p)-[:PART_OF]->(proc:Process)
            RETURN p.name AS name,
                   coalesce(p.description,'') AS description,
                   collect(DISTINCT f.name) AS functions,
                   collect(DISTINCT proc.name) AS processes,
                   [] AS connects_to
            """
            params = {"name": resolved}

        recs = neo4j_client.run(q, params)
        if not recs:
            return {}

        r = recs[0]
        return {
            "name": r["name"],
            "description": r["description"],
            "functions": [x for x in r["functions"] if x],
            "processes": [x for x in r["processes"] if x],
            "connects_to": [x for x in r["connects_to"] if x],
        }

    # ---------- Actions / timelines ----------

    def resolve_action(
        self,
        action_id: str,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return timeline rows for an action.
        If model_id is set, ensure the Action belongs to that Model.
        """
        if model_id:
            q = """
            MATCH (m:Model {id:$modelId})-[:HAS_ACTION]->(a:Action {id:$aid})
            MATCH (a)-[:HAS_STEP]->(s:Step)
            OPTIONAL MATCH (s)-[:TARGETS]->(t:Part)
            OPTIONAL MATCH (s)-[:FOLLOWS_PATH]->(p:Path)
            WITH s, t, p
            ORDER BY s.order ASC
            RETURN collect({
              effect: s.effect,
              params: coalesce(s.params, {}),
              target: t.name,
              path: p.nodes
            }) AS rows
            """
            params = {"modelId": model_id, "aid": action_id}
        else:
            q = """
            MATCH (a:Action {id:$aid})-[:HAS_STEP]->(s:Step)
            OPTIONAL MATCH (s)-[:TARGETS]->(t:Part)
            OPTIONAL MATCH (s)-[:FOLLOWS_PATH]->(p:Path)
            WITH s, t, p
            ORDER BY s.order ASC
            RETURN collect({
              effect: s.effect,
              params: coalesce(s.params, {}),
              target: t.name,
              path: p.nodes
            }) AS rows
            """
            params = {"aid": action_id}

        recs = neo4j_client.run(q, params)
        return {"rows": recs[0]["rows"]} if recs else {"rows": []}

    # ---------- Function → Part heuristic ----------

    def find_part_by_function(
        self,
        user_question: str,
        model_id: str | None = None,
        model_name: str | None = None,
    ) -> str:
        """
        Heuristic:
        1. Find the best matching Function name mentioned in the question.
        2. Return a Part that PERFORMS that function.
           If model_id/model_name are provided, prefer parts under that model.
        """
        q = """
        WITH toLower($question) AS q,
             $modelId AS modelId,
             $modelName AS modelName

        // 1) candidate function whose name appears in the question
        CALL {
          WITH q
          MATCH (f:Function)
          WHERE q CONTAINS toLower(f.name)
          RETURN f.name AS fname
          ORDER BY size(f.name) DESC
          LIMIT 1
        }

        WITH fname, modelId, modelName
        WHERE fname IS NOT NULL

        // 2) prefer a part attached to the specified model (if given)
        CALL {
          WITH fname, modelId, modelName
          MATCH (f:Function {name: fname})
          MATCH (p:Part)-[:PERFORMS]->(f)
          OPTIONAL MATCH (m:Model)-[:HAS_PART]->(p)
          WHERE
            (modelId IS NOT NULL AND m.id = modelId) OR
            (modelId IS NULL AND modelName IS NOT NULL AND m.name = modelName)
          RETURN p.name AS part
          ORDER BY part
          LIMIT 1
        }

        WITH fname, part

        // 3) fallback: any part performing the function
        CALL {
          WITH fname, part
          WHERE part IS NULL
          MATCH (p2:Part)-[:PERFORMS]->(:Function {name: fname})
          RETURN p2.name AS fallbackPart
          LIMIT 1
        }

        RETURN coalesce(part, fallbackPart, "") AS part
        LIMIT 1
        """

        params = {
            "question": user_question,
            "modelId": model_id,
            "modelName": model_name,
        }
        recs = neo4j_client.run(q, params)
        return recs[0]["part"] if recs else ""
