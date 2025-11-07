#BodhiRAG-main\src\graph_rag\vector_connector.py
"""
Vector Store Connector using ChromaDB with Granite Embeddings
Handles semantic search and document retrieval
"""

import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

class VectorStoreConnector:
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            # Always use project root/data/chroma_db
            project_root = Path(__file__).parent.parent.parent
            self.persist_directory = project_root / "data" / "chroma_db"
        else:
            self.persist_directory = persist_directory
        
        # Create directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)
    def initialize_store(self, collection_name: str = "nasa_publications"):
        """Initialize ChromaDB client and collection"""
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Initialize embedding model (Granite or fallback)
            self._initialize_embedding_model()
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(collection_name)
                self.logger.info(f"✅ Loaded existing collection: {collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "NASA Space Biology Publications"}
                )
                self.logger.info(f"✅ Created new collection: {collection_name}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize vector store: {e}")
            return False
    
    def _initialize_embedding_model(self):
        """Initialize the embedding model (Granite or fallback)"""
        try:
            # Try to load Granite embeddings
            self.embedding_model = SentenceTransformer('ibm/granite-embedding-30m-english')
            self.logger.info("✅ Loaded Granite embedding model")
        except Exception as e:
            # Fallback to all-MiniLM
            self.logger.warning(f"⚠️  Granite not available, using all-MiniLM: {e}")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def populate_store(self, documents: List[Document]) -> Dict[str, Any]:
        """Populate vector store with document chunks"""
        if not self.collection:
            self.initialize_store()

        try:
            # Prepare documents for ingestion
            documents_data = []
            metadatas = []
            ids = []

            for i, doc in enumerate(documents):
                documents_data.append(doc.page_content)
                metadatas.append({
                    'source_title': doc.metadata.get('original_title', ''),
                    'source_url': doc.metadata.get('source_url', ''),
                    'doc_id': doc.metadata.get('doc_id', ''),
                    'chunk_id': doc.metadata.get('chunk_id', f'chunk_{i}'),
                    'content_length': len(doc.page_content)
                })
                ids.append(f"doc_{i}_{doc.metadata.get('doc_id', 'unknown')}")

            # Add to collection
            self.collection.add(
                documents=documents_data,
                metadatas=metadatas,
                ids=ids
            )

            self.logger.info(f"✅ Added {len(documents)} documents to vector store")

            return {
                "documents_added": len(documents),
                "collection_size": self.collection.count()
            }

        except Exception as e:
            self.logger.error(f"❌ Failed to populate vector store: {e}")
            return {"error": str(e)}
        
    def semantic_search(self, query: str, n_results: int = 5, filters: Dict = None) -> List[Dict]:
        """Perform semantic search on the vector store"""
        if not self.collection:
            self.initialize_store()
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Perform search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filters,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i],
                    'score': 1 - results['distances'][0][i]  # Convert distance to similarity score
                })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"❌ Semantic search failed: {e}")
            return []
    
    def hybrid_search(self, query: str, kg_results: List[Dict], n_results: int = 5) -> List[Dict]:
        """
        Hybrid search combining KG relationships and semantic search
        """
        # Get semantic results
        semantic_results = self.semantic_search(query, n_results * 2)
        
        # Combine and rank results
        all_results = []
        
        # Add semantic results
        for result in semantic_results:
            all_results.append({
                'type': 'semantic',
                'content': result['content'],
                'metadata': result['metadata'],
                'score': result['score'] * 0.7  # Weight semantic results
            })
        
        # Add KG results as context
        for kg_result in kg_results:
            all_results.append({
                'type': 'kg_relationship',
                'content': f"{kg_result['subject']} {kg_result['relationship']} {kg_result['object']}",
                'metadata': {
                    'source_title': kg_result.get('source_title', ''),
                    'evidence': kg_result.get('evidence', '')
                },
                'score': 0.8  # Fixed score for KG relationships
            })
        
        # Sort by score and return top results
        all_results.sort(key=lambda x: x['score'], reverse=True)
        return all_results[:n_results]
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection"""
        if not self.collection:
            self.initialize_store()
        
        try:
            # Get sample to estimate stats
            sample = self.collection.peek(limit=100)
            
            return {
                "total_documents": self.collection.count(),
                "sample_metadata_fields": list(sample['metadatas'][0].keys()) if sample['metadatas'] else [],
                "average_content_length": np.mean([len(doc) for doc in sample['documents']]) if sample['documents'] else 0
            }
        except Exception as e:
            self.logger.error(f"❌ Failed to get collection stats: {e}")
            return {"error": str(e)}