# scripts/seed_neo4j.py
"""
Seed Neo4j for AR-Learn.

- Introduces a Model node so we can support multiple 3D models.
- Attaches jet-engine parts, functions, and processes to that model.
- Keeps data identical to the original seed, but structured for multi-model.

Usage:
  python scripts/seed_neo4j.py
  python scripts/seed_neo4j.py --wipe

Env (.env):
  NEO4J_URI=neo4j+s://...         # or bolt://... for local
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=yourpassword
  NEO4J_DATABASE=neo4j            # optional for Aura / multi-db
"""

import os
import argparse
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

# ---------- config ----------

def get_driver():
    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    if not uri:
        raise ValueError("NEO4J_URI not found in .env file!")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD", "neo4j")
    return GraphDatabase.driver(uri, auth=(user, pwd))

def get_database() -> Optional[str]:
    return os.getenv("NEO4J_DATABASE") or None

# ---------- constraints ----------

def ensure_constraints(session):
    """
    Create constraints for the new schema.
    Also drops old name-only constraint if it exists (from previous version).
    """
    # Try to drop old constraint if present (safe if it doesn't exist)
    try:
        session.execute_write(
            lambda tx: tx.run("DROP CONSTRAINT part_name IF EXISTS")
        )
    except Exception:
        pass

    stmts = [
        # One Model node per model id
        "CREATE CONSTRAINT model_id IF NOT EXISTS "
        "FOR (m:Model) REQUIRE m.id IS UNIQUE",

        # Unity object id is unique per Part
        "CREATE CONSTRAINT part_unity IF NOT EXISTS "
        "FOR (p:Part) REQUIRE p.unityId IS UNIQUE",

        # Optional: composite uniqueness if you ever set p.modelId + p.name
        # "CREATE CONSTRAINT part_model_name IF NOT EXISTS "
        # "FOR (p:Part) REQUIRE (p.modelId, p.name) IS UNIQUE",

        "CREATE CONSTRAINT process_name IF NOT EXISTS "
        "FOR (pr:Process) REQUIRE pr.name IS UNIQUE",

        "CREATE CONSTRAINT function_name IF NOT EXISTS "
        "FOR (f:Function) REQUIRE f.name IS UNIQUE",
    ]
    for q in stmts:
        session.execute_write(lambda tx, q=q: tx.run(q))

def wipe_all(session):
    session.execute_write(lambda tx: tx.run("MATCH (n) DETACH DELETE n"))

# ---------- seed data: Jet Engine model ----------

JET_ENGINE_MODEL = {
    "id": "jet-engine-v1",
    "name": "Jet Engine",
    "subject": "Aerospace",
}

# Same parts as your original script
PARTS: List[Dict[str, Any]] = [
    {
        "unityId": "blades_dividers_turbine_017",
        "name": "Turbine Dividers",
        "description": "Dividers that condition/guide flow before/through the turbine section.",
    },
    {
        "unityId": "blades_turbine_001",
        "name": "Turbine Blades",
        "description": "Blade row that extracts energy from high-temperature gas.",
    },
    {
        "unityId": "blades_turbine_002_non",
        "name": "Turbine Blades",
        "description": "Blade row that extracts energy from high-temperature gas.",
    },
    {
        "unityId": "blades_turbine_003",
        "name": "Turbine Blades",
        "description": "Blade row that extracts energy from high-temperature gas.",
    },
    {
        "unityId": "blades_turbine_004",
        "name": "Turbine Blades",
        "description": "Blade row that extracts energy from high-temperature gas.",
    },
    {
        "unityId": "canister_turbine_011",
        "name": "Combustion Canister",
        "description": "Chamber where fuel mixes with compressed air and ignites.",
    },
    {
        "unityId": "grid_turbine_007",
        "name": "Support Grid",
        "description": "Structural grid providing internal support/positioning.",
    },
    {
        "unityId": "hull_turbine_004_01",
        "name": "Turbine Casing (Outer)",
        "description": "Outer containment casing for turbine section.",
    },
    {
        "unityId": "hull_turbine_004_02",
        "name": "Turbine Casing (Inner)",
        "description": "Inner casing forming the hot gas path boundary.",
    },
    {
        "unityId": "hull_turbine_004_03",
        "name": "Turbine Casing (Mid)",
        "description": "Mid shell segment between inner and outer turbine casings.",
    },
    {
        "unityId": "mount_turbine_014",
        "name": "Engine Mount",
        "description": "Mounting structure that attaches engine to the airframe/rig.",
    },
    {
        "unityId": "pipes_turbine_009",
        "name": "Fuel and Oil Lines",
        "description": "Lines and manifolds that route fuel and oil.",
    },
    {
        "unityId": "plates_turbine_016",
        "name": "Access Panel",
        "description": "Service panel for inspection/maintenance access.",
    },
    {
        "unityId": "screws_turbine_001",
        "name": "Fastening Screws",
        "description": "Fasteners that secure panels or subcomponents.",
    },
]

# Minimal process set needed for demo
PROCESSES = [
    {"name": "Combustion"},
]

PART_OF_MAP: Dict[str, str] = {
    "Combustion Canister": "Combustion",
}

FUNCTIONS = [
    {"name": "Energy Extraction"},
    {"name": "Flow Guidance"},
    {"name": "Fuel Burning"},
    {"name": "Structural Support"},
    {"name": "Containment"},
    {"name": "Gas Path Boundary"},
    {"name": "Structural Mounting"},
    {"name": "Fuel Transport"},
    {"name": "Oil Transport"},
    {"name": "Maintenance Access"},
    {"name": "Fastening"},
]

PERFORMS_MAP: Dict[str, List[str]] = {
    "Turbine Blades": ["Energy Extraction"],
    "Turbine Dividers": ["Flow Guidance"],
    "Combustion Canister": ["Fuel Burning"],
    "Support Grid": ["Structural Support"],
    "Turbine Casing (Outer)": ["Containment"],
    "Turbine Casing (Inner)": ["Gas Path Boundary"],
    "Turbine Casing (Mid)": ["Gas Path Boundary"],
    "Engine Mount": ["Structural Mounting"],
    "Fuel and Oil Lines": ["Fuel Transport", "Oil Transport"],
    "Access Panel": ["Maintenance Access"],
    "Fastening Screws": ["Fastening"],
}

# ---------- seed routines ----------

def seed_model(session, model: Dict[str, Any]) -> str:
    q = """
    MERGE (m:Model {id:$id})
      ON CREATE SET m.name = $name, m.subject = $subject
      ON MATCH  SET m.name = $name, m.subject = $subject
    RETURN m.id AS id
    """
    res = session.execute_write(lambda tx: tx.run(q, **model).single())
    mid = res["id"]
    print(f"[seed] Model upserted: {mid}")
    return mid

def seed_parts_for_model(session, model_id: str, parts: List[Dict[str, Any]]):
    q = """
    MATCH (m:Model {id:$modelId})
    UNWIND $rows AS row
    MERGE (p:Part {unityId: row.unityId})
      ON CREATE SET
        p.name = row.name,
        p.description = row.description,
        p.modelId = $modelId
      ON MATCH SET
        p.name = row.name,
        p.description = row.description,
        p.modelId = $modelId
    MERGE (m)-[:HAS_PART]->(p)
    RETURN count(*) AS upserted
    """
    res = session.execute_write(
        lambda tx: tx.run(q, modelId=model_id, rows=parts).single()
    )
    print(f"[seed] Parts linked to {model_id}: {res['upserted']}")

def seed_processes(session, processes: List[Dict[str, Any]]):
    q = """
    UNWIND $rows AS row
    MERGE (:Process {name: row.name})
    RETURN count(*) AS upserted
    """
    res = session.execute_write(
        lambda tx: tx.run(q, rows=processes).single()
    )
    print(f"[seed] Processes upserted: {res['upserted']}")

def seed_part_of_for_model(session, model_id: str, mapping: Dict[str, str]):
    if not mapping:
        print("[seed] No PART_OF mappings.")
        return

    rows = [
        {"modelId": model_id, "part": part_name, "proc": proc_name}
        for part_name, proc_name in mapping.items()
    ]

    q = """
    UNWIND $rows AS row
    MATCH (m:Model {id:row.modelId})-[:HAS_PART]->(p:Part {name: row.part})
    MATCH (pr:Process {name: row.proc})
    MERGE (p)-[:PART_OF]->(pr)
    RETURN count(*) AS linked
    """
    res = session.execute_write(
        lambda tx: tx.run(q, rows=rows).single()
    )
    print(f"[seed] PART_OF links created: {res['linked']}")

def seed_functions(session, functions: List[Dict[str, Any]]):
    q = """
    UNWIND $rows AS row
    MERGE (:Function {name: row.name})
    RETURN count(*) AS upserted
    """
    res = session.execute_write(
        lambda tx: tx.run(q, rows=functions).single()
    )
    print(f"[seed] Functions upserted: {res['upserted']}")

def seed_performs_for_model(session, model_id: str, mapping: Dict[str, List[str]]):
    if not mapping:
        print("[seed] No PERFORMS mappings.")
        return

    rows: List[Dict[str, str]] = []
    for part_name, funcs in mapping.items():
        for func_name in funcs:
            rows.append(
                {"modelId": model_id, "part": part_name, "func": func_name}
            )

    q = """
    UNWIND $rows AS row
    MATCH (m:Model {id:row.modelId})-[:HAS_PART]->(p:Part {name: row.part})
    MATCH (f:Function {name: row.func})
    MERGE (p)-[:PERFORMS]->(f)
    RETURN count(*) AS linked
    """
    res = session.execute_write(
        lambda tx: tx.run(q, rows=rows).single()
    )
    print(f"[seed] PERFORMS links created: {res['linked']}")

# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(
        description="Seed Neo4j for AR-Learn (Jet Engine model)."
    )
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="Wipe ALL nodes/edges before seeding.",
    )
    args = parser.parse_args()

    driver = get_driver()
    db = get_database()

    with driver.session(database=db) if db else driver.session() as session:
        print("[seed] Ensuring constraints…")
        ensure_constraints(session)

        if args.wipe:
            print("[seed] WIPING ALL DATA…")
            wipe_all(session)

        print("[seed] Seeding Jet Engine model…")
        mid = seed_model(session, JET_ENGINE_MODEL)

        seed_parts_for_model(session, mid, PARTS)
        seed_processes(session, PROCESSES)
        seed_part_of_for_model(session, mid, PART_OF_MAP)
        seed_functions(session, FUNCTIONS)
        seed_performs_for_model(session, mid, PERFORMS_MAP)

        # final counts (no deprecated CALL {} subqueries)
        counts = session.run(
            """
            MATCH (m:Model)    WITH count(m)    AS models
            MATCH (p:Part)     WITH models, count(p) AS parts
            MATCH (pr:Process) WITH models, parts, count(pr) AS procs
            MATCH (f:Function) WITH models, parts, procs, count(f) AS funcs
            RETURN models, parts, procs, funcs
            """
        ).single()

        print(
            f"[seed] Done. Models={counts['models']} "
            f"Parts={counts['parts']} Processes={counts['procs']} "
            f"Functions={counts['funcs']}"
        )

    driver.close()

if __name__ == "__main__":
    main()
