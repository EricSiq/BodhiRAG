import pandas as pd
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed # Optimization for speed
from typing import List, Tuple, Dict, Any, Optional

# LangChain and Docling specific imports
from langchain_core.documents import Document
from langchain_docling import DoclingLoader # Main loader class
from docling.chunking import HybridChunker
# NOTE: Using the standard import paths for Docling types
from langchain_docling.loader import DoclingLoader, ExportType

#  Core Logic for Extracting URLs 
def extract_publication_data(file_path: str) -> List[Tuple[str, str]]:
    """Loads CSV and extracts (Title, Link) pairs, filtering for valid PMC links."""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found at: {file_path}")

        df = pd.read_csv(file_path, quoting=csv.QUOTE_MINIMAL)
        base_url_prefix = "https://www.ncbi.nlm.nih.gov/pmc/articles/"
        df_filtered = df[df['Link'].astype(str).str.startswith(base_url_prefix, na=False)].copy()

        publication_list = list(zip(df_filtered['Title'], df_filtered['Link']))
        print(f" Document Loader: Extracted {len(publication_list)} valid PMC links.")
        return publication_list

    except Exception as e:
        print(f" Error during CSV extraction: {e}")
        return []

# --- Parallel Processing Worker Function ---

def _process_single_document(item: Tuple[int, str, str], chunker: HybridChunker, csv_file_path: str) -> List[Document]:
    """Worker function executed concurrently to fetch, parse, and enrich a single URL."""
    i, title, url = item
    doc_id = f"PMC_{url.split('/')[-2]}"
    
    try:
        # 1. DoclingLoader handles the web fetch and PDF parsing
        loader = DoclingLoader(
            file_path=url,
            chunker=chunker,
            export_type=ExportType.MARKDOWN 
        )
        docs = loader.load()

        # 2. Add consistent, enriched metadata (Crucial for XAI and KG linkage)
        for doc in docs:
            doc.metadata['original_title'] = title
            doc.metadata['source_url'] = url
            doc.metadata['doc_id'] = doc_id
            doc.metadata['source_file'] = csv_file_path
        
        # NOTE: Reduced logging noise for concurrency
        # print(f"  [Doc {i}] Success: {len(docs)} chunks for '{title[:40]}...'")
        return docs

    except Exception as e:
        # Log failure but return empty list so the main thread continues
        print(f" FAILED document {i} ({doc_id}). Skipping. Error: {e}")
        return []

def load_and_chunk_documents(csv_file_path: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> List[Document]:
    """
    Orchestrates the parallel Docling ingestion process using a ThreadPoolExecutor.
    """
    publication_data = extract_publication_data(csv_file_path)
    if not publication_data:
        return []

    processed_documents: List[Document] = []
    # Instantiate HybridChunker with optimized parameters
    chunker = HybridChunker(max_chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # Use ThreadPoolExecutor for I/O-bound tasks (network fetching)
    MAX_WORKERS = 15 
    total_docs = len(publication_data)
    
    print(f"Starting parallel Docling ingestion for {total_docs} documents with {MAX_WORKERS} workers...")

    tasks = [(i + 1, title, url) for i, (title, url) in enumerate(publication_data)]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks and map futures to the original document tuple
        future_to_doc = {executor.submit(_process_single_document, item, chunker, csv_file_path): item for item in tasks}
        
        # Wait for tasks to complete, extending the final list with results
        for future in as_completed(future_to_doc):
            try:
                result_chunks = future.result()
                processed_documents.extend(result_chunks)
            except Exception as e:
                print(f"  Critical error in executor thread: {e}")
                
    print(f"\n Docling Ingestion Complete. Total chunks generated: {len(processed_documents)}")
    return processed_documents
