"""
BodhiRAG Guided Ingestion Workflow
Implements the ingestion workflow from FRONTEND_UX_DESIGN.md:
1. Choose data
2. Preflight checks
3. Run with progress
4. Review results
"""

import os
import logging
from typing import Dict, Any, List, Optional, Callable, Generator
from datetime import datetime
from pathlib import Path

from src.models import RunManifest, ServiceHealth
from src.pipeline.manifest_manager import get_manifest_manager
from src.services.health_manager import get_health_manager

logger = logging.getLogger(__name__)


class GuidedIngestionWorkflow:
    """
    Guided workflow for corpus ingestion with preflight checks and progress tracking.
    
    Workflow phases:
    1. preflight() - Validate environment, estimate scope
    2. run() - Execute pipeline with progress
    3. review() - Show results and download manifest
    """
    
    def __init__(self):
        self.manifest_manager = get_manifest_manager()
        self.health_manager = get_health_manager()
        
        # State
        self.csv_file: Optional[str] = None
        self.max_docs: int = 10
        self.preflight_results: Dict[str, Any] = {}
        self.current_manifest: Optional[RunManifest] = None
        
        # Progress callback
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable):
        """Set callback for progress updates."""
        self._progress_callback = callback
    
    def _emit_progress(self, message: str, progress: float = 0.0):
        """Emit progress update."""
        if self._progress_callback:
            self._progress_callback(message, progress)
        logger.info(f"[{progress:.0%}] {message}")
    
    # -------------------------------------------------------------------------
    # Phase 1: Choose Data
    # -------------------------------------------------------------------------
    
    def set_data_source(self, csv_file: str, max_docs: int = 10) -> Dict[str, Any]:
        """
        Set the data source for ingestion.
        Returns validation results.
        """
        self.csv_file = csv_file
        self.max_docs = max_docs
        
        result = {
            "valid": True,
            "file": csv_file,
            "max_docs": max_docs,
            "errors": [],
            "warnings": []
        }
        
        # Validate file exists
        if not csv_file or not Path(csv_file).exists():
            result["valid"] = False
            result["errors"].append("CSV file not found")
            return result
        
        # Validate extension
        if not csv_file.lower().endswith('.csv'):
            result["valid"] = False
            result["errors"].append("File must be a CSV")
            return result
        
        # Check file size
        try:
            file_size = Path(csv_file).stat().st_size
            max_size = 50 * 1024 * 1024  # 50 MB
            if file_size > max_size:
                result["valid"] = False
                result["errors"].append(f"File size {file_size / 1024 / 1024:.1f}MB exceeds 50MB limit")
        except Exception as e:
            result["warnings"].append(f"Could not check file size: {e}")
        
        return result
    
    def get_accepted_columns(self) -> List[str]:
        """Return list of accepted CSV columns."""
        return [
            "Title (required)",
            "Link (required) - PMC URL",
            "Authors (optional)",
            "Publication Date (optional)",
            "Abstract (optional)",
        ]
    
    # -------------------------------------------------------------------------
    # Phase 2: Preflight Checks
    # -------------------------------------------------------------------------
    
    def preflight(self) -> Dict[str, Any]:
        """
        Run preflight checks before ingestion.
        Returns detailed status of all components.
        """
        self._emit_progress("Running preflight checks...", 0.0)
        
        results = {
            "passed": True,
            "checks": {},
            "warnings": [],
            "errors": [],
            "estimates": {}
        }
        
        # Check 1: Parser availability
        self._emit_progress("Checking parser availability...", 0.1)
        try:
            from src.data_ingestion.document_loader import DOCLING_AVAILABLE
            parser = "Docling" if DOCLING_AVAILABLE else "Simple HTML loader"
            results["checks"]["parser"] = {
                "status": "available",
                "name": parser,
                "message": f"Parser: {parser}"
            }
        except ImportError:
            results["checks"]["parser"] = {
                "status": "fallback",
                "name": "Simple HTML loader",
                "message": "Docling not available, using fallback"
            }
        
        # Check 2: Vector store
        self._emit_progress("Checking vector store...", 0.2)
        health = self.health_manager.get_health()
        if health.vector_available:
            results["checks"]["vector_store"] = {
                "status": "available",
                "message": f"Vector store ready ({health.vector_document_count} existing documents)"
            }
        else:
            results["checks"]["vector_store"] = {
                "status": "warning",
                "message": "Vector store will be initialized"
            }
        
        # Check 3: Graph database
        self._emit_progress("Checking graph database...", 0.3)
        if health.graph_available:
            results["checks"]["graph"] = {
                "status": "available",
                "message": f"Neo4j connected ({health.graph_entity_count} entities)"
            }
        else:
            results["checks"]["graph"] = {
                "status": "optional",
                "message": "Neo4j not configured (optional)"
            }
            results["warnings"].append("Graph database not configured - relationships will not be stored")
        
        # Check 4: Model availability
        self._emit_progress("Checking model availability...", 0.4)
        if health.generation_available:
            results["checks"]["model"] = {
                "status": "available",
                "message": f"LLM: {health.generation_model}"
            }
        else:
            results["checks"]["model"] = {
                "status": "fallback",
                "message": "Using keyword extraction (no LLM)"
            }
            results["warnings"].append("LLM not available - using keyword-based extraction")
        
        # Check 5: Storage capacity
        self._emit_progress("Checking storage...", 0.5)
        try:
            from src.core.config import settings
            chroma_path = Path(settings.chroma_path)
            chroma_path.mkdir(parents=True, exist_ok=True)
            
            # Check if we can write
            test_file = chroma_path / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            
            results["checks"]["storage"] = {
                "status": "available",
                "message": f"Storage path: {settings.chroma_path}"
            }
        except Exception as e:
            results["checks"]["storage"] = {
                "status": "error",
                "message": f"Storage not writable: {e}"
            }
            results["errors"].append(f"Cannot write to storage: {e}")
            results["passed"] = False
        
        # Check 6: Duplicate estimate
        self._emit_progress("Estimating duplicates...", 0.6)
        if self.csv_file:
            try:
                import pandas as pd
                df = pd.read_csv(self.csv_file)
                if 'Link' in df.columns:
                    total = len(df)
                    unique = df['Link'].nunique()
                    duplicates = total - unique
                    results["estimates"]["total_sources"] = total
                    results["estimates"]["unique_sources"] = unique
                    results["estimates"]["duplicates"] = duplicates
                    
                    if duplicates > 0:
                        results["warnings"].append(f"{duplicates} duplicate URLs will be skipped")
            except Exception as e:
                results["warnings"].append(f"Could not estimate duplicates: {e}")
        
        # Estimate scope
        self._emit_progress("Calculating estimates...", 0.8)
        results["estimates"]["max_docs"] = self.max_docs
        results["estimates"]["estimated_chunks"] = self.max_docs * 10  # ~10 chunks per doc
        results["estimates"]["estimated_time"] = f"{self.max_docs * 30} to {self.max_docs * 60} seconds"
        
        self._emit_progress("Preflight complete", 1.0)
        self.preflight_results = results
        return results
    
    # -------------------------------------------------------------------------
    # Phase 3: Run Pipeline
    # -------------------------------------------------------------------------
    
    def run(self) -> Generator[Dict[str, Any], None, None]:
        """
        Run the ingestion pipeline with progress updates.
        Yields status dicts for UI updates.
        """
        if not self.csv_file:
            yield {"error": "No data source set"}
            return
        
        # Import dependencies
        from src.data_ingestion.document_loader import extract_publication_data
        from src.data_ingestion.simple_loader import load_and_chunk_documents_simple
        from src.data_ingestion import extract_knowledge_from_chunk
        from src.graph_rag.vector_connector import VectorStoreConnector
        from src.graph_rag.graph_connector import KnowledgeGraphConnector
        from src.core.config import settings
        
        # Create manifest
        self.current_manifest = self.manifest_manager.create_staging_manifest(
            input_sources=self.max_docs,
            parser_name="simple_loader",
            parser_version="1.0.0",
        )
        
        status = {
            "phase": "starting",
            "progress": 0.0,
            "message": "Starting pipeline..."
        }
        yield status
        
        # Phase 1: Load publications
        self._emit_progress("Loading publications from CSV...", 0.1)
        status["phase"] = "loading"
        status["message"] = "Loading publication data..."
        yield status
        
        publication_data = extract_publication_data(self.csv_file)
        if not publication_data:
            self.current_manifest.add_failure("csv", "loading", "No valid PMC links found")
            status["error"] = "No valid PMC links found in CSV"
            yield status
            return
        
        status["message"] = f"Found {len(publication_data)} publications"
        yield status
        
        # Phase 2: Fetch and chunk documents
        self._emit_progress("Fetching and chunking documents...", 0.2)
        status["phase"] = "chunking"
        status["message"] = "Processing documents..."
        yield status
        
        log_lines = []
        def progress_cb(msg):
            log_lines.append(msg.strip())
        
        documents = load_and_chunk_documents_simple(
            publication_data=publication_data,
            max_docs=self.max_docs,
            chunk_size=1000,
            progress_callback=progress_cb,
        )
        
        self.current_manifest.sources_processed = len(documents) // 10  # rough estimate
        self.current_manifest.chunks_created = len(documents)
        
        status["message"] = f"Processed {len(documents)} document chunks"
        yield status
        
        if not documents:
            self.current_manifest.add_failure("documents", "chunking", "No documents processed")
            status["error"] = "No documents could be processed"
            yield status
            return
        
        # Phase 3: Knowledge extraction
        self._emit_progress("Extracting knowledge triples...", 0.4)
        status["phase"] = "extraction"
        status["message"] = "Extracting knowledge..."
        yield status
        
        all_triples = []
        extract_limit = min(10, len(documents))
        
        for i, doc in enumerate(documents[:extract_limit]):
            triples = extract_knowledge_from_chunk(doc)
            all_triples.extend(triples)
            
            if (i + 1) % 3 == 0:
                progress = 0.4 + (i / extract_limit) * 0.2
                status["progress"] = progress
                status["message"] = f"Extracted {len(all_triples)} triples"
                yield status
        
        self.current_manifest.triples_extracted = len(all_triples)
        
        # Phase 4: Graph population
        self._emit_progress("Populating knowledge graph...", 0.6)
        status["phase"] = "graph"
        status["message"] = "Writing to graph..."
        yield status
        
        kg_connector = KnowledgeGraphConnector(
            uri=settings.neo4j_uri,
            username=settings.neo4j_username,
            password=settings.neo4j_password,
        )
        
        kg_results = None
        if kg_connector.connect():
            kg_results = kg_connector.populate_graph(all_triples)
            kg_connector.close()
            
            self.current_manifest.entities_created = kg_results.get("entities_created", 0)
            self.current_manifest.relationships_created = kg_results.get("relationships_created", 0)
            status["message"] = f"Graph: {kg_results.get('entities_created', 0)} entities, {kg_results.get('relationships_created', 0)} relationships"
        else:
            status["message"] = "Graph not configured, skipping"
        yield status
        
        # Phase 5: Vector store
        self._emit_progress("Embedding and storing vectors...", 0.8)
        status["phase"] = "vector"
        status["message"] = "Writing to vector store..."
        yield status
        
        vs_connector = VectorStoreConnector()
        vs_connector.initialize_store()
        vs_results = vs_connector.populate_store(documents)
        
        self.current_manifest.sources_processed = self.max_docs
        status["message"] = f"Vector store: {vs_results.get('documents_added', 0)} chunks added"
        yield status
        
        # Phase 6: Finalize
        self._emit_progress("Finalizing...", 0.95)
        status["phase"] = "finalizing"
        status["message"] = "Publishing manifest..."
        yield status
        
        # Publish manifest
        published = self.manifest_manager.publish()
        
        status["phase"] = "complete"
        status["progress"] = 1.0
        status["message"] = "Pipeline complete!"
        status["manifest_id"] = self.current_manifest.build_id
        status["published"] = published
        yield status
    
    # -------------------------------------------------------------------------
    # Phase 4: Review
    # -------------------------------------------------------------------------
    
    def review(self) -> Dict[str, Any]:
        """Return summary of completed run."""
        if not self.current_manifest:
            return {"error": "No run completed"}
        
        manifest = self.current_manifest
        
        return {
            "build_id": manifest.build_id,
            "status": manifest.status,
            "processed": manifest.sources_processed,
            "skipped": manifest.sources_skipped,
            "failed": manifest.sources_failed,
            "chunks": manifest.chunks_created,
            "triples": manifest.triples_extracted,
            "entities": manifest.entities_created,
            "relationships": manifest.relationships_created,
            "duplicates": manifest.duplicate_count,
            "failures": manifest.failures[:10],  # First 10 failures
            "duration": str(manifest.completed_at - manifest.started_at) if manifest.completed_at else "N/A",
        }
    
    def download_manifest(self) -> Optional[str]:
        """Return path to manifest file for download."""
        if self.current_manifest:
            manifest_path = self.manifest_manager.manifest_dir / f"manifest_{self.current_manifest.build_id}.json"
            if manifest_path.exists():
                return str(manifest_path)
        return None
