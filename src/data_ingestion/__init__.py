#BodhiRAG/src/data_ingestion/__init__.py
"""
Data Ingestion Module — NASA Space Biology Knowledge Extraction.

Exposes core functions for document loading and knowledge extraction.
The `document_loader` import is guarded because langchain_docling is
optional (not available on HF Spaces), allowing graceful fallback.
"""

# Guard the Docling-based loader — langchain_docling is optional
try:
    from .document_loader import load_and_chunk_documents, extract_publication_data
except ImportError:
    load_and_chunk_documents = None
    extract_publication_data = None

from .knowledge_extractor import (
    Entity,
    RelationshipTriple,
    ExtractionSchema,
    extract_knowledge_from_chunk,
)

__all__ = [
    "load_and_chunk_documents",
    "extract_publication_data",
    "extract_knowledge_from_chunk",
    "Entity",
    "RelationshipTriple",
    "ExtractionSchema",
]
