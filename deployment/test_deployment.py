"""
Test script for BodhiRAG deployment
Validates all components before deployment
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from src.data_ingestion import load_and_chunk_documents, extract_knowledge_from_chunk
        print("  ✓ data_ingestion module")
    except Exception as e:
        print(f"  ✗ data_ingestion module: {e}")
        return False
    
    try:
        from src.graph_rag.graph_connector import KnowledgeGraphConnector
        print("  ✓ graph_connector module")
    except Exception as e:
        print(f"  ✗ graph_connector module: {e}")
        return False
    
    try:
        from src.graph_rag.vector_connector import VectorStoreConnector
        print("  ✓ vector_connector module")
    except Exception as e:
        print(f"  ✗ vector_connector module: {e}")
        return False
    
    try:
        from src.graph_rag.agent_router import HybridRAGAgent
        print("  ✓ agent_router module")
    except Exception as e:
        print(f"  ✗ agent_router module: {e}")
        return False
    
    return True

def test_connectors():
    """Test connector initialization"""
    print("\nTesting connectors...")
    
    try:
        from src.graph_rag.graph_connector import KnowledgeGraphConnector
        kg = KnowledgeGraphConnector()
        print("  ✓ KnowledgeGraphConnector initialized")
    except Exception as e:
        print(f"  ✗ KnowledgeGraphConnector: {e}")
        return False
    
    try:
        from src.graph_rag.vector_connector import VectorStoreConnector
        vs = VectorStoreConnector()
        print("  ✓ VectorStoreConnector initialized")
    except Exception as e:
        print(f"  ✗ VectorStoreConnector: {e}")
        return False
    
    return True

def test_agent():
    """Test agent initialization"""
    print("\nTesting agent...")
    
    try:
        from src.graph_rag.graph_connector import KnowledgeGraphConnector
        from src.graph_rag.vector_connector import VectorStoreConnector
        from src.graph_rag.agent_router import HybridRAGAgent
        
        kg = KnowledgeGraphConnector()
        vs = VectorStoreConnector()
        agent = HybridRAGAgent(kg, vs)
        
        print("  ✓ HybridRAGAgent initialized")
        
        # Test query classification
        query_type = agent.classify_query_intent("What causes bone loss?")
        print(f"  ✓ Query classification: {query_type}")
        
        return True
    except Exception as e:
        print(f"  ✗ Agent test failed: {e}")
        return False

def test_deployment_files():
    """Test that deployment files exist"""
    print("\nTesting deployment files...")
    
    deploy_dir = project_root / "deployment"
    required_files = [
        "huggingface_deploy.py",
        "DEPLOYMENT_GUIDE.md",
        "MODEL_CARD.md",
        "Dockerfile",
        "docker-compose.yml",
        "deploy.bat"
    ]
    
    all_exist = True
    for file in required_files:
        file_path = deploy_dir / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} missing")
            all_exist = False
    
    return all_exist

def test_mock_query():
    """Test a mock query end-to-end"""
    print("\nTesting mock query...")
    
    try:
        from src.graph_rag.graph_connector import KnowledgeGraphConnector
        from src.graph_rag.vector_connector import VectorStoreConnector
        from src.graph_rag.agent_router import HybridRAGAgent
        
        kg = KnowledgeGraphConnector()
        vs = VectorStoreConnector()
        agent = HybridRAGAgent(kg, vs)
        
        # Test query without actual database connections
        query = "What causes bone loss in space?"
        query_type = agent.classify_query_intent(query)
        
        print(f"  ✓ Query: {query}")
        print(f"  ✓ Classified as: {query_type}")
        
        return True
    except Exception as e:
        print(f"  ✗ Mock query failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("BodhiRAG Deployment Tests")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Connectors", test_connectors),
        ("Agent", test_agent),
        ("Deployment Files", test_deployment_files),
        ("Mock Query", test_mock_query)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! Ready for deployment.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Fix issues before deploying.")
        return 