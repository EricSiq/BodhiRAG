#BodhiRAG-main\src\api\models\chat_models.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Source(BaseModel):
    title: str
    url: str
    confidence: float
    excerpt: str
    source_type: str  # "publication", "dataset", "experiment"

class MobileChatResponse(BaseModel):
    answer: str
    sources: List[Source] = Field(default_factory=list, max_items=3)  # Limited to 3 for mobile
    suggested_questions: List[str] = Field(default_factory=list)
    processing_time: float
    entity_relationships: Optional[List[dict]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            # Add any custom serializers for React Native compatibility
        }

class ChatRequest(BaseModel):
    query: str
    use_kg: bool = True
    use_vector: bool = True
    mobile_optimized: bool = False  # Flag for mobile-specific optimizations