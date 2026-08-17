# Pipeline Architecture and Data Contracts

## Target Pipeline

The ingestion path should be a durable, versioned batch pipeline. Query serving must read only a completed corpus build; it must never query documents that are halfway through ingestion.

```text
NASA catalogue / public documents
  → validate and deduplicate
  → fetch with provenance
  → Docling parse (or deterministic fallback)
  → normalize multimodal content
  → chunk and validate
  → embed + write vector build
  → extract validated triples
  → write Neo4j graph build
  → BERTopic offline artifact
  → quality gates
  → atomically publish build manifest
```

## Component Responsibilities

| Component | Responsibility | Must not do |
| --- | --- | --- |
| Pydantic | Validate configuration, source metadata, chunks, triples, route/output envelopes, and run manifests | Hide invalid fields or silently coerce provenance |
| Docling | Parse supported PDFs/HTML and retain document structure, tables, figures, captions, and page locations | Be the only parser or make the full pipeline unavailable |
| Neo4j | Store normalized entity nodes, evidence-backed relationship edges, document links, and build IDs | Store unsupported model conclusions as facts |
| Qwen | Structured route classification and bounded grounded synthesis | Choose sources, invent citations, or bypass validation |
| BERTopic | Produce offline thematic navigation and corpus diagnostics for a named build | Run on every user query or claim validated research gaps |

## Data Contracts

Every artifact should be Pydantic-validated and persisted with an explicit schema version. Use immutable IDs, UTC timestamps, and a `corpus_build_id` on every downstream object.

| Artifact | Minimum fields | Validation and quality rule |
| --- | --- | --- |
| Source record | `source_id`, `title`, `canonical_url`, `license_or_access`, `retrieved_at`, `content_hash` | Canonical URL and non-empty title; duplicate content hashes are linked, not re-ingested |
| Parsed element | `source_id`, `element_id`, `kind`, `text_or_asset_ref`, `page_or_section`, `parser_name`, `parser_version` | `kind` is controlled (`text`, `table`, `figure`, `caption`); parsing warnings are retained |
| Chunk | `chunk_id`, `source_id`, `text`, `element_refs`, `token_count`, `chunker_version`, `content_hash` | Bounded length; no empty text; provenance survives chunking |
| Triple | `triple_id`, `subject`, `predicate`, `object`, `evidence_chunk_id`, `evidence_span`, `extractor_version`, `confidence` | Predicate allowlist; evidence span must occur in cited chunk; reject self-loops unless explicitly allowed |
| Retrieval result | `source_id`, `chunk_id`, `score`, `rank`, `retriever`, `corpus_build_id` | Scores are comparable only within retriever/model version |
| Answer | `answer_id`, `query`, `route`, `claims`, `citation_ids`, `model_id`, `corpus_build_id` | Each factual claim has at least one eligible citation or is marked unsupported |
| Run manifest | build ID, inputs, versions, counts, failures, start/end, status | `published` only after all required quality gates pass |

## Multimodal and Docling Strategy

Docling should be the preferred parser where it is supported and practical. The pipeline must still accept HTML and plain text through the existing simple loader when Docling is unavailable. Preserve raw input references and parser output so future parser upgrades can reprocess a corpus without re-downloading it.

For figures and tables, first deliver citation-preserving text/caption retrieval. Add image embedding or visual question answering only after the project can reliably show the page/figure and license context. Do not flatten a table into prose without retaining its original table reference.

## Query Routing with Qwen

Use Qwen as a constrained classifier, not an unconstrained agent. Its output should validate against a small Pydantic routing schema such as `route`, `reason`, `entities`, `filters`, and `needs_clarification`. Allowed routes are `semantic`, `graph`, `hybrid`, and `clarify`.

Routing policy:

1. Reject invalid structured output and use deterministic routing.
2. Retrieve from every route required by the validated decision; do not let the model fabricate retrieval results.
3. If graph retrieval is empty or unhealthy, run semantic retrieval and disclose the fallback.
4. Re-rank and deduplicate results by source and passage before synthesis.
5. Pass only selected, provenance-bearing evidence to answer generation.
6. Require citation markers in the answer; validate them after generation and fall back to evidence summary on failure.

The existing keyword router remains a valuable zero-cost fallback and a baseline for evaluation.

## Graph Model and Provenance

Use stable `Entity` nodes with a normalized name, display name, type, aliases, and build ID. Each extracted relationship should carry its predicate, source/chunk IDs, exact evidence span, extractor version, confidence, and review status. If the same relationship is found in multiple publications, model evidence as separate records linked to the relationship rather than overwriting the source.

Create Neo4j constraints for immutable source, chunk, and entity keys, and indexes for normalized entity names and build IDs. Query APIs must filter to the active published build so an incomplete ingest cannot leak into answers.

## BERTopic as a Corpus Artifact

Fit BERTopic only after a completed corpus build. Persist its model, topic labels, source/chunk membership, embedding-model ID, configuration, random seed, and evaluation summary. Show topics as “exploratory clusters” and offer links back to underlying documents. Recompute topics when the embedding model, preprocessing, or enough corpus content changes; do not silently mix topic-model versions.

## Quality Gates Before Publication

- Source schema and access metadata validate.
- Retrieval smoke queries return expected documents from the candidate build.
- A sampled set of triple evidence spans match their original chunks.
- Duplicate, empty, and parser-failed rates stay below agreed thresholds and are reported.
- Citation-validation tests pass for a fixed evaluation set.
- The build manifest is complete, including known failures.

Failure in an optional stage (Docling, graph writing, topic modelling, Qwen availability) must leave the last published corpus intact and produce a clear degraded-mode report.
