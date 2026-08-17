# Open-Source Operations and Hardening Plan

## Deployment Principle

BodhiRAG must be usable without a paid API or proprietary model. Hugging Face Spaces is a distribution target, not the only supported environment. Maintain a local, self-hostable reference deployment that uses public data, open-source packages, open-weight Qwen models, Neo4j Community Edition, and local persistent storage.

## Supported Operating Modes

| Mode | Required services | Intended use | Degraded behavior |
| --- | --- | --- | --- |
| Demo | Prebuilt local vector corpus; template evidence summary | Public Space and first-run experience | No model credentials needed |
| Local open-source | Qwen served locally, Neo4j Community, local vector store | Complete reproducible development | Model service can be stopped; evidence mode remains available |
| Hosted free-tier | Public Hugging Face inference/Qwen option plus optional free hosted graph | Lightweight demonstrations | Explicit quotas, timeouts, and local fallback |
| Maintainer ingest | Local write-enabled storage and graph | Curated corpus builds | Not exposed as a shared public write path |

Use a configuration switch to identify the mode and display it in the application. Do not imply that a hosted “free tier” has unlimited availability or is suitable for production.

## Dependency and Packaging Policy

- Pin compatible version ranges, maintain a lockfile or reproducible environment definition, and test a clean install regularly.
- Declare Docling and BERTopic as clearly optional extras until the baseline installation can support them within Space resource limits.
- Split dependencies into `base`, `ingest`, `topics`, and `local-llm` groups. The query-only demo must not install large ingestion/topic dependencies unnecessarily.
- Record model name, revision/commit, tokenizer, embedding model, parser version, and chunking configuration in the corpus manifest.
- Prefer well-maintained, OSI-licensed libraries. Track license obligations for models, datasets, and bundled corpus artifacts separately from the repository’s MIT code license.

## Configuration and Secrets

Pydantic settings should be the single configuration boundary. Validate values at startup and show safe, actionable diagnostics (for example, “graph disabled: password not configured”) without printing secrets. Keep `.env` local, maintain an exhaustive `.env.template` with harmless defaults, and use Hugging Face Space Secrets for any token or password.

Required hardening rules:

- Never commit tokens, Neo4j passwords, downloaded private data, or unredacted logs.
- Set connection, fetch, embedding, and generation timeouts; bound retry count with exponential backoff and jitter.
- Restrict uploaded CSV size and validate columns, URLs, encodings, and row counts before any network fetch.
- Enforce URL allowlists for supported public sources and reject local paths, private IP ranges, redirects to unapproved hosts, and oversized responses.
- Use parameterized Cypher and a least-privilege Neo4j account; make read-only query credentials the public default.
- Limit query length, history size, concurrent requests, retrieved chunks, prompt size, and response tokens to protect shared resources.
- Sanitize and escape retrieved content before rendering it in HTML/Markdown.

## Reliability Pattern

Treat external services as optional dependencies with explicit health checks and circuit breakers. Startup should not fail because a remote model or Neo4j instance is absent. The service health hierarchy is:

1. Vector corpus available: search and source cards work.
2. Generation available: grounded answer synthesis works.
3. Graph available: relationship evidence and visual graph work.
4. Parser/topic tools available: maintainer-only enrichment works.

Publish structured logs and metrics for request ID, active corpus build, selected route, latency by stage, result counts, fallback reason, and error class. Do not log raw user queries by default; if opt-in diagnostics are introduced, state retention and redaction rules clearly.

## Data Integrity and Recovery

- Build corpus artifacts in a staging directory/database namespace, then mark a manifest as published only after validation.
- Store vector and graph artifacts with the same build ID and verify their compatibility before serving them together.
- Preserve the prior published build for rollback.
- Make ingestion idempotent through canonical source IDs and content hashes.
- Keep a failure ledger with source ID, stage, error category, retry count, and next action.
- Back up Neo4j and corpus manifests on a documented cadence; test restoration with a sample build.

## Hugging Face Spaces Considerations

Spaces can restart, sleep, and have ephemeral local storage depending on hardware and settings. Ship a small prebuilt demonstration corpus with the repository or fetch a versioned public artifact at startup with integrity checks. Do not depend on `/tmp` for the only copy of a production corpus. Keep public Spaces in read-only query mode, minimize startup work, and provide clear first-load progress rather than a blank or unresponsive interface.

## Operational Acceptance Checks

- A fresh environment reaches demo mode with no secret configured.
- Loss of Neo4j, the Qwen endpoint, or Docling results in a labelled fallback, not an application crash.
- A malformed upload and an unreachable source are rejected/recorded without corrupting the published corpus.
- A restarted Space can identify and load its last compatible corpus build.
- A maintainer can reproduce a build from its manifest and verify counts and source hashes.
