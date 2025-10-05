
"""
Data Ingestion Module - NASA Space Biology Knowledge Extraction

Initializes the data_ingestion module, exposing core functions and schemas.
This allows other scripts (like run_pipeline.py) to import key components easily.
"""
from .document_loader import load_and_chunk_documents
from .knowledge_extractor import Entity, RelationshipTriple, extract_knowledge_from_chunk

# Expose the Pydantic schemas for upstream modules (e.g., graph_connector)
__all__ = [
    'load_and_chunk_documents',
    'extract_publication_data', 
    'extract_knowledge_from_chunk',
    'Entity',
    'RelationshipTriple', 
    'ExtractionSchema'
]