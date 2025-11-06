

"""
Database Setup Script for BodhiRAG
Initializes Neo4j constraints, indexes, and validates connections
Run this BEFORE running the main pipeline
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.graph_rag import KnowledgeGraphConnector, VectorStoreConnector
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self):
        self.kg_connector = KnowledgeGraphConnector()
        self.vs_connector = VectorStoreConnector()
    
    def setup_knowledge_graph(self):
        """Initialize Neo4j database with constraints and indexes"""
        logger.info("Setting up Knowledge Graph Database...")
        
        try:
            # Connect to Neo4j
            if not self.kg_connector.connect():
                logger.error("Failed to connect to Neo4j. Please ensure:")
                logger.error("   - Neo4j is running on bolt://localhost:7687")
                logger.error("   - Credentials are set in environment variables")
                logger.error("   - Database is accessible")
                return False
            
            # Initialize schema (constraints and indexes)
            self.kg_connector.initialize_schema()
            
            # Verify setup
            stats = self.kg_connector.export_graph_stats()
            logger.info(f"Knowledge Graph setup complete")
            logger.info(f"   - Database: {self.kg_connector.uri}")
            logger.info(f"   - Constraints/indexes created successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Knowledge Graph setup failed: {e}")
            return False
    
    def setup_vector_store(self):
        """Initialize ChromaDB vector store"""
        logger.info("Setting up Vector Store...")
        
        try:
            # Initialize ChromaDB
            if not self.vs_connector.initialize_store():
                logger.error("Failed to initialize Vector Store")
                return False
            
            # Verify setup
            stats = self.vs_connector.get_collection_stats()
            logger.info(f"Vector Store setup complete")
            logger.info(f"   - Persistence: {self.vs_connector.persist_directory}")
            logger.info(f"   - Collection: nasa_publications")
            
            return True
            
        except Exception as e:
            logger.error(f"Vector Store setup failed: {e}")
            return False
    
    def validate_connections(self):
        """Validate all database connections are working"""
        logger.info("Validating database connections...")
        
        results = {
            'neo4j': False,
            'chromadb': False
        }
        
        # Test Neo4j connection
        try:
            if self.kg_connector.connect():
                # Test a simple query
                with self.kg_connector.driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    if result.single()["test"] == 1:
                        results['neo4j'] = True
                        logger.info("Neo4j connection: HEALTHY")
            else:
                logger.error("Neo4j connection: FAILED")
        except Exception as e:
            logger.error(f"Neo4j connection: FAILED - {e}")
        
        # Test ChromaDB connection
        try:
            if self.vs_connector.initialize_store():
                stats = self.vs_connector.get_collection_stats()
                if 'error' not in stats:
                    results['chromadb'] = True
                    logger.info("ChromaDB connection: HEALTHY")
            else:
                logger.error("ChromaDB connection: FAILED")
        except Exception as e:
            logger.error(f"ChromaDB connection: FAILED - {e}")
        
        return results
    
    def cleanup_test_data(self):
        """Clean up any test data (optional - for development)"""
        logger.info("Cleaning up test data...")
        
        try:
            if self.kg_connector.connect():
                # Remove all test entities (you might want to be more selective)
                with self.kg_connector.driver.session() as session:
                    session.run("MATCH (n) DETACH DELETE n")
                logger.info("Test data cleaned from Knowledge Graph")
            
            # For ChromaDB, the setup script will recreate the collection
            logger.info(" Vector Store ready for new data")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def run_complete_setup(self, cleanup=False):
        """Run the complete database setup process"""
        logger.info("Starting BodhiRAG Database Setup")
        logger.info("=" * 50)
        
        # Step 1: Validate connections
        connection_status = self.validate_connections()
        
        if not any(connection_status.values()):
            logger.error("No database connections available. Please check:")
            logger.error("   - Neo4j installation and running status")
            logger.error("   - ChromaDB dependencies")
            return False
        
        # Step 2: Cleanup if requested
        if cleanup:
            self.cleanup_test_data()
        
        # Step 3: Setup Knowledge Graph
        if connection_status['neo4j']:
            kg_success = self.setup_knowledge_graph()
        else:
            kg_success = False
            logger.warning("Skipping Knowledge Graph setup (connection failed)")
        
        # Step 4: Setup Vector Store
        if connection_status['chromadb']:
            vs_success = self.setup_vector_store()
        else:
            vs_success = False
            logger.warning("Skipping Vector Store setup (connection failed)")
        
        # Step 5: Summary
        logger.info("=" * 50)
        logger.info("SETUP SUMMARY:")
        logger.info(f"   Knowledge Graph: {'READY' if kg_success else '❌ FAILED'}")
        logger.info(f"   Vector Store: {'READY' if vs_success else '❌ FAILED'}")
        
        if kg_success or vs_success:
            logger.info("Setup completed successfully!")
            logger.info("   Next: Run 'python scripts/run_pipeline.py' to process NASA data")
            return True
        else:
            logger.error("Setup failed. Please check the errors above.")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='BodhiRAG Database Setup')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Clean up existing data before setup')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate connections, do not setup')
    
    args = parser.parse_args()
    
    setup = DatabaseSetup()
    
    if args.validate_only:
        setup.validate_connections()
    else:
        setup.run_complete_setup(cleanup=args.cleanup)

if __name__ == "__main__":
    main()
