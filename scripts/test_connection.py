from neo4j import GraphDatabase

# --- IMPORTANT ---
# Manually enter your credentials here for this test.
# Copy them directly from your Neo4j Aura dashboard.

URI = "neo4j://127.0.0.1:7687"
USERNAME = "neo4j"
PASSWORD = "namaste@123"

class Neo4jConnection:
    def __init__(self, uri, user, password):
        # The only change is adding encrypted=False for this test
        self.driver = GraphDatabase.driver(uri, auth=(user, password), encrypted=False)

    def close(self):
        self.driver.close()

    def verify_connection(self):
        try:
            self.driver.verify_connectivity()
            print("✅ Connection successful (without encryption)!")
        except Exception as e:
            print("❌ Connection failed again. Details below:")
            print(e)

if __name__ == "__main__":
    print("--- Running Neo4j Aura Connection Test (Encryption Disabled) ---")
    connection = Neo4jConnection(URI, USERNAME, PASSWORD)
    connection.verify_connection()
    connection.close()
    print("--- Test finished ---")
