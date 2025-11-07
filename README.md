---
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
