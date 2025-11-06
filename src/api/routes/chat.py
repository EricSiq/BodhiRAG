#BodhiRAG-main\src\api\routes\chat.py
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from src.api.models.chat_models import ChatRequest, MobileChatResponse
from src.services.rag_service import HybridRAGService

router = APIRouter()
rag_service = HybridRAGService()

@router.post("/chat", response_model=MobileChatResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint with rate limiting (10 requests per minute)
    Optimized for mobile and web clients
    """
    try:
        start_time = time.time()
        
        result = await rag_service.process_query(
            query=request.query,
            use_kg=request.use_kg,
            use_vector=request.use_vector,
            mobile_optimized=request.mobile_optimized
        )
        
        processing_time = time.time() - start_time
        
        return MobileChatResponse(
            answer=result.answer,
            sources=result.sources[:3],  # Limit sources for mobile
            suggested_questions=result.suggested_questions,
            processing_time=processing_time,
            entity_relationships=result.entity_relationships
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")