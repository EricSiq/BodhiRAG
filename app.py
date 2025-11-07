"""
BodhiRAG - NASA Space Biology Knowledge Engine
Gradio Interface for Hugging Face Spaces
"""

import gradio as gr
import os
from pathlib import Path

# Import BodhiRAG components
from src.graph_rag.graph_connector import KnowledgeGraphConnector
from src.graph_rag.vector_connector import VectorStoreConnector
from src.graph_rag.agent_router import HybridRAGAgent

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
    """
    Query the BodhiRAG system
    
    Args:
        query: User question
        use_kg: Use Knowledge Graph
        use_vector: Use Vector Store
    
    Returns:
        Answer, KG results, VS results, stats
    """
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

# Example queries
examples = [
    ["What causes bone loss in space?", True, True],
    ["How does microgravity affect muscle tissue?", True, True],
    ["What countermeasures exist for radiation exposure?", True, True],
    ["Describe oxidative stress in space environments", False, True],
    ["What are the effects of space radiation on DNA?", True, True],
]

# Create Gradio interface
with gr.Blocks(title="BodhiRAG - Space Biology Knowledge Engine", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 BodhiRAG: NASA Space Biology Knowledge Engine
    
    Ask questions about space biology research and get answers powered by:
    - **Knowledge Graph** (Neo4j) - Relationship-based reasoning
    - **Vector Store** (ChromaDB) - Semantic search
    - **Hybrid RAG** - Intelligent query routing
    
    Built for NASA Space Apps Challenge 2025
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

if __name__ == "__main__":
    demo.launch()
