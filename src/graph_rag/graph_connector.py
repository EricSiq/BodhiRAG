#BodhiRAG-main\src\graph_rag\graph_connector.py
"""
Neo4j Knowledge Graph Connector
Handles entity and relationship persistence with XAI metadata
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase, basic_auth
import logging

try:
    import networkx as nx
except ImportError:
    nx = None

from src.data_ingestion.knowledge_extractor import RelationshipTriple

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_PRESEEDED_TRIPLES_PATH = _PROJECT_ROOT / "data" / "preseeded_triples.json"

class KnowledgeGraphConnector:
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "")
        self.driver = None
        self.logger = logging.getLogger(__name__)
        self._in_memory_graph = None
        self._in_memory_triples: List[Dict[str, Any]] = []
        self._load_fallback_graph()

    def _load_fallback_graph(self):
        """Build in-memory networkx fallback graph from preseeded triples if available."""
        if _PRESEEDED_TRIPLES_PATH.exists():
            try:
                with open(_PRESEEDED_TRIPLES_PATH, "r", encoding="utf-8") as f:
                    self._in_memory_triples = json.load(f)
                if nx is not None:
                    self._in_memory_graph = nx.MultiDiGraph()
                    for t in self._in_memory_triples:
                        s = t.get("subject", "").strip()
                        o = t.get("object", "").strip()
                        rel = t.get("relationship", "RELATES_TO")
                        ev = t.get("evidence_span", "")
                        if s and o:
                            self._in_memory_graph.add_node(s, entity_type=self._infer_entity_type(s))
                            self._in_memory_graph.add_node(o, entity_type=self._infer_entity_type(o))
                            self._in_memory_graph.add_edge(s, o, relationship=rel, evidence=ev)
                    self.logger.info(
                        f"Initialized in-memory graph fallback with {self._in_memory_graph.number_of_nodes()} nodes "
                        f"and {self._in_memory_graph.number_of_edges()} edges"
                    )
            except Exception as e:
                self.logger.warning(f"Could not load in-memory fallback graph: {e}")
    
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
        if not self.driver:
            self.logger.error("❌ Cannot initialize schema: not connected to Neo4j")
            return

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

        # Counters
        successful_triples = 0
        failed_triples = 0

        with self.driver.session() as session:
            # Process all triples
            for triple in triples:
                try:
                    # Convert Pydantic model to dict if needed
                    if hasattr(triple, 'model_dump'):
                        triple_data = triple.model_dump()
                    elif hasattr(triple, 'dict'):
                        triple_data = triple.dict()
                    else:
                        triple_data = triple

                    # Normalize entity names to title case
                    subject_name = triple_data['subject'].title()
                    object_name = triple_data['object'].title()

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
                    subject_type = self._infer_entity_type(subject_name)
                    object_type = self._infer_entity_type(object_name)

                    parameters = {
                        'subject_name': subject_name,
                        'subject_type': subject_type,
                        'object_name': object_name,
                        'object_type': object_type,
                        'rel_type': triple_data['relationship'],
                        'evidence': triple_data.get('evidence_span', ''),
                        'source_title': triple_data.get('source_title', ''),
                        'source_url': triple_data.get('source_url', ''),
                        'doc_id': triple_data.get('doc_id', '')
                    }

                    session.run(query, parameters)
                    successful_triples += 1

                except Exception as e:
                    self.logger.error(f"❌ Failed to process triple: {triple_data} - Error: {e}")
                    failed_triples += 1
                    continue

            # Count actual entities (avoiding double counting)
            count_query = "MATCH (e:Entity) RETURN count(e) as entity_count"
            actual_entities = session.run(count_query).single()["entity_count"]

            count_query = "MATCH ()-[r:RELATES_TO]->() RETURN count(r) as rel_count"
            actual_relationships = session.run(count_query).single()["rel_count"]

        return {
            "entities_created": actual_entities,
            "relationships_created": actual_relationships,
            "triples_processed": len(triples),
            "successful_triples": successful_triples,
            "failed_triples": failed_triples
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
        """Query relationships for an entity, using Neo4j if available or in-memory graph as fallback."""
        if self.driver:
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
            
            try:
                with self.driver.session() as session:
                    results = session.run(query, params)
                    return [dict(record) for record in results]
            except Exception as e:
                self.logger.warning(f"Neo4j query error: {e}, falling back to in-memory graph")

        # In-memory graph fallback
        results = []
        name_lower = entity_name.lower().strip()
        for t in self._in_memory_triples:
            s = t.get("subject", "")
            o = t.get("object", "")
            rel = t.get("relationship", "RELATES_TO")
            ev = t.get("evidence_span", "")

            # Match subject or object case-insensitively or substring
            if name_lower in s.lower() or name_lower in o.lower():
                if relationship_type is None or relationship_type.lower() == rel.lower():
                    results.append({
                        "subject": s,
                        "relationship": rel,
                        "object": o,
                        "evidence": ev,
                        "source": "NASA Space Biology Corpus",
                    })

        return results[:15]

    def get_entity_network(self, entity_name: str, depth: int = 2) -> Dict:
        """Get the network around an entity up to specified depth with in-memory fallback."""
        if self.driver:
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
            try:
                with self.driver.session() as session:
                    result = session.run(query, {'entity_name': entity_name, 'depth': depth})
                    record = result.single()
                    if record:
                        return dict(record)
            except Exception as e:
                self.logger.warning(f"Neo4j network error: {e}, falling back to in-memory graph")

        # In-memory fallback
        matched_rels = self.query_relationships(entity_name)
        return {
            "central_entity": entity_name,
            "relationships": matched_rels,
        }

    def export_graph_stats(self) -> Dict[str, Any]:
        """Export graph statistics for analytics with in-memory fallback."""
        if self.driver:
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
            try:
                with self.driver.session() as session:
                    for stat_name, query in stats_queries.items():
                        result = session.run(query)
                        if stat_name == "total_entities":
                            record = result.single()
                            stats[stat_name] = record["count"] if record else 0
                        else:
                            stats[stat_name] = [dict(record) for record in result]
                return stats
            except Exception as e:
                self.logger.warning(f"Neo4j stats error: {e}, using in-memory stats")

        # In-memory statistics
        if self._in_memory_graph is not None:
            total_entities = self._in_memory_graph.number_of_nodes()
            degrees = sorted(self._in_memory_graph.degree(), key=lambda x: x[1], reverse=True)[:10]
            most_connected = [
                {"entity": node, "type": self._infer_entity_type(node), "degree": deg}
                for node, deg in degrees
            ]
            rel_counts = {}
            for t in self._in_memory_triples:
                r = t.get("relationship", "RELATES_TO")
                rel_counts[r] = rel_counts.get(r, 0) + 1
            rel_types = [{"type": k, "count": v} for k, v in rel_counts.items()]

            return {
                "total_entities": total_entities,
                "entity_types": [{"type": "Biological_Process", "count": total_entities}],
                "relationship_types": rel_types,
                "most_connected_entities": most_connected,
            }

        return {
            "total_entities": len(self._in_memory_triples) * 2,
            "entity_types": [],
            "relationship_types": [],
            "most_connected_entities": [],
        }