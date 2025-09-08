 # all managers will use this client to connect to neo4j

from neo4j import GraphDatabase
from app.config.settings import settings

class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,                                                        
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
        )
    def run(self, cypher: str, params: dict = None):
        with self.driver.session() as s:
            return list(s.run(cypher, params or {}))

neo4j_client = Neo4jClient()
