

# BodhiRAG: NASA Space Biology Knowledge Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org)
[![Gradio](https://img.shields.io/badge/Gradio-4.44-orange.svg)](https://gradio.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![NASA Space Apps 2025](https://img.shields.io/badge/NASA-Space%20Apps%202025-red.svg)](https://www.spaceappschallenge.org/)

**BodhiRAG** is an open research assistant for NASA space-biology literature that helps researchers move from natural-language questions to answers traceable to specific passages and graph relationships.

## ✨ Key Features

- **Mode-Based Routing**: Choose Auto, Literature, Relationships, or Both
- **Evidence Cards**: Every answer shows which sources contributed with citations
- **Open Source**: Works without paid APIs using open-weight Qwen models
- **Graceful Degradation**: Remains useful when optional services are unavailable
- **Data Provenance**: All artifacts tracked with corpus build IDs

---

## 🎯 What You Can Ask

| Query Type | Example |
|------------|---------|
| Causal | *"What causes bone loss in microgravity?"* |
| Mechanistic | *"How does radiation affect DNA repair?"* |
| Countermeasures | *"What exercise protocols prevent muscle atrophy?"* |
| Comparative | *"How does spaceflight affect immune vs. cardiovascular systems?"* |
| Overview | *"Describe oxidative stress in space environments"* |

---

## 🏗️ Architecture

```
User Query
    │
    ├── Mode Selector (Auto/Literature/Relationships/Both)
    │
    ├── Knowledge Graph (Neo4j)
    │   └── Entity relationships: causes, inhibits, affects, mitigated_by...
    │
    ├── Vector Store (ChromaDB + IBM Granite embeddings)  
    │   └── 600+ NASA publications
    │
    └── LLM Synthesis (Mistral-7B or Qwen)
        └── Grounded answer with citations → Evidence cards
```

---

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://huggingface.co/spaces/YOUR_USERNAME/BodhiRAG
cd BodhiRAG
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.template .env
# Edit .env: set OPERATING_MODE and HF_TOKEN (optional)
```

### 3. Launch

```bash
python app_new.py
# → http://localhost:7860
```

---

## ⚙️ Operating Modes

| Mode | Description | Requirements |
|------|-------------|--------------|
| **Demo** | Pre-built corpus, no credentials | None |
| **Local Open-Source** | Full local stack with Qwen | Local model |
| **Hosted Free-Tier** | Using free hosted services | HF_TOKEN |
| **Maintainer** | Corpus ingestion enabled | Write access |

Set via `OPERATING_MODE` environment variable.

---

## 🔧 Configuration

### Required (for model-based answers)

| Variable | Description |
|----------|-------------|
| `HF_TOKEN` | Hugging Face API token for LLM |

### Optional

| Variable | Description |
|----------|-------------|
| `OPERATING_MODE` | demo \| local_opensource \| hosted_freetier \| maintainer_ingest |
| `LLM_PROVIDER` | mistral \| qwen \| template |
| `NEO4J_URI` | Neo4j connection URI |
| `NEO4J_USERNAME` | Neo4j username |
| `NEO4J_PASSWORD` | Neo4j password |
| `EMBEDDING_MODEL` | Embedding model name |

---

## 📊 Data Contracts

All artifacts are Pydantic-validated with provenance:

- **SourceRecord**: `source_id`, `canonical_url`, `content_hash`
- **Chunk**: `chunk_id`, `source_id`, `text`, `element_refs`
- **Triple**: `triple_id`, `subject`, `predicate`, `object`, `evidence_span`
- **Answer**: `answer_id`, `query`, `route`, `claims`, `citation_ids`

---

## 📁 Project Structure

```
src/
├── core/
│   └── config.py              # Pydantic settings
├── models/
│   └── data_contracts.py      # Data models
├── services/
│   ├── llm_inference.py       # Mistral/Qwen integration
│   └── health_manager.py      # Service health checks
├── ui/
│   └── evidence_formatter.py  # Evidence cards
├── graph_rag/
│   ├── graph_connector.py     # Neo4j
│   ├── vector_connector.py    # ChromaDB
│   └── agent_router.py        # Query routing
└── data_ingestion/
    ├── document_loader.py
    └── knowledge_extractor.py
```

---

## 🩺 Service States

The UI displays real-time status with user-facing language:

| State | Meaning |
|-------|---------|
| ✅ Ready | Literature and relationship evidence available |
| 📖 Literature Only | Graph unavailable, semantic search active |
| 📚 Evidence Only | Generation unavailable, showing evidence |
| ⚠️ Setup Required | No corpus installed |

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Pre-seeded publications | 60 |
| Vector store chunks | 170 |
| Query latency (VS only) | <2s |
| Query latency (LLM) | 15-30s |
| KG relationship types | 7 |

---

## 📜 License

MIT License — see LICENSE file for details.

---

## 🙏 Credits

Built for **NASA Space Apps Challenge 2025** — *Build a Space Biology Knowledge Engine*
