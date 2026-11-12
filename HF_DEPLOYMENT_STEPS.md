# 🚀 BodhiRAG — HF Space Deployment Guide

## Overview

This guide walks you through deploying BodhiRAG to Hugging Face Spaces step-by-step.
The app works out-of-the-box with vector search. Adding HF_TOKEN enables AI-powered answers.

---

## Prerequisites

- [ ] Hugging Face account
- [ ] HF token with **write** scope: https://huggingface.co/settings/tokens
- [ ] (Optional) Neo4j AuraDB instance: https://neo4j.com/cloud/aura/
- [ ] Git installed
- [ ] Python 3.11 or 3.12 (NOT 3.14 — ChromaDB incompatible)

---

## Step 1: Create HF Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Space name**: `BodhiRAG` (or your preferred name)
   - **SDK**: Gradio
   - **Visibility**: Public (required for free tier)
   - **Hardware**: CPU Basic (free)
3. Click **Create Space**

---

## Step 2: Pre-seed the Vector Store (Run Locally)

This embeds 60 NASA paper abstracts so the Space works immediately on launch.

```powershell
# From project root
py -3.12 -m pip install -r requirements.txt
py -3.12 scripts/seed_vector_store.py
```

This creates `data/chroma_preseeded/` — **commit this to your repo**.

---

## Step 3: Push to HF Space

```bash
# Clone your new HF Space
git clone https://huggingface.co/spaces/YOUR_USERNAME/BodhiRAG
cd BodhiRAG

# Copy project files (excluding .git, node_modules, etc.)
# OR: Add the HF Space as a remote to your existing repo
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/BodhiRAG

# Push everything
git push space main
```

**If using LFS** (for the ChromaDB and CSV):
```bash
git lfs install
git lfs track "*.parquet" "*.arrow"
git push space main
```

---

## Step 4: Configure Space Secrets

In your Space settings (Settings → Repository secrets):

| Secret Name | Value | Required |
|-------------|-------|----------|
| `HF_TOKEN` | Your HF token | Recommended |
| `NEO4J_URI` | `bolt://xxx.databases.neo4j.io:7687` | Optional |
| `NEO4J_USERNAME` | `neo4j` | Optional |
| `NEO4J_PASSWORD` | Your password | Optional |

---

## Step 5: Wait for Build

- Build takes 3–8 minutes on first launch
- Watch the **Logs** tab for any errors
- Common issues:
  - `ModuleNotFoundError` → check requirements.txt versions
  - `PermissionError` → ChromaDB path issue (should be auto-fixed)

---

## Step 6: Test Your Space

Visit `https://huggingface.co/spaces/YOUR_USERNAME/BodhiRAG`

Test queries:
1. "What causes bone loss in space?" — should return VS results immediately
2. "How does microgravity affect the cardiovascular system?"
3. "What countermeasures exist for muscle atrophy?"

---

## Step 7: Add to Resume

Your Space URL becomes your project link:
```
https://huggingface.co/spaces/YOUR_USERNAME/BodhiRAG
```

Talking points:
- "Built a production Hybrid RAG system combining Knowledge Graph (Neo4j) and semantic search (ChromaDB)"
- "Deployed on Hugging Face Spaces with LLM-powered answer synthesis (Mistral-7B)"
- "Processes 607+ NASA space biology publications from PubMed Central"
- "Implements entity extraction, relationship modeling, and explainable AI with source attribution"
- "Built for NASA Space Apps Challenge 2025"

---

## Troubleshooting

### Space won't build
- Check README.md YAML frontmatter: `sdk_version: 4.44.1`
- Check requirements.txt — ensure no conflicting versions

### No results on query
- Run the pipeline tab with the included `sample_data.csv`
- OR commit `data/chroma_preseeded/` to the repo

### LLM not working
- Verify `HF_TOKEN` is set in Space secrets
- Check the status bar on the UI — it shows LLM mode

### Slow responses
- Normal on free CPU tier: ~15-30s for LLM
- Vector-only queries are fast (<2s)
- Consider HF Spaces Pro ($9/mo) for 2x CPU

---

## Architecture Summary

```
HF Space (Gradio 4.x)
│
├── app.py — Main UI + routing
├── src/graph_rag/
│   ├── agent_router.py  — Query routing + synthesis
│   ├── vector_connector.py — ChromaDB interface
│   ├── graph_connector.py  — Neo4j interface  
│   └── graph_visualizer.py — Plotly KG viz
├── src/services/
│   └── llm_inference.py — HF API wrapper (Mistral-7B)
├── src/data_ingestion/
│   ├── simple_loader.py    — HTML → Document chunks
│   └── knowledge_extractor.py — Triple extraction
└── data/chroma_preseeded/  — Pre-embedded NASA papers
```
