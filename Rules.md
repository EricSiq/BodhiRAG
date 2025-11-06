
# BodhiRAG Quality Rules & Development Standards

## 🎯 Code Quality & Architecture

### Modular Design Principles
```
✅ Each module must have single responsibility
✅ Clear separation between data, business logic, and presentation layers
✅ Configurable components with dependency injection patterns
✅ Interface segregation for database connectors
```

### Python Development Standards
```python
# REQUIRED PATTERNS
# Type hints for all function signatures
def process_document(chunk_size: int = 512) -> List[Document]:
    """Clear docstrings with Google-style format."""
    
# Context managers for resource handling
with ThreadPoolExecutor(max_workers=8) as executor:
    results = list(executor.map(process, documents))
    
# Pydantic models for data validation
class ResearchEntity(BaseModel):
    entity_type: Literal["Organism", "Environment", "Biological_Process"]
    name: str
    evidence_span: str
    source_url: str
```

### Error Handling & Resilience
```
✅ Comprehensive try-catch blocks with specific exceptions
✅ Logging at appropriate levels (DEBUG, INFO, WARNING, ERROR)
✅ Retry mechanisms with exponential backoff for external services
✅ Graceful degradation when secondary services are unavailable
```

## 🔧 NASA-Specific Requirements

### Data Processing Excellence
```
✅ Parallel processing with configurable worker counts
✅ Memory optimization for large document batches (607+ papers)
✅ Intermediate checkpointing for pipeline resilience
✅ Source URL preservation and traceability
```

### Knowledge Graph Quality
```
✅ Entity type validation against predefined schema
✅ Relationship evidence spans with source attribution
✅ Constraint enforcement to prevent duplicate entities
✅ Network centrality calculations for analytics
```

### Vector Database Standards
```
✅ Consistent embedding model across all documents
✅ Metadata filtering capabilities for targeted retrieval
✅ Collection statistics monitoring
✅ Semantic similarity scoring with configurable thresholds
```

## 🚀 Performance & Scalability

### Processing Optimization
```python
# REQUIRED: Batch processing for large datasets
def process_batch(documents: List[Document], batch_size: int = 50):
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        yield from process_documents_parallel(batch)

# REQUIRED: Async operations for I/O bound tasks
async def async_embed_documents(docs: List[Document]):
    tasks = [embed_document_async(doc) for doc in docs]
    return await asyncio.gather(*tasks)
```

### Memory Management
```
✅ Stream processing for large files (>10MB)
✅ Garbage collection awareness in long-running processes
✅ Connection pooling for database interactions
✅ Chunk size optimization based on content type
```

## 🎨 Dashboard & UX Standards

### Plotly Dash Conventions
```python
# REQUIRED: Dark theme consistency
app = Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

# REQUIRED: Bootstrap component integration
layout = dbc.Container([
    dbc.Row([
        dbc.Col([component], width=6)
    ], className="mb-4")
])

# REQUIRED: Callback error handling
@app.callback(
    Output('results', 'children'),
    [Input('query', 'value')],
    prevent_initial_call=True
)
def update_results(query):
    try:
        return process_query(query)
    except Exception as e:
        return dbc.Alert(f"Error: {str(e)}", color="danger")
```

### Interactive Features
```
✅ Real-time query classification display
✅ KG relationship visualization with interactive nodes
✅ Source document tracking with clickable URLs
✅ Example queries for user guidance
```

## 🔍 Testing & Validation

### Test Coverage Requirements
```
✅ Unit tests for all data processing functions (min 80% coverage)
✅ Integration tests for database connectors
✅ End-to-end tests for complete query pipeline
✅ Performance benchmarks for critical paths
```

### Data Validation Rules
```python
# REQUIRED: Input validation decorators
@validate_input
def add_to_knowledge_graph(entity: ResearchEntity) -> bool:
    # Validation logic here
    pass

# REQUIRED: Output validation
def validate_graph_response(response: Dict) -> bool:
    required_fields = ['entities', 'relationships', 'sources']
    return all(field in response for field in required_fields)
```

## 📊 Analytics & Monitoring

### Research Analytics Standards
```
✅ BERTopic modeling with consistent hyperparameters
✅ Centrality calculations using standardized algorithms
✅ Gap analysis with reproducible scoring methodology
✅ Visualization consistency across all charts
```

### Logging & Observability
```python
# REQUIRED: Structured logging
import structlog
logger = structlog.get_logger()

def process_document(doc: Document):
    logger.info("processing_document", 
                doc_id=doc.id, 
                chunk_count=len(doc.chunks))
    
# REQUIRED: Performance metrics
@timed
def hybrid_search(query: str, top_k: int = 10):
    start_time = time.time()
    # Search logic
    duration = time.time() - start_time
    metrics.record_search_duration(duration)
```

## 🔒 Security & Data Integrity

### NASA Data Handling
```
✅ No hardcoded credentials - use environment variables
✅ Input sanitization for all user queries
✅ Rate limiting on API endpoints
✅ Data encryption at rest for sensitive metadata
```

### Source Attribution
```
✅ All KG relationships must include source evidence
✅ Vector search results must reference original documents
✅ Direct links to NASA publication URLs
✅ Clear provenance tracking in analytics
```

## 🛠 Deployment & Operations

### One-Click Deployment Standards
```bash
# REQUIRED: Environment setup script
#!/bin/bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# REQUIRED: Database initialization
python scripts/init_databases.py

# REQUIRED: Health checks
python scripts/health_check.py
```

### Configuration Management
```python
# REQUIRED: Environment-based configuration
@dataclass
class Config:
    neo4j_url: str = os.getenv('NEO4J_URL', 'bolt://localhost:7687')
    chroma_path: str = os.getenv('CHROMA_PATH', './chroma_db')
    max_workers: int = int(os.getenv('MAX_WORKERS', '8'))
```

## 📈 Quality Gates

### Pre-commit Requirements
```
✅ Code formatting with Black and isort
✅ Type checking with MyPy
✅ Linting with Flake8 and Pylint
✅ Security scanning with Bandit
✅ Test execution with pytest
```

### Performance Thresholds
```
✅ Document processing: < 2 seconds per document avg
✅ Query response: < 3 seconds for complex hybrid queries
✅ Dashboard load: < 2 seconds for initial render
✅ Knowledge graph queries: < 1 second for 3-hop reasoning
```

## 🔄 Maintenance & Evolution

### Code Documentation
```
✅ README.md with setup and usage instructions
✅ API documentation for all public functions
✅ Architecture decision records (ADRs)
✅ Data schema documentation with examples
```

### Future-Proofing
```
✅ Granite model compatibility layer
✅ Modular architecture for easy component replacement
✅ Configuration-driven feature toggles
✅ Backward compatibility for data migrations
```

---

*These quality rules ensure BodhiRAG maintains production-grade reliability while enabling rapid development and NASA-compliance.*
```

This quality rules file provides comprehensive guidelines covering all aspects of the BodhiRAG project development. You can append this to your project documentation or use it as a checklist during development and code reviews.
