"""
BodhiRAG - NASA Space Biology Knowledge Engine
Enhanced Gradio Interface with Pipeline Support
"""

import gradio as gr
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Import BodhiRAG components
from src.graph_rag.graph_connector import KnowledgeGraphConnector
from src.graph_rag.vector_connector import VectorStoreConnector
from src.graph_rag.agent_router import HybridRAGAgent
from src.data_ingestion import extract_knowledge_from_chunk
from langchain_core.documents import Document

# Import both loaders
from src.data_ingestion.simple_loader import load_and_chunk_documents_simple
from src.data_ingestion.document_loader import extract_publication_data

# Check if Docling is available by checking the module
try:
    from src.data_ingestion.document_loader import DOCLING_AVAILABLE
except:
    DOCLING_AVAILABLE = False

if not DOCLING_AVAILABLE:
    print("⚠️ Using simple document loader (langchain_docling not available)")

# Initialize connectors
kg_connector = KnowledgeGraphConnector(
    uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    username=os.getenv("NEO4J_USERNAME", "neo4j"),
    password=os.getenv("NEO4J_PASSWORD", "password")
)

vs_connector = VectorStoreConnector()

# Initialize agent
agent = HybridRAGAgent(kg_connector, vs_connector)

def query_bodhirag(query: str, use_kg: bool = True, use_vector: bool = True):
    """Query the BodhiRAG system"""
    try:
        # Connect to databases
        if use_kg:
            kg_connector.connect()
        if use_vector:
            vs_connector.initialize_store()
        
        # Route query
        result = agent.route_query(query, use_kg, use_vector)
        
        # Format results
        answer = result["final_answer"]
        
        # Format KG results
        kg_text = ""
        if result["kg_results"]:
            kg_text = "**Knowledge Graph Relationships:**\n\n"
            for i, rel in enumerate(result["kg_results"][:5], 1):
                kg_text += f"{i}. {rel['subject']} → {rel['relationship']} → {rel['object']}\n"
                if rel.get('evidence'):
                    kg_text += f"   *Evidence: {rel['evidence'][:150]}...*\n\n"
        else:
            kg_text = "No knowledge graph relationships found."
        
        # Format VS results
        vs_text = ""
        if result["vs_results"]:
            vs_text = "**Relevant Documents:**\n\n"
            for i, doc in enumerate(result["vs_results"][:3], 1):
                vs_text += f"{i}. {doc['content'][:200]}...\n"
                if doc['metadata'].get('source_title'):
                    vs_text += f"   *Source: {doc['metadata']['source_title']}*\n\n"
        else:
            vs_text = "No relevant documents found."
        
        # Stats
        stats = f"""**Retrieval Statistics:**
- Query Type: {result['query_type']}
- KG Relationships: {result['retrieval_stats']['kg_relationships']}
- VS Documents: {result['retrieval_stats']['vs_documents']}
"""
        
        return answer, kg_text, vs_text, stats
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return error_msg, "", "", ""
    finally:
        if use_kg:
            kg_connector.close()

def run_pipeline(max_docs: int, csv_file):
    """
    Run the data ingestion pipeline
    
    Args:
        max_docs: Maximum number of documents to process
        csv_file: Uploaded CSV file with publication data
    
    Returns:
        Status message with progress
    """
    try:
        status = "🚀 Starting pipeline...\n\n"
        yield status
        
        # Check if CSV file is provided
        if csv_file is None:
            status += "❌ Error: Please upload a CSV file with publication data\n"
            yield status
            return
        
        csv_path = csv_file.name
        
        # Phase 1: Data Ingestion
        status += "=" * 60 + "\n"
        status += "PHASE 1: DATA INGESTION & CHUNKING\n"
        status += "=" * 60 + "\n"
        yield status
        
        # Always use simple loader for HF Spaces (Docling not available)
        status += "Using simple HTML loader (Docling not available in HF Spaces)...\n"
        yield status
        
        # Extract publication data from CSV
        publication_data = extract_publication_data(csv_path)
        if not publication_data:
            status += "❌ Failed to extract publication data from CSV\n"
            yield status
            return
        
        status += f"Found {len(publication_data)} publications in CSV\n"
        yield status
        
        # Progress callback for loader
        def update_progress(msg):
            nonlocal status
            status += msg
        
        # Load with simple loader
        documents = load_and_chunk_documents_simple(
            publication_data=publication_data,
            max_docs=max_docs,
            chunk_size=1000,
            progress_callback=update_progress
        )
        
        yield status
        
        status += f"✅ Loaded and chunked {len(documents)} documents\n\n"
        yield status
        
        if not documents:
            status += "❌ No documents processed. Exiting.\n"
            yield status
            return
        
        # Phase 2: Knowledge Extraction
        status += "=" * 60 + "\n"
        status += "PHASE 2: KNOWLEDGE EXTRACTION\n"
        status += "=" * 60 + "\n"
        yield status
        
        all_triples = []
        for i, doc in enumerate(documents[:10]):  # Limit for demo
            triples = extract_knowledge_from_chunk(doc)
            all_triples.extend(triples)
            
            if (i + 1) % 5 == 0:
                status += f"📊 Progress: {i+1}/{min(10, len(documents))} chunks, {len(all_triples)} triples\n"
                yield status
        
        status += f"✅ Extracted {len(all_triples)} knowledge triples\n\n"
        yield status
        
        # Phase 3: Knowledge Graph Population
        status += "=" * 60 + "\n"
        status += "PHASE 3: KNOWLEDGE GRAPH POPULATION\n"
        status += "=" * 60 + "\n"
        yield status
        
        kg_connector.connect()
        results = kg_connector.populate_graph(all_triples)
        kg_connector.close()
        
        status += f"✅ Knowledge Graph populated:\n"
        status += f"   - Entities: {results.get('entities_created', 0)}\n"
        status += f"   - Relationships: {results.get('relationships_created', 0)}\n\n"
        yield status
        
        # Phase 4: Vector Store Population
        status += "=" * 60 + "\n"
        status += "PHASE 4: VECTOR STORE POPULATION\n"
        status += "=" * 60 + "\n"
        yield status
        
        vs_connector.initialize_store()
        vs_results = vs_connector.populate_store(documents)
        
        status += f"✅ Vector Store populated: {vs_results.get('documents_added', 0)} documents\n\n"
        yield status
        
        # Summary
        status += "=" * 60 + "\n"
        status += "✅ PIPELINE COMPLETE!\n"
        status += "=" * 60 + "\n"
        status += f"Total documents: {len(documents)}\n"
        status += f"Total triples: {len(all_triples)}\n"
        status += f"Entities: {results.get('entities_created', 0)}\n"
        status += f"Relationships: {results.get('relationships_created', 0)}\n"
        status += "\n🎉 Your knowledge base is ready for querying!\n"
        yield status
        
    except Exception as e:
        status += f"\n❌ Pipeline failed: {str(e)}\n"
        yield status

def get_database_stats():
    """Get statistics about the knowledge base"""
    try:
        # Connect to databases
        kg_connector.connect()
        vs_connector.initialize_store()
        
        # Get KG stats
        kg_stats = kg_connector.export_graph_stats()
        
        # Get VS stats
        vs_stats = vs_connector.get_collection_stats()
        
        kg_connector.close()
        
        # Format stats
        stats_text = "## Knowledge Graph Statistics\n\n"
        stats_text += f"- **Total Entities**: {kg_stats.get('total_entities', 0)}\n"
        stats_text += f"- **Total Relationships**: {sum(r['count'] for r in kg_stats.get('relationship_types', []))}\n\n"
        
        stats_text += "### Entity Types:\n"
        for entity_type in kg_stats.get('entity_types', []):
            stats_text += f"- {entity_type.get('type', 'Unknown')}: {entity_type.get('count', 0)}\n"
        
        stats_text += "\n### Relationship Types:\n"
        for rel_type in kg_stats.get('relationship_types', []):
            stats_text += f"- {rel_type.get('type', 'Unknown')}: {rel_type.get('count', 0)}\n"
        
        stats_text += "\n## Vector Store Statistics\n\n"
        stats_text += f"- **Total Documents**: {vs_stats.get('total_documents', 0)}\n"
        
        return stats_text
        
    except Exception as e:
        return f"Error getting stats: {str(e)}"

# Example queries
examples = [
    ["What causes bone loss in space?", True, True],
    ["How does microgravity affect muscle tissue?", True, True],
    ["What countermeasures exist for radiation exposure?", True, True],
    ["Describe oxidative stress in space environments", False, True],
    ["What are the effects of space radiation on DNA?", True, True],
]

# Create Gradio interface with tabs
with gr.Blocks(title="BodhiRAG - Space Biology Knowledge Engine", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 BodhiRAG: NASA Space Biology Knowledge Engine
    
    A Hybrid RAG system combining Knowledge Graph reasoning with semantic search.
    
    **Built for NASA Space Apps Challenge 2025**
    """)
    
    with gr.Tabs():
        # Tab 1: Query Interface
        with gr.Tab("💬 Query"):
            gr.Markdown("""
            Ask questions about space biology research and get answers powered by:
            - **Knowledge Graph** (Neo4j) - Relationship-based reasoning
            - **Vector Store** (ChromaDB) - Semantic search
            - **Hybrid RAG** - Intelligent query routing
            """)
            
            with gr.Row():
                with gr.Column(scale=2):
                    query_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., What causes bone loss in microgravity?",
                        lines=2
                    )
                    
                    with gr.Row():
                        use_kg = gr.Checkbox(label="Use Knowledge Graph", value=True)
                        use_vector = gr.Checkbox(label="Use Vector Store", value=True)
                    
                    submit_btn = gr.Button("Ask BodhiRAG", variant="primary")
                
                with gr.Column(scale=1):
                    gr.Markdown("""
                    ### 💡 Tips
                    - Use KG for relationship queries
                    - Use Vector for descriptive queries
                    - Use both for comprehensive answers
                    """)
            
            with gr.Row():
                answer_output = gr.Textbox(label="Answer", lines=8)
            
            with gr.Row():
                with gr.Column():
                    kg_output = gr.Markdown(label="Knowledge Graph Results")
                with gr.Column():
                    vs_output = gr.Markdown(label="Vector Store Results")
            
            stats_output = gr.Markdown(label="Statistics")
            
            # Examples
            gr.Examples(
                examples=examples,
                inputs=[query_input, use_kg, use_vector],
                label="Example Queries"
            )
            
            # Event handler
            submit_btn.click(
                fn=query_bodhirag,
                inputs=[query_input, use_kg, use_vector],
                outputs=[answer_output, kg_output, vs_output, stats_output]
            )
        
        # Tab 2: Pipeline
        with gr.Tab("⚙️ Data Pipeline"):
            gr.Markdown("""
            ## Run Data Ingestion Pipeline
            
            Process NASA publications and populate the knowledge base.
            
            **Steps:**
            1. Upload CSV file with publication data
            2. Set maximum documents to process
            3. Click "Run Pipeline"
            4. Wait for completion (may take several minutes)
            """)
            
            with gr.Row():
                with gr.Column():
                    csv_upload = gr.File(
                        label="Upload CSV File",
                        file_types=[".csv"],
                        type="filepath"
                    )
                    
                    max_docs_input = gr.Slider(
                        minimum=1,
                        maximum=200,
                        value=10,
                        step=1,
                        label="Maximum Documents to Process"
                    )
                    
                    pipeline_btn = gr.Button("🚀 Run Pipeline", variant="primary")
                
                with gr.Column():
                    gr.Markdown("""
                    ### ⚠️ Important Notes
                    
                    - Processing takes time (1-5 min per document)
                    - Start with small numbers (10-20 docs)
                    - Requires Neo4j connection
                    - CSV format: Title, Link columns
                    """)
            
            pipeline_output = gr.Textbox(
                label="Pipeline Status",
                lines=20,
                max_lines=30
            )
            
            # Event handler
            pipeline_btn.click(
                fn=run_pipeline,
                inputs=[max_docs_input, csv_upload],
                outputs=pipeline_output
            )
        
        # Tab 3: Statistics
        with gr.Tab("📊 Statistics"):
            gr.Markdown("""
            ## Knowledge Base Statistics
            
            View statistics about your knowledge graph and vector store.
            """)
            
            stats_btn = gr.Button("🔄 Refresh Statistics", variant="primary")
            stats_display = gr.Markdown()
            
            # Event handler
            stats_btn.click(
                fn=get_database_stats,
                outputs=stats_display
            )
            
            # Load stats on tab open
            demo.load(fn=get_database_stats, outputs=stats_display)

if __name__ == "__main__":
    demo.launch()
