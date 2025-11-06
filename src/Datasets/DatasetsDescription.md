

## Dataset Description

The BodhiRAG dataset is derived from a curated CSV of **607+ NASA bioscience publications** (PMC-hosted). Each row represents a single paper and includes metadata such as:

| Field      | Description                          |
| ---------- | ------------------------------------ |
| `Title`    | The title of the publication         |
| `Link`     | PMC URL to the full paper            |
| `Authors`  | List of contributing authors         |
| `Abstract` | Text summary of the study            |
| `Year`     | Publication year                     |
| `Keywords` | Author-assigned or database keywords |

### Problem Statement:

Space biology research spans multiple domains (radiation biology, microgravity physiology, closed-loop life support, etc.), but existing literature is fragmented across papers, data repositories, and funding documents. Researchers, managers, and mission designers struggle to:

* **Connect findings across experiments**
* **See crosscutting trends and gaps**
* **Formulate multi-step hypotheses backed by evidence**

### My Approach:

BodhiRAG transforms this static CSV of publications into a **rich, queryable knowledge engine** by:

1. **Parsing full documents via Docling** to convert unstructured content (PDFs) into structured semantic units.
2. Extracting **entities and relations** to build a **Knowledge Graph** for multi-hop reasoning.
3. Embedding text chunks into a **vector store** for contextual search and similarity matching.
4. Combining KG + vector search through an **agentic hybrid RAG approach** to answer deep scientific queries with provenance.

In this way, we turn a flat list of publications into an **explainable, interactive body of knowledge** that supports hypothesis generation, research gap discovery, and mission risk analysis in space biology.

---

If you share the exact column names from your CSV, I can tailor this dataset description further. Would you like me to do that?

