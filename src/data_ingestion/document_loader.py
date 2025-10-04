
import pandas as pd
import csv
import os
import time
from typing import List, Tuple, Dict, Any

# LangChain and Docling specific imports
from langchain_core.documents import Document
from langchain_docling import DoclingLoader
# NOTE: The ExportType must be correctly imported from docling_project.docling.document_converter 
# in the actual environment, but we use the common alias path here.
from docling.chunking import HybridChunker
from langchain_docling.loader import DoclingLoader, ExportType

def extract_publication_data(file_path: str) -> List[Tuple[str, str]]:
    """
    Loads the input CSV and extracts (Title, Link) pairs, filtering for valid PMC links.
    """
    try:
        # Check if the file exists before attempting to load
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found at: {file_path}")

        df = pd.read_csv(file_path, quoting=csv.QUOTE_MINIMAL)

        # Assuming columns 'Title' and 'Link'
        base_url_prefix = "https://www.ncbi.nlm.nih.gov/pmc/articles/"
        
        # Filter for links that start with the expected base URL for reliability
        df_filtered = df[df['Link'].astype(str).str.startswith(base_url_prefix, na=False)].copy()

        publication_list = list(zip(df_filtered['Title'], df_filtered['Link']))

        print(f"Document Loader: Extracted {len(publication_list)} valid PMC links.")
        return publication_list

    except Exception as e:
        print(f"Error during CSV extraction: {e}")
        return []

def load_and_chunk_documents(csv_file_path: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> List[Document]:
    """
    Orchestrates the Docling ingestion process for the entire corpus.
    Uses lazy loading and enriched metadata for traceability.
    """
    publication_data = extract_publication_data(csv_file_path)
    if not publication_data:
        return []

    processed_documents: List[Document] = []
    
    # Initialize the chunking strategy once
    chunker = HybridChunker(max_chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    total_docs = len(publication_data)
    print(f"Starting Docling structural ingestion for {total_docs} documents...")

    for i, (title, url) in enumerate(publication_data):
        # Time the process for performance tracking
        start_time = time.time()
        
        # Use an external identifier for the Knowledge Graph trace
        doc_id = f"PMC_{url.split('/')[-2]}"
        
        try:
            # 1. Initialize DoclingLoader with the URL
            loader = DoclingLoader(
                file_path=url,
                chunker=chunker,
                # Export as Markdown is CRUCIAL for preserving semantic structure
                export_type=ExportType.MARKDOWN 
            )

            # 2. Load the structured document (list of chunks)
            docs = loader.load()

            # 3. Add consistent, enriched metadata to every chunk
            for doc in docs:
                # Store the required XAI and traceability metadata
                doc.metadata['original_title'] = title
                doc.metadata['source_url'] = url
                doc.metadata['doc_id'] = doc_id
                doc.metadata['source_file'] = csv_file_path
                processed_documents.append(doc)

            end_time = time.time()
            print(f"  [Doc {i+1}/{total_docs}] Processed {len(docs)} chunks for '{title[:40]}...'. Time: {end_time - start_time:.2f}s")
            
        except Exception as e:
            print(f"  Docling FAILED for document {doc_id} ({url}). Error: {e}")
            continue

    print(f"\n Docling Ingestion Complete. Total chunks generated: {len(processed_documents)}")
    return processed_documents

# Example of how this function is used in run_pipeline.py:
# if __name__ == "__main__":
#     CHUNKED_DOCUMENTS = load_and_chunk_documents(
#         csv_file_path="../data/SB_publication_PMC.csv"
#     )
#     # The output list is now ready to be fed to knowledge_extractor.py
