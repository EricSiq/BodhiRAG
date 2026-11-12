#BodhiRAG/src/data_ingestion/knowledge_extractor.py
"""
Knowledge Extractor: extracts structured entity/relationship triples from
NASA space biology text using:
  - Mistral-7B via HF Inference API (when HF_TOKEN is set)
  - Keyword-based mock extraction (fallback, no API key needed)
"""

import logging
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, ValidationError
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas (define the structured output format)
# ---------------------------------------------------------------------------

class Entity(BaseModel):
    """A scientific entity identified in the space bioscience domain."""
    name: str = Field(description="Canonical name of the entity")
    entity_type: str = Field(
        description="One of: Organism, Environment, Biological_Process, Biomolecule, Technology, Location"
    )


class RelationshipTriple(BaseModel):
    """A structured triple representing a verifiable scientific relationship."""
    subject: str = Field(description="Subject entity name")
    relationship: str = Field(
        description=(
            "One of: causes, inhibits, affects, measured_in, "
            "mitigated_by, studied_in, shows_effect"
        )
    )
    object: str = Field(description="Object entity name")
    evidence_span: str = Field(description="Exact text supporting this relationship")
    # Optional enrichment fields (populated after extraction)
    source_title: str = ""
    source_url: str = ""
    doc_id: str = ""
    chunk_id: str = ""


class ExtractionSchema(BaseModel):
    """Complete structured output for a text chunk."""
    entities: List[Entity] = Field(default_factory=list)
    triples: List[RelationshipTriple] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# LLM-based extraction
# ---------------------------------------------------------------------------

def _llm_extract(text_chunk: str) -> Dict[str, Any]:
    """
    Use Mistral-7B via HF Inference API to extract entities and triples.
    Returns a dict compatible with ExtractionSchema.
    Falls back to mock extraction if HF_TOKEN is not set.
    """
    try:
        from src.services.llm_inference import extract_triples_from_text
        result = extract_triples_from_text(text_chunk)
        if result and (result.get("entities") or result.get("triples")):
            return result
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"LLM extraction failed, using mock: {e}")
    
    return _mock_extract(text_chunk)


# ---------------------------------------------------------------------------
# Mock extraction (keyword-based, no API key needed)
# ---------------------------------------------------------------------------

VALID_RELATIONSHIPS = frozenset([
    "causes", "inhibits", "affects", "measured_in",
    "mitigated_by", "studied_in", "shows_effect",
])

ENTITY_KEYWORDS = {
    "microgravity": ("Microgravity", "Environment"),
    "zero gravity": ("Microgravity", "Environment"),
    "weightlessness": ("Microgravity", "Environment"),
    "radiation": ("Space Radiation", "Environment"),
    "cosmic ray": ("Cosmic Radiation", "Environment"),
    "bone loss": ("Bone Loss", "Biological_Process"),
    "osteoporosis": ("Osteoporosis", "Biological_Process"),
    "bone density": ("Bone Density", "Biological_Process"),
    "muscle atrophy": ("Muscle Atrophy", "Biological_Process"),
    "muscle wasting": ("Muscle Wasting", "Biological_Process"),
    "oxidative stress": ("Oxidative Stress", "Biological_Process"),
    "reactive oxygen": ("Reactive Oxygen Species", "Biomolecule"),
    "dna damage": ("DNA Damage", "Biological_Process"),
    "gene expression": ("Gene Expression", "Biological_Process"),
    "immune": ("Immune Response", "Biological_Process"),
    "cardiovascular": ("Cardiovascular System", "Biological_Process"),
    "fluid shift": ("Fluid Shift", "Biological_Process"),
    "stem cell": ("Stem Cells", "Biomolecule"),
    "mouse": ("Mus musculus", "Organism"),
    "rat": ("Rattus norvegicus", "Organism"),
    "astronaut": ("Human Astronaut", "Organism"),
    "arabidopsis": ("Arabidopsis thaliana", "Organism"),
    "exercise": ("Exercise Countermeasure", "Technology"),
    "iss": ("International Space Station", "Location"),
    "space station": ("International Space Station", "Location"),
}

TRIPLE_RULES = [
    # (subject_keyword, object_keyword, relationship)
    ("microgravity", "bone", "causes"),
    ("microgravity", "muscle", "causes"),
    ("radiation", "dna", "causes"),
    ("radiation", "oxidative stress", "causes"),
    ("microgravity", "oxidative stress", "causes"),
    ("exercise", "bone loss", "mitigated_by"),
    ("exercise", "muscle atrophy", "mitigated_by"),
    ("microgravity", "immune", "affects"),
    ("microgravity", "cardiovascular", "affects"),
    ("radiation", "gene expression", "affects"),
]


def _mock_extract(text_chunk: str) -> Dict[str, Any]:
    """Keyword-based fallback extraction: always works, lower precision."""
    text_lower = text_chunk.lower()
    entities = []
    seen_entities = set()

    for keyword, (name, etype) in ENTITY_KEYWORDS.items():
        if keyword in text_lower and name not in seen_entities:
            entities.append({"name": name, "entity_type": etype})
            seen_entities.add(name)

    triples = []
    for subj_kw, obj_kw, rel in TRIPLE_RULES:
        if subj_kw in text_lower and obj_kw in text_lower:
            # Find the canonical entity names
            subj_name = next(
                (n for kw, (n, _) in ENTITY_KEYWORDS.items() if kw == subj_kw), subj_kw.title()
            )
            obj_candidates = [
                n for kw, (n, _) in ENTITY_KEYWORDS.items() if kw in obj_kw or obj_kw in kw
            ]
            obj_name = obj_candidates[0] if obj_candidates else obj_kw.title()

            triples.append({
                "subject": subj_name,
                "relationship": rel,
                "object": obj_name,
                "evidence_span": text_chunk[:200] + "...",
            })

    return {"entities": entities, "triples": triples}


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def extract_knowledge_from_chunk(doc_chunk: Document) -> List[RelationshipTriple]:
    """
    Extract entity/relationship triples from a document chunk.
    
    Uses LLM extraction when HF_TOKEN is available, falls back to 
    keyword-based extraction otherwise. Returns a list of validated
    RelationshipTriple objects enriched with source metadata.
    """
    try:
        raw_data = _llm_extract(doc_chunk.page_content)
        
        if not raw_data:
            return []

        # Validate via Pydantic
        extracted = ExtractionSchema.model_validate(raw_data)

        # Enrich triples with source metadata
        enriched: List[RelationshipTriple] = []
        for triple in extracted.triples:
            triple_data = triple.model_dump()
            triple_data.update({
                "source_title": doc_chunk.metadata.get("original_title", ""),
                "source_url":   doc_chunk.metadata.get("source_url", ""),
                "doc_id":       doc_chunk.metadata.get("doc_id", ""),
                "chunk_id":     doc_chunk.metadata.get("chunk_id", ""),
            })
            try:
                enriched.append(RelationshipTriple(**triple_data))
            except ValidationError:
                continue

        if enriched:
            logger.info(
                f"Extracted {len(enriched)} triples from "
                f"{doc_chunk.metadata.get('doc_id', 'unknown')}"
            )
        return enriched

    except ValidationError as e:
        logger.error(f"Pydantic validation failed: {e}")
        return []
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return []