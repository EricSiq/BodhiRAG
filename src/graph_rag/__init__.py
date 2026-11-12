#BodhiRAG/src/graph_rag/__init__.py
"""
Graph RAG module: Knowledge Graph + Vector Store components.
Imports are lazy to avoid import errors when optional dependencies are missing.
"""

# Lazy exports to avoid cascading import failures during testing
def __getattr__(name):
    if name == "KnowledgeGraphConnector":
        from src.graph_rag.graph_connector import KnowledgeGraphConnector
        return KnowledgeGraphConnector
    if name == "VectorStoreConnector":
        from src.graph_rag.vector_connector import VectorStoreConnector
        return VectorStoreConnector
    if name == "HybridRAGAgent":
        from src.graph_rag.agent_router import HybridRAGAgent
        return HybridRAGAgent
    if name == "build_kg_graph":
        from src.graph_rag.graph_visualizer import build_kg_graph
        return build_kg_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "KnowledgeGraphConnector",
    "VectorStoreConnector",
    "HybridRAGAgent",
    "build_kg_graph",
]