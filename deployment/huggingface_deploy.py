"""
Hugging Face Deployment Script for BodhiRAG
Deploys the Hybrid RAG model to Hugging Face Spaces
"""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, create_repo, upload_folder
import shutil
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class BodhiRAGDeployer:
    def __init__(self, hf_token: str = None, repo_name: str = "bodhirag-space-biology"):
        """
        Initialize deployer
        
        Args:
            hf_token: Hugging Face API token (or set HF_TOKEN env var)
            repo_name: Name for the Hugging Face Space
        """
        self.hf_token = hf_token or os.getenv("HF_TOKEN")
        if not self.hf_token:
            raise ValueError("Hugging Face token required. Set HF_TOKEN env var or pass hf_token parameter")
        
        self.repo_name = repo_name
        self.api = HfApi(token=self.hf_token)
        self.deploy_dir = project_root / "deployment" / "hf_space"
        
    def prepare_deployment_files(self):
        """Prepare files for Hugging Face Space deployment"""
        print("📦 Preparing deployment files...")
        
        # Create deployment directory
        self.deploy_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy essential source files
        src_files = [
            "src/data_ingestion/__init__.py",
            "src/data_ingestion/document_loader.py",
            "src/data_ingestion/knowledge_extractor.py",
            "src/graph_rag/__init__.py",
            "src/graph_rag/graph_connector.py",
            "src/graph_rag/vector_connector.py",
            "src/graph_rag/agent_router.py",
        ]
        
        for src_file in src_files:
            src_path = project_root / src_file
            dest_path = self.deploy_dir / src_file
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if src_path.exists():
                shutil.copy2(src_path, dest_path)
                print(f"  ✓ Copied {src_file}")
        
        # Create app.py for Gradio interface
        self._create_gradio_app()
        
        # Create requirements.txt for HF Space
        self._create_hf_requirements()
        
        # Create README.md
        self._create_readme()
        
        # Create .env template
        self._create_env_template()
        
        print("✅ Deployment files prepared")
    
    def _create_gradio_app(self):
        """Create Gradio app for Hugging Face Space"""
        app_code = '''"""
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
            kg_text = "**Knowledge Graph Relationships:**\\n\\n"
            for i, rel in enumerate(result["kg_results"][:5], 1):
                kg_text += f"{i}. {rel['subject']} → {rel['relationship']} → {rel['object']}\\n"
                if rel.get('evidence'):
                    kg_text += f"   *Evidence: {rel['evidence'][:150]}...*\\n\\n"
        else:
            kg_text = "No knowledge graph relationships found."
        
        # Format VS results
        vs_text = ""
        if result["vs_results"]:
            vs_text = "**Relevant Documents:**\\n\\n"
            for i, doc in enumerate(result["vs_results"][:3], 1):
                vs_text += f"{i}. {doc['content'][:200]}...\\n"
                if doc['metadata'].get('source_title'):
                    vs_text += f"   *Source: {doc['metadata']['source_title']}*\\n\\n"
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
'''
        
        app_path = self.deploy_dir / "app.py"
        with open(app_path, 'w', encoding='utf-8') as f:
            f.write(app_code)
        print("  ✓ Created app.py")
    
    def _create_hf_requirements(self):
        """Create requirements.txt for Hugging Face Space"""
        requirements = """gradio>=4.0.0
neo4j>=5.0.0
chromadb==0.4.22
sentence-transformers>=2.2.0
pydantic>=2.6.0,<3.0.0
python-dotenv>=1.0.0
langchain==0.0.352
langchain-community==0.0.15
torch>=2.0.0
numpy>=1.21.0
"""
        
        req_path = self.deploy_dir / "requirements.txt"
        with open(req_path, 'w') as f:
            f.write(requirements)
        print("  ✓ Created requirements.txt")
    
    def _create_readme(self):
        """Create README for Hugging Face Space"""
        readme = """---
title: BodhiRAG Space Biology
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.0.0
app_file: app.py
pinned: false
license: mit
---

# BodhiRAG: NASA Space Biology Knowledge Engine

A Hybrid RAG system that combines Knowledge Graph reasoning with semantic search to answer questions about NASA space biology research.

## Features

- **Knowledge Graph (Neo4j)**: Stores relationships between biological entities
- **Vector Store (ChromaDB)**: Semantic search over 607+ NASA publications
- **Hybrid RAG Agent**: Intelligent query routing and answer synthesis
- **Explainable AI**: Source attribution and evidence tracking

## Usage

1. Enter your question about space biology
2. Choose retrieval methods (Knowledge Graph, Vector Store, or both)
3. Get comprehensive answers with source citations

## Example Queries

- "What causes bone loss in space?"
- "How does microgravity affect muscle tissue?"
- "What countermeasures exist for radiation exposure?"

## Built For

NASA Space Apps Challenge 2025 - Build a Space Biology Knowledge Engine

## Architecture

- **Backend**: Python with LangChain
- **Graph DB**: Neo4j
- **Vector DB**: ChromaDB with Sentence Transformers
- **Frontend**: Gradio

## Configuration

Set these environment variables in Space settings:

```
NEO4J_URI=bolt://your-neo4j-instance:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
```

## Data

Processes 607+ NASA Bioscience Research Publications from PubMed Central.

## License

MIT License
"""
        
        readme_path = self.deploy_dir / "README.md"
        with open(readme_path, 'w') as f:
            f.write(readme)
        print("  ✓ Created README.md")
    
    def _create_env_template(self):
        """Create .env template"""
        env_template = """# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password-here

# Hugging Face Token (for deployment)
HF_TOKEN=your-hf-token-here
"""
        
        env_path = self.deploy_dir / ".env.template"
        with open(env_path, 'w') as f:
            f.write(env_template)
        print("  ✓ Created .env.template")
    
    def create_space(self):
        """Create Hugging Face Space"""
        print(f"🚀 Creating Hugging Face Space: {self.repo_name}")
        
        try:
            # Create space
            repo_url = create_repo(
                repo_id=self.repo_name,
                token=self.hf_token,
                repo_type="space",
                space_sdk="gradio",
                exist_ok=True
            )
            print(f"✅ Space created: {repo_url}")
            return repo_url
        except Exception as e:
            print(f"❌ Failed to create space: {e}")
            return None
    
    def upload_files(self):
        """Upload files to Hugging Face Space"""
        print("📤 Uploading files to Hugging Face...")
        
        try:
            self.api.upload_folder(
                folder_path=str(self.deploy_dir),
                repo_id=self.repo_name,
                repo_type="space",
                token=self.hf_token
            )
            print("✅ Files uploaded successfully")
            return True
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False
    
    def deploy(self):
        """Complete deployment workflow"""
        print("=" * 60)
        print("BODHIRAG HUGGING FACE DEPLOYMENT")
        print("=" * 60)
        
        # Step 1: Prepare files
        self.prepare_deployment_files()
        
        # Step 2: Create space
        repo_url = self.create_space()
        if not repo_url:
            print("❌ Deployment failed at space creation")
            return False
        
        # Step 3: Upload files
        success = self.upload_files()
        if not success:
            print("❌ Deployment failed at file upload")
            return False
        
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        print(f"Space URL: https://huggingface.co/spaces/{self.repo_name}")
        print("\nNext steps:")
        print("1. Go to your Space settings on Hugging Face")
        print("2. Add environment variables (NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)")
        print("3. Wait for the Space to build and start")
        print("4. Test your deployed model!")
        
        return True

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy BodhiRAG to Hugging Face')
    parser.add_argument('--token', type=str, help='Hugging Face API token')
    parser.add_argument('--repo-name', type=str, default='bodhirag-space-biology',
                       help='Name for the Hugging Face Space')
    parser.add_argument('--prepare-only', action='store_true',
                       help='Only prepare files without uploading')
    
    args = parser.parse_args()
    
    try:
        deployer = BodhiRAGDeployer(
            hf_token=args.token,
            repo_name=args.repo_name
        )
        
        if args.prepare_only:
            deployer.prepare_deployment_files()
            print(f"\n✅ Files prepared in: {deployer.deploy_dir}")
            print("Review files and run without --prepare-only to deploy")
        else:
            deployer.deploy()
            
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
