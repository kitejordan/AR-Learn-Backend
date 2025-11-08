# app/clients/neo4j_client.py

import os
from neo4j import GraphDatabase
from app.config.settings import settings

class Neo4jClient:
    def __init__(self):
        uri = settings.NEO4J_URI
        user = settings.NEO4J_USERNAME
        password = settings.NEO4J_PASSWORD

        if not uri:
            raise ValueError("NEO4J_URI is not set")
        if not user or not password:
            raise ValueError("NEO4J_USERNAME/NEO4J_PASSWORD not set")

        # For Aura:
        # - use neo4j+s:// (or bolt+s://) in NEO4J_URI
        # - encryption is implied by the scheme
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

        # Optional: if you use multi-db, add NEO4J_DATABASE to settings
        self._database = os.getenv("NEO4J_DATABASE") or None

    def run(self, cypher: str, params: dict | None = None):
        params = params or {}
        # Always open short-lived sessions; Aura likes that.
        if self._database:
            with self._driver.session(database=self._database) as session:
                return list(session.run(cypher, params))
        else:
            with self._driver.session() as session:
                return list(session.run(cypher, params))

    def close(self):
        self._driver.close()


neo4j_client = Neo4jClient()
