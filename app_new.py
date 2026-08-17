"""
BodhiRAG: NASA Space Biology Knowledge Engine
================================================
Hybrid RAG system combining Knowledge Graph (Neo4j) with Vector Store (ChromaDB)
and LLM-powered answer synthesis (Mistral/Qwen via HF Inference API).

Implements UX from FRONTEND_UX_DESIGN.md and architecture from PIPELINE_ARCHITECTURE_AND_DATA_CONTRACTS.md

Built for NASA Space Apps Challenge 2025.
"""

import gradio as gr
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

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

# Import new components
from src.core.config import settings
from src.models import OperatingMode, ServiceState, QueryRoute
from src.services.health_manager import (
    ServiceHealthManager, 
    get_health_manager,
    initialize_health_manager
)
from src.services.llm_inference import (
    generate_answer, 
    classify_route_with_qwen,
    get_model_status
)
from src.ui.evidence_formatter import (
    EvidenceFormatter, 
    build_answer_with_citations,
    format_status_bar
)

# Check Docling availability
try:
    from src.data_ingestion.document_loader import DOCLING_AVAILABLE
except ImportError:
    DOCLING_AVAILABLE = False

# ---------------------------------------------------------------------------
# Initialize components
# ---------------------------------------------------------------------------

# Initialize health manager with operating mode
health_manager = initialize_health_manager(settings.operating_mode)

# Initialize connectors
kg_connector = KnowledgeGraphConnector(
    uri=settings.neo4j_uri,
    username=settings.neo4j_username,
    password=settings.neo4j_password,
)
vs_connector = VectorStoreConnector()
agent = HybridRAGAgent(kg_connector, vs_connector)

# Evidence formatter
evidence_formatter = EvidenceFormatter()

# ---------------------------------------------------------------------------
# Service state management
# ---------------------------------------------------------------------------

def update_service_health():
    """Update health status for all services."""
    # Check vector store
    health_manager.check_vector_store(vs_connector)
    
    # Check graph
    health_manager.check_graph(kg_connector)
    
    # Check generation
    model_status = get_model_status()
    health_manager.check_generation(
        model_status["provider"],
        model_status["hf_token_set"]
    )
    
    return health_manager.get_health()

def get_service_state_message() -> str:
    """Get user-facing service state message."""
    return health_manager.get_state_message()

# ---------------------------------------------------------------------------
# Query routing with mode selector
# ---------------------------------------------------------------------------

def determine_route_from_mode(mode: str, query: str) -> str:
    """
    Determine retrieval route based on user-selected mode.
    Implements mode selector from FRONTEND_UX_DESIGN.md
    """
    if mode == "Auto":
        # Use Qwen/LLM-based routing
        routing = classify_route_with_qwen(query)
        return routing.get("route", "hybrid")
    elif mode == "Literature":
        return "semantic"
    elif mode == "Relationships":
        return "graph"
    elif mode == "Both":
        return "hybrid"
    else:
        return "hybrid"

# ---------------------------------------------------------------------------
# Core query function (updated with evidence cards)
# ---------------------------------------------------------------------------

def query_bodhirag(
    query: str, 
    mode: str, 
    history: List,
    advanced_kg: bool = True,
    advanced_vector: bool = True,
    max_results: int = 5
) -> Tuple[List, str, Any, str]:
    """
    Main query handler with mode-based routing and evidence cards.
    Implements answer format from FRONTEND_UX_DESIGN.md
    """
    if not query or not query.strip():
        yield history or [], "*Please enter a question.*", None, ""
        return

    history = history or []

    # Show loading message
    history.append((query, "Searching knowledge base..."))
    yield history, "", None, ""

    try:
        # Update health
        health = update_service_health()
        
        # Determine route from mode
        route = determine_route_from_mode(mode, query)
        
        # Determine which sources to use based on route and availability
        use_kg = (route in ["graph", "hybrid"]) and advanced_kg and health.graph_available
        use_vector = (route in ["semantic", "hybrid"]) and advanced_vector and health.vector_available
        
        # Handle graph fallback
        if route == "graph" and not health.graph_available:
            use_vector = True
            route = "semantic"
            logger.info("Graph unavailable, falling back to semantic retrieval")
        
        # Connect to KG if needed
        if use_kg:
            kg_available = kg_connector.connect()
            if not kg_available:
                use_kg = False
                if route == "graph":
                    use_vector = True
                    route = "semantic"

        # Initialize vector store if needed
        if use_vector:
            vs_connector.initialize_store()

        # Execute retrieval
        result = agent.route_query(query, use_kg, use_vector)
        answer = result["final_answer"]
        kg_results = result["kg_results"]
        vs_results = result["vs_results"]
        query_type = route
        
        # Build evidence panel with route badge
        evidence_md = evidence_formatter.format_retrieval_results(
            kg_results, vs_results, route
        )
        
        # Build complete answer with citations
        complete_answer = build_answer_with_citations(
            answer,
            kg_results,
            vs_results,
            route,
            model_available=health.generation_available
        )

        # Build KG graph visualization (optional)
        kg_fig = None
        try:
            from src.graph_rag.graph_visualizer import build_kg_graph
            if kg_results:
                kg_fig = build_kg_graph(
                    kg_results,
                    title=f"Knowledge Graph: {query[:40]}{'...' if len(query) > 40 else ''}",
                )
        except Exception as e:
            logger.warning(f"Graph visualization failed: {e}")

        # Build stats with route badge
        route_badge = {
            "semantic": "📚 Literature Search",
            "graph": "🔗 Graph Retrieval", 
            "hybrid": "🔀 Hybrid"
        }.get(route, route)
        
        stats_text = (
            f"**{route_badge}** • "
            f"{len(kg_results)} graph relationships • "
            f"{len(vs_results)} literature passages"
        )

        # Update history with complete answer
        history[-1] = (query, complete_answer)

        if use_kg:
            kg_connector.close()

        yield history, evidence_md, kg_fig, stats_text

    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        history[-1] = (query, f"Error: {str(e)}\n\nPlease try again or check the logs.")
        yield history, "", None, ""

        if use_kg:
            try:
                kg_connector.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Status bar (user-facing language)
# ---------------------------------------------------------------------------

def get_connection_status() -> Tuple[bool, bool, int, bool, int, str]:
    """Return connection status for all services."""
    health = update_service_health()
    return (
        health.vector_available,
        health.graph_available, 
        health.generation_available,
        health.vector_document_count,
        health.graph_entity_count,
        health.generation_model
    )


def format_status_html_user_facing(
    vector_ok: bool,
    graph_ok: bool,
    generation_ok: bool,
    vector_count: int,
    graph_count: int,
    model_name: str
) -> str:
    """Generate status bar with user-facing language."""
    return format_status_bar(
        vector_available=vector_ok,
        graph_available=graph_ok,
        generation_available=generation_ok,
        vector_count=vector_count,
        graph_count=graph_count,
        model_name=model_name,
        operating_mode=settings.operating_mode.value
    )


# ---------------------------------------------------------------------------
# Pipeline function (with preflight checks)
# ---------------------------------------------------------------------------

def run_pipeline_with_preflight(max_docs: int, csv_file):
    """Run the data ingestion pipeline with preflight checks and progress."""
    # Check if ingestion is allowed
    if not settings.is_maintainer_mode():
        yield "⚠️ **Ingestion is disabled in this mode.**\n\nSet `OPERATING_MODE=maintainer_ingest` to enable corpus builds."
        return
    
    status = "**Pipeline Preflight Checks**\n\n"
    yield status
    
    # Preflight checks
    health = update_service_health()
    
    checks = []
    checks.append(f"✅ Parser available: {'Docling' if DOCLING_AVAILABLE else 'Simple HTML loader'}")
    checks.append(f"{'✅' if health.vector_available else '❌'} Vector store: {'Ready' if health.vector_available else 'Not available'}")
    checks.append(f"{'✅' if health.graph_available else '⚠️'} Graph database: {'Connected' if health.graph_available else 'Not configured (optional)'}")
    checks.append(f"{'✅' if health.generation_available else '⚠️'} Model: {health.generation_model or 'Template fallback'}")
    
    status += "\n".join(checks) + "\n\n"
    yield status
    
    if csv_file is None:
        yield status + "❌ **Error: Please upload a CSV file first.**\n"
        return

    csv_path = csv_file if isinstance(csv_file, str) else csv_file.name

    # Phase 1: Load publications
    status += "---\n### Phase 1: Data Ingestion\n"
    yield status

    publication_data = extract_publication_data(csv_path)
    if not publication_data:
        yield status + "❌ **Error: No valid PMC links found in CSV.**\n"
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

    if log_lines:
        status += "```\n" + "\n".join(log_lines[-10:]) + "\n```\n\n"

    status += f"Loaded and chunked **{len(documents)}** document chunks\n\n"
    yield status

    if not documents:
        yield status + "❌ **Error: No documents could be processed.**\n"
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
    if health.graph_available and kg_connector.connect():
        kg_results_data = kg_connector.populate_graph(all_triples)
        kg_connector.close()
        status += (
            f"KG populated: "
            f"**{kg_results_data.get('entities_created', 0)} entities**, "
            f"**{kg_results_data.get('relationships_created', 0)} relationships**\n\n"
        )
    else:
        status += "Neo4j not configured: skipping KG (add `NEO4J_*` secrets)\n\n"
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
    status += "**Your knowledge base has been updated.**"
    yield status


# ---------------------------------------------------------------------------
# Statistics function (Explore tab)
# ---------------------------------------------------------------------------

def get_explore_stats():
    """Return formatted statistics for the Explore tab."""
    health = update_service_health()
    
    text = f"*Last updated: {datetime.now().strftime('%H:%M:%S')}*\n\n"
    
    # Corpus coverage
    text += "### Corpus Coverage\n\n"
    
    if health.vector_available and health.vector_document_count > 0:
        text += f"| Metric | Value |\n|--------|-------|\n"
        text += f"| Literature chunks | {health.vector_document_count:,} |\n"
        
        if health.graph_available and health.graph_entity_count > 0:
            text += f"| Graph entities | {health.graph_entity_count:,} |\n"
        
        # Corpus build info
        if settings.corpus_build_id:
            text += f"\n**Corpus Build:** `{settings.corpus_build_id}`\n"
        else:
            text += f"\n**Corpus Build:** Pre-seeded demo corpus\n"
    else:
        text += "⚠️ **No corpus installed.** Run the data pipeline or use the pre-seeded demo.\n"
    
    # Model status
    text += "\n---\n### Model Status\n\n"
    if health.generation_available:
        text += f"🤖 **{health.generation_model}** active\n"
    else:
        text += "📝 **Template mode** — Set HF_TOKEN for model-based answers\n"
    
    # Operating mode
    text += f"\n---\n### Operating Mode\n\n"
    text += f"⚙️ **{settings.get_mode_description()}**\n"
    
    # Example queries
    text += "\n---\n### Suggested Queries\n\n"
    text += "Try these example questions:\n"
    text += "- What causes bone loss in microgravity?\n"
    text += "- How does space radiation affect DNA?\n"
    text += "- What countermeasures exist for muscle atrophy?\n"
    
    return text


# ---------------------------------------------------------------------------
# Custom CSS (enhanced for accessibility)
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
    --error:         #ef4444;
}

/* Accessibility: Focus states */
*:focus {
    outline: 2px solid var(--accent-blue) !important;
    outline-offset: 2px !important;
}

/* Accessibility: Minimum contrast */
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
    padding: 24px 32px;
    margin-bottom: 12px;
    position: relative;
    overflow: hidden;
}

.hero-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 6px 0;
}

.hero-subtitle {
    font-size: 1rem;
    color: var(--text-secondary);
    margin: 0 0 16px 0;
}

.hero-stats {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}

.stat-chip {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 0.8rem;
    color: #93c5fd;
    font-weight: 500;
}

/* ===== Status Bar ===== */
.status-bar {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    padding: 8px 0;
    align-items: center;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 16px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.2px;
}

.badge-green  { background: rgba(34,197,94,0.15);  border: 1px solid rgba(34,197,94,0.4);  color: #86efac; }
.badge-blue   { background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.4); color: #93c5fd; }
.badge-purple { background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.4); color: #c4b5fd; }
.badge-yellow { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.4); color: #fcd34d; }
.badge-gray   { background: rgba(148,163,184,0.1); border: 1px solid rgba(148,163,184,0.3);color: #94a3b8; }
.badge-gold   { background: rgba(245,158,11,0.2);  border: 1px solid rgba(245,158,11,0.5); color: #fcd34d; }

/* ===== Mode Selector ===== */
.mode-selector {
    margin-bottom: 12px;
}

/* ===== Evidence Panel ===== */
.evidence-panel {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
}

.route-badge {
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.85rem;
    color: #c4b5fd;
    font-weight: 600;
    margin-bottom: 12px;
}

/* ===== Source Cards ===== */
.source-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
}

.source-card-title {
    font-weight: 600;
    color: #93c5fd;
}

/* ===== Tabs ===== */
.tab-nav button {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 600 !important;
    padding: 8px 16px !important;
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
    border-radius: 8px !important;
    font-size: 0.9rem !important;
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
    border-radius: 8px !important;
    padding: 10px 20px !important;
    font-size: 0.9rem !important;
    transition: all 0.2s ease !important;
}

button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(124,58,237,0.3) !important;
}

button.secondary {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-primary) !important;
    border-radius: 8px !important;
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
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

.chatbot .message.user {
    background: rgba(59,130,246,0.15) !important;
    border: 1px solid rgba(59,130,246,0.3) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
}

/* ===== Markdown ===== */
.prose, .markdown {
    color: var(--text-primary) !important;
}

.prose h3, .markdown h3 { color: #93c5fd !important; }
.prose h4, .markdown h4 { color: #a78bfa !important; }
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

/* ===== Scrollbars ===== */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* ===== Mobile Responsive ===== */
@media (max-width: 768px) {
    .hero-banner {
        padding: 16px 20px;
    }
    .hero-title {
        font-size: 1.5rem;
    }
    .hero-stats {
        gap: 8px;
    }
    .stat-chip {
        font-size: 0.7rem;
        padding: 3px 8px;
    }
}

/* ===== Accessibility: Skip Link ===== */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--accent-blue);
    color: white;
    padding: 8px 16px;
    border-radius: 0 0 8px 0;
    z-index: 100;
}

.skip-link:focus {
    top: 0;
}
"""


# ---------------------------------------------------------------------------
# Example queries
# ---------------------------------------------------------------------------

EXAMPLE_QUERIES = [
    "What causes bone loss in space?",
    "How does microgravity affect the cardiovascular system?",
    "What countermeasures exist for muscle atrophy during spaceflight?",
    "Describe the effects of space radiation on DNA repair",
    "How does spaceflight affect the immune system?",
    "What is the role of oxidative stress in space biology?",
]


# ---------------------------------------------------------------------------
# About content
# ---------------------------------------------------------------------------

ABOUT_CONTENT = """
## About BodhiRAG

BodhiRAG is an **open research assistant** for NASA space-biology and astronomy-adjacent literature. It helps researchers move from natural-language questions to answers traceable to specific passages and graph relationships.

### How It Works

1. **Ask a question** — Enter your research question in natural language
2. **Choose a mode** — Select Auto, Literature, Relationships, or Both
3. **Review evidence** — See which sources contributed to the answer
4. **Explore relationships** — Visualize connections in the knowledge graph

### Retrieval Modes

| Mode | Description |
|------|-------------|
| **Auto** | Router selects the best evidence path based on your question |
| **Literature** | Search publication passages using semantic similarity |
| **Relationships** | Explore entities and mechanisms via the knowledge graph |
| **Both** | Combine literature and relationships for comprehensive results |

### Technology

- **Knowledge Graph**: Neo4j stores entity relationships (causes, affects, mitigates)
- **Vector Store**: ChromaDB with IBM Granite embeddings for semantic search
- **Answer Synthesis**: Mistral-7B or Qwen for grounded, cited answers
- **Data**: 600+ NASA PubMed Central publications

### Operating Modes

This instance is running in **{mode}** mode.

### Privacy

Questions are processed by the selected model provider (local or hosted). No queries are stored by default.

### Credits

Built for **NASA Space Apps Challenge 2025** — *Build a Space Biology Knowledge Engine*
"""


# ---------------------------------------------------------------------------
# Gradio UI (with mode selector)
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

    # Skip link for accessibility
    gr.HTML('<a href="#query-input" class="skip-link">Skip to main content</a>')
    
    # Hero Banner
    gr.HTML(f"""
    <div class="hero-banner">
        <h1 class="hero-title">BodhiRAG</h1>
        <p class="hero-subtitle">NASA Space Biology Knowledge Engine • Research assistant with traceable evidence</p>
        <div class="hero-stats">
            <span class="stat-chip">Hybrid RAG</span>
            <span class="stat-chip">Knowledge Graph</span>
            <span class="stat-chip">Vector Search</span>
            <span class="stat-chip">Open Source</span>
        </div>
    </div>
    """)

    # Status Bar
    status_html = gr.HTML(value="<div class='status-bar'>Checking services...</div>")

    # Tabs
    with gr.Tabs() as tabs:

        # Tab 1: Ask
        with gr.Tab("Ask BodhiRAG", id="query_tab"):
            with gr.Row(equal_height=False):

                # Left column - controls
                with gr.Column(scale=1, min_width=280):
                    gr.Markdown("### Ask a Question")
                    
                    query_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., What causes bone loss in microgravity?",
                        lines=3,
                        max_lines=6,
                        elem_id="query-input",
                    )
                    
                    # Mode selector (replaces raw toggles)
                    gr.Markdown("### Retrieval Mode")
                    mode_selector = gr.Radio(
                        choices=["Auto", "Literature", "Relationships", "Both"],
                        value="Auto",
                        label="Select how to search the knowledge base",
                        info="Auto chooses the best path for your question",
                    )
                    
                    # Advanced settings (disclosure)
                    with gr.Accordion("Advanced retrieval settings", open=False):
                        advanced_kg = gr.Checkbox(
                            label="Enable Knowledge Graph",
                            value=True,
                            info="Use relationship-based reasoning"
                        )
                        advanced_vector = gr.Checkbox(
                            label="Enable Vector Search",
                            value=True,
                            info="Use semantic similarity search"
                        )
                        max_results = gr.Slider(
                            minimum=3,
                            maximum=10,
                            value=5,
                            step=1,
                            label="Maximum results",
                        )
                    
                    with gr.Row():
                        submit_btn = gr.Button("Ask BodhiRAG", variant="primary", scale=3)
                        clear_btn = gr.Button("Clear", variant="secondary", scale=1)
                    
                    gr.Markdown("---")
                    gr.Markdown("### Example Questions")
                    
                    for i, example in enumerate(EXAMPLE_QUERIES):
                        ex_btn = gr.Button(
                            f"{example[:50]}{'…' if len(example) > 50 else ''}",
                            variant="secondary",
                            size="sm",
                        )
                        ex_btn.click(
                            fn=lambda q=example: q,
                            outputs=query_input,
                        )

                # Right column - results
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(
                        label="BodhiRAG Answers",
                        height=400,
                        show_copy_button=True,
                        bubble_full_width=False,
                    )
                    
                    stats_display = gr.Markdown(
                        value="*Submit a query to see retrieval statistics.*",
                    )

            # Evidence panel
            with gr.Row():
                with gr.Column(scale=1):
                    source_display = gr.Markdown(
                        value="*Sources and evidence will appear here after a query.*",
                        label="Evidence",
                    )
                with gr.Column(scale=1):
                    kg_plot = gr.Plot(
                        label="Knowledge Graph",
                        show_label=True,
                    )
            
            # Graph path disclosure
            with gr.Accordion("Graph paths (text)", open=False):
                graph_path_text = gr.Markdown(
                    value="*Graph paths will appear here after a query.*"
                )

            # State
            chat_history = gr.State([])

            # Event handlers
            def submit_query_handler(query, mode, history, adv_kg, adv_vector, max_res):
                return query_bodhirag(query, mode, history, adv_kg, adv_vector, max_res)

            submit_btn.click(
                fn=submit_query_handler,
                inputs=[query_input, mode_selector, chat_history, advanced_kg, advanced_vector, max_results],
                outputs=[chatbot, source_display, kg_plot, stats_display],
            )

            query_input.submit(
                fn=submit_query_handler,
                inputs=[query_input, mode_selector, chat_history, advanced_kg, advanced_vector, max_results],
                outputs=[chatbot, source_display, kg_plot, stats_display],
            )

            def clear_chat():
                return [], [], "*Sources will appear here after a query.*", None, "*Submit a query to see retrieval statistics.*", "*Graph paths will appear here.*"

            clear_btn.click(
                fn=clear_chat,
                outputs=[chatbot, chat_history, source_display, kg_plot, stats_display, graph_path_text],
            )

        # Tab 2: Explore (renamed from Statistics)
        with gr.Tab("Explore the Corpus", id="explore_tab"):
            gr.Markdown("## Explore the Corpus\n\nDiscover what's in the knowledge base and find example queries.")
            
            with gr.Row():
                refresh_btn = gr.Button("Refresh Statistics", variant="secondary")
            
            explore_md = gr.Markdown(value="*Click Refresh to load corpus information.*")
            
            refresh_btn.click(fn=get_explore_stats, outputs=explore_md)
            demo.load(fn=get_explore_stats, outputs=explore_md)

        # Tab 3: Data Pipeline (maintainer only)
        with gr.Tab("Data Pipeline", id="pipeline_tab"):
            if settings.is_maintainer_mode():
                gr.Markdown("""
                ## Corpus Ingestion Pipeline
                
                Process NASA publications from PubMed Central to build the knowledge base.
                
                **Warning:** This modifies the shared corpus. Only run in maintainer mode.
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
                            label="Max Documents",
                        )

                        pipeline_btn = gr.Button("Run Pipeline", variant="primary")

                    with gr.Column(scale=1):
                        gr.Markdown("""
                        ### CSV Format
                        
                        Required columns:
                        - **Title** — publication title
                        - **Link** — PMC URL
                        
                        ### Estimates
                        - 15-60 seconds per document
                        - 10 docs ≈ 5-10 minutes
                        
                        ### Optional: Neo4j
                        
                        Set these secrets for Knowledge Graph:
                        ```
                        NEO4J_URI
                        NEO4J_USERNAME
                        NEO4J_PASSWORD
                        ```
                        """)

                pipeline_output = gr.Markdown(value="*Pipeline output will appear here.*")
                
                pipeline_btn.click(
                    fn=run_pipeline_with_preflight,
                    inputs=[max_docs_slider, csv_upload],
                    outputs=pipeline_output,
                )
            else:
                gr.Markdown("""
                ## Data Pipeline
                
                ⚠️ **Ingestion is disabled in this mode.**
                
                The data pipeline is only available in **Maintainer Mode** to prevent 
                concurrent uploads from contaminating a shared public corpus.
                
                To enable corpus builds, set:
                ```
                OPERATING_MODE=maintainer_ingest
                ```
                
                For query-only access, use the **Ask BodhiRAG** tab.
                """)

        # Tab 4: About
        with gr.Tab("About", id="about_tab"):
            about_content_filled = ABOUT_CONTENT.format(
                mode=settings.get_mode_description()
            )
            gr.Markdown(about_content_filled)

    # Load status on startup
    def load_status():
        v_ok, g_ok, gen_ok, v_count, g_count, model = get_connection_status()
        return format_status_html_user_facing(v_ok, g_ok, gen_ok, v_count, g_count, model)

    demo.load(fn=load_status, outputs=status_html)


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(f"Starting BodhiRAG in {settings.operating_mode.value} mode")
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", 7860)),
        show_error=True,
    )
