# Quality Assurance and Iteration Roadmap

## Delivery Sequence

This roadmap prioritizes a reliable evidence experience over feature breadth. Each phase ends with observable acceptance criteria before the next begins.

| Phase | Focus | Deliverables | Exit criteria |
| --- | --- | --- | --- |
| 0 — Baseline | Establish truth | Dependency audit, current capability matrix, clean-install record, fixed sample queries | Documentation distinguishes current Mistral/optional Docling state from target Qwen stack |
| 1 — Trustworthy query UX | Make the Space understandable | Auto mode, evidence cards, service states, accessible source/graph disclosures | Every answer path shows active systems, result counts, and citations/fallback reason |
| 2 — Reproducible ingestion | Stabilize 600+ source processing | Pydantic contracts, manifests, resume/idempotency, parser fallback, preflight and run report | A full corpus build is rerunnable and failures are traceable by source/stage |
| 3 — Grounded hybrid retrieval | Deliver Qwen routing and synthesis | Structured Qwen router, deterministic fallback, source-aware re-ranking, post-generation citation validation | Evaluation set shows no uncited factual claims in accepted responses |
| 4 — Graph and topics | Add research exploration carefully | Provenance graph migration, graph-path evidence, offline BERTopic artifacts | Every edge/topic links back to a corpus build and source evidence |
| 5 — Operations | Sustain open deployment | Local reference stack, health checks, rollback, release checklist, monitoring | Demo and local modes withstand optional-service loss gracefully |

## Test Strategy

### Unit and contract tests

- Pydantic models reject malformed source metadata, chunks, triples, routes, and answers.
- Canonicalization, deduplication, chunk IDs, evidence-span matching, and predicate allowlists are deterministic.
- The routing fallback is selected when Qwen returns invalid JSON, times out, or is disabled.
- Prompt construction enforces a size budget and includes only provenance-bearing evidence.
- UI formatter tests verify that citation links and unavailable-state labels are rendered safely.

### Integration tests

- Ingest a compact, public fixture corpus through both Docling-enabled and fallback-loader paths.
- Exercise vector-only, graph-only, hybrid, and no-generation modes.
- Test Neo4j schema creation and query isolation by corpus build ID using Neo4j Community.
- Start the Space with missing credentials, read-only filesystem assumptions, and unavailable remote endpoints.
- Run the publicly documented deployment command in a fresh environment.

### Evaluation set

Create a small, versioned evaluation set of researcher-style questions spanning causal, mechanism, comparison, overview, negative-evidence, and ambiguous queries. Each item should include expected sources or evidence requirements—not a single “golden” prose answer. Track:

| Metric | Definition | Release use |
| --- | --- | --- |
| Citation precision | Fraction of displayed citations that support the nearby claim | Trust gate |
| Citation completeness | Fraction of factual answer claims with eligible citations | Trust gate |
| Retrieval recall | Fraction of expected relevant sources found in top-k | Retrieval iteration |
| Route correctness | Appropriate semantic/graph/hybrid path against labelled intent | Router iteration |
| Groundedness | Human or rubric judgment that claims stay within context | Model iteration |
| P95 latency | 95th percentile response time by operating mode | UX/service budget |
| Ingestion success | Valid sources completed / valid sources attempted | Corpus health |

Report metrics by corpus build, parser version, embedding model, and Qwen model revision. Never compare scores across materially different datasets without saying so.

## Review Workflow

Use a lightweight review queue for high-impact extraction errors and user feedback. A reviewer should be able to inspect the original source passage, parsed element, triple/answer claim, model and build version, and disposition. Corrections should create a new corpus build or annotation record; they must not silently alter historical provenance.

## Release Checklist

- README and Space card describe the active model, corpus scope, data access terms, known limitations, and fallback modes accurately.
- All newly declared dependencies install in a clean environment and their licenses are reviewed.
- No source, model, or graph credential is present in tracked files, logs, or example output.
- Demo, local open-source, and maintenance/ingest paths have been exercised.
- The fixed evaluation suite and accessibility smoke test pass.
- The latest run manifest, quality report, and rollback target are available.

## Backlog Prioritization Rules

Prioritize in this order: citation correctness and data provenance; graceful service degradation; reproducible ingestion; query clarity and accessibility; retrieval quality; then discovery features such as topic maps and research-gap views. A feature should not be exposed in the public Space until it has a user-facing explanation, degraded-mode behavior, a testable acceptance criterion, and an owner.

## Definition of Done for Future Improvements

An improvement is complete only when it changes no undocumented behavior, works in the documented free/open-source mode, has a failure path that preserves the last good corpus, and has validation appropriate to its risk. For user-visible changes, this includes a short release note explaining what users will notice and how evidence or privacy is affected.
