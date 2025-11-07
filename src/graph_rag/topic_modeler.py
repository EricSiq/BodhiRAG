#BodhiRAG-main\src\graph_rag\topic_modeler.py
"""
Topic Modeling and Research Gap Analysis
Uses BERTopic for clustering and NetworkX for centrality analysis
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
import networkx as nx
from sentence_transformers import SentenceTransformer
import logging
from collections import Counter

class TopicModeler:
    def __init__(self):
        self.topic_model = None
        self.embedding_model = None
        self.logger = logging.getLogger(__name__)
    
    def initialize_model(self):
        """Initialize BERTopic model with optimized parameters for scientific text"""
        try:
            # Use smaller model for efficiency
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Custom vectorizer for scientific terms
            vectorizer = CountVectorizer(
                ngram_range=(1, 2),
                max_features=5000,
                stop_words='english'
            )
            
            self.topic_model = BERTopic(
                embedding_model=self.embedding_model,
                vectorizer_model=vectorizer,
                min_topic_size=5,
                verbose=True
            )
            
            self.logger.info("✅ BERTopic model initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize topic model: {e}")
            return False
    
    def fit_topics(self, documents: List[str]) -> Dict[str, Any]:
        """Fit topic model to documents and return topic analysis"""
        if not self.topic_model:
            self.initialize_model()
        
        try:
            # Fit the model
            topics, probabilities = self.topic_model.fit_transform(documents)
            
            # Get topic information
            return {
                "topics": topics,
                "probabilities": probabilities,
                "topic_info": self.topic_model.get_topic_info().to_dict('records'),
                "topic_terms": self._get_topic_terms(),
                "topic_sizes": self._get_topic_sizes(topics)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Topic modeling failed: {e}")
            return {"error": str(e)}
    
    def _get_topic_terms(self, n_terms: int = 10) -> Dict[int, List[Tuple[str, float]]]:
        """Get top terms for each topic"""
        topic_terms = {}
        for topic_num in range(len(self.topic_model.get_topic_info())):
            terms = self.topic_model.get_topic(topic_num)
            if terms:  # Skip outlier topic (-1)
                topic_terms[topic_num] = terms[:n_terms]
        return topic_terms
    
    def _get_topic_sizes(self, topics: List[int]) -> Dict[int, int]:
        """Get size (document count) for each topic"""
        return dict(Counter(topics))

class ResearchGapAnalyzer:
    def __init__(self, kg_connector, topic_modeler):
        self.kg_connector = kg_connector
        self.topic_modeler = topic_modeler
        self.logger = logging.getLogger(__name__)
    
    def calculate_centrality_scores(self) -> Dict[str, float]:
        """Calculate network centrality scores for entities"""
        try:
            # Get graph statistics
            stats = self.kg_connector.export_graph_stats()
            
            # Build network for centrality calculation
            G = nx.Graph()
            
            # Add entities as nodes
            if 'most_connected_entities' in stats:
                for entity_data in stats['most_connected_entities']:
                    G.add_node(
                        entity_data['entity'],
                        entity_type=entity_data['type'],
                        degree=entity_data['degree']
                    )
            
            # Calculate centrality measures
            centrality_scores = {}
            
            if G.number_of_nodes() > 0:
                # Degree centrality
                degree_centrality = nx.degree_centrality(G)
                
                # Betweenness centrality (if graph is large enough)
                if G.number_of_nodes() > 10:
                    betweenness_centrality = nx.betweenness_centrality(G, k=min(50, G.number_of_nodes()))
                else:
                    betweenness_centrality = {node: 0 for node in G.nodes()}
                
                # Combine scores
                for node in G.nodes():
                    centrality_scores[node] = {
                        'degree_centrality': degree_centrality.get(node, 0),
                        'betweenness_centrality': betweenness_centrality.get(node, 0),
                        'combined_score': (
                            degree_centrality.get(node, 0) * 0.6 +
                            betweenness_centrality.get(node, 0) * 0.4
                        )
                    }
            
            return centrality_scores
            
        except Exception as e:
            self.logger.error(f"❌ Centrality calculation failed: {e}")
            return {}
    
    def identify_research_gaps(self, 
                             topics_data: Dict[str, Any],
                             centrality_scores: Dict[str, float],
                             min_topic_size: int = 10) -> List[Dict[str, Any]]:
        """Identify research gaps using topic prevalence and network centrality"""
        
        gaps = []
        
        try:
            # Analyze topic distribution
            topic_sizes = topics_data.get('topic_sizes', {})
            topic_terms = topics_data.get('topic_terms', {})
            
            # Find underrepresented topics (small topic size)
            total_docs = sum(topic_sizes.values())
            underrepresented_topics = []
            
            for topic_id, size in topic_sizes.items():
                if topic_id != -1:  # Skip outliers
                    topic_proportion = size / total_docs
                    if topic_proportion < 0.05:  # Less than 5% of documents
                        underrepresented_topics.append({
                            'topic_id': topic_id,
                            'size': size,
                            'proportion': topic_proportion,
                            'terms': topic_terms.get(topic_id, [])
                        })
            
            # Find high-centrality entities with low research coverage
            high_centrality_entities = []
            for entity, scores in centrality_scores.items():
                if scores['combined_score'] > 0.1:  # High centrality threshold
                    high_centrality_entities.append({
                        'entity': entity,
                        'centrality_score': scores['combined_score'],
                        'research_coverage': self._estimate_research_coverage(entity)
                    })
            
            # Generate gap analysis
            for topic in underrepresented_topics[:5]:  # Top 5 underrepresented
                gaps.append({
                    'type': 'underrepresented_topic',
                    'description': f"Topic with terms {[term[0] for term in topic['terms'][:3]]} is underrepresented",
                    'evidence': f"Only {topic['size']} documents ({topic['proportion']:.1%} of corpus)",
                    'priority_score': 0.7,
                    'suggested_research': f"Expand research on {topic['terms'][0][0]} in space environments"
                })
            
            for entity in high_centrality_entities[:5]:
                if entity['research_coverage'] < 0.3:  # Low coverage threshold
                    gaps.append({
                        'type': 'high_centrality_low_coverage',
                        'description': f"Entity '{entity['entity']}' is central but under-researched",
                        'evidence': f"Centrality score: {entity['centrality_score']:.3f}, Coverage: {entity['research_coverage']:.1%}",
                        'priority_score': 0.8,
                        'suggested_research': f"Focus studies on {entity['entity']} mechanisms in microgravity"
                    })
            
            # Sort by priority
            gaps.sort(key=lambda x: x['priority_score'], reverse=True)
            
            return gaps
            
        except Exception as e:
            self.logger.error(f"❌ Research gap analysis failed: {e}")
            return []
    
    def _estimate_research_coverage(self, entity: str) -> float:
        """Estimate research coverage for an entity (simplified)"""
        try:
            # Query relationships for this entity
            relationships = self.kg_connector.query_relationships(entity)
            
            # Simple coverage estimate based on relationship count
            if len(relationships) > 10:
                return 1.0
            elif len(relationships) > 5:
                return 0.7
            elif len(relationships) > 2:
                return 0.4
            else:
                return 0.1
                
        except:
            return 0.0
    
    def generate_gap_report(self, gaps: List[Dict[str, Any]]) -> str:
        """Generate a human-readable research gap report"""
        
        if not gaps:
            return "No significant research gaps identified based on current analysis."
        
        report = "🔬 NASA SPACE BIOLOGY RESEARCH GAP ANALYSIS\n"
        report += "=" * 50 + "\n\n"
        
        for i, gap in enumerate(gaps, 1):
            report += f"{i}. {gap['description']}\n"
            report += f"   📊 Evidence: {gap['evidence']}\n"
            report += f"   🎯 Priority: {gap['priority_score']:.1f}/1.0\n"
            report += f"   💡 Suggestion: {gap['suggested_research']}\n\n"
        
        report += f"Total gaps identified: {len(gaps)}"
        return report