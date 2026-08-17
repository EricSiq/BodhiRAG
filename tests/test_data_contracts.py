"""
Tests for BodhiRAG Data Contracts
Validates Pydantic models from src/models/data_contracts.py
"""

import pytest
from datetime import datetime
from src.models import (
    SourceRecord,
    ParsedElement,
    Chunk,
    Triple,
    RetrievalResult,
    Answer,
    AnswerClaim,
    RoutingDecision,
    RunManifest,
    ServiceHealth,
    OperatingMode,
    ServiceState,
    QueryRoute,
    ElementType,
    Predicate,
)


class TestSourceRecord:
    """Tests for SourceRecord validation."""
    
    def test_valid_source_record(self):
        """Test creating a valid source record."""
        record = SourceRecord(
            title="Test Publication",
            canonical_url="https://example.com/paper",
            content_hash="abc123",
        )
        assert record.title == "Test Publication"
        assert record.canonical_url == "https://example.com/paper"
        assert record.license_or_access == "public"
    
    def test_empty_title_fails(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValueError):
            SourceRecord(
                title="",
                canonical_url="https://example.com",
                content_hash="abc123",
            )
    
    def test_empty_url_fails(self):
        """Test that empty URL is rejected."""
        with pytest.raises(ValueError):
            SourceRecord(
                title="Test",
                canonical_url="",
                content_hash="abc123",
            )
    
    def test_invalid_url_format_fails(self):
        """Test that invalid URL format is rejected."""
        with pytest.raises(ValueError):
            SourceRecord(
                title="Test",
                canonical_url="not-a-url",
                content_hash="abc123",
            )
    
    def test_doi_url_accepted(self):
        """Test that DOI URLs are accepted."""
        record = SourceRecord(
            title="Test",
            canonical_url="doi:10.1234/test",
            content_hash="abc123",
        )
        assert record.canonical_url == "doi:10.1234/test"
    
    def test_compute_hash(self):
        """Test content hash computation."""
        hash1 = SourceRecord.compute_hash("test content")
        hash2 = SourceRecord.compute_hash("test content")
        hash3 = SourceRecord.compute_hash("different content")
        
        assert hash1 == hash2
        assert hash1 != hash3


class TestChunk:
    """Tests for Chunk validation."""
    
    def test_valid_chunk(self):
        """Test creating a valid chunk."""
        chunk = Chunk(
            source_id="src123",
            text="This is a test chunk with enough content to pass validation.",
        )
        assert chunk.source_id == "src123"
        assert len(chunk.text) > 0
        assert chunk.content_hash != ""
    
    def test_empty_text_fails(self):
        """Test that empty text is rejected."""
        with pytest.raises(ValueError):
            Chunk(source_id="src123", text="")
    
    def test_content_hash_auto_computed(self):
        """Test that content hash is auto-computed."""
        chunk = Chunk(
            source_id="src123",
            text="Test content for hashing",
        )
        assert chunk.content_hash != ""


class TestTriple:
    """Tests for Triple validation."""
    
    def test_valid_triple(self):
        """Test creating a valid triple."""
        triple = Triple(
            subject="Microgravity",
            predicate=Predicate.CAUSES,
            object="Bone Loss",
            evidence_chunk_id="chunk123",
            evidence_span="Microgravity causes bone loss in astronauts.",
        )
        assert triple.subject == "Microgravity"
        assert triple.predicate == Predicate.CAUSES
    
    def test_invalid_predicate_fails(self):
        """Test that invalid predicate is rejected."""
        with pytest.raises(ValueError):
            Triple(
                subject="A",
                predicate="invalid_predicate",
                object="B",
                evidence_chunk_id="chunk123",
                evidence_span="test",
            )
    
    def test_self_loop_fails(self):
        """Test that self-loop relationships are rejected."""
        with pytest.raises(ValueError):
            Triple(
                subject="Entity",
                predicate=Predicate.CAUSES,
                object="Entity",
                evidence_chunk_id="chunk123",
                evidence_span="test",
            )


class TestRoutingDecision:
    """Tests for RoutingDecision."""
    
    def test_valid_routing_decision(self):
        """Test creating a valid routing decision."""
        decision = RoutingDecision(
            route=QueryRoute.HYBRID,
            reason="Query asks about mechanism",
            entities=["Microgravity", "Bone Loss"],
        )
        assert decision.route == QueryRoute.HYBRID
        assert decision.needs_clarification is False


class TestRunManifest:
    """Tests for RunManifest."""
    
    def test_manifest_creation(self):
        """Test creating a run manifest."""
        manifest = RunManifest(
            input_sources=100,
            parser_name="simple_loader",
        )
        assert manifest.status == "running"
        assert manifest.sources_processed == 0
    
    def test_mark_published(self):
        """Test marking manifest as published."""
        manifest = RunManifest()
        manifest.sources_processed = 100
        manifest.chunks_created = 500
        
        manifest.mark_published()
        
        assert manifest.status == "published"
        assert manifest.completed_at is not None
    
    def test_add_failure(self):
        """Test adding a failure record."""
        manifest = RunManifest()
        manifest.add_failure("src123", "parsing", "Network error", retry_count=1)
        
        assert manifest.sources_failed == 1
        assert len(manifest.failures) == 1
        assert manifest.failures[0]["source_id"] == "src123"


class TestServiceHealth:
    """Tests for ServiceHealth."""
    
    def test_ready_state(self):
        """Test ready state when all services available."""
        health = ServiceHealth(
            vector_available=True,
            vector_document_count=100,
            graph_available=True,
            generation_available=True,
        )
        assert health.get_service_state() == ServiceState.READY
        assert "ready" in health.get_state_message().lower()
    
    def test_literature_only_state(self):
        """Test literature-only state when graph unavailable."""
        health = ServiceHealth(
            vector_available=True,
            vector_document_count=100,
            graph_available=False,
            generation_available=True,
        )
        assert health.get_service_state() == ServiceState.LITERATURE_ONLY
    
    def test_evidence_only_state(self):
        """Test evidence-only state when generation unavailable."""
        health = ServiceHealth(
            vector_available=True,
            vector_document_count=100,
            graph_available=True,
            generation_available=False,
        )
        assert health.get_service_state() == ServiceState.EVIDENCE_ONLY
    
    def test_needs_setup_state(self):
        """Test needs setup state when no corpus."""
        health = ServiceHealth(
            vector_available=False,
            vector_document_count=0,
        )
        assert health.get_service_state() == ServiceState.NEEDS_SETUP


class TestAnswer:
    """Tests for Answer validation."""
    
    def test_valid_answer(self):
        """Test creating a valid answer."""
        answer = Answer(
            query="What causes bone loss?",
            route=QueryRoute.HYBRID,
            direct_answer="Microgravity causes bone loss.",
        )
        assert answer.query == "What causes bone loss?"
        assert answer.route == QueryRoute.HYBRID
    
    def test_unsupported_claim_marked(self):
        """Test that unsupported claims are marked."""
        claim = AnswerClaim(
            claim_text="Some claim",
            citation_ids=[],
            is_supported=True,
        )
        
        answer = Answer(
            query="Test",
            route=QueryRoute.SEMANTIC,
            claims=[claim],
        )
        
        # Should be marked unsupported
        assert answer.claims[0].is_supported is False


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
