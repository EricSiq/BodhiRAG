#BodhiRAG-main\src\scripts\run_pipeline.py

#python run_pipeline.py --max-docs 2
"""
Master Pipeline Orchestrator for BodhiRAG
Runs the complete ETL: Documents → Knowledge Extraction → Graph DB → Vector DB
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add src to path (robustly find the repository root and add its `src` folder)
def _find_repo_root(start: Path) -> Path:
    """Walk up parents to find a repo root marker file.
    Looks for requirements.txt, setup.py, README.md, or .git as hints.
    Falls back to two levels up if none found.
    """
    start = start.resolve()
    candidates = [start] + list(start.parents)
    for p in candidates:
        if (p / 'requirements.txt').exists() or (p / 'setup.bat').exists() or (p / 'README.md').exists() or (p / '.git').exists():
            return p
    # fallback: assume repo root is two levels up (original code's intent)
    return Path(__file__).resolve().parent.parent


project_root = _find_repo_root(Path(__file__).parent)
# Add repository root to sys.path so `src` is importable as a top-level package (i.e. import src.*)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.data_ingestion import document_loader, knowledge_extractor, load_and_chunk_documents, extract_knowledge_from_chunk
from langchain_core.documents import Document  # ADD THIS IMPORT

from src.graph_rag.graph_connector import KnowledgeGraphConnector
from src.graph_rag.vector_connector import VectorStoreConnector

class ArtemisPipeline:
    def __init__(self):
        self.data_dir = project_root / 'data'
        self.processed_dir = self.data_dir / 'processed'
        
        # FIX: Create parent directory first, then subdirectory
        self.data_dir.mkdir(parents=True, exist_ok=True)  # ADD parents=True
        self.processed_dir.mkdir(exist_ok=True)
        
        self.kg_connector = KnowledgeGraphConnector()
        self.vs_connector = VectorStoreConnector()
        
    def run_phase1_data_ingestion(self, max_docs: int = None) -> list:
        # Phase 1: Document loading and chunking
        print("=" * 60)
        print("PHASE 1: DATA INGESTION & CHUNKING")
        print("=" * 60)
        
        # UPDATE: New CSV path based on your structure
        csv_path = project_root / "src" / "Datasets" / "SB_publication_PMC.csv"
        
        # CHECK IF CSV FILE EXISTS
        if not csv_path.exists():
            print(f"CSV file not found at: {csv_path}")
            print("Please make sure the CSV file exists in the correct location")
            return []
        
        print(f"Using CSV file: {csv_path}")
        
        documents = load_and_chunk_documents(
            csv_file_path=str(csv_path),
            max_docs=max_docs,
            max_workers=6
        )
        
        # Save intermediate results
        docs_file = self.processed_dir / f"chunked_documents_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(docs_file, 'w', encoding='utf-8') as f:
            # Convert documents to serializable format
            docs_data = []
            for doc in documents:
                docs_data.append({
                    'page_content': doc.page_content,
                    'metadata': doc.metadata
                })
            json.dump(docs_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(documents)} chunks to {docs_file}")
        return documents

    def run_phase2_knowledge_extraction(self, documents: list) -> list:
        # Phase 2: Knowledge extraction 
        print("\n" + "=" * 60)
        print("PHASE 2: KNOWLEDGE EXTRACTION")
        print("=" * 60)
        
        all_triples = []
        total_chunks = len(documents)
        
        for i, doc in enumerate(documents):
            print(f"🔬 Processing chunk {i+1}/{total_chunks}: {doc.metadata.get('original_title', '')[:50]}...")
            
            triples = extract_knowledge_from_chunk(doc)
            all_triples.extend(triples)
            
            # Progress reporting
            if (i + 1) % 10 == 0:
                print(f"📊 Progress: {i+1}/{total_chunks} chunks, {len(all_triples)} triples extracted")
            
            time.sleep(0.5)  # Rate limiting
        
        # Save triples
        triples_file = self.processed_dir / f"knowledge_triples_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        triples_data = [triple.dict() for triple in all_triples]
        with open(triples_file, 'w', encoding='utf-8') as f:
            json.dump(triples_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(all_triples)} triples to {triples_file}")
        return all_triples
    
    def run_phase3_knowledge_graph(self, triples: list):
        # Phase 3: Populate Knowledge Graph
        print("\n" + "=" * 60)
        print("PHASE 3: KNOWLEDGE GRAPH POPULATION")
        print("=" * 60)
        
        self.kg_connector.connect()
        results = self.kg_connector.populate_graph(triples)
        self.kg_connector.close()
        
        print(f"Knowledge Graph populated: {results}")
    
    def run_phase4_vector_store(self, documents: list):
        # Phase 4: Populate Vector Store
        print("\n" + "=" * 60)
        print("PHASE 4: VECTOR STORE POPULATION")
        print("=" * 60)
        
        self.vs_connector.initialize_store()
        results = self.vs_connector.populate_store(documents)
        
        print(f"Vector Store populated: {len(documents)} documents indexed")
    
    def run_complete_pipeline(self, max_docs: int = None):
        # Run the complete ETL pipeline
        start_time = time.time()
        
        try:
            # Phase 1: Data Ingestion
            documents = self.run_phase1_data_ingestion(max_docs)
            if not documents:
                print("No documents processed. Exiting.")
                return
            
            # Phase 2: Knowledge Extraction  
            triples = self.run_phase2_knowledge_extraction(documents)
            
            # Phase 3: Knowledge Graph
            if triples:
                self.run_phase3_knowledge_graph(triples)
            else:
                print("No triples extracted, skipping Knowledge Graph")
            
            # Phase 4: Vector Store
            self.run_phase4_vector_store(documents)
            
            # Summary
            elapsed = time.time() - start_time
            print(f"\nPIPELINE COMPLETE!")
            print(f"Total time: {elapsed:.2f} seconds")
            print(f"Documents processed: {len(documents)}")
            print(f"Triples extracted: {len(triples) if triples else 0}")
            
        except Exception as e:
            print(f"Pipeline failed: {e}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='BodhiRAG Pipeline Orchestrator')
    parser.add_argument('--max-docs', type=int, default=None, 
                       help='Limit number of documents processed (for testing)')
    parser.add_argument('--phase', choices=['1', '2', '3', '4', 'all'], default='all',
                       help='Run specific phase only')
    
    args = parser.parse_args()
    
    pipeline = ArtemisPipeline()
    
    if args.phase == 'all':
        pipeline.run_complete_pipeline(max_docs=args.max_docs)
    elif args.phase == '1':
        pipeline.run_phase1_data_ingestion(max_docs=args.max_docs)
    elif args.phase == '2':
        # Load existing documents for phase 2 only
        docs_files = list(pipeline.processed_dir.glob("chunked_documents_*.json"))
        if not docs_files:
            print("No existing documents found. Run phase 1 first.")
            return
        latest_docs = max(docs_files, key=os.path.getctime)
        with open(latest_docs, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
        documents = [Document(page_content=doc['page_content'], metadata=doc['metadata']) 
                    for doc in docs_data]
        pipeline.run_phase2_knowledge_extraction(documents)
    elif args.phase == '3':
        # Load existing triples for phase 3 only
        triples_files = list(pipeline.processed_dir.glob("knowledge_triples_*.json"))
        if not triples_files:
            print("No existing triples found. Run phase 2 first.")
            return
        latest_triples = max(triples_files, key=os.path.getctime)
        with open(latest_triples, 'r', encoding='utf-8') as f:
            triples_data = json.load(f)
        # Convert dict back to RelationshipTriple objects
        from src.data_ingestion.knowledge_extractor import RelationshipTriple
        triples = [RelationshipTriple(**triple_dict) for triple_dict in triples_data]
        pipeline.run_phase3_knowledge_graph(triples)
    elif args.phase == '4':
        # Load existing documents for phase 4 only
        docs_files = list(pipeline.processed_dir.glob("chunked_documents_*.json"))
        if not docs_files:
            print("No existing documents found. Run phase 1 first.")
            return
        latest_docs = max(docs_files, key=os.path.getctime)
        with open(latest_docs, 'r', encoding='utf-8') as f:
            docs_data = json.load(f)
        documents = [Document(page_content=doc['page_content'], metadata=doc['metadata']) 
                    for doc in docs_data]
        pipeline.run_phase4_vector_store(documents)

if __name__ == "__main__":
    main()