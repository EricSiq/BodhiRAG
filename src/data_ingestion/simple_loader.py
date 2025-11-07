"""
Simple document loader for Hugging Face Spaces
Fallback when langchain_docling is not available
"""

import requests
from bs4 import BeautifulSoup
from typing import List
from langchain_core.documents import Document
import time

def load_document_from_url(url: str, title: str, doc_id: str, chunk_size: int = 1000) -> List[Document]:
    """
    Load and chunk a document from URL using simple HTML parsing
    
    Args:
        url: URL to fetch
        title: Document title
        doc_id: Document ID
        chunk_size: Size of chunks
    
    Returns:
        List of Document objects
    """
    try:
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract text from paragraphs
        paragraphs = soup.find_all('p')
        text = ' '.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
        
        # If no paragraphs, try to get all text
        if not text:
            text = soup.get_text()
        
        # Clean text
        text = ' '.join(text.split())
        
        # Chunk the text
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk_text = text[i:i + chunk_size]
            if chunk_text.strip():
                doc = Document(
                    page_content=chunk_text,
                    metadata={
                        'original_title': title,
                        'source_url': url,
                        'doc_id': doc_id,
                        'chunk_id': f"{doc_id}_chunk_{len(chunks):03d}"
                    }
                )
                chunks.append(doc)
        
        return chunks
        
    except Exception as e:
        print(f"  ❌ Failed to load {url}: {e}")
        return []

def load_and_chunk_documents_simple(
    publication_data: List[tuple],
    max_docs: int = None,
    chunk_size: int = 1000
) -> List[Document]:
    """
    Simple document loader for HF Spaces
    
    Args:
        publication_data: List of (title, url) tuples
        max_docs: Maximum documents to process
        chunk_size: Size of text chunks
    
    Returns:
        List of Document objects
    """
    if max_docs:
        publication_data = publication_data[:max_docs]
    
    all_documents = []
    total = len(publication_data)
    
    print(f"Loading {total} documents...")
    
    for i, (title, url) in enumerate(publication_data, 1):
        print(f"  [{i}/{total}] Loading: {title[:50]}...")
        
        doc_id = f"PMC_{url.split('/')[-1]}"
        chunks = load_document_from_url(url, title, doc_id, chunk_size)
        
        if chunks:
            all_documents.extend(chunks)
            print(f"    ✓ {len(chunks)} chunks")
        else:
            print(f"    ✗ Failed")
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n✅ Loaded {len(all_documents)} total chunks from {total} documents")
    return all_documents
