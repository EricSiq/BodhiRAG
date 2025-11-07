# test_connectors.py
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.graph_rag.graph_connector import KnowledgeGraphConnector
from src.graph_rag.vector_connector import VectorStoreConnector

def test_kg():
    print("Testing Knowledge Graph Connector...")
    kg = KnowledgeGraphConnector()
    if kg.connect():
        print("✅ Neo4j connected")
        # Try to query for a known entity
        results = kg.query_relationships("Microgravity")
        print(f"Found {len(results)} relationships for 'Microgravity'")
        for rel in results:
            print(f"  {rel}")
    else:
        print("❌ Neo4j connection failed")

def test_vs():
    print("Testing Vector Store Connector...")
    vs = VectorStoreConnector()
    if vs.initialize_store():
        print("✅ ChromaDB initialized")
        # Try a search
        results = vs.semantic_search("bone loss", n_results=3)
        print(f"Found {len(results)} documents for 'bone loss'")
        for doc in results:
            print(f"  Score: {doc['score']}, Content: {doc['content'][:100]}...")
    else:
        print("❌ ChromaDB initialization failed")

if __name__ == "__main__":
    test_kg()
    test_vs()