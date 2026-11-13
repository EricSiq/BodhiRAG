"""
BodhiRAG: NASA Space Biology Knowledge Engine
================================================
Hybrid RAG system combining Knowledge Graph (Neo4j) with Vector Store (ChromaDB)
and LLM-powered answer synthesis (Mistral-7B via HF Inference API).

Built for NASA Space Apps Challenge 2025.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Hotfix for Gradio 4.x schema generator with Pydantic 2.x
try:
    import gradio_client.utils as _gcu
    _orig_get_type = _gcu.get_type
    def _safe_get_type(schema):
        if not isinstance(schema, dict):
            return "unknown"
        return _orig_get_type(schema)
    _gcu.get_type = _safe_get_type
except Exception:
    pass

import gradio as gr

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bodhirag")

# Import BodhiRAG components
from src.graph_rag.graph_connector import KnowledgeGraphConnector
from src.graph_rag.vector_connector import VectorStoreConnector
from src.graph_rag.agent_router import HybridRAGAgent
from src.data_ingestion import extract_knowledge_from_chunk
from src.data_ingestion.document_loader import extract_publication_data
from src.data_ingestion.simple_loader import load_and_chunk_documents_simple
from langchain_core.documents import Document

# Check Docling availability
try:
    from src.data_ingestion.document_loader import DOCLING_AVAILABLE
except ImportError:
    DOCLING_AVAILABLE = False

# ---------------------------------------------------------------------------
# Initialize connectors (deferred filesystem operations to initialize_store)
# ---------------------------------------------------------------------------
kg_connector = KnowledgeGraphConnector(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", ""),
)
vs_connector = VectorStoreConnector()
agent = HybridRAGAgent(kg_connector, vs_connector)

# Check HF token
HF_TOKEN_SET = bool(os.getenv("HF_TOKEN", ""))

# ---------------------------------------------------------------------------
# Helper: connection status
# ---------------------------------------------------------------------------

def get_connection_status():
    """Return (kg_ok, vs_ok, vs_count) for the status bar."""
    kg_ok = False
    try:
        kg_ok = kg_connector.connect()
        if kg_ok:
            kg_connector.close()
    except Exception:
        pass

    vs_ok = False
    vs_count = 0
    try:
        vs_connector.initialize_store()
        stats = vs_connector.get_collection_stats()
        vs_count = stats.get("total_documents", 0)
        vs_ok = True
    except Exception:
        pass

    return kg_ok, vs_ok, vs_count


def format_status_html(kg_ok: bool, vs_ok: bool, vs_count: int) -> str:
    """Generate the status bar HTML."""
    kg_badge = (
        '<span class="badge badge-green">KG Connected</span>'
        if kg_ok else
        '<span class="badge badge-gray">KG Offline (vector-only)</span>'
    )
    vs_badge = (
        f'<span class="badge badge-blue">Vector Store: {vs_count:,} chunks</span>'
        if vs_ok else
        '<span class="badge badge-gray">Vector Store Offline</span>'
    )
    llm_badge = (
        '<span class="badge badge-purple">LLM: Mistral-7B (HF API)</span>'
        if HF_TOKEN_SET else
        '<span class="badge badge-yellow">LLM: Template mode (set HF_TOKEN)</span>'
    )
    return f'<div class="status-bar">{kg_badge}{vs_badge}{llm_badge}</div>'


# ---------------------------------------------------------------------------
# Core query function
# ---------------------------------------------------------------------------

def query_bodhirag(query: str, use_kg: bool, use_vector: bool, history):
    """Main query handler: runs hybrid retrieval + LLM synthesis."""
    if not query or not query.strip():
        yield history or [], "*Please enter a question.*", None, ""
        return

    history = history or []

    # Show loading message
    history.append((query, "Searching knowledge base..."))
    yield history, "", None, ""

    try:
        # Connect to KG if requested
        if use_kg:
            kg_available = kg_connector.connect()
            if not kg_available:
                use_kg = False

        # Initialize vector store
        if use_vector:
            vs_connector.initialize_store()

        # Run retrieval + synthesis
        result = agent.route_query(query, use_kg, use_vector)
        answer = result["final_answer"]
        kg_results = result["kg_results"]
        vs_results = result["vs_results"]
        query_type = result["query_type"]
        stats = result["retrieval_stats"]

        # Build source cards markdown
        source_md = build_source_cards(kg_results, vs_results)

        # Build KG graph
        kg_fig = None
        try:
            from src.graph_rag.graph_visualizer import build_kg_graph
            kg_fig = build_kg_graph(
                kg_results,
                title=f"Knowledge Graph: {query[:40]}{'...' if len(query) > 40 else ''}",
            )
        except Exception as e:
            logger.warning(f"Graph visualization failed: {e}")

        # Build stats text
        mode = {
            "kg_primary": "Knowledge Graph Primary",
            "vs_primary": "Vector Search Primary",
            "hybrid":     "Hybrid Mode",
        }.get(query_type, query_type)

        stats_text = (
            f"**Mode:** {mode} | "
            f"**KG Relationships:** {stats['kg_relationships']} | "
            f"**Documents:** {stats['vs_documents']}"
        )

        # Update history
        history[-1] = (query, answer)

        if use_kg:
            kg_connector.close()

        yield history, source_md, kg_fig, stats_text

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        history[-1] = (query, f"Error: {str(e)}\n\nPlease try again or check the logs.")
        yield history, "", None, ""

        if use_kg:
            try:
                kg_connector.close()
            except Exception:
                pass


def build_source_cards(kg_results: list, vs_results: list) -> str:
    """Build markdown source attribution cards."""
    if not kg_results and not vs_results:
        return "*No sources retrieved: try running the data pipeline first.*"

    md = ""

    if vs_results:
        md += "### Research Sources\n\n"
        seen_titles = set()
        for i, doc in enumerate(vs_results[:4], 1):
            title = doc.get("metadata", {}).get("source_title", "NASA Publication")
            url = doc.get("metadata", {}).get("source_url", "")
            score = doc.get("score", 0)
            content = doc.get("content", "")[:200]
            score_pct = int(score * 100)

            if title in seen_titles:
                continue
            seen_titles.add(title)

            score_color = "[High Match]" if score_pct > 75 else "[Medium Match]" if score_pct > 50 else "[Low Match]"
            md += f"**[{i}]** {score_color} (`{score_pct}%` similarity) "
            if url:
                md += f"[**{title[:70]}**]({url})\n"
            else:
                md += f"**{title[:70]}**\n"
            md += f"> {content}...\n\n"

    if kg_results:
        md += "### Knowledge Graph Evidence\n\n"
        for rel in kg_results[:5]:
            s = rel.get("subject", "?")
            p = rel.get("relationship", "→")
            o = rel.get("object", "?")
            evidence = rel.get("evidence", "")
            src = rel.get("source", rel.get("source_title", ""))
            md += f"- **{s}** *{p}* **{o}**"
            if src:
                md += f" *(from {src[:60]})*"
            md += "\n"
            if evidence:
                md += f"  > \"{evidence[:120]}...\"\n"

    return md


# ---------------------------------------------------------------------------
# Pipeline function
# ---------------------------------------------------------------------------

def run_pipeline(max_docs: int, csv_file):
    """Run the data ingestion pipeline with streaming progress updates."""
    status = "**Pipeline Ingestion Starting...**\n\n"
    yield status

    if csv_file is None:
        yield status + "Error: Please upload a CSV file first.\n"
        return

    csv_path = csv_file if isinstance(csv_file, str) else csv_file.name

    # Phase 1: Load publications
    status += "---\n### Phase 1: Data Ingestion\n"
    yield status

    publication_data = extract_publication_data(csv_path)
    if not publication_data:
        yield status + "Error: No valid PMC links found in CSV.\n"
        return

    status += f"Found **{len(publication_data)}** publications in CSV\n"
    yield status

    log_lines = []
    def progress_cb(msg):
        log_lines.append(msg.strip())

    documents = load_and_chunk_documents_simple(
        publication_data=publication_data,
        max_docs=int(max_docs),
        chunk_size=1000,
        progress_callback=progress_cb,
    )

    # Show last 10 log lines
    if log_lines:
        status += "```\n" + "\n".join(log_lines[-10:]) + "\n```\n\n"

    status += f"Loaded and chunked **{len(documents)}** document chunks\n\n"
    yield status

    if not documents:
        yield status + "Error: No documents could be processed.\n"
        return

    # Phase 2: Knowledge Extraction
    status += "---\n### Phase 2: Knowledge Extraction\n"
    yield status

    all_triples = []
    extract_limit = min(10, len(documents))
    for i, doc in enumerate(documents[:extract_limit]):
        triples = extract_knowledge_from_chunk(doc)
        all_triples.extend(triples)
        if (i + 1) % 3 == 0:
            status += f"  `[{i+1}/{extract_limit}]` {len(all_triples)} triples extracted\n"
            yield status

    status += f"Extracted **{len(all_triples)}** knowledge triples\n\n"
    yield status

    # Phase 3: Knowledge Graph
    status += "---\n### Phase 3: Knowledge Graph Population\n"
    yield status

    kg_results_data = None
    if kg_connector.connect():
        kg_results_data = kg_connector.populate_graph(all_triples)
        kg_connector.close()
        status += (
            f"KG populated: "
            f"**{kg_results_data.get('entities_created', 0)} entities**, "
            f"**{kg_results_data.get('relationships_created', 0)} relationships**\n\n"
        )
    else:
        status += "Neo4j not configured: skipping KG (add `NEO4J_*` secrets in Space settings)\n\n"
    yield status

    # Phase 4: Vector Store
    status += "---\n### Phase 4: Vector Store Population\n"
    yield status

    vs_connector.initialize_store()
    vs_result = vs_connector.populate_store(documents)
    status += f"Vector store: **{vs_result.get('documents_added', 0)} chunks** added\n\n"
    yield status

    # Summary
    status += "---\n### Pipeline Complete!\n\n"
    status += f"| Metric | Value |\n|--------|-------|\n"
    status += f"| Documents loaded | {len(documents)} |\n"
    status += f"| Triples extracted | {len(all_triples)} |\n"
    if kg_results_data:
        status += f"| KG entities | {kg_results_data.get('entities_created', 0)} |\n"
        status += f"| KG relationships | {kg_results_data.get('relationships_created', 0)} |\n"
    status += f"| Vector chunks | {vs_result.get('documents_added', 0)} |\n\n"
    status += "**Your local knowledge base has been updated and is ready.**"
    yield status


# ---------------------------------------------------------------------------
# Statistics function
# ---------------------------------------------------------------------------

def get_database_stats():
    """Return formatted statistics for the Statistics tab."""
    text = f"*Last refreshed: {datetime.now().strftime('%H:%M:%S')}*\n\n"

    # KG stats
    try:
        if kg_connector.connect():
            stats = kg_connector.export_graph_stats()
            kg_connector.close()
            total_e = stats.get("total_entities", 0)
            rel_types = stats.get("relationship_types", [])
            total_r = sum(r.get("count", 0) for r in rel_types if isinstance(r, dict))

            text += "### Knowledge Graph\n\n"
            text += f"| Metric | Count |\n|--------|-------|\n"
            text += f"| Total Entities | {total_e:,} |\n"
            text += f"| Total Relationships | {total_r:,} |\n"

            entity_types = stats.get("entity_types", [])
            if isinstance(entity_types, list) and entity_types:
                text += "\n**Entity Types:**\n"
                for et in entity_types:
                    if isinstance(et, dict):
                        text += f"- `{et.get('type', '?')}`: {et.get('count', 0)}\n"

            top_entities = stats.get("most_connected_entities", [])
            if top_entities:
                text += "\n**Most Connected Entities:**\n"
                for e in top_entities[:5]:
                    text += f"- **{e.get('entity', '?')}** ({e.get('degree', 0)} connections)\n"
        else:
            text += "### Knowledge Graph\n\n"
            text += "Offline: add `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` to Space secrets.\n\n"
    except Exception as e:
        text += f"### Knowledge Graph\n\nError: {e}\n\n"

    # VS stats
    try:
        vs_connector.initialize_store()
        stats = vs_connector.get_collection_stats()
        total_d = stats.get("total_documents", 0)

        text += "\n---\n### Vector Store\n\n"
        text += f"| Metric | Value |\n|--------|-------|\n"
        text += f"| Total Chunks | {total_d:,} |\n"

        if total_d > 0:
            avg = stats.get("average_content_length", 0)
            text += f"| Avg. Chunk Length | {int(avg):,} chars |\n"
            fields = stats.get("sample_metadata_fields", [])
            if fields:
                text += f"| Metadata Fields | {', '.join(f'`{f}`' for f in fields)} |\n"
        else:
            text += "\nNote: Run the pipeline to populate the vector store.\n"
    except Exception as e:
        text += f"### Vector Store\n\nError: {e}\n"

    # LLM status
    text += "\n---\n### Language Model Status\n\n"
    if HF_TOKEN_SET:
        text += "Mistral-7B-Instruct active via HF Inference API\n"
    else:
        text += (
            "Template mode: set `HF_TOKEN` in Space secrets to enable structured model answers.\n"
            "Get your token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)\n"
        )

    return text


# ---------------------------------------------------------------------------
# Custom CSS: dark space theme
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
/* ===== Global ===== */
:root {
    --bg-primary:    #020817;
    --bg-secondary:  #0f172a;
    --bg-card:       #1e293b;
    --border:        #334155;
    --accent-blue:   #3b82f6;
    --accent-purple: #8b5cf6;
    --accent-gold:   #f59e0b;
    --text-primary:  #f1f5f9;
    --text-secondary:#94a3b8;
    --success:       #22c55e;
    --warning:       #f59e0b;
}

body, .gradio-container {
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}

/* ===== Hero Banner ===== */
.hero-banner {
    background: linear-gradient(135deg, #020817 0%, #0f172a 40%, #1a0a2e 100%);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}

.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at center, rgba(139, 92, 246, 0.08) 0%, transparent 60%);
    pointer-events: none;
}

.hero-title {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 8px 0;
    letter-spacing: -0.5px;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: var(--text-secondary);
    margin: 0 0 20px 0;
}

.hero-stats {
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
}

.stat-chip {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.85rem;
    color: #93c5fd;
    font-weight: 500;
}

/* ===== Status Bar ===== */
.status-bar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    padding: 10px 0;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.badge-green  { background: rgba(34,197,94,0.15);  border: 1px solid rgba(34,197,94,0.4);  color: #86efac; }
.badge-blue   { background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.4); color: #93c5fd; }
.badge-purple { background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.4); color: #c4b5fd; }
.badge-yellow { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4); color: #fcd34d; }
.badge-gray   { background: rgba(148,163,184,0.1); border: 1px solid rgba(148,163,184,0.3);color: #94a3b8; }

/* ===== Tabs ===== */
.tab-nav button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}

.tab-nav button.selected {
    color: var(--accent-blue) !important;
    border-bottom-color: var(--accent-blue) !important;
}

.tab-nav button:hover:not(.selected) {
    color: var(--text-primary) !important;
}

/* ===== Inputs ===== */
textarea, input[type="text"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
    transition: border-color 0.2s ease !important;
}

textarea:focus, input[type="text"]:focus {
    border-color: var(--accent-blue) !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}

/* ===== Buttons ===== */
button.primary {
    background: linear-gradient(135deg, #2563eb, #7c3aed) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(124,58,237,0.3) !important;
}

button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(124,58,237,0.4) !important;
}

button.secondary {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
}

/* ===== Chatbot ===== */
.chatbot {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}

.chatbot .message.bot {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}

.chatbot .message.user {
    background: rgba(59,130,246,0.15) !important;
    border: 1px solid rgba(59,130,246,0.3) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}

/* ===== Cards ===== */
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
}

/* ===== Checkboxes ===== */
input[type="checkbox"] {
    accent-color: var(--accent-blue) !important;
}

/* ===== Labels ===== */
label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

/* ===== Markdown ===== */
.prose, .markdown {
    color: var(--text-primary) !important;
}

.prose h3, .markdown h3 { color: #93c5fd !important; }
.prose code, .markdown code {
    background: var(--bg-card) !important;
    color: #fbbf24 !important;
    border-radius: 4px !important;
    padding: 2px 6px !important;
}
.prose blockquote, .markdown blockquote {
    border-left: 3px solid var(--accent-purple) !important;
    color: var(--text-secondary) !important;
    background: rgba(139,92,246,0.07) !important;
    border-radius: 0 6px 6px 0 !important;
    padding: 8px 12px !important;
}
.prose table, .markdown table {
    border-collapse: collapse !important;
    width: 100% !important;
}
.prose th, .markdown th {
    background: rgba(59,130,246,0.1) !important;
    color: #93c5fd !important;
    padding: 8px 12px !important;
    border: 1px solid var(--border) !important;
}
.prose td, .markdown td {
    padding: 7px 12px !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
}

/* ===== Sliders ===== */
input[type="range"] { accent-color: var(--accent-blue) !important; }

/* ===== Scrollbars ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* ===== Animations ===== */
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 8px rgba(59,130,246,0.3); }
    50%       { box-shadow: 0 0 16px rgba(59,130,246,0.6); }
}

.glow { animation: pulse-glow 2s ease-in-out infinite; }
"""

# ---------------------------------------------------------------------------
# Example queries
# ---------------------------------------------------------------------------

EXAMPLE_QUERIES = [
    "What causes bone loss in space and what are the mechanisms involved?",
    "How does microgravity affect the cardiovascular system?",
    "What countermeasures exist for muscle atrophy during spaceflight?",
    "Describe the effects of space radiation on DNA repair mechanisms",
    "How does spaceflight affect the immune system?",
    "What is the role of oxidative stress in space biology?",
    "How does long-duration spaceflight affect gene expression?",
    "What are the main challenges of maintaining astronaut health on Mars missions?",
]

# ---------------------------------------------------------------------------
# About / Architecture content
# ---------------------------------------------------------------------------

ABOUT_CONTENT = """
## How BodhiRAG Works

BodhiRAG is a **Hybrid Retrieval-Augmented Generation** system that combines two complementary knowledge sources to answer questions about NASA space biology research.

### Architecture

```
User Query
    │
    ▼
Query Classifier
    │
    ├─── KG Primary?  ──→  Neo4j Knowledge Graph
    │                           (entity relationships)
    ├─── VS Primary?  ──→  ChromaDB Vector Store
    │                           (semantic similarity)
    └─── Hybrid?     ──→  Both sources combined
                                    │
                                    ▼
                          Mistral-7B-Instruct (HF API)
                          (RAG prompt + answer synthesis)
                                    │
                                    ▼
                          Structured Answer + Sources
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| **Knowledge Graph** | Neo4j (relationship storage) |
| **Vector Store** | ChromaDB + IBM Granite embeddings |
| **LLM** | Mistral-7B-Instruct (HF Inference API) |
| **Framework** | LangChain Core + Gradio |
| **Data** | 607+ NASA PubMed Central publications |

### Knowledge Sources

- **Knowledge Graph**: Neo4j stores entity relationships extracted from papers.
  Entities: organisms, environments, biological processes, biomolecules.
  Relationships: *causes*, *inhibits*, *affects*, *mitigated_by*, etc.

- **Vector Store**: ChromaDB stores semantic embeddings of paper chunks,
  enabling similarity search across 607+ NASA publications.

### Retrieval Strategy

1. **Query Classification**: Pattern matching identifies whether the query asks
   about relationships (→ KG primary) or descriptions (→ VS primary).

2. **Parallel Retrieval**: Both sources are queried simultaneously.

3. **Context Building**: Top KG relationships + top VS passages are assembled
   into a structured RAG prompt.

4. **LLM Synthesis**: Mistral-7B generates a grounded, cited answer.

### Built For

NASA Space Apps Challenge 2025 — *Build a Space Biology Knowledge Engine*
"""

# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

with gr.Blocks(
    title="BodhiRAG: NASA Space Biology Knowledge Engine",
    css=CUSTOM_CSS,
    theme=gr.themes.Base(
        primary_hue=gr.themes.colors.blue,
        secondary_hue=gr.themes.colors.purple,
        neutral_hue=gr.themes.colors.slate,
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui"],
    ).set(
        body_background_fill="#020817",
        body_text_color="#f1f5f9",
        block_background_fill="#0f172a",
        block_border_color="#334155",
        input_background_fill="#1e293b",
        button_primary_background_fill="linear-gradient(135deg, #2563eb, #7c3aed)",
        button_primary_text_color="#ffffff",
    ),
) as demo:

    # ── Hero Banner ──────────────────────────────────────────────────────────
    gr.HTML("""
    <div class="hero-banner">
        <h1 class="hero-title">BodhiRAG</h1>
        <p class="hero-subtitle">NASA Space Biology Knowledge Engine: Hybrid retrieval architecture with graph-relational context</p>
        <div class="hero-stats">
            <span class="stat-chip">607+ Publications</span>
            <span class="stat-chip">Knowledge Graph (Neo4j)</span>
            <span class="stat-chip">Vector Search (ChromaDB)</span>
            <span class="stat-chip">Mistral-7B-Instruct</span>
            <span class="stat-chip">NASA Space Apps 2025</span>
        </div>
    </div>
    """)

    # ── Connection Status Bar ────────────────────────────────────────────────
    status_html = gr.HTML(value="<div class='status-bar'>Checking connections...</div>")

    # ── Tabs ─────────────────────────────────────────────────────────────────
    with gr.Tabs() as tabs:

        # ── Tab 1: Query ──────────────────────────────────────────────────────
        with gr.Tab("Ask BodhiRAG", id="query_tab"):
            with gr.Row(equal_height=False):

                # Left column — input controls
                with gr.Column(scale=1, min_width=280):
                    gr.Markdown("### Query Controls")

                    query_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., What causes bone loss in microgravity?",
                        lines=3,
                        max_lines=6,
                    )

                    with gr.Row():
                        use_kg = gr.Checkbox(
                            label="Knowledge Graph",
                            value=True,
                            info="Relationship-based reasoning",
                        )
                        use_vector = gr.Checkbox(
                            label="Vector Search",
                            value=True,
                            info="Semantic similarity search",
                        )

                    with gr.Row():
                        submit_btn = gr.Button("Ask BodhiRAG", variant="primary", scale=3)
                        clear_btn  = gr.Button("Clear", variant="secondary", scale=1)

                    gr.Markdown("---")
                    gr.Markdown("### Example Queries")
                    
                    for i, example in enumerate(EXAMPLE_QUERIES):
                        ex_btn = gr.Button(
                            f"{example[:55]}{'…' if len(example) > 55 else ''}",
                            variant="secondary",
                            size="sm",
                            elem_id=f"ex_btn_{i}",
                        )
                        ex_btn.click(
                            fn=lambda q=example: q,
                            outputs=query_input,
                        )

                # Right column — chat + results
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(
                        label="BodhiRAG Answers",
                        height=420,
                        show_copy_button=True,
                        bubble_full_width=False,
                    )

                    stats_display = gr.Markdown(
                        value="*Submit a query to see retrieval statistics.*",
                        label="Retrieval Stats",
                    )

            # Sources + KG Graph row
            with gr.Row():
                with gr.Column(scale=1):
                    source_display = gr.Markdown(
                        value="*Sources will appear here after a query.*",
                        label="Sources & Evidence",
                    )
                with gr.Column(scale=1):
                    kg_plot = gr.Plot(
                        label="Knowledge Graph Visualization",
                        show_label=True,
                    )

            # Chat history state
            chat_history = gr.State([])

            # Event handlers
            def submit_query(query, use_kg_val, use_vector_val, history):
                return query_bodhirag(query, use_kg_val, use_vector_val, history)

            submit_btn.click(
                fn=submit_query,
                inputs=[query_input, use_kg, use_vector, chat_history],
                outputs=[chatbot, source_display, kg_plot, stats_display],
            )

            query_input.submit(
                fn=submit_query,
                inputs=[query_input, use_kg, use_vector, chat_history],
                outputs=[chatbot, source_display, kg_plot, stats_display],
            )

            def clear_chat():
                return [], [], "*Sources will appear here after a query.*", None, "*Submit a query to see retrieval statistics.*"

            clear_btn.click(
                fn=clear_chat,
                outputs=[chatbot, chat_history, source_display, kg_plot, stats_display],
            )

        # ── Tab 2: Data Pipeline ──────────────────────────────────────────────
        with gr.Tab("Data Pipeline", id="pipeline_tab"):
            gr.Markdown("""
            ## Data Ingestion Pipeline
            
            Process NASA publications from PubMed Central and populate the knowledge base.
            The pipeline performs:
            1. **HTML extraction** from PMC article pages
            2. **Text chunking** into overlapping 1000-char segments  
            3. **Knowledge extraction** (entity + relationship triples via LLM)
            4. **KG population** (Neo4j: optional)
            5. **Vector embedding** (ChromaDB: always available)
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    csv_upload = gr.File(
                        label="Upload Publications CSV",
                        file_types=[".csv"],
                        type="filepath",
                    )

                    max_docs_slider = gr.Slider(
                        minimum=1,
                        maximum=100,
                        value=10,
                        step=1,
                        label="Max Documents to Process",
                        info="Start small (10) to test: each doc takes 15 to 60 seconds",
                    )

                    pipeline_btn = gr.Button("Run Pipeline", variant="primary")

                with gr.Column(scale=1):
                    gr.Markdown("""
                    ### CSV Format Required
                    
                    Your CSV must have these columns:
                    - **`Title`** — publication title
                    - **`Link`** — PMC URL (https://www.ncbi.nlm.nih.gov/pmc/articles/...)
                    
                    The **sample_data.csv** in this repo has the correct format.
                    
                    ### Timing Estimates
                    - 15 to 60 seconds per document (network speed dependent)
                    - 10 docs ≈ 5 to 10 minutes
                    - 50 docs ≈ 30 to 60 minutes
                    
                    ### Optional: Neo4j Setup
                    Add these Space secrets for Knowledge Graph:
                    ```
                    NEO4J_URI      = bolt://...
                    NEO4J_USERNAME = neo4j
                    NEO4J_PASSWORD = your-password
                    ```
                    Get a free instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/).
                    """)

            pipeline_output = gr.Markdown(
                value="*Pipeline output will appear here.*",
                label="Pipeline Progress",
                height=500,
            )

            pipeline_btn.click(
                fn=run_pipeline,
                inputs=[max_docs_slider, csv_upload],
                outputs=pipeline_output,
            )

        # ── Tab 3: Statistics ─────────────────────────────────────────────────
        with gr.Tab("Statistics", id="stats_tab"):
            gr.Markdown("## Knowledge Base Statistics")

            with gr.Row():
                refresh_btn = gr.Button("Refresh", variant="secondary")

            stats_md = gr.Markdown(value="*Click Refresh to load statistics.*")

            refresh_btn.click(fn=get_database_stats, outputs=stats_md)
            demo.load(fn=get_database_stats, outputs=stats_md)

        # ── Tab 4: About ──────────────────────────────────────────────────────
        with gr.Tab("About", id="about_tab"):
            gr.Markdown(ABOUT_CONTENT)

    # ── Load connection status on startup ────────────────────────────────────
    def load_status():
        kg_ok, vs_ok, vs_count = get_connection_status()
        return format_status_html(kg_ok, vs_ok, vs_count)

    demo.load(fn=load_status, outputs=status_html)


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 7860)),
        show_error=True,
    )
