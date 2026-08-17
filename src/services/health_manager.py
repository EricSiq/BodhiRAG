"""
BodhiRAG Service Health Manager
Implements health checks, circuit breakers, and state management.
From OPEN_SOURCE_OPERATIONS_AND_HARDENING.md
"""

import logging
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from src.models import ServiceHealth, ServiceState, OperatingMode

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for external service calls."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    
    def can_execute(self) -> bool:
        """Check if calls are allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker [{self.name}] entering HALF_OPEN state")
                return True
            return False
        
        # HALF_OPEN - allow one test call
        return True
    
    def record_success(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit breaker [{self.name}] recovered to CLOSED state")
    
    def record_failure(self, error: Optional[Exception] = None):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker [{self.name}] failed in HALF_OPEN, back to OPEN")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker [{self.name}] opened after {self.failure_count} failures"
            )


# ---------------------------------------------------------------------------
# Service Health Manager
# ---------------------------------------------------------------------------

class ServiceHealthManager:
    """
    Manages health checks and state for all services.
    Implements service hierarchy from OPEN_SOURCE_OPERATIONS_AND_HARDENING.md:
    
    1. Vector corpus available: search and source cards work
    2. Generation available: grounded answer synthesis works  
    3. Graph available: relationship evidence and visual graph work
    4. Parser/topic tools available: maintainer-only enrichment works
    """
    
    def __init__(self, operating_mode: OperatingMode = OperatingMode.DEMO):
        self.operating_mode = operating_mode
        self._health = ServiceHealth(operating_mode=operating_mode)
        
        # Circuit breakers for each service
        self.circuit_breakers = {
            "vector": CircuitBreaker("vector", failure_threshold=3, recovery_timeout=30),
            "graph": CircuitBreaker("graph", failure_threshold=3, recovery_timeout=30),
            "generation": CircuitBreaker("generation", failure_threshold=5, recovery_timeout=60),
        }
        
        # Health check functions (injected)
        self._checkers: Dict[str, Callable] = {}
    
    def register_checker(self, service: str, checker: Callable[[], bool]):
        """Register a health check function for a service."""
        self._checkers[service] = checker
    
    def check_vector_store(self, vector_connector) -> bool:
        """Check if vector store is healthy."""
        breaker = self.circuit_breakers["vector"]
        
        if not breaker.can_execute():
            logger.info("Vector store circuit breaker is OPEN")
            return False
        
        try:
            # Try to initialize and get stats
            if hasattr(vector_connector, 'initialize_store'):
                vector_connector.initialize_store()
            
            if hasattr(vector_connector, 'get_collection_stats'):
                stats = vector_connector.get_collection_stats()
                doc_count = stats.get("total_documents", 0)
                
                self._health.vector_available = True
                self._health.vector_document_count = doc_count
                breaker.record_success()
                return True
            else:
                # Fallback check
                self._health.vector_available = True
                breaker.record_success()
                return True
                
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            self._health.vector_available = False
            breaker.record_failure(e)
            return False
    
    def check_graph(self, graph_connector) -> bool:
        """Check if Neo4j graph is healthy."""
        breaker = self.circuit_breakers["graph"]
        
        if not breaker.can_execute():
            logger.info("Graph circuit breaker is OPEN")
            return False
        
        try:
            # Check if password is configured
            if hasattr(graph_connector, 'password') and not graph_connector.password:
                logger.info("Graph unavailable: password not configured")
                self._health.graph_available = False
                return False
            
            # Try to connect
            connected = False
            if hasattr(graph_connector, 'connect'):
                connected = graph_connector.connect()
            
            if connected:
                # Get entity count
                if hasattr(graph_connector, 'export_graph_stats'):
                    stats = graph_connector.export_graph_stats()
                    self._health.graph_entity_count = stats.get("total_entities", 0)
                
                self._health.graph_available = True
                breaker.record_success()
                
                # Close connection after check
                if hasattr(graph_connector, 'close'):
                    graph_connector.close()
                    
                return True
            else:
                self._health.graph_available = False
                breaker.record_failure(Exception("Connection failed"))
                return False
                
        except Exception as e:
            logger.error(f"Graph health check failed: {e}")
            self._health.graph_available = False
            breaker.record_failure(e)
            return False
    
    def check_generation(self, llm_provider: str = "mistral", hf_token: str = "") -> bool:
        """Check if LLM generation is available."""
        breaker = self.circuit_breakers["generation"]
        
        if not breaker.can_execute():
            logger.info("Generation circuit breaker is OPEN")
            return False
        
        try:
            # For HF API, check if token is set
            if llm_provider == "mistral":
                if not hf_token:
                    logger.info("Generation unavailable: HF_TOKEN not set")
                    self._health.generation_available = False
                    self._health.generation_model = "template_fallback"
                    return False
                
                # Could do a test call here, but that consumes quota
                self._health.generation_available = True
                self._health.generation_model = "Mistral-7B-Instruct"
                breaker.record_success()
                return True
            
            elif llm_provider == "qwen":
                # Local Qwen - assume available if provider is set to qwen
                self._health.generation_available = True
                self._health.generation_model = "Qwen2.5-7B-Instruct"
                breaker.record_success()
                return True
            
            else:
                self._health.generation_available = False
                return False
                
        except Exception as e:
            logger.error(f"Generation health check failed: {e}")
            self._health.generation_available = False
            breaker.record_failure(e)
            return False
    
    def get_health(self) -> ServiceHealth:
        """Get current health status."""
        return self._health
    
    def get_state(self) -> ServiceState:
        """Get current service state."""
        return self._health.get_service_state()
    
    def get_state_message(self) -> str:
        """Get user-facing state message."""
        return self._health.get_state_message()
    
    def get_status_badge(self) -> Dict[str, str]:
        """Get badge information for UI display."""
        state = self.get_state()
        
        badges = {
            ServiceState.READY: {
                "class": "badge-green",
                "text": "Ready",
                "tooltip": "Literature and relationship evidence are ready"
            },
            ServiceState.LITERATURE_ONLY: {
                "class": "badge-yellow", 
                "text": "Literature Only",
                "tooltip": "Relationship evidence temporarily unavailable"
            },
            ServiceState.EVIDENCE_ONLY: {
                "class": "badge-blue",
                "text": "Evidence Only",
                "tooltip": "Answer generation unavailable, showing evidence"
            },
            ServiceState.INDEXING: {
                "class": "badge-purple",
                "text": "Indexing",
                "tooltip": "Corpus is being updated"
            },
            ServiceState.NEEDS_SETUP: {
                "class": "badge-gray",
                "text": "Setup Required",
                "tooltip": "No searchable corpus installed"
            }
        }
        
        return badges.get(state, badges[ServiceState.NEEDS_SETUP])
    
    def get_mode_badge(self) -> Dict[str, str]:
        """Get operating mode badge for UI."""
        modes = {
            OperatingMode.DEMO: {
                "class": "badge-blue",
                "text": "Demo Mode",
                "tooltip": "Pre-built corpus, no credentials needed"
            },
            OperatingMode.LOCAL_OPENSOURCE: {
                "class": "badge-green",
                "text": "Local Open-Source",
                "tooltip": "Full local stack with open models"
            },
            OperatingMode.HOSTED_FREETIER: {
                "class": "badge-purple",
                "text": "Hosted Free-Tier",
                "tooltip": "Using free hosted services"
            },
            OperatingMode.MAINTAINER_INGEST: {
                "class": "badge-gold",
                "text": "Maintainer Mode",
                "tooltip": "Corpus ingestion enabled"
            }
        }
        
        return modes.get(self.operating_mode, modes[OperatingMode.DEMO])


# ---------------------------------------------------------------------------
# Global health manager instance
# ---------------------------------------------------------------------------

_health_manager: Optional[ServiceHealthManager] = None


def get_health_manager() -> ServiceHealthManager:
    """Get or create global health manager."""
    global _health_manager
    if _health_manager is None:
        from src.core.config import settings
        _health_manager = ServiceHealthManager(settings.operating_mode)
    return _health_manager


def initialize_health_manager(operating_mode: OperatingMode) -> ServiceHealthManager:
    """Initialize global health manager with specified mode."""
    global _health_manager
    _health_manager = ServiceHealthManager(operating_mode)
    return _health_manager
