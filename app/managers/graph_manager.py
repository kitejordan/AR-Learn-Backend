# app/managers/graph_manager.py
from typing import Dict, Any, List, Optional
from app.clients.neo4j_client import neo4j_client

class GraphManager:
    """
    Encapsulates Cypher queries used by other managers.
    Uses a Model node to support multiple 3D models.
    """

    def get_part_context(self, part_name: str, model_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Return details about a part, its functions, processes, and neighbors.
        If model_id is provided, scope to that model.
        """
        if model_id:
            q = """
            MATCH (m:Model {id:$modelId})-[:HAS_PART]->(p:Part {name:$name})
            OPTIONAL MATCH (p)-[:PERFORMS]->(f:Function)
            OPTIONAL MATCH (p)-[:PART_OF]->(proc:Process)
            OPTIONAL MATCH (p)-[:CONNECTS_TO]->(n:Part)
            RETURN p.name AS name,
                   coalesce(p.description,'') AS description,
                   collect(DISTINCT f.name) AS functions,
                   collect(DISTINCT proc.name) AS processes,
                   collect(DISTINCT n.name) AS connects_to
            """
            params = {"modelId": model_id, "name": part_name}
        else:
            q = """
            MATCH (p:Part {name:$name})
            OPTIONAL MATCH (p)-[:PERFORMS]->(f:Function)
            OPTIONAL MATCH (p)-[:PART_OF]->(proc:Process)
            OPTIONAL MATCH (p)-[:CONNECTS_TO]->(n:Part)
            RETURN p.name AS name,
                   coalesce(p.description,'') AS description,
                   collect(DISTINCT f.name) AS functions,
                   collect(DISTINCT proc.name) AS processes,
                   collect(DISTINCT n.name) AS connects_to
            """
            params = {"name": part_name}

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

    def resolve_action(self, action_id: str, model_id: Optional[str] = None) -> Dict[str, Any]:
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
        return recs[0].data() if recs else {"rows": []}

    def find_part_by_function(self, question: str, model_id: Optional[str] = None) -> str:
        """
        Naive heuristic:
        - Look for a Function/Process name mentioned in the question.
        - Return a Part in the given model that is linked to it.
        """
        if model_id:
            q = """
            // collect candidate function/process names scoped to this model
            CALL {
              MATCH (m:Model {id:$modelId})-[:HAS_PART]->(p:Part)
              MATCH (p)-[r:PERFORMS|:PART_OF]->(x)
              WHERE x:Function OR x:Process
              RETURN collect(DISTINCT x.name) AS names
            }
            WITH names, toLower($qtext) AS ql
            WITH [n IN names WHERE ql CONTAINS toLower(n)] AS hits
            WITH CASE WHEN size(hits) > 0 THEN hits[0] ELSE '' END AS key
            CALL {
              WITH key, $modelId AS mid
              MATCH (m:Model {id:mid})-[:HAS_PART]->(p:Part)-[:PERFORMS]->(:Function {name:key})
              RETURN p.name AS part
              UNION
              WITH key, mid
              MATCH (m:Model {id:mid})-[:HAS_PART]->(p:Part)-[:PART_OF]->(:Process {name:key})
              RETURN p.name AS part
            }
            RETURN part LIMIT 1
            """
            params = {"modelId": model_id, "qtext": question}
        else:
            q = """
            CALL {
              MATCH (x)
              WHERE x:Function OR x:Process
              RETURN collect(DISTINCT x.name) AS names
            }
            WITH names, toLower($qtext) AS ql
            WITH [n IN names WHERE ql CONTAINS toLower(n)] AS hits
            WITH CASE WHEN size(hits) > 0 THEN hits[0] ELSE '' END AS key
            CALL {
              WITH key
              MATCH (p:Part)-[:PERFORMS]->(:Function {name:key})
              RETURN p.name AS part
              UNION
              WITH key
              MATCH (p:Part)-[:PART_OF]->(:Process {name:key})
              RETURN p.name AS part
            }
            RETURN part LIMIT 1
            """
            params = {"qtext": question}

        recs = neo4j_client.run(q, params)
        return recs[0]["part"] if recs else ""
