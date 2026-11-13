#BodhiRAG/src/graph_rag/vector_connector.py
"""
Vector Store Connector: ChromaDB + Sentence Transformers semantic search.

Startup logic:
1. If /tmp/chroma_db already has data -> use it (pipeline was run before)
2. If data/chroma_preseeded/ exists -> copy it to /tmp/chroma_db (HF Space launch)
3. Otherwise -> create empty collection (users must run pipeline)
"""

import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

# Paths
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_PRESEEDED_DIR = _PROJECT_ROOT / "data" / "chroma_preseeded"
_RUNTIME_DIR_DEFAULT = "/tmp/chroma_db"


class VectorStoreConnector:
    def __init__(self, persist_directory: str = None):
        # Respect explicit argument, then env var, then /tmp default
        if persist_directory is not None:
            self.persist_directory = str(persist_directory)
        else:
            self.persist_directory = os.environ.get("CHROMA_PATH", _RUNTIME_DIR_DEFAULT)

        # NOTE: do NOT call os.makedirs here — initialize_store() does it
        self.embedding_model: Optional[SentenceTransformer] = None
        self.collection = None
        self.client = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize_store(self, collection_name: str = "nasa_publications") -> bool:
        """Initialize ChromaDB, copying pre-seeded data if available."""
        try:
            self._ensure_runtime_dir()
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )

            # Initialize embedding model
            self._initialize_embedding_model()

            # Get or create collection
            try:
                self.collection = self.client.get_collection(collection_name)
                count = self.collection.count()
                logger.info(f"✅ Loaded existing collection '{collection_name}' ({count} docs)")
            except Exception:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "NASA Space Biology Publications"},
                )
                logger.info(f"✅ Created new collection: {collection_name}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize vector store: {e}")
            return False

    def _ensure_runtime_dir(self):
        """
        Set up the runtime ChromaDB directory.
        If it's empty/missing and a pre-seeded DB exists, copy that over.
        """
        runtime = Path(self.persist_directory)
        runtime.mkdir(parents=True, exist_ok=True)

        # Check if runtime dir is empty (new Space launch)
        runtime_files = list(runtime.iterdir()) if runtime.exists() else []
        is_empty = len(runtime_files) == 0

        if is_empty and _PRESEEDED_DIR.exists():
            logger.info(f"📦 Copying pre-seeded ChromaDB from {_PRESEEDED_DIR}")
            try:
                # Copy all files from pre-seeded to runtime
                for item in _PRESEEDED_DIR.iterdir():
                    if item.name == "seed_manifest.json":
                        continue  # skip manifest
                    dest = runtime / item.name
                    if item.is_dir():
                        shutil.copytree(str(item), str(dest), dirs_exist_ok=True)
                    else:
                        shutil.copy2(str(item), str(dest))
                logger.info(f"✅ Pre-seeded DB copied to {runtime}")
            except Exception as e:
                logger.warning(f"⚠️  Could not copy pre-seeded DB: {e}: starting fresh")

    def _initialize_embedding_model(self):
        """Initialize embedding model (Granite preferred, MiniLM fallback)."""
        if self.embedding_model is not None:
            return  # already initialized
        try:
            self.embedding_model = SentenceTransformer("ibm-granite/granite-embedding-30m-english", device="cpu")
            logger.info("Loaded Granite embedding model")
        except Exception as e:
            logger.warning(f"Granite unavailable, using all-MiniLM-L6-v2: {e}")
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")

    # ------------------------------------------------------------------
    # Document population
    # ------------------------------------------------------------------

    def populate_store(self, documents: List[Document]) -> Dict[str, Any]:
        """Add document chunks to the vector store."""
        if self.collection is None:
            self.initialize_store()

        try:
            doc_texts = []
            metadatas = []
            ids = []

            for i, doc in enumerate(documents):
                doc_texts.append(doc.page_content)
                metadatas.append({
                    "source_title":   doc.metadata.get("original_title", ""),
                    "source_url":     doc.metadata.get("source_url", ""),
                    "doc_id":         doc.metadata.get("doc_id", ""),
                    "chunk_id":       doc.metadata.get("chunk_id", f"chunk_{i}"),
                    "content_length": len(doc.page_content),
                })
                ids.append(f"doc_{i}_{doc.metadata.get('doc_id', 'unknown')}")

            self.collection.add(documents=doc_texts, metadatas=metadatas, ids=ids)
            count = self.collection.count()
            logger.info(f"✅ Added {len(documents)} documents: total: {count}")

            return {"documents_added": len(documents), "collection_size": count}

        except Exception as e:
            logger.error(f"❌ Failed to populate vector store: {e}")
            return {"error": str(e), "documents_added": 0}

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def semantic_search(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """Semantic search using query embedding."""
        if self.collection is None:
            self.initialize_store()
        if self.embedding_model is None:
            self._initialize_embedding_model()

        try:
            # Check if collection has any documents
            if self.collection.count() == 0:
                logger.info("Vector store is empty: no results")
                return []

            query_embedding = self.embedding_model.encode([query]).tolist()[0]

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, self.collection.count()),
                where=filters,
                include=["documents", "metadatas", "distances"],
            )

            formatted = []
            for i in range(len(results["documents"][0])):
                distance = results["distances"][0][i]
                formatted.append({
                    "content":  results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": distance,
                    "score":    max(0.0, 1.0 - distance),  # cosine → similarity
                })

            return formatted

        except Exception as e:
            logger.error(f"❌ Semantic search failed: {e}")
            return []

    def hybrid_search(
        self,
        query: str,
        kg_results: List[Dict],
        n_results: int = 5,
    ) -> List[Dict]:
        """Combine semantic search with KG results for re-ranked retrieval."""
        semantic_results = self.semantic_search(query, n_results * 2)

        all_results = [
            {
                "type":     "semantic",
                "content":  r["content"],
                "metadata": r["metadata"],
                "score":    r["score"] * 0.7,
            }
            for r in semantic_results
        ]

        for kg_r in kg_results:
            all_results.append({
                "type":     "kg_relationship",
                "content":  f"{kg_r['subject']} {kg_r['relationship']} {kg_r['object']}",
                "metadata": {
                    "source_title": kg_r.get("source_title", ""),
                    "evidence":     kg_r.get("evidence", ""),
                },
                "score": 0.8,
            })

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:n_results]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return statistics about the vector store."""
        if self.collection is None:
            self.initialize_store()

        try:
            if not self.collection or self.collection.count() == 0:
                return {
                    "total_documents": 0,
                    "sample_metadata_fields": [],
                    "average_content_length": 0,
                    "message": "Collection is empty: run the pipeline to add documents",
                }

            sample = self.collection.peek(limit=min(100, self.collection.count()))
            avg_len = (
                float(np.mean([len(d) for d in sample["documents"]]))
                if sample["documents"]
                else 0.0
            )

            return {
                "total_documents":       self.collection.count(),
                "sample_metadata_fields": list(sample["metadatas"][0].keys()) if sample["metadatas"] else [],
                "average_content_length": avg_len,
            }
        except Exception as e:
            logger.error(f"❌ get_collection_stats failed: {e}")
            return {"error": str(e), "total_documents": 0}