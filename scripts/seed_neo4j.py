# scripts/seed_neo4j.py
"""
Seeds ONLY the parts and mappings specified in the project doc,
plus the minimal Process needed for /find-part-by-function.

Usage:
  python scripts/seed_neo4j.py
  python scripts/seed_neo4j.py --wipe

Env (.env):
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=yourpassword
  # optional (Neo4j 4/5 multi-db)
  # NEO4J_DATABASE=neo4j
"""

import os
import argparse
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

# -------------------- config --------------------

def get_driver():
    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    if not uri:
        raise ValueError("NEO4J_URI not found in .env file!")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd  = os.getenv("NEO4J_PASSWORD", "neo4j")
    return GraphDatabase.driver(uri, auth=(user, pwd))

def get_database() -> Optional[str]:
    return os.getenv("NEO4J_DATABASE") or None

# -------------------- cypher helpers --------------------

def ensure_constraints(session):
    stmts = [
        "CREATE CONSTRAINT part_name IF NOT EXISTS FOR (p:Part) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT part_unity IF NOT EXISTS FOR (p:Part) REQUIRE p.unityId IS UNIQUE",
        "CREATE CONSTRAINT process_name IF NOT EXISTS FOR (pr:Process) REQUIRE pr.name IS UNIQUE",
    ]
    for q in stmts:
        session.execute_write(lambda tx: tx.run(q))

def wipe_all(session):
    session.execute_write(lambda tx: tx.run("MATCH (n) DETACH DELETE n"))

# -------------------- seed data (STRICT to your list) --------------------
# From your table: GameObject Name -> Part Name (for AI)
# (Unity will send the "Part Name (for AI)" to backend)  ← per your doc
# blades_dividers_turbine_017 → Turbine Dividers, etc.  :contentReference[oaicite:3]{index=3}

PARTS: List[Dict[str, Any]] = [
    {"unityId": "blades_dividers_turbine_017", "name": "Turbine Dividers",
     "description": "Dividers that condition/guide flow before/through the turbine section."},
    {"unityId": "blades_turbine_001",          "name": "Turbine Blades",
     "description": "Blade row that extracts energy from high-temperature gas."},
    {"unityId": "blades_turbine_002_non",      "name": "Turbine Blades",
     "description": "Blade row that extracts energy from high-temperature gas."},
    {"unityId": "blades_turbine_003",          "name": "Turbine Blades",
     "description": "Blade row that extracts energy from high-temperature gas."},
    {"unityId": "blades_turbine_004",          "name": "Turbine Blades",
     "description": "Blade row that extracts energy from high-temperature gas."},
    {"unityId": "canister_turbine_011",        "name": "Combustion Canister",
     "description": "Chamber where fuel mixes with compressed air and ignites."},
    {"unityId": "grid_turbine_007",            "name": "Support Grid",
     "description": "Structural grid providing internal support/positioning."},
    {"unityId": "hull_turbine_004_01",         "name": "Turbine Casing (Outer)",
     "description": "Outer containment casing for turbine section."},
    {"unityId": "hull_turbine_004_02",         "name": "Turbine Casing (Inner)",
     "description": "Inner casing forming the hot gas path boundary."},
    {"unityId": "hull_turbine_004_03",         "name": "Turbine Casing (Mid)",
     "description": "Mid shell segment between inner and outer turbine casings."},
    {"unityId": "mount_turbine_014",           "name": "Engine Mount",
     "description": "Mounting structure that attaches engine to the airframe/rig."},
    {"unityId": "pipes_turbine_009",           "name": "Fuel and Oil Lines",
     "description": "Lines and manifolds that route fuel and oil."},
    {"unityId": "plates_turbine_016",          "name": "Access Panel",
     "description": "Service panel for inspection/maintenance access."},
    {"unityId": "screws_turbine_001",          "name": "Fastening Screws",
     "description": "Fasteners that secure panels or subcomponents."},
]

# Minimal process set strictly needed for endpoint B demo:
# /find-part-by-function must resolve "where the fuel is burned" → Combustion Canister
# so we add Process('Combustion') and PART_OF(Combustion Canister → Combustion). :contentReference[oaicite:4]{index=4}
PROCESSES = [{"name": "Combustion"}]

PART_OF_MAP = {
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

PERFORMS_MAP = {
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

# -------------------- seed routines --------------------

def seed_parts(session, parts: List[Dict[str, Any]]):
    q = """
    UNWIND $rows AS row
    MERGE (p:Part {name: row.name})
      ON CREATE SET p.unityId = row.unityId, p.description = row.description
      ON MATCH  SET p.unityId = row.unityId, p.description = row.description
    RETURN count(*) AS upserted
    """
    res = session.execute_write(lambda tx: tx.run(q, rows=parts).single())
    print(f"[seed] Parts upserted: {res['upserted']}")

def seed_processes(session, processes: List[Dict[str, Any]]):
    q = """
    UNWIND $rows AS row
    MERGE (:Process {name: row.name})
    RETURN count(*) AS upserted
    """
    res = session.execute_write(lambda tx: tx.run(q, rows=processes).single())
    print(f"[seed] Processes upserted: {res['upserted']}")

def seed_part_of(session, mapping: Dict[str, str]):
    rows = [{"part": p, "proc": mapping[p]} for p in mapping]
    if not rows:
        print("[seed] No PART_OF mappings provided.")
        return
    q = """
    UNWIND $rows AS row
    MATCH (p:Part {name: row.part})
    MATCH (pr:Process {name: row.proc})
    MERGE (p)-[:PART_OF]->(pr)
    RETURN count(*) AS linked
    """
    res = session.execute_write(lambda tx: tx.run(q, rows=rows).single())
    print(f"[seed] PART_OF links created: {res['linked']}")

def seed_functions(session, functions: List[Dict[str, Any]]):
    q = """
    UNWIND $rows AS row
    MERGE (:Function {name: row.name})
    RETURN count(*) AS upserted
    """
    res = session.execute_write(lambda tx: tx.run(q, rows=functions).single())
    print(f"[seed] Functions upserted: {res['upserted']}")

def seed_performs(session, mapping: Dict[str, List[str]]):
    rows = []
    for part, funcs in mapping.items():
        for f in funcs:
            rows.append({"part": part, "func": f})
    if not rows:
        print("[seed] No PERFORMS mappings provided.")
        return
    q = """
    UNWIND $rows AS row
    MATCH (p:Part {name: row.part})
    MATCH (f:Function {name: row.func})
    MERGE (p)-[:PERFORMS]->(f)
    RETURN count(*) AS linked
    """
    res = session.execute_write(lambda tx: tx.run(q, rows=rows).single())
    print(f"[seed] PERFORMS links created: {res['linked']}")

# -------------------- main --------------------

def main():
    parser = argparse.ArgumentParser(description="Seed Neo4j with strict turbine parts + minimal process.")
    parser.add_argument("--wipe", action="store_true", help="Danger: wipe all nodes/edges before seeding.")
    args = parser.parse_args()

    driver = get_driver()
    db = get_database()

    with driver.session(database=db) if db else driver.session() as session:
        print("[seed] Ensuring constraints…")
        ensure_constraints(session)

        if args.wipe:
            print("[seed] WIPING ALL DATA…")
            wipe_all(session)

        print("[seed] Seeding parts…")
        seed_parts(session, PARTS)

        print("[seed] Seeding processes…")
        seed_processes(session, PROCESSES)

        print("[seed] Linking PART_OF (Combustion Canister → Combustion)…")
        seed_part_of(session, PART_OF_MAP)

        print("[seed] Seeding functions…")
        seed_functions(session, FUNCTIONS)

        print("[seed] Linking PERFORMS (Part → Function)…")
        seed_performs(session, PERFORMS_MAP)

        # quick counts
        counts = session.run("""
        CALL { MATCH (p:Part) RETURN count(p) AS parts }
        CALL { MATCH (pr:Process) RETURN count(pr) AS procs }
        CALL { MATCH (f:Function) RETURN count(f) AS funcs }
        RETURN parts, procs, funcs
        """).single()
        print(f"[seed] Done. Parts={counts['parts']}  Processes={counts['procs']}  Functions={counts['funcs']}")

    driver.close()

if __name__ == "__main__":
    main()