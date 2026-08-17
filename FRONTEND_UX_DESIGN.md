# Frontend UX Improvement Specification

## Design Objective

The Gradio Space should feel like a trustworthy research workbench rather than a collection of database controls. The current tabbed layout (Ask, Data Pipeline, Statistics, About) is a sensible base. The next iteration should reduce configuration burden, make evidence visible, and clearly communicate degraded service states.

## Recommended Information Architecture

### 1. Ask

This is the default page. Keep the query box prominent, with one primary action: **Ask BodhiRAG**. Replace raw retrieval toggles as the first decision with a plain-language mode selector:

| Mode | User-facing copy | System behavior |
| --- | --- | --- |
| Auto (default) | “Choose the best evidence path” | Router selects semantic, graph, or hybrid retrieval |
| Literature | “Search publication passages” | Vector retrieval only |
| Relationships | “Explore entities and mechanisms” | Graph retrieval with semantic fallback when no graph evidence exists |
| Both | “Combine literature and relationships” | Hybrid retrieval |

Keep expert controls behind an **Advanced retrieval settings** disclosure. These can include result count, source-date filter, model selection, and the existing independent graph/vector switches. Preserve current values in the browser session so experiments are repeatable.

### 2. Sources and reasoning

Do not place raw KG and vector output beside the answer by default. Instead, show an **Evidence** panel directly below each answer:

- A short route badge: `Hybrid • 2 graph relationships • 4 literature passages`.
- Numbered source cards that match inline answer citations, for example `[S1]`.
- Each card shows title, source URL/identifier, publication year when available, supporting passage, and why it was selected.
- A “Graph path” disclosure presents subject → relationship → object plus its evidence span.
- A “No supporting source found” state prevents empty panels from looking like a successful search.

The existing Plotly graph should be optional, accessible after the evidence cards, and accompanied by a textual graph-path equivalent. This improves mobile usability and accessibility.

### 3. Corpus and ingestion

The current Data Pipeline tab exposes an upload and a “Run Pipeline” button. Because a full run can be slow and external-network dependent, present it as a guided workflow:

1. **Choose data** — use the bundled NASA catalog or upload a catalogue; explain accepted columns and data handling.
2. **Preflight** — display parser availability, storage capacity, Neo4j status, model availability, duplicate estimate, and projected scope.
3. **Run** — show stage progress and an explicit cancel/retry/resume option.
4. **Review** — report processed, skipped, failed, duplicated, chunked, embedded, and graph-written counts. Let the curator download a run manifest.

The normal public Space should default to query-only mode. Put write-capable ingestion behind a clearly labelled maintainer configuration, because concurrent user uploads can contaminate a shared public corpus.

### 4. Explore

Promote the current Statistics tab into **Explore the corpus**. It should provide corpus coverage, recent ingestion build ID, topic browse (when a BERTopic artifact is available), and suggested example queries. Label topic clusters as exploratory and include the corpus version used to create them.

## Interaction States

Use a compact persistent status bar, but phrase states for people rather than infrastructure:

| State | Message | Allowed behavior |
| --- | --- | --- |
| Ready | “Literature and relationship evidence are ready.” | Full query experience |
| Literature only | “Relationship evidence is temporarily unavailable; literature search remains active.” | Automatic semantic fallback |
| Evidence only | “Answer generation is unavailable; showing retrieved evidence.” | Retrieval and source cards |
| Indexing | “The corpus is being updated. Search uses build `<id>`.” | Read-only queries against last complete build |
| Needs setup | “No searchable corpus is installed.” | Explain setup and show sample workflow |

Never use a green “connected” indicator to imply that retrieved results are reliable. Connectivity and evidence sufficiency are separate states.

## Answer Format

Use a stable response template:

1. **Direct answer** — 2–5 sentences, qualified when evidence is incomplete.
2. **What the evidence shows** — short bullets with inline source markers.
3. **Limits or disagreement** — missing coverage, conflicting sources, or an explicit “not established by retrieved sources.”
4. **Sources** — expandable cards.
5. **Next question** — one or two query suggestions based on corpus terms, not invented facts.

When no model is available, label the result “Retrieved evidence summary” rather than presenting template text as an AI-generated answer.

## Accessibility, Mobile, and Trust

- Meet WCAG 2.2 AA contrast and keyboard navigation expectations; do not rely on color, emoji, or hover alone for status.
- Use semantic headings, descriptive button labels, visible focus states, and text alternatives for the graph visualization.
- Keep important controls and evidence usable at 320 px width; side-by-side source/graph panels should stack on narrow screens.
- Provide plain-language help for “knowledge graph,” “semantic search,” and “confidence.”
- State that questions may be processed by the selected local or hosted model provider, and expose the active provider in the UI.
- Add a feedback affordance for “citation mismatch,” “missing source,” and “answer quality,” storing no personal information by default.

## UX Acceptance Checks

- A first-time visitor can ask an example question and open its sources in two interactions or fewer.
- A visitor can tell exactly which retrieval systems contributed to the answer.
- With Neo4j disabled, the route and source panels explain the semantic fallback without errors or blank artifacts.
- With generation disabled, the app returns useful evidence cards rather than a failed chat response.
- A keyboard-only user can submit, inspect sources, and clear a conversation.
