
"""
Neo4j Knowledge Graph Connector
Handles entity and relationship persistence with XAI metadata
"""

import os
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, basic_auth
import logging

from ..data_ingestion.knowledge_extractor import RelationshipTriple

class KnowledgeGraphConnector:
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = None
        self.logger = logging.getLogger(__name__)
    
    def connect(self):
        #Establish connection to Neo4j database
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=basic_auth(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info("✅ Successfully connected to Neo4j")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        # Close database connection
        if self.driver:
            self.driver.close()
            self.logger.info("🔌 Neo4j connection closed")
    
    def initialize_schema(self):
        """Create constraints and indexes for optimal performance"""
        constraints_queries = [
            "CREATE CONSTRAINT entity_name IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
            "CREATE CONSTRAINT entity_type IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_type IS NOT NULL",
            "CREATE INDEX entity_type_index IF NOT EXISTS FOR (e:Entity) ON (e.entity_type)",
            "CREATE INDEX relationship_type IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.relationship)",
        ]
        
        with self.driver.session() as session:
            for query in constraints_queries:
                try:
                    session.run(query)
                    self.logger.info(f"Created constraint/index: {query[:50]}...")
                except Exception as e:
                    self.logger.warning(f"Could not create constraint: {e}")
    
    def populate_graph(self, triples: List[RelationshipTriple]) -> Dict[str, int]:
        """
        Populate knowledge graph with entities and relationships
        Uses MERGE to avoid duplicates
        """
        if not self.driver:
            self.connect()
        
        entity_count = 0
        relationship_count = 0
        
        with self.driver.session() as session:
            # Process all triples
            for triple in triples:
                try:
                    # Convert Pydantic model to dict if needed
                    if hasattr(triple, 'dict'):
                        triple_data = triple.dict()
                    else:
                        triple_data = triple
                    
                    # Create/Merge entities and relationship
                    query = """
                    MERGE (subject:Entity {name: $subject_name})
                    SET subject.entity_type = $subject_type,
                        subject.last_updated = timestamp()
                    
                    MERGE (object:Entity {name: $object_name})  
                    SET object.entity_type = $object_type,
                        object.last_updated = timestamp()
                    
                    MERGE (subject)-[r:RELATES_TO {relationship: $rel_type}]->(object)
                    SET r.evidence = $evidence,
                        r.source_title = $source_title,
                        r.source_url = $source_url, 
                        r.doc_id = $doc_id,
                        r.confidence = 0.9,
                        r.created_at = timestamp()
                    """
                    
                    # Extract entity types (simplified - in production, you'd have entity type mapping)
                    subject_type = self._infer_entity_type(triple_data['subject'])
                    object_type = self._infer_entity_type(triple_data['object'])
                    
                    parameters = {
                        'subject_name': triple_data['subject'],
                        'subject_type': subject_type,
                        'object_name': triple_data['object'], 
                        'object_type': object_type,
                        'rel_type': triple_data['relationship'],
                        'evidence': triple_data.get('evidence_span', ''),
                        'source_title': triple_data.get('source_title', ''),
                        'source_url': triple_data.get('source_url', ''),
                        'doc_id': triple_data.get('doc_id', '')
                    }
                    
                    result = session.run(query, parameters)
                    relationship_count += 1
                    entity_count += 2  # Subject and object
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to process triple: {triple_data} - Error: {e}")
                    continue
            
            # Count actual entities (avoiding double counting)
            count_query = "MATCH (e:Entity) RETURN count(e) as entity_count"
            actual_entities = session.run(count_query).single()["entity_count"]
            
            count_query = "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as rel_count"
            actual_relationships = session.run(count_query).single()["rel_count"]
        
        return {
            "entities_created": actual_entities,
            "relationships_created": actual_relationships,
            "triples_processed": len(triples)
        }
    
    def _infer_entity_type(self, entity_name: str) -> str:
        # Simple entity type inference based on naming patterns
        entity_lower = entity_name.lower()
        
        if any(word in entity_lower for word in ['microgravity', 'radiation', 'space', 'environment']):
            return "Environment"
        elif any(word in entity_lower for word in ['mouse', 'rat', 'human', 'arabidopsis', 'drosophila']):
            return "Organism" 
        elif any(word in entity_lower for word in ['bone', 'muscle', 'cell', 'tissue', 'gene']):
            return "Biological_Process"
        elif any(word in entity_lower for word in ['protein', 'enzyme', 'molecule', 'dna', 'rna']):
            return "Biomolecule"
        elif any(word in entity_lower for word in ['iss', 'station', 'facility', 'location']):
            return "Location"
        else:
            return "Unknown"
    
    def query_relationships(self, entity_name: str, relationship_type: str = None) -> List[Dict]:
        # Query relationships for a specific entity
        if not self.driver:
            self.connect()
        
        if relationship_type:
            query = """
            MATCH (e:Entity {name: $entity_name})-[r:RELATES_TO {relationship: $rel_type}]->(target)
            RETURN e.name as subject, r.relationship as relationship, target.name as object,
                   r.evidence as evidence, r.source_title as source
            """
            params = {'entity_name': entity_name, 'rel_type': relationship_type}
        else:
            query = """
            MATCH (e:Entity {name: $entity_name})-[r:RELATES_TO]->(target)
            RETURN e.name as subject, r.relationship as relationship, target.name as object,
                   r.evidence as evidence, r.source_title as source
            """
            params = {'entity_name': entity_name}
        
        with self.driver.session() as session:
            results = session.run(query, params)
            return [dict(record) for record in results]
    
    def get_entity_network(self, entity_name: str, depth: int = 2) -> Dict:
        # Get the network around an entity up to specified depth
        if not self.driver:
            self.connect()
        
        query = """
        MATCH path = (start:Entity {name: $entity_name})-[*1..$depth]-(connected)
        UNWIND relationships(path) as rel
        RETURN start.name as central_entity,
               collect(DISTINCT {
                 subject: startNode(rel).name,
                 relationship: rel.relationship, 
                 object: endNode(rel).name,
                 evidence: rel.evidence
               }) as relationships
        """
        
        with self.driver.session() as session:
            result = session.run(query, {'entity_name': entity_name, 'depth': depth})
            return result.single()
    
    def export_graph_stats(self) -> Dict[str, Any]:
        # Export graph statistics for analytics
        if not self.driver:
            self.connect()
        
        stats_queries = {
            "total_entities": "MATCH (e:Entity) RETURN count(e) as count",
            "entity_types": "MATCH (e:Entity) RETURN e.entity_type as type, count(e) as count",
            "relationship_types": "MATCH ()-[r:RELATES_TO]->() RETURN r.relationship as type, count(r) as count",
            "most_connected_entities": """
            MATCH (e:Entity)-[r:RELATES_TO]-()
            RETURN e.name as entity, e.entity_type as type, count(r) as degree
            ORDER BY degree DESC LIMIT 10
            """
        }
        
        stats = {}
        with self.driver.session() as session:
            for stat_name, query in stats_queries.items():
                if "count" in query:
                    result = session.run(query)
                    stats[stat_name] = result.single()["count"]
                else:
                    result = session.run(query)
                    stats[stat_name] = [dict(record) for record in result]
        
        return stats