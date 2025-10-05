import pandas as pd
import csv
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any

from langchain_core.documents import Document
from langchain_docling import DoclingLoader
from docling.chunking import HybridChunker

def extract_publication_data(file_path: str) -> List[Tuple[str, str]]:
    """Loads CSV and extracts (Title, Link) pairs for valid PMC links."""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found at: {file_path}")

        df = pd.read_csv(file_path, quoting=csv.QUOTE_MINIMAL)
        base_url_prefix = "https://www.ncbi.nlm.nih.gov/pmc/articles/"
        df_filtered = df[df['Link'].astype(str).str.startswith(base_url_prefix, na=False)].copy()

        publication_list = list(zip(df_filtered['Title'], df_filtered['Link']))
        print(f"✅ Extracted {len(publication_list)} valid PMC links.")
        return publication_list

    except Exception as e:
        print(f"❌ Error during CSV extraction: {e}")
        return []

def _process_single_document(item: Tuple[int, str, str], chunker: HybridChunker, csv_file_path: str) -> List[Document]:
    """Worker function for parallel document processing."""
    i, title, url = item
    doc_id = f"PMC_{url.split('/')[-2]}"
    
    try:
        loader = DoclingLoader(
            file_path=url,
            chunker=chunker,
            export_type="markdown"
        )
        docs = loader.load()

        for doc in docs:
            doc.metadata.update({
                'original_title': title,
                'source_url': url,
                'doc_id': doc_id,
                'source_file': csv_file_path,
                'chunk_id': f"{doc_id}_chunk_{len(docs)}"
            })
        
        print(f"  ✅ Document {i}: {len(docs)} chunks from '{title[:40]}...'")
        return docs

    except Exception as e:
        print(f"  ❌ FAILED document {i}. Skipping. Error: {e}")
        return []

def load_and_chunk_documents(
    csv_file_path: str, 
    chunk_size: int = 2000, 
    chunk_overlap: int = 200, 
    max_docs: int = None,
    max_workers: int = 8
) -> List[Document]:
    """
    Orchestrates parallel Docling ingestion process.
    
    Args:
        csv_file_path: Path to NASA publications CSV
        chunk_size: Size of text chunks
        chunk_overlap: Overlap between chunks
        max_docs: Limit number of documents processed (for testing)
        max_workers: Number of parallel workers
    """
    publication_data = extract_publication_data(csv_file_path)
    if not publication_data:
        return []

    # Apply limit for testing
    if max_docs:
        publication_data = publication_data[:max_docs]
    
    processed_documents = []
    chunker = HybridChunker(max_chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    total_docs = len(publication_data)
    print(f"🚀 Starting parallel processing of {total_docs} NASA publications with {max_workers} workers...")

    tasks = [(i + 1, title, url) for i, (title, url) in enumerate(publication_data)]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_doc = {
            executor.submit(_process_single_document, item, chunker, csv_file_path): item 
            for item in tasks
        }
        
        for future in as_completed(future_to_doc):
            try:
                result_chunks = future.result()
                processed_documents.extend(result_chunks)
            except Exception as e:
                print(f"  💥 Critical error in executor: {e}")
                
    print(f"\n🎉 PROCESSING COMPLETE: {len(processed_documents)} chunks from {total_docs} documents")
    return processed_documents