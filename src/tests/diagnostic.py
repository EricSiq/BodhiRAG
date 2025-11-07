# diagnostic.py
import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def main():
    print("🔍 Running BodhiRAG Diagnostic...")
    
    # Test 1: Import RAG service
    try:
        from src.services.rag_service import HybridRAGService
        print("✅ RAG Service imports successfully")
    except Exception as e:
        print(f"❌ RAG Service import failed: {e}")
        return
    
    # Test 2: Initialize RAG service
    try:
        service = HybridRAGService()
        print("✅ RAG Service initialized")
    except Exception as e:
        print(f"❌ RAG Service initialization failed: {e}")
        return
    
    # Test 3: Test a query
    try:
        result = await service.process_query(
            query="What causes bone loss in space?",
            use_kg=True,
            use_vector=True,
            mobile_optimized=True
        )
        print("✅ RAG Service processed query")
        print(f"Answer: {result['answer']}")
        print(f"Sources: {result['sources']}")
        print(f"Entity Relationships: {result['entity_relationships']}")
    except Exception as e:
        print(f"❌ RAG Service query failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())