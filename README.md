# BodhiRAG:

A Knowledge Graph Platform for Space Biology Research Intelligence

**NASA Space Apps Challenge 2025**  
**Problem Statement:** Build a Space Biology Knowledge Engine

---

## Executive Summary

BodhiRAG is an advanced knowledge management and reasoning platform designed to unify NASA's space biology research ecosystem. By integrating scientific literature, experimental datasets, and funding metadata into a structured knowledge graph, the platform enables intelligent querying, multi-hop reasoning, and research gap analysis to support scientific discovery and mission planning.

## Data Integration

- **Primary Corpus:** 607+ NASA Bioscience Research Publications (PMC)
- **Secondary Sources:** NASA Open Science Data Repository (OSDR), NASA Task Book
- **Data Types:** Peer-reviewed publications, experimental datasets, funding metadata

## System Architecture

### 1. Data Ingestion & Processing Pipeline

**Components:**
- Document parsing and chunking (`DoclingLoader`, `HybridChunker`)
- Parallel processing with configurable workers
- Metadata enrichment and normalization

**Key Features:**
- Automated extraction of publication metadata (title, URL, identifiers)
- Intelligent text segmentation with configurable chunk sizes
- Fault-tolerant processing with comprehensive error handling

### 2. Knowledge Extraction Engine

**Capabilities:**
- Entity recognition for scientific concepts (organisms, processes, environments)
- Relationship extraction using structured LLM outputs
- Pydantic schema validation for data quality assurance

**Entity Types:**
- Organisms, Biological Processes, Environments, Biomolecules, Technologies, Locations

**Relationship Types:**
- Causal effects, inhibition, measurement contexts, mitigation strategies

### 3. Multi-Modal Storage Layer

#### Knowledge Graph (Neo4j)
- Stores semantic relationships and factual triples
- Supports complex graph queries and network analysis
- Maintains provenance metadata and source attribution

#### Vector Store (ChromaDB)
- Semantic embeddings using Granite-30M model
- Hybrid search capabilities combining KG and vector retrieval
- Configurable similarity metrics and filtering

### 4. Intelligent Query Processing

**Hybrid RAG Agent:**
- Dynamic query routing based on intent classification
- Knowledge graph reasoning for relationship-based queries
- Vector similarity search for contextual information
- Response synthesis with source attribution

**Query Classification:**
- Relationship queries → Knowledge Graph prioritization
- Descriptive queries → Vector Store retrieval
- Complex queries → Hybrid approach

## Core Features

### Interactive Dashboard
- **Hybrid RAG Chat Interface:** Natural language querying with explainable responses
- **Knowledge Graph Explorer:** Visual network analysis and entity relationship mapping
- **Research Analytics:** Entity distribution and relationship pattern visualization
- **Gap Analysis:** Identification of under-researched areas using centrality metrics

### Explainable AI (XAI) Capabilities
- Source traceability with direct links to original publications
- Retrieval path visualization showing KG vs. vector store contributions
- Confidence scoring and evidence highlighting
- Research coverage estimation for entities

### Research Intelligence
- Topic modeling using BERTopic for emerging research themes
- Network centrality analysis to identify key biological mechanisms
- Investment gap detection combining publication volume and network importance
- Priority scoring for research recommendations

## Technical Implementation

### Backend Infrastructure
- **Language:** Python 3.11
- **Data Processing:** Pandas, LangChain, Pydantic
- **ML/NLP:** Sentence Transformers, BERTopic, spaCy
- **Graph Database:** Neo4j with Cypher query language
- **Vector Database:** ChromaDB with Granite embeddings
- **Web Framework:** Plotly Dash with Bootstrap components

### Deployment Requirements
- **Compute:** High-VRAM GPU for LLM inference, multi-core CPU for parallel processing
- **Storage:** Persistent graph database and vector store
- **Dependencies:** Comprehensive Python ecosystem with scientific computing libraries

## Usage Scenarios

### For Research Scientists
- Explore biological mechanisms through multi-hop reasoning
- Identify relevant studies and experimental data
- Formulate hypotheses based on existing knowledge

### For Program Managers
- Assess research portfolio coverage and gaps
- Evaluate funding allocation effectiveness
- Identify emerging research priorities

### For Mission Architects
- Evaluate biological risks for long-duration spaceflight
- Assess countermeasure effectiveness across multiple studies
- Plan integrated research strategies

---

## Impact and Future Development

BodhiRAG provides a scalable, explainable platform that transforms disconnected space biology research into an interconnected knowledge ecosystem. The platform enables:

- **Accelerated Discovery:** Reduced time from question to insight through intelligent retrieval
- **Strategic Planning:** Data-driven research investment decisions
- **Collaborative Science:** Shared understanding of the space biology landscape
- **Mission Readiness:** Comprehensive risk assessment and mitigation planning

Future enhancements include integration with real-time experimental data, federated learning capabilities, and expanded domain coverage to encompass the full spectrum of space life sciences.

---
