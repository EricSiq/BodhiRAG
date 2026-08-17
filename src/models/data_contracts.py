"""
BodhiRAG Data Contracts
Pydantic models for all pipeline artifacts with validation.
Implements data contracts from PIPELINE_ARCHITECTURE_AND_DATA_CONTRACTS.md
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
from enum import Enum
import hashlib
import uuid


# ---------------------------------------------------------------------------
# Enums and Controlled Vocabularies
# ---------------------------------------------------------------------------

class OperatingMode(str, Enum):
    """Deployment operating modes from OPEN_SOURCE_OPERATIONS_AND_HARDENING.md"""
    DEMO = "demo"  # Prebuilt corpus, no credentials needed
    LOCAL_OPENSOURCE = "local_opensource"  # Qwen local, Neo4j Community, local vector store
    HOSTED_FREETIER = "hosted_freetier"  # HF inference, optional hosted graph
    MAINTAINER_INGEST = "maintainer_ingest"  # Write-enabled for corpus builds


class ServiceState(str, Enum):
    """Service health states from FRONTEND_UX_DESIGN.md"""
    READY = "ready"  # Literature and relationship evidence ready
    LITERATURE_ONLY = "literature_only"  # Graph unavailable, semantic fallback
    EVIDENCE_ONLY = "evidence_only"  # Generation unavailable, showing evidence
    INDEXING = "indexing"  # Corpus being updated
    NEEDS_SETUP = "needs_setup"  # No searchable corpus


class QueryRoute(str, Enum):
    """Query routing options from PIPELINE_ARCHITECTURE_AND_DATA_CONTRACTS.md"""
    SEMANTIC = "semantic"  # Vector retrieval only
    GRAPH = "graph"  # Graph retrieval with semantic fallback
    HYBRID = "hybrid"  # Combine both
    CLARIFY = "clarify"  # Ambiguous query needs clarification


class ElementType(str, Enum):
    """Parsed element types"""
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"


class Predicate(str, Enum):
    """Allowed relationship predicates"""
    CAUSES = "causes"
    INHIBITS = "inhibits"
    AFFECTS = "affects"
    MEASURED_IN = "measured_in"
    MITIGATED_BY = "mitigated_by"
    STUDIED_IN = "studied_in"
    SHOWS_EFFECT = "shows_effect"


# ---------------------------------------------------------------------------
# Source Record (Phase 2 - Reproducible Ingestion)
# ---------------------------------------------------------------------------

class SourceRecord(BaseModel):
    """Validated source metadata for ingestion pipeline."""
    source_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = Field(..., min_length=1, description="Non-empty title")
    canonical_url: str = Field(..., description="Canonical URL or identifier")
    license_or_access: str = Field(default="public", description="License or access terms")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    content_hash: str = Field(..., description="SHA-256 hash of raw content")
    
    @field_validator('canonical_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure canonical URL is present and valid."""
        if not v or not v.strip():
            raise ValueError("Canonical URL must not be empty")
        # Basic validation - must start with http, https, or be a DOI/PMID
        if not (v.startswith('http') or v.startswith('doi:') or v.startswith('PMID:')):
            raise ValueError("URL must be http/https, doi:, or PMID:")
        return v.strip()
    
    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Parsed Element (Multimodal content)
# ---------------------------------------------------------------------------

class ParsedElement(BaseModel):
    """Parsed document element with provenance."""
    source_id: str
    element_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    kind: ElementType
    text_or_asset_ref: str = Field(..., description="Text content or asset reference")
    page_or_section: Optional[str] = None
    parser_name: str = "unknown"
    parser_version: str = "0.0.0"
    parsing_warnings: List[str] = Field(default_factory=list)
    
    @field_validator('kind', mode='before')
    @classmethod
    def validate_kind(cls, v):
        """Ensure kind is valid element type."""
        if isinstance(v, str):
            try:
                return ElementType(v.lower())
            except ValueError:
                return ElementType.TEXT
        return v


# ---------------------------------------------------------------------------
# Chunk (with provenance)
# ---------------------------------------------------------------------------

class Chunk(BaseModel):
    """Document chunk with full provenance tracking."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str
    text: str = Field(..., min_length=10, description="Chunk text content")
    element_refs: List[str] = Field(default_factory=list, description="Referenced element IDs")
    token_count: int = Field(default=0, ge=0)
    chunker_version: str = "1.0.0"
    content_hash: str = Field(default="", description="Hash of chunk text")
    corpus_build_id: Optional[str] = None
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Ensure non-empty text."""
        if not v or not v.strip():
            raise ValueError("Chunk text must not be empty")
        return v.strip()
    
    @model_validator(mode='after')
    def compute_content_hash(self):
        """Auto-compute content hash if not provided."""
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.text.encode('utf-8')).hexdigest()[:16]
        return self


# ---------------------------------------------------------------------------
# Triple (Knowledge Graph relationship)
# ---------------------------------------------------------------------------

class Triple(BaseModel):
    """Validated relationship triple with evidence."""
    triple_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: str = Field(..., min_length=1)
    predicate: Predicate
    object: str = Field(..., min_length=1)
    evidence_chunk_id: str
    evidence_span: str = Field(..., description="Exact text from chunk supporting this relationship")
    extractor_version: str = "1.0.0"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    corpus_build_id: Optional[str] = None
    review_status: str = "pending"  # pending, approved, rejected
    
    @field_validator('predicate', mode='before')
    @classmethod
    def validate_predicate(cls, v):
        """Ensure predicate is in allowlist."""
        if isinstance(v, str):
            try:
                return Predicate(v.lower())
            except ValueError:
                raise ValueError(f"Predicate must be one of: {[p.value for p in Predicate]}")
        return v
    
    @model_validator(mode='after')
    def check_no_self_loop(self):
        """Reject self-loops unless explicitly allowed."""
        if self.subject.lower() == self.object.lower():
            raise ValueError("Self-loop relationships are not allowed")
        return self


# ---------------------------------------------------------------------------
# Retrieval Result
# ---------------------------------------------------------------------------

class RetrievalResult(BaseModel):
    """Single retrieval result with provenance."""
    source_id: str
    chunk_id: str
    score: float = Field(..., ge=0.0, le=1.0)
    rank: int = Field(..., ge=1)
    retriever: str = "unknown"  # semantic, graph, hybrid
    corpus_build_id: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Answer (with citations)
# ---------------------------------------------------------------------------

class AnswerClaim(BaseModel):
    """A single factual claim with citations."""
    claim_text: str
    citation_ids: List[str] = Field(default_factory=list)
    is_supported: bool = True


class Answer(BaseModel):
    """Generated answer with citations and provenance."""
    answer_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query: str
    route: QueryRoute
    claims: List[AnswerClaim] = Field(default_factory=list)
    citation_ids: List[str] = Field(default_factory=list)
    model_id: str = "unknown"
    corpus_build_id: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    direct_answer: str = ""
    limits_or_disagreement: str = ""
    next_questions: List[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_claims_have_citations(self):
        """Ensure factual claims have at least one citation or are marked unsupported."""
        for claim in self.claims:
            if claim.is_supported and not claim.citation_ids:
                claim.is_supported = False
        return self


# ---------------------------------------------------------------------------
# Routing Decision
# ---------------------------------------------------------------------------

class RoutingDecision(BaseModel):
    """Structured routing decision from Qwen router."""
    route: QueryRoute
    reason: str = ""
    entities: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ---------------------------------------------------------------------------
# Run Manifest (Phase 2)
# ---------------------------------------------------------------------------

class RunManifest(BaseModel):
    """Complete ingestion run manifest with validation status."""
    build_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: Literal["running", "published", "failed"] = "running"
    
    # Inputs
    input_sources: int = 0
    input_hash: str = ""
    
    # Component versions
    parser_name: str = "unknown"
    parser_version: str = "0.0.0"
    chunker_version: str = "1.0.0"
    embedding_model: str = "unknown"
    extractor_version: str = "1.0.0"
    
    # Counts
    sources_processed: int = 0
    sources_skipped: int = 0
    sources_failed: int = 0
    chunks_created: int = 0
    triples_extracted: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    
    # Quality metrics
    duplicate_count: int = 0
    parser_failed_count: int = 0
    empty_chunk_count: int = 0
    
    # Failures
    failures: List[Dict[str, Any]] = Field(default_factory=list)
    
    def mark_published(self):
        """Mark manifest as published after quality gates pass."""
        self.completed_at = datetime.utcnow()
        self.status = "published"
    
    def add_failure(self, source_id: str, stage: str, error: str, retry_count: int = 0):
        """Record a failure in the run."""
        self.failures.append({
            "source_id": source_id,
            "stage": stage,
            "error": error,
            "retry_count": retry_count,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.sources_failed += 1


# ---------------------------------------------------------------------------
# Service Health
# ---------------------------------------------------------------------------

class ServiceHealth(BaseModel):
    """Current health status of all services."""
    vector_available: bool = False
    vector_document_count: int = 0
    graph_available: bool = False
    graph_entity_count: int = 0
    generation_available: bool = False
    generation_model: str = "none"
    
    operating_mode: OperatingMode = OperatingMode.DEMO
    corpus_build_id: Optional[str] = None
    
    def get_service_state(self) -> ServiceState:
        """Determine overall service state based on component health."""
        if not self.vector_available or self.vector_document_count == 0:
            return ServiceState.NEEDS_SETUP
        
        if not self.generation_available:
            return ServiceState.EVIDENCE_ONLY
        
        if not self.graph_available:
            return ServiceState.LITERATURE_ONLY
        
        return ServiceState.READY
    
    def get_state_message(self) -> str:
        """Get user-facing state message."""
        state = self.get_service_state()
        messages = {
            ServiceState.READY: "Literature and relationship evidence are ready.",
            ServiceState.LITERATURE_ONLY: "Relationship evidence is temporarily unavailable; literature search remains active.",
            ServiceState.EVIDENCE_ONLY: "Answer generation is unavailable; showing retrieved evidence.",
            ServiceState.INDEXING: f"The corpus is being updated. Search uses build {self.corpus_build_id or 'unknown'}.",
            ServiceState.NEEDS_SETUP: "No searchable corpus is installed. Run the data pipeline or use the pre-seeded demo."
        }
        return messages.get(state, "Service status unknown.")
