"""
BodhiRAG Configuration
Pydantic settings as single configuration boundary.
Implements configuration from OPEN_SOURCE_OPERATIONS_AND_HARDENING.md
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator
from enum import Enum


class OperatingMode(str, Enum):
    """Deployment operating modes"""
    DEMO = "demo"
    LOCAL_OPENSOURCE = "local_opensource"
    HOSTED_FREETIER = "hosted_freetier"
    MAINTAINER_INGEST = "maintainer_ingest"


class Settings(BaseSettings):
    """Single configuration boundary for BodhiRAG."""
    
    # Operating mode - determines feature availability
    operating_mode: OperatingMode = OperatingMode.DEMO
    
    # Database — leave password empty so misconfigured deployments fail
    # loudly on connect() rather than silently with a wrong default.
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_read_only: bool = True  # Use least-privilege by default
    
    # Vector DB — /tmp is always writable on HF Spaces and in Docker
    chroma_path: str = "/tmp/chroma_db"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False
    
    # Model configuration - support both Mistral (current) and Qwen (target)
    llm_provider: str = "mistral"  # "mistral" or "qwen"
    llm_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    qwen_model: str = "Qwen/Qwen2.5-7B-Instruct"
    
    # Hugging Face
    hf_token: str = ""
    
    # Embedding model
    embedding_model: str = "ibm/granite-embedding-30m-english"
    embedding_fallback: str = "all-MiniLM-L6-v2"
    
    # Corpus build tracking
    corpus_build_id: Optional[str] = None
    corpus_manifest_path: str = "data/manifests"
    
    # Timeouts and limits (hardening)
    request_timeout: int = 90
    embedding_timeout: int = 30
    generation_timeout: int = 120
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    
    # Query limits
    max_query_length: int = 1000
    max_history_size: int = 20
    max_retrieved_chunks: int = 10
    max_prompt_size: int = 4000
    max_response_tokens: int = 800
    
    # File upload limits
    max_upload_size_mb: int = 50
    allowed_upload_extensions: str = ".csv,.json,.txt"
    
    # URL allowlist for fetching
    allowed_url_patterns: str = "pubmed.ncbi.nlm.nih.gov,ncbi.nlm.nih.gov,nasa.gov,arxiv.org"
    
    # Ingestion mode
    ingestion_enabled: bool = False  # Only enabled in maintainer mode
    
    @field_validator('operating_mode', mode='before')
    @classmethod
    def validate_operating_mode(cls, v):
        """Convert string to enum."""
        if isinstance(v, str):
            try:
                return OperatingMode(v.lower())
            except ValueError:
                return OperatingMode.DEMO
        return v
    
    @field_validator('ingestion_enabled', mode='after')
    @classmethod
    def check_ingestion_permission(cls, v, info):
        """Only allow ingestion in maintainer mode."""
        if v and info.data.get('operating_mode') != OperatingMode.MAINTAINER_INGEST:
            return False
        return v
    
    def get_mode_description(self) -> str:
        """Get user-facing description of current mode."""
        descriptions = {
            OperatingMode.DEMO: "Demo Mode — Pre-built corpus, no credentials required",
            OperatingMode.LOCAL_OPENSOURCE: "Local Open-Source — Full local stack with Qwen",
            OperatingMode.HOSTED_FREETIER: "Hosted Free-Tier — Using free hosted services",
            OperatingMode.MAINTAINER_INGEST: "Maintainer Mode — Corpus build enabled"
        }
        return descriptions.get(self.operating_mode, "Unknown mode")
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.operating_mode == OperatingMode.DEMO
    
    def is_maintainer_mode(self) -> bool:
        """Check if ingestion is allowed."""
        return self.operating_mode == OperatingMode.MAINTAINER_INGEST
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()

