"""
Hugging Face Deployment Script for BodhiRAG
Deploys the Hybrid RAG model to Hugging Face Spaces
"""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, create_repo, upload_folder
import shutil

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
            raise ValueError(
                "Hugging Face token required. "
                "Set HF_TOKEN env var or pass hf_token parameter"
            )

        self.repo_name = repo_name
        self.api = HfApi(token=self.hf_token)
        self.deploy_dir = project_root / "deployment" / "hf_space"

    def prepare_deployment_files(self):
        """Prepare files for Hugging Face Space deployment"""
        print("📦 Preparing deployment files...")

        # Create deployment directory
        self.deploy_dir.mkdir(parents=True, exist_ok=True)

        # Copy src/__init__.py so Python treats src as a package
        root_init = project_root / "src" / "__init__.py"
        if root_init.exists():
            dest = self.deploy_dir / "src" / "__init__.py"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root_init, dest)
            print("  ✓ Copied src/__init__.py")

        # Copy essential source files
        src_files = [
            "src/data_ingestion/__init__.py",
            "src/data_ingestion/document_loader.py",
            "src/data_ingestion/knowledge_extractor.py",
            "src/data_ingestion/simple_loader.py",
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

        # Generate derived files
        self._create_gradio_app()
        self._create_hf_requirements()
        self._create_readme()
        self._create_env_template()

        print("✅ Deployment files prepared")

    # ------------------------------------------------------------------
    # FIX-13: generated app.py uses lazy connector init, not module-scope
    # ------------------------------------------------------------------
    def _create_gradio_app(self):
        """Create Gradio app for Hugging Face Space"""
        lines = [
            '"""',
            "BodhiRAG - NASA Space Biology Knowledge Engine",
            "Gradio Interface for Hugging Face Spaces",
            '"""',
            "",
            "import gradio as gr",
            "import os",
            "import logging",
            "",
            "from src.graph_rag.graph_connector import KnowledgeGraphConnector",
            "from src.graph_rag.vector_connector import VectorStoreConnector",
            "from src.graph_rag.agent_router import HybridRAGAgent",
            "",
            "logging.basicConfig(level=logging.INFO)",
            "logger = logging.getLogger(__name__)",
            "",
            "# ---------------------------------------------------------------------------",
            "# Connectors are initialised lazily on first query, NOT at module scope.",
            "# Module-scope init calls os.makedirs / network connects which raises",
            "# PermissionError / ConnectionError before Gradio even starts on HF Spaces.",
            "# ---------------------------------------------------------------------------",
            "_kg_connector = None",
            "_vs_connector = None",
            "_agent = None",
            "",
            "",
            "def _get_connectors():",
            '    """Return (kg, vs, agent), initialising on first call."""',
            "    global _kg_connector, _vs_connector, _agent",
            "    if _agent is None:",
            "        _kg_connector = KnowledgeGraphConnector(",
            '            uri=os.getenv("NEO4J_URI", ""),',
            '            username=os.getenv("NEO4J_USERNAME", "neo4j"),',
            '            password=os.getenv("NEO4J_PASSWORD", ""),',
            "        )",
            "        _vs_connector = VectorStoreConnector()",
            "        _agent = HybridRAGAgent(_kg_connector, _vs_connector)",
            "    return _kg_connector, _vs_connector, _agent",
            "",
            "",
            "def query_bodhirag(query: str, use_kg: bool = True, use_vector: bool = True):",
            '    """Query the BodhiRAG system"""',
            "    try:",
            "        kg_connector, vs_connector, agent = _get_connectors()",
            "",
            "        # Check KG connection — degrade gracefully rather than crash",
            "        if use_kg:",
            "            kg_available = kg_connector.connect()",
            "            if not kg_available:",
            "                use_kg = False",
            "        if use_vector:",
            "            vs_connector.initialize_store()",
            "",
            "        result = agent.route_query(query, use_kg, use_vector)",
            "        answer = result[\"final_answer\"]",
            "",
            "        kg_text = \"No knowledge graph relationships found.\"",
            "        if result[\"kg_results\"]:",
            "            kg_text = \"**Knowledge Graph Relationships:**\\n\\n\"",
            "            for i, rel in enumerate(result[\"kg_results\"][:5], 1):",
            "                kg_text += f\"{i}. {rel['subject']} -> {rel['relationship']} -> {rel['object']}\\n\"",
            "                if rel.get(\"evidence\"):",
            "                    kg_text += f\"   *Evidence: {rel['evidence'][:150]}...*\\n\\n\"",
            "",
            "        vs_text = \"No relevant documents found.\"",
            "        if result[\"vs_results\"]:",
            "            vs_text = \"**Relevant Documents:**\\n\\n\"",
            "            for i, doc in enumerate(result[\"vs_results\"][:3], 1):",
            "                vs_text += f\"{i}. {doc['content'][:200]}...\\n\"",
            "                if doc[\"metadata\"].get(\"source_title\"):",
            "                    vs_text += f\"   *Source: {doc['metadata']['source_title']}*\\n\\n\"",
            "",
            "        stats = (",
            "            \"**Retrieval Statistics:**\\n\"",
            "            f\"- Query Type: {result['query_type']}\\n\"",
            "            f\"- KG Relationships: {result['retrieval_stats']['kg_relationships']}\\n\"",
            "            f\"- VS Documents: {result['retrieval_stats']['vs_documents']}\\n\"",
            "        )",
            "        return answer, kg_text, vs_text, stats",
            "",
            "    except Exception as e:",
            "        logger.error(f\"Query failed: {e}\")",
            "        return f\"Error: {e}\", \"\", \"\", \"\"",
            "    finally:",
            "        try:",
            "            if use_kg and _kg_connector:",
            "                _kg_connector.close()",
            "        except Exception:",
            "            pass",
            "",
            "",
            "examples = [",
            '    ["What causes bone loss in space?", True, True],',
            '    ["How does microgravity affect muscle tissue?", True, True],',
            '    ["What countermeasures exist for radiation exposure?", True, True],',
            '    ["Describe oxidative stress in space environments", False, True],',
            '    ["What are the effects of space radiation on DNA?", True, True],',
            "]",
            "",
            "",
            "with gr.Blocks(",
            '    title="BodhiRAG - Space Biology Knowledge Engine",',
            "    theme=gr.themes.Soft(),",
            ") as demo:",
            '    gr.Markdown("""',
            "    # BodhiRAG: NASA Space Biology Knowledge Engine",
            "",
            "    Ask questions about space biology research and get answers powered by:",
            "    - **Knowledge Graph** (Neo4j) - Relationship-based reasoning",
            "    - **Vector Store** (ChromaDB) - Semantic search",
            "    - **Hybrid RAG** - Intelligent query routing",
            "",
            "    Built for NASA Space Apps Challenge 2025",
            '    """)',
            "",
            "    with gr.Row():",
            "        with gr.Column(scale=2):",
            "            query_input = gr.Textbox(",
            '                label="Your Question",',
            '                placeholder="e.g., What causes bone loss in microgravity?",',
            "                lines=2,",
            "            )",
            "            with gr.Row():",
            '                use_kg = gr.Checkbox(label="Use Knowledge Graph", value=True)',
            '                use_vector = gr.Checkbox(label="Use Vector Store", value=True)',
            '            submit_btn = gr.Button("Ask BodhiRAG", variant="primary")',
            "        with gr.Column(scale=1):",
            '            gr.Markdown("""',
            "            ### Tips",
            "            - Use KG for relationship queries",
            "            - Use Vector for descriptive queries",
            "            - Use both for comprehensive answers",
            '            """)',
            "",
            "    with gr.Row():",
            '        answer_output = gr.Textbox(label="Answer", lines=8)',
            "    with gr.Row():",
            "        with gr.Column():",
            '            kg_output = gr.Markdown(label="Knowledge Graph Results")',
            "        with gr.Column():",
            '            vs_output = gr.Markdown(label="Vector Store Results")',
            '    stats_output = gr.Markdown(label="Statistics")',
            "",
            "    gr.Examples(",
            "        examples=examples,",
            "        inputs=[query_input, use_kg, use_vector],",
            '        label="Example Queries",',
            "    )",
            "    submit_btn.click(",
            "        fn=query_bodhirag,",
            "        inputs=[query_input, use_kg, use_vector],",
            "        outputs=[answer_output, kg_output, vs_output, stats_output],",
            "    )",
            "",
            "",
            'if __name__ == "__main__":',
            "    demo.launch()",
        ]

        app_path = self.deploy_dir / "app.py"
        with open(app_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print("  ✓ Created app.py")

    # ------------------------------------------------------------------
    # FIX-11: requirements match the fixed root requirements.txt
    # ------------------------------------------------------------------
    def _create_hf_requirements(self):
        """Create requirements.txt for Hugging Face Space"""
        requirements = (
            "--extra-index-url https://download.pytorch.org/whl/cpu\n"
            "gradio>=4.44.1,<5.0.0\n"
            "neo4j>=5.0.0,<6.0.0\n"
            "chromadb>=0.5.3,<0.7.0\n"
            "sentence-transformers>=2.2.0,<4.0.0\n"
            "pydantic>=2.6.0,<3.0.0\n"
            "pydantic-settings>=2.0.0,<3.0.0\n"
            "python-dotenv>=1.0.0,<2.0.0\n"
            "langchain-core>=0.2.0,<0.4.0\n"
            "torch>=2.2.0,<3.0.0\n"
            "numpy>=1.21.0,<2.0.0\n"
            "pandas>=1.5.0,<3.0.0\n"
            "beautifulsoup4>=4.12.0,<5.0.0\n"
            "requests>=2.31.0,<3.0.0\n"
        )

        req_path = self.deploy_dir / "requirements.txt"
        with open(req_path, "w") as f:
            f.write(requirements)
        print("  ✓ Created requirements.txt")

    # ------------------------------------------------------------------
    # FIX-12: sdk_version bumped to 4.44.1
    # ------------------------------------------------------------------
    def _create_readme(self):
        """Create README for Hugging Face Space"""
        readme = (
            "---\n"
            "title: BodhiRAG Space Biology\n"
            "emoji: \U0001f680\n"
            "colorFrom: blue\n"
            "colorTo: purple\n"
            "sdk: gradio\n"
            "sdk_version: 4.44.1\n"
            "app_file: app.py\n"
            "pinned: false\n"
            "license: mit\n"
            "---\n\n"
            "# BodhiRAG: NASA Space Biology Knowledge Engine\n\n"
            "A Hybrid RAG system combining Knowledge Graph reasoning with semantic search "
            "to answer questions about NASA space biology research.\n\n"
            "## Features\n\n"
            "- **Knowledge Graph (Neo4j)**: Stores relationships between biological entities\n"
            "- **Vector Store (ChromaDB)**: Semantic search over 607+ NASA publications\n"
            "- **Hybrid RAG Agent**: Intelligent query routing and answer synthesis\n"
            "- **Explainable AI**: Source attribution and evidence tracking\n\n"
            "## Configuration\n\n"
            "Set these environment variables in Space settings:\n\n"
            "```\n"
            "NEO4J_URI=bolt://your-neo4j-instance:7687\n"
            "NEO4J_USERNAME=neo4j\n"
            "NEO4J_PASSWORD=your-password\n"
            "```\n\n"
            "## License\n\nMIT License\n"
        )

        readme_path = self.deploy_dir / "README.md"
        with open(readme_path, "w") as f:
            f.write(readme)
        print("  ✓ Created README.md")

    def _create_env_template(self):
        """Create .env template"""
        env_template = (
            "# Neo4j Configuration\n"
            "NEO4J_URI=bolt://your-neo4j-instance:7687\n"
            "NEO4J_USERNAME=neo4j\n"
            "NEO4J_PASSWORD=your-password-here\n\n"
            "# Hugging Face Token (for deployment)\n"
            "HF_TOKEN=your-hf-token-here\n"
        )

        env_path = self.deploy_dir / ".env.template"
        with open(env_path, "w") as f:
            f.write(env_template)
        print("  ✓ Created .env.template")

    def create_space(self):
        """Create Hugging Face Space"""
        print(f"🚀 Creating Hugging Face Space: {self.repo_name}")

        try:
            repo_url = create_repo(
                repo_id=self.repo_name,
                token=self.hf_token,
                repo_type="space",
                space_sdk="gradio",
                exist_ok=True,
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
                token=self.hf_token,
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

        self.prepare_deployment_files()

        repo_url = self.create_space()
        if not repo_url:
            print("❌ Deployment failed at space creation")
            return False

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

    parser = argparse.ArgumentParser(description="Deploy BodhiRAG to Hugging Face")
    parser.add_argument("--token", type=str, help="Hugging Face API token")
    parser.add_argument(
        "--repo-name",
        type=str,
        default="bodhirag-space-biology",
        help="Name for the Hugging Face Space",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only prepare files without uploading",
    )

    args = parser.parse_args()

    try:
        deployer = BodhiRAGDeployer(hf_token=args.token, repo_name=args.repo_name)

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
