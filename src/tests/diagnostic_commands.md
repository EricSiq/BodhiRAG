🧪 Run These Diagnostic Commands:
1. Test Database Connections:
bash
# Test Neo4j connection
python -c "
from src.graph_rag.graph_connector import KnowledgeGraphConnector
kg = KnowledgeGraphConnector()
print('Neo4j URI:', kg.uri)
connected = kg.connect()
print('Neo4j Connected:', connected)
if connected:
    stats = kg.export_graph_stats()
    print('Neo4j Stats:', stats)
    kg.close()
"

# Test ChromaDB connection
python -c "
from src.graph_rag.vector_connector import VectorStoreConnector
vs = VectorStoreConnector()
initialized = vs.initialize_store()
print('ChromaDB Initialized:', initialized)
if initialized:
    stats = vs.get_collection_stats()
    print('ChromaDB Stats:', stats)
"
2. Test RAG Service Initialization:
bash
# Test RAG service directly
python -c "
import asyncio
from src.services.rag_service import HybridRAGService

async def test():
    service = HybridRAGService()
    print('RAG Service initialized')
    print('Agent available:', service.agent is not None)
    
    result = await service.process_query('test query', True, True)
    print('Answer preview:', result['answer'][:100])
    
asyncio.run(test())
"
3. Check if Data Exists:
bash
# Check if we have processed data
python -c "
import json
from pathlib import Path

data_dir = Path('./data/processed')
print('Data directory exists:', data_dir.exists())

triple_files = list(data_dir.glob('knowledge_triples_*.json'))
print('Triple files found:', len(triple_files))

if triple_files:
    latest = max(triple_files, key=lambda x: x.stat().st_mtime)
    with open(latest) as f:
        data = json.load(f)
    print('Latest triples file has:', len(data), 'triples')
    if data:
        print('Sample triple:', data[0])
"