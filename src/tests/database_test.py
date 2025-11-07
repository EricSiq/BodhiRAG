from neo4j import GraphDatabase

uri = "neo4j://127.0.0.1:7687"
# Alternatively, try "neo4j://localhost:7687"
username = "neo4j"
password = "password"  # Replace with the actual password

try:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    print("Connection successful")
    driver.close()
except Exception as e:
    print("Connection failed:", e)

#This Connection address is successful. use these values for database connections