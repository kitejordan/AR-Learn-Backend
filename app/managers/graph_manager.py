# This manager will be used by other managers to query the graph database

from typing import List, Dict, Any
from app.clients.neo4j_client import neo4j_client

class GraphManager:                                                     
    def get_part_context(self, part_name: str) -> Dict[str, Any]:                  # get details about a part, its functions, processes, connections        
        q = """
        MATCH (p:Part {name:$name})
        OPTIONAL MATCH (p)-[:PERFORMS]->(f:Function)
        OPTIONAL MATCH (p)-[:PART_OF]->(proc:Process)
        OPTIONAL MATCH (p)-[:CONNECTS_TO]->(n:Part)
        RETURN p.name AS name, p.description AS description,                         
               collect(DISTINCT f.name) AS functions,
               collect(DISTINCT proc.name) AS processes,
               collect(DISTINCT n.name) AS connects_to
        """
        recs = neo4j_client.run(q, {"name": part_name})
        return recs[0].data() if recs else {}

    def find_part_by_function(self, user_question: str) -> str:                     #  naive heuristic: look for a Process/Function that maps this intent
        
        q = """
        // If your graph encodes processes like Combustion, map by keywords
        WITH $question AS q
        CALL {
          WITH q
          MATCH (proc:Process)
          WHERE toLower(q) CONTAINS toLower(proc.name)
          RETURN proc.name AS pname LIMIT 1
        }
        MATCH (p:Part)-[:PART_OF]->(proc:Process {name:pname})
        RETURN p.name AS part LIMIT 1
        """
        recs = neo4j_client.run(q, {"question": user_question})
        return recs[0]["part"] if recs else ""

    def resolve_action(self, action_id: str) -> Dict[str, Any]:
        # Build timeline from Action → Steps → TARGETS, and optional FLOWS_TO paths
        q = """
        MATCH (a:Action {id:$id})-[:HAS_STEP]->(s:Step)
        OPTIONAL MATCH (s)-[:TARGETS]->(p:Part)
        OPTIONAL MATCH path=(src:Part)-[:FLOWS_TO*1..6]->(dst:Part)
        WHERE s.effect = 'pathFlow'   // only attach path when needed
        RETURN a.id AS actionId, s.order AS ord, s.effect AS effect,
               s.params AS params, p.name AS target,
               [n IN nodes(path) | n.name] AS path
        ORDER BY ord ASC
        """
        rows = [r.data() for r in neo4j_client.run(q, {"id": action_id})]
        return {"rows": rows}
