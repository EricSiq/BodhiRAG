"""
BodhiRAG: Local Integration Test
===================================
Validates that all components work before pushing to HF Spaces.

Usage:
    py -3.12 scripts/test_local.py
"""

import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"

results = []

def check(name: str, fn, warn_only: bool = False):
    try:
        fn()
        results.append((PASS, name))
        print(f"  {PASS} {name}")
        return True
    except Exception as e:
        symbol = WARN if warn_only else FAIL
        results.append((symbol, f"{name}: {e}"))
        print(f"  {symbol} {name}: {e}")
        return False


print("\nBodhiRAG Integration Test Suite")
print("=" * 50)

# ── 1. Import checks ──────────────────────────────────────────────────────────
print("\n[1/6] Import Checks")

check("Import chromadb", lambda: __import__("chromadb"))
check("Import sentence_transformers", lambda: __import__("sentence_transformers"))
check("Import gradio", lambda: __import__("gradio"))
check("Import plotly", lambda: __import__("plotly"))
check("Import langchain_core", lambda: __import__("langchain_core"))
check("Import bs4", lambda: __import__("bs4"))
check("Import pydantic v2", lambda: (
    __import__("pydantic"), 
    setattr(sys.modules["__main__"], "_pydantic_ver",
            __import__("pydantic").VERSION.split(".")[0]),
    None if sys.modules["__main__"]._pydantic_ver == "2" else (_ for _ in ()).throw(
        ValueError(f"Pydantic v2 required, got v{sys.modules['__main__']._pydantic_ver}")
    )
))

# ── 2. BodhiRAG module imports ────────────────────────────────────────────────
print("\n[2/6] BodhiRAG Module Imports")

check("from src.graph_rag.vector_connector import VectorStoreConnector",
      lambda: __import__("src.graph_rag.vector_connector", fromlist=["VectorStoreConnector"]))
check("from src.graph_rag.agent_router import HybridRAGAgent",
      lambda: __import__("src.graph_rag.agent_router", fromlist=["HybridRAGAgent"]))
check("from src.graph_rag.graph_visualizer import build_kg_graph",
      lambda: __import__("src.graph_rag.graph_visualizer", fromlist=["build_kg_graph"]))
check("from src.services.llm_inference import generate_answer",
      lambda: __import__("src.services.llm_inference", fromlist=["generate_answer"]))
check("from src.data_ingestion import extract_knowledge_from_chunk",
      lambda: __import__("src.data_ingestion", fromlist=["extract_knowledge_from_chunk"]))

# ── 3. Vector Store ────────────────────────────────────────────────────────────
print("\n[3/6] Vector Store")

from src.graph_rag.vector_connector import VectorStoreConnector
vs = VectorStoreConnector(persist_directory="C:/tmp/test_chroma_db")

def test_vs_init():
    ok = vs.initialize_store(collection_name="test_collection")
    assert ok, "initialize_store returned False"

check("VectorStoreConnector.initialize_store()", test_vs_init)

def test_vs_populate():
    from langchain_core.documents import Document
    docs = [
        Document(
            page_content="Microgravity causes bone loss in astronauts during spaceflight.",
            metadata={"original_title": "Test Paper", "source_url": "https://example.com", "doc_id": "test_001", "chunk_id": "test_001_chunk_000"}
        ),
        Document(
            page_content="Space radiation induces oxidative stress and DNA damage in cells.",
            metadata={"original_title": "Test Paper 2", "source_url": "https://example.com/2", "doc_id": "test_002", "chunk_id": "test_002_chunk_000"}
        ),
    ]
    result = vs.populate_store(docs)
    assert result.get("documents_added", 0) > 0, f"No docs added: {result}"

check("VectorStoreConnector.populate_store()", test_vs_populate)

def test_vs_search():
    results = vs.semantic_search("bone loss in space", n_results=2)
    assert len(results) > 0, "No search results"
    assert "content" in results[0], "Missing 'content' key in results"

check("VectorStoreConnector.semantic_search()", test_vs_search)

# ── 4. Knowledge Extraction ───────────────────────────────────────────────────
print("\n[4/6] Knowledge Extraction")

from src.data_ingestion.knowledge_extractor import extract_knowledge_from_chunk
from langchain_core.documents import Document as LC_Doc

def test_extraction():
    doc = LC_Doc(
        page_content=(
            "Microgravity causes bone loss in astronauts. "
            "Exercise countermeasures have been shown to mitigate muscle atrophy. "
            "Radiation-induced oxidative stress affects DNA repair mechanisms."
        ),
        metadata={"original_title": "Test", "doc_id": "t1", "chunk_id": "t1_000"}
    )
    triples = extract_knowledge_from_chunk(doc)
    assert isinstance(triples, list), "Expected list of triples"
    # Note: may be empty if HF_TOKEN not set (falls back to mock)

check("extract_knowledge_from_chunk (mock/LLM)", test_extraction)

# ── 5. Agent Router ────────────────────────────────────────────────────────────
print("\n[5/6] Agent Router")

from src.graph_rag.agent_router import HybridRAGAgent
from src.graph_rag.graph_connector import KnowledgeGraphConnector

kg = KnowledgeGraphConnector(uri="bolt://localhost:7687", username="neo4j", password="")
agent = HybridRAGAgent(kg, vs)

def test_query_routing():
    result = agent.route_query("bone loss in space", use_kg=False, use_vector=True)
    assert "final_answer" in result, "Missing final_answer"
    assert "vs_results" in result, "Missing vs_results"
    assert len(result["final_answer"]) > 0, "Empty answer"

check("HybridRAGAgent.route_query() (vector-only)", test_query_routing)

# ── 6. Graph Visualization ────────────────────────────────────────────────────
print("\n[6/6] Graph Visualization")

from src.graph_rag.graph_visualizer import build_kg_graph

def test_graph_empty():
    fig = build_kg_graph([])
    assert fig is not None, "Expected Plotly figure for empty graph"

def test_graph_with_data():
    mock_kg = [
        {"subject": "Microgravity", "relationship": "causes", "object": "Bone Loss", "evidence": "test"},
        {"subject": "Radiation", "relationship": "causes", "object": "Oxidative Stress", "evidence": "test"},
    ]
    fig = build_kg_graph(mock_kg, title="Test Graph")
    assert fig is not None, "Expected Plotly figure"

check("build_kg_graph(): empty", test_graph_empty)
check("build_kg_graph(): with relationships", test_graph_with_data)

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
passes = sum(1 for r in results if r[0] == PASS)
warns = sum(1 for r in results if r[0] == WARN)
fails = sum(1 for r in results if r[0] == FAIL)

print(f"\nResults: {passes} passed, {warns} warnings, {fails} failed")

if fails == 0:
    print("All critical tests passed! Ready for HF Space deployment.")
else:
    print("Some tests failed -- fix before deploying.")
    sys.exit(1)

# Cleanup temp test DB
import shutil
test_db = Path("C:/tmp/test_chroma_db")
if test_db.exists():
    shutil.rmtree(str(test_db), ignore_errors=True)
