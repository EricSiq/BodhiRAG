"""
BodhiRAG: Vector Store Seeding Script
========================================
Pre-embeds NASA space biology abstracts so the HF Space works out-of-the-box.

Usage (run from project root):
    python scripts/seed_vector_store.py

Output:
    data/chroma_preseeded/   <-- commit this directory to the HF repo

The script reads sample_data.csv, fetches abstracts from PubMed Central for
the first MAX_DOCS papers, and embeds them with the Granite/MiniLM model.
"""

import os
import sys
import time
import csv
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ---- Config ---------------------------------------------------------------
MAX_DOCS = 60           # number of papers to seed
CHUNK_SIZE = 800        # characters per chunk
PERSIST_DIR = project_root / "data" / "chroma_preseeded"
CSV_PATH = project_root / "sample_data.csv"
COLLECTION_NAME = "nasa_publications"
SLEEP_BETWEEN = 1.5     # seconds between HTTP requests (be polite to PMC)
# ---------------------------------------------------------------------------


def fetch_abstract_from_pmc(url: str) -> str:
    """Fetch abstract text from a PMC article URL using NCBI E-utilities API, 
    with a raw HTML scraper as fallback."""
    import re
    import xml.etree.ElementTree as ET

    # Try E-utilities API first (reliable, no bot block)
    pmcid_match = re.search(r'PMC(\d+)', url, re.IGNORECASE)
    if pmcid_match:
        pmcid = pmcid_match.group(1)
        eutils_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmcid}&retmode=xml"
        try:
            response = requests.get(eutils_url, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Extract abstract text
            abstract_parts = []
            for abs_tag in root.findall(".//abstract"):
                abs_text = "".join(abs_tag.itertext()).strip()
                if abs_text:
                    abstract_parts.append(abs_text)
            abstract_text = " ".join(abstract_parts)
            
            if abstract_text:
                return abstract_text
                
            # Fall back to first 3 body paragraphs
            body_parts = []
            for p_tag in root.findall(".//body//p")[:3]:
                p_text = "".join(p_tag.itertext()).strip()
                if p_text:
                    body_parts.append(p_text)
            body_text = " ".join(body_parts)
            
            if body_text:
                return body_text
                
            # Fallback to any p tags
            fallback_parts = []
            for p_tag in root.findall(".//p")[:3]:
                p_text = "".join(p_tag.itertext()).strip()
                if p_text:
                    fallback_parts.append(p_text)
            return " ".join(fallback_parts)
            
        except Exception as e:
            print(f"    [WARN] E-utilities failed for {url}: {e} — trying fallback scraper")

    # Fallback to scraping HTML
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; BodhiRAG-seeder/1.0; "
            "+https://github.com/NASA-SpaceBio)"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Try abstract section first
        abstract_div = soup.find("div", class_="abstract") or soup.find("abstract")
        if abstract_div:
            text = abstract_div.get_text(separator=" ", strip=True)
            if len(text) > 100:
                return text

        # Fall back to first 3 body paragraphs
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs[:5])
        return text[:3000] if text else ""

    except Exception as e:
        print(f"    [WARN] Fallback scraping failed for {url}: {e}")
        return ""


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    overlap = chunk_size // 5
    i = 0
    while i < len(text):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def load_csv_publications(csv_path: Path, max_docs: int) -> list:
    """Load unique (title, url) pairs from the sample CSV."""
    records = []
    seen_urls = set()
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("Link", "").strip()
                title = row.get("Title", "Unknown").strip()
                if url.startswith("https://www.ncbi.nlm.nih.gov/pmc/articles/"):
                    if url not in seen_urls:
                        records.append((title, url))
                        seen_urls.add(url)
                if len(records) >= max_docs:
                    break
    except Exception as e:
        print(f"❌ Failed to read CSV: {e}")
    return records


def seed_vector_store():
    """Main seeding function."""
    print("[INFO] BodhiRAG Vector Store Seeder")
    print("=" * 50)

    # Import ChromaDB + sentence-transformers
    try:
        import chromadb
        from chromadb.config import Settings
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        print("Install with: pip install chromadb sentence-transformers")
        sys.exit(1)

    # Ensure persist directory exists
    PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[INFO] Persist directory: {PERSIST_DIR}")

    # Initialize ChromaDB
    client = chromadb.PersistentClient(
        path=str(PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )

    # Delete existing collection if present (fresh seed)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"[INFO] Deleted existing '{COLLECTION_NAME}' collection")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "NASA Space Biology Publications — Pre-seeded"},
    )
    print(f"[PASS] Created collection: {COLLECTION_NAME}")

    # Load embedding model
    print("\n[INFO] Loading embedding model...")
    try:
        model = SentenceTransformer("ibm/granite-embedding-30m-english")
        print("[PASS] Loaded ibm/granite-embedding-30m-english")
    except Exception:
        print("[WARN] Granite not available, using all-MiniLM-L6-v2")
        model = SentenceTransformer("all-MiniLM-L6-v2")

    # Load publications
    print(f"\n[INFO] Reading CSV: {CSV_PATH}")
    publications = load_csv_publications(CSV_PATH, MAX_DOCS)
    print(f"   Found {len(publications)} publications to process")

    # Process each publication
    all_docs = []
    all_embeddings = []
    all_metadatas = []
    all_ids = []

    for i, (title, url) in enumerate(publications, 1):
        print(f"\n[{i}/{len(publications)}] {title[:60]}...")
        print(f"   URL: {url}")

        text = fetch_abstract_from_pmc(url)
        if not text:
            print("   [WARN] No text found — skipping")
            time.sleep(SLEEP_BETWEEN)
            continue

        # Extract PMC ID
        pmc_id = url.rstrip("/").split("/")[-1]
        doc_id = f"PMC_{pmc_id}"

        # Chunk the text
        chunks = chunk_text(text)
        print(f"   [INFO] {len(text)} chars -> {len(chunks)} chunks")

        for j, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{j:03d}"
            embedding = model.encode([chunk])[0].tolist()

            all_docs.append(chunk)
            all_embeddings.append(embedding)
            all_metadatas.append({
                "source_title": title,
                "source_url": url,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "content_length": len(chunk),
                "paper_index": i,
            })
            all_ids.append(chunk_id)

        time.sleep(SLEEP_BETWEEN)

    # Batch insert into ChromaDB
    if all_docs:
        print(f"\n[INFO] Inserting {len(all_docs)} chunks into ChromaDB...")

        # Insert in batches of 100
        batch_size = 100
        for start in range(0, len(all_docs), batch_size):
            end = min(start + batch_size, len(all_docs))
            collection.add(
                documents=all_docs[start:end],
                embeddings=all_embeddings[start:end],
                metadatas=all_metadatas[start:end],
                ids=all_ids[start:end],
            )
            print(f"   [PASS] Inserted batch {start//batch_size + 1} ({end - start} chunks)")

        final_count = collection.count()
        print(f"\n[INFO] Seeding complete!")
        print(f"   Total chunks in collection: {final_count}")
        print(f"   Papers processed: {len(publications)}")
        print(f"   Persist directory: {PERSIST_DIR}")
        print(f"\n[INFO] Next step: Commit '{PERSIST_DIR.relative_to(project_root)}/' to your HF Space repo")

        # Write a seed manifest
        manifest_path = PERSIST_DIR / "seed_manifest.json"
        manifest = {
            "seeded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_chunks": final_count,
            "papers_processed": len(publications),
            "embedding_model": "ibm/granite-embedding-30m-english",
            "collection_name": COLLECTION_NAME,
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"   Manifest written to: {manifest_path}")

    else:
        print("\n[WARN] No documents were processed: check your CSV file and internet connection")


if __name__ == "__main__":
    seed_vector_store()
