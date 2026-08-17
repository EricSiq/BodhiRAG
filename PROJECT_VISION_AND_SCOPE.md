# BodhiRAG Product Vision and Scope

## Purpose

BodhiRAG is an open research assistant for NASA space-biology and astronomy-adjacent literature. It should help a researcher move from a natural-language question to an answer that is traceable to specific passages and graph relationships. It is a research-navigation tool, not a source of clinical, operational, or mission-critical advice.

The product combines four evidence layers:

1. **Publications and assets** — NASA and other permissively accessible scientific material, including text, tables, figures, and captions.
2. **Semantic retrieval** — passage-level search for relevant textual evidence.
3. **Knowledge graph** — normalized entities and evidence-backed relationships for multi-hop and mechanism questions.
4. **Grounded synthesis** — a Qwen-family instruct model that answers only from retrieved evidence and returns source citations.

## Current State and Target State

The repository already contains a Gradio interface, Chroma-based semantic search, Neo4j connectors, Pydantic models for triple extraction, an optional Docling loader, and a BERTopic module. The default inference service currently refers to Mistral rather than Qwen; Docling and BERTopic are not declared as required runtime dependencies. Documentation and implementation should therefore use the following terminology consistently:

| Capability | Current repository posture | Target product posture |
| --- | --- | --- |
| Answer model | Hosted Mistral endpoint with template fallback | Configurable Qwen Instruct provider; local/open weights first, template fallback retained |
| Document parsing | HTML loader is dependable; Docling is optional | Docling for supported multimodal files, deterministic text/HTML fallback |
| Graph | Optional external Neo4j | Neo4j Community Edition locally or a clearly labelled optional hosted free tier |
| Topics | BERTopic module exists but is not integrated | Offline, versioned corpus-analysis job; never a required query-path dependency |
| Query routing | Keyword intent classification | Bounded, observable router that selects semantic, graph, or hybrid retrieval and reports why |

No document should claim that all 600+ publications, Docling multimodal extraction, Qwen routing, or BERTopic-powered discovery are live until each has a reproducible build record and acceptance evidence.

## Primary Users and Jobs

| User | Primary job | Successful outcome |
| --- | --- | --- |
| Researcher | Understand a mechanism or compare findings | A concise answer with direct, inspectable evidence |
| Student | Explore an unfamiliar topic | Plain-language explanation, suggested query refinements, and source context |
| Data curator | Ingest and improve a corpus | A resumable run with counts, failures, provenance, and validation results |
| Maintainer | Run the project without paid services | A documented local stack and predictable degraded modes |

## Product Principles

- **Evidence before eloquence.** Every substantive claim in an answer maps to one or more source cards. If support is absent, say so.
- **Progressive disclosure.** Show an answer first; reveal route reasoning, graph paths, scores, chunks, and raw metadata on demand.
- **Honest capability status.** The UI must distinguish ready, degraded, indexing, and unavailable states. It must never imply a graph or model was used when it was not.
- **Reproducible public science.** Preserve source URL, publication identifier, retrieval timestamp, parser version, chunk version, and extraction-model version.
- **Free and open source by default.** A local-only path must work using open-weight models and self-hostable storage. Hosted free tiers are conveniences, not dependencies.
- **Safe uncertainty.** State coverage limits, contradiction, and confidence; do not convert weak retrieval into a definitive conclusion.

## Success Criteria

Release readiness requires all of the following:

- A fresh local install can query a prebuilt public sample corpus without credentials.
- A full 600+ publication ingest is resumable and produces a machine-readable manifest of every source and outcome.
- Each answer presents source cards with title, persistent identifier or URL, passage, and retrieval provenance.
- The interface remains useful when the graph, model, or optional multimodal parser is unavailable.
- Qwen, Docling, Neo4j, Pydantic, and BERTopic have explicit ownership, versioning, test coverage, and fallback behavior.
- No required feature relies on a paid API, proprietary model, or silently collected user data.

## Non-Goals

- Replacing expert interpretation of scientific literature.
- Inferring results not supported by retrieved publications.
- Treating BERTopic clusters as validated research gaps without methodological review.
- Uploading user files or queries to third parties without a clear, affirmative user choice.
