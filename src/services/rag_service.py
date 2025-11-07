#BodhiRAG-main\src\services\rag_service.py
import asyncio
from src.graph_rag.agent_router import AgentRouter

class HybridRAGService:
    def __init__(self):
        self.agent = AgentRouter()
    
    async def process_query(self, query: str, use_kg: bool, use_vector: bool):
        # Your existing agent logic, made async
        result = await asyncio.to_thread(
            self.agent.route_query, 
            query, 
            use_kg, 
            use_vector
        )
        return result
