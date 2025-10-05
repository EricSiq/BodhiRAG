
"""
Hybrid RAG Agent using LangGraph for dynamic query routing
Combines Knowledge Graph reasoning with Vector Store retrieval
"""

from typing import Dict, List, Any, Optional, TypedDict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
import logging

class RouterState(TypedDict):
    """State definition for the LangGraph router"""
    query: str
    query_type: str
    kg_results: List[Dict]
    vs_results: List[Dict] 
    final_answer: str
    reasoning_path: List[str]

class HybridRAGAgent:
    def __init__(self, kg_connector, vs_connector):
        self.kg_connector = kg_connector
        self.vs_connector = vs_connector
        self.logger = logging.getLogger(__name__)
        
        # Define query classification patterns
        self.kg_query_patterns = [
            'relationship', 'effect', 'cause', 'impact', 'influence',
            'how does', 'what causes', 'what affects', 'mechanism',
            'interaction', 'pathway', 'network'
        ]
        
        self.vs_query_patterns = [
            'describe', 'what is', 'explain', 'overview', 'summary',
            'information about', 'details about', 'tell me about'
        ]
    
    def classify_query_intent(self, query: str) -> str:
        """Classify query intent to determine best retrieval strategy"""
        query_lower = query.lower()
        
        # Check for KG patterns (relationship queries)
        if any(pattern in query_lower for pattern in self.kg_query_patterns):
            return "kg_primary"
        
        # Check for VS patterns (descriptive queries)  
        elif any(pattern in query_lower for pattern in self.vs_query_patterns):
            return "vs_primary"
        
        # Default to hybrid approach
        else:
            return "hybrid"
    
    def execute_kg_retrieval(self, query: str) -> List[Dict]:
        # Execute knowledge graph retrieval
        try:
            # Extract entity names from query (simplified)
            entities = self._extract_entities_from_query(query)
            
            kg_results = []
            for entity in entities:
                # Get relationships for this entity
                relationships = self.kg_connector.query_relationships(entity)
                kg_results.extend(relationships)
            
            self.logger.info(f"🔗 KG retrieval found {len(kg_results)} relationships")
            return kg_results
            
        except Exception as e:
            self.logger.error(f"❌ KG retrieval failed: {e}")
            return []
    
    def execute_vs_retrieval(self, query: str, n_results: int = 5) -> List[Dict]:
        # Execute vector store retrieval
        try:
            vs_results = self.vs_connector.semantic_search(query, n_results)
            self.logger.info(f"🔍 VS retrieval found {len(vs_results)} documents")
            return vs_results
        except Exception as e:
            self.logger.error(f"❌ VS retrieval failed: {e}")
            return []
    
    def _extract_entities_from_query(self, query: str) -> List[str]:
        # Simple entity extraction from query (in production, use NER)
        # Common NASA biology entities
        common_entities = [
            'microgravity', 'radiation', 'bone loss', 'muscle atrophy', 
            'oxidative stress', 'stem cells', 'immune system', 'cardiovascular',
            'neurovestibular', 'tissue regeneration', 'gene expression'
        ]
        
        query_lower = query.lower()
        found_entities = []
        
        for entity in common_entities:
            if entity in query_lower:
                found_entities.append(entity.title())
        
        return found_entities if found_entities else ['Space Biology']  # Fallback
    
    def generate_answer(self, query: str, kg_results: List[Dict], vs_results: List[Dict]) -> str:
       # Generate final answer by synthesizing KG and VS results
        
        # Build context from KG results
        kg_context = ""
        if kg_results:
            kg_context = "RELATIONSHIPS:\n"
            for i, rel in enumerate(kg_results[:5], 1):
                kg_context += f"{i}. {rel['subject']} → {rel['relationship']} → {rel['object']}\n"
                if rel.get('evidence'):
                    kg_context += f"   Evidence: {rel['evidence'][:100]}...\n"
        
        # Build context from VS results  
        vs_context = ""
        if vs_results:
            vs_context = "DOCUMENT CONTEXT:\n"
            for i, doc in enumerate(vs_results[:3], 1):
                vs_context += f"{i}. {doc['content'][:200]}...\n"
                if doc['metadata'].get('source_title'):
                    vs_context += f"   Source: {doc['metadata']['source_title']}\n"
        
        # Generate answer using template (simplified - in production, use LLM)
        if kg_results and vs_results:
            answer = f"""Based on NASA space biology research:

{kg_context}

Additional context from scientific publications:
{vs_context}

This suggests that {query} involves complex biological mechanisms that are actively being researched in space environments."""
        
        elif kg_results:
            answer = f"""Based on known relationships in space biology:

{kg_context}

These relationships demonstrate how {query} operates in microgravity environments."""
        
        elif vs_results:
            answer = f"""Based on NASA research publications:

{vs_context}

The research indicates that {query} is an important area of study for long-duration space missions."""
        
        else:
            answer = f"I couldn't find specific information about '{query}' in the NASA space biology knowledge base. This might be an emerging research area."
        
        return answer
    
    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Main query interface - routes to appropriate retrieval strategy
        and synthesizes results
        """
        self.logger.info(f"Processing query: {user_query}")
        
        # Step 1: Classify query intent
        query_type = self.classify_query_intent(user_query)
        self.logger.info(f"Query classified as: {query_type}")
        
        # Step 2: Execute retrieval based on intent
        kg_results = []
        vs_results = []
        
        if query_type in ["kg_primary", "hybrid"]:
            kg_results = self.execute_kg_retrieval(user_query)
        
        if query_type in ["vs_primary", "hybrid"]:
            vs_results = self.execute_vs_retrieval(user_query)
        
        # Step 3: Generate final answer
        final_answer = self.generate_answer(user_query, kg_results, vs_results)
        
        # Step 4: Return comprehensive results
        return {
            "query": user_query,
            "query_type": query_type,
            "kg_results": kg_results,
            "vs_results": vs_results,
            "final_answer": final_answer,
            "retrieval_stats": {
                "kg_relationships": len(kg_results),
                "vs_documents": len(vs_results)
            }
        }