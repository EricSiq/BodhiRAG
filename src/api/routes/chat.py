import time
from fastapi import APIRouter, HTTPException
from src.api.models.chat_models import ChatRequest, MobileChatResponse, Source
from src.services.rag_service import HybridRAGService

router = APIRouter()
rag_service = HybridRAGService()

@router.post("/chat", response_model=MobileChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint (rate limiting disabled temporarily)
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
        
        # Convert sources to Source objects
        sources = []
        for source_dict in result.get('sources', []):
            source = Source(
                title=source_dict.get('title', ''),
                url=source_dict.get('url', ''),
                confidence=source_dict.get('confidence', 0.0),
                excerpt=source_dict.get('excerpt', ''),
                source_type=source_dict.get('source_type', 'publication')
            )
            sources.append(source)
        
        return MobileChatResponse(
            answer=result['answer'],
            sources=sources[:3],  # Limit sources for mobile
            suggested_questions=result.get('suggested_questions', []),
            processing_time=processing_time,
            entity_relationships=result.get('entity_relationships', None)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")