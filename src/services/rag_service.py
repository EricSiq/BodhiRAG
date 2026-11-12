#BodhiRAG/src/services/rag_service.py
"""
Async wrapper for HybridRAGAgent: for use in async API contexts.
The Gradio interface calls agent_router directly; this service is for
future API (FastAPI/Flask) integrations.
"""

import asyncio
from src.graph_rag.agent_router import HybridRAGAgent, AgentRouter


class HybridRAGService:
    """Async wrapper around HybridRAGAgent for API usage."""

    def __init__(self, kg_connector=None, vs_connector=None):
        if kg_connector and vs_connector:
            self.agent = HybridRAGAgent(kg_connector, vs_connector)
        else:
            # Lazy init: connectors must be set before calling process_query
            self.agent = None

    def set_agent(self, agent: HybridRAGAgent):
        self.agent = agent

    async def process_query(self, query: str, use_kg: bool = True, use_vector: bool = True):
        """Process a query asynchronously."""
        if not self.agent:
            raise RuntimeError("Agent not initialized — call set_agent() first")
        result = await asyncio.to_thread(
            self.agent.route_query,
            query,
            use_kg,
            use_vector,
        )
        return result
