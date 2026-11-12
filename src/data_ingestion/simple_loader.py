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
    Load and chunk a document from URL. Uses NCBI E-utilities API first (clean XML, 
    bypasses reCAPTCHA), falling back to raw web scraping if necessary.
    
    Args:
        url: URL of the PMC article
        title: Document title
        doc_id: Document ID
        chunk_size: Size of chunks
    
    Returns:
        List of Document objects
    """
    import re
    import xml.etree.ElementTree as ET
    from bs4 import BeautifulSoup

    # Try E-utilities API first (reliable, no bot block)
    pmcid_match = re.search(r'PMC(\d+)', url, re.IGNORECASE)
    if pmcid_match:
        pmcid = pmcid_match.group(1)
        eutils_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&retmode=xml"
        try:
            response = requests.get(eutils_url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Extract abstract
            abstract_parts = []
            for abs_tag in root.findall(".//abstract"):
                abs_text = "".join(abs_tag.itertext()).strip()
                if abs_text:
                    abstract_parts.append(abs_text)
            abstract_text = " ".join(abstract_parts)
            
            # Extract body paragraphs
            body_parts = []
            for p_tag in root.findall(".//body//p"):
                p_text = "".join(p_tag.itertext()).strip()
                if p_text:
                    body_parts.append(p_text)
            body_text = " ".join(body_parts)
            
            combined_text = ""
            if abstract_text:
                combined_text += f"Abstract: {abstract_text}\n\n"
            if body_text:
                combined_text += body_text
                
            # If still empty, try any paragraphs in the XML
            if not combined_text.strip():
                fallback_parts = []
                for p_tag in root.findall(".//p"):
                    p_text = "".join(p_tag.itertext()).strip()
                    if p_text:
                        fallback_parts.append(p_text)
                combined_text = " ".join(fallback_parts)
                
            if combined_text.strip():
                # Clean and chunk
                text = ' '.join(combined_text.split())
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
            print(f"  [WARN] E-utilities failed for {url}: {e} — falling back to scraper")
            
    # Web scraping fallback (might be blocked by reCAPTCHA on some networks)
    try:
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
        print(f"  ❌ Fallback scraping failed for {url}: {e}")
        return []

def load_and_chunk_documents_simple(
    publication_data: List[tuple],
    max_docs: int = None,
    chunk_size: int = 1000,
    progress_callback=None
) -> List[Document]:
    """
    Simple document loader for HF Spaces
    
    Args:
        publication_data: List of (title, url) tuples
        max_docs: Maximum documents to process
        chunk_size: Size of text chunks
        progress_callback: Optional callback for progress updates
    
    Returns:
        List of Document objects
    """
    if max_docs:
        publication_data = publication_data[:max_docs]
    
    all_documents = []
    total = len(publication_data)
    
    print(f"Loading {total} documents...")
    if progress_callback:
        progress_callback(f"Loading {total} documents...\n")
    
    for i, (title, url) in enumerate(publication_data, 1):
        msg = f"  [{i}/{total}] Loading: {title[:50]}..."
        print(msg)
        if progress_callback:
            progress_callback(msg + "\n")
        
        doc_id = f"PMC_{url.split('/')[-1]}"
        chunks = load_document_from_url(url, title, doc_id, chunk_size)
        
        if chunks:
            all_documents.extend(chunks)
            success_msg = f"    ✓ {len(chunks)} chunks"
            print(success_msg)
            if progress_callback:
                progress_callback(success_msg + "\n")
        else:
            fail_msg = f"    ✗ Failed"
            print(fail_msg)
            if progress_callback:
                progress_callback(fail_msg + "\n")
        
        # Rate limiting
        time.sleep(1)
    
    final_msg = f"\n✅ Loaded {len(all_documents)} total chunks from {total} documents"
    print(final_msg)
    if progress_callback:
        progress_callback(final_msg + "\n")
    
    return all_documents
