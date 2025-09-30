# The Artemis Knowledge Accelerator

**Challenge Focus:** Build a Space Biology Knowledge Engine
**Event:** NASA Space Apps Challenge 2025

---

## Overview

The Artemis Knowledge Accelerator is a **Space Biology Knowledge Engine** designed to integrate scientific literature, experimental datasets, and funding metadata into a unified, explainable reasoning system. It enables:

* **Scientists** – to explore hypotheses through multi-hop reasoning.
* **Managers** – to assess research investment and gaps.
* **Mission Architects** – to evaluate biological risk in spaceflight contexts.

---

## Data Scope

* **Primary Source:** 607+ NASA Bioscience Publications (PMC URLs)
* **Secondary Sources:** NASA OSDR data (for linkage), NASA Task Book (for funding metadata)

---

## Core Architecture: Agentic Hybrid RAG

### 1. Data Structuring & Ingestion

* **Function:** Transform unstructured PDFs into structured, semantic chunks.
* **Workflow:** CSV extraction → Parsing (Docling/Unstructured) → Max-normalized chunking
* **Libraries:** `pandas`, `docling`, `spacy`, `langchain-core`

### 2. Knowledge Graph (KG) Creation

* **Function:** Store relationships and logical facts for multi-hop reasoning.
* **Workflow:** NER/RE (BioBERT/LLaMA) → Schema validation → KG population
* **Libraries:** `transformers`, `pydantic`, `networkx`, `neo4j`

### 3. Vector Database (VS) Creation

* **Function:** Semantic embeddings for similarity search.
* **Workflow:** Embedding generation → Vector indexing → Linking vectors to KG node IDs
* **Libraries:** `sentence-transformers`, `chroma`/`milvus`

### 4. Agentic Reasoning Core

* **Function:** Route queries dynamically to KG or VS.
* **Workflow:** Query intent analysis → Dynamic routing → LLM synthesis (Finetuned LLaMA)
* **Libraries:** `langgraph`, `transformers`, `langchain`

---

## Key Features & XAI

* **Hybrid RAG Chatbot**

  * Combines factual triples (KG) and contextual text (VS).
  * **Explainability:** Source traceability (URLs), retrieval path logging.

* **Interactive Knowledge Map**

  * Graph-based visualization with entity filters.
  * **Explainability:** Node size (centrality), node color (entity type).
  * **Libraries:** `pyvis`, `plotly-dash`

* **Gaps & Investment Analysis**

  * Identifies under/over-researched areas.
  * **Explainability:** Augmented scoring (centrality + topic relevance).
  * **Libraries:** `bertopic`, `networkx`

---

## Deployment Stack

* **Backend:** Python (`Flask` or `FastAPI`)
* **Dashboard:** Plotly Dash / Streamlit
* **UI Libraries:** Vis.js / Plotly.js
* **Compute Requirements:** High-VRAM GPU (LLM NER/RE), multi-core CPU (parallel ingestion)

---

## Hackathon Impact

The Artemis Knowledge Accelerator provides a **scalable and explainable platform** for space bioscience, bridging research literature, experimental data, and funding decisions to accelerate NASA’s exploration goals.
