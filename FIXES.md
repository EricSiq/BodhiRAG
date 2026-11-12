# BodhiRAG — HF Spaces Deployment Fix Plan

This document lists every confirmed issue with exact file locations, the root cause,
and the precise change required. Fixes are ordered by severity then dependency:
critical blockers first, then runtime errors, then quality improvements.

---

## SECTION 1 — BUILD BLOCKERS (Space never starts)

These issues prevent `pip install` or Gradio launch from completing at all.

---

### FIX-01 · `sdk_version` in README.md is unsupported

**File:** `README.md` — line 7  
**Current value:** `sdk_version: 4.0.0`  
**Root cause:** HF Spaces validates the `sdk_version` YAML field against a list of
supported Gradio versions. `4.0.0` is no longer on that list. The Space fails at
the "Building" phase with a validation error before any code runs.  
**Required change:** Bump to a current supported version.

```yaml
# BEFORE
sdk_version: 4.0.0

# AFTER
sdk_version: 4.44.1
```

---

### FIX-02 · `langchain==0.0.352` and `langchain-community==0.0.15` cannot be installed

**File:** `requirements.txt` — lines 7–8  
**Current values:**
```
langchain==0.0.352
langchain-community==0.0.15
```
**Root cause:** `langchain-community==0.0.15` does not exist on PyPI — the package
did not exist until `0.0.1` was published on the new versioning track, but
`0.0.15` predates the community split and is not resolvable. `langchain==0.0.352`
is the last of the old monolith series; it pins `langchain-core<0.0.4` internally
which directly conflicts with the `langchain-core` imports already used throughout
the codebase (`langchain_core.documents`, `langchain_core.prompts`, etc.).

The code only uses `langchain-core` — the full `langchain` and
`langchain-community` packages are never imported anywhere in the source files.
They can be replaced entirely.

**Required change:**
```
# REMOVE both lines and ADD:
langchain-core>=0.2.0,<0.4.0
```

---

### FIX-03 · `chromadb==0.4.22` conflicts with `pydantic>=2.6.0`

**File:** `requirements.txt` — line 3  
**Current value:** `chromadb==0.4.22`  
**Root cause:** ChromaDB 0.4.x uses Pydantic v1 internally for its own models.
With `pydantic>=2.6.0` also required, pip either fails to resolve the constraint
or installs a broken mix that raises `PydanticUserError` at import time.
ChromaDB 0.5.x was the first release with full Pydantic v2 compatibility.
ChromaDB 0.6.x is the current stable line.

The code uses `chromadb.PersistentClient` and `chromadb.config.Settings` —
both APIs are unchanged in 0.5.x/0.6.x.

**Required change:**
```
# BEFORE
chromadb==0.4.22

# AFTER
chromadb>=0.5.3,<0.7.0
```

---

### FIX-04 · `pydantic-settings` not in `requirements.txt`

**File:** `requirements.txt` (missing entry)  
**Root cause:** `src/core/config.py` line 2 does:
```python
from pydantic_settings import BaseSettings
```
Since Pydantic v2, `pydantic-settings` is a separate package not bundled with
`pydantic`. It is not in `requirements.txt`. Any module that imports
`src.core.config` (including startup) will raise `ModuleNotFoundError`.

**Required change:** Add to `requirements.txt`:
```
pydantic-settings>=2.0.0,<3.0.0
```

---

### FIX-05 · `src/data_ingestion/__init__.py` unconditional import crashes the package

**File:** `src/data_ingestion/__init__.py` — line 8  
**Current code:**
```python
from .document_loader import load_and_chunk_documents
```
**Root cause:** `document_loader.py` attempts `from langchain_docling import DoclingLoader`
at module level (it is guarded by a try/except), but the import of
`load_and_chunk_documents` itself is *not* guarded in `__init__.py`. On HF Spaces
where `langchain_docling` is absent, `document_loader.py` loads fine (the guard
catches the import error), but if any downstream issue occurs during that module
load, `__init__.py` will re-raise it.

More critically, `__init__.py` also **does not export `extract_publication_data`**
even though it lists it in `__all__` — `extract_publication_data` is defined in
`document_loader.py` but is not imported in `__init__.py`. `app.py` line 22 does:
```python
from src.data_ingestion.document_loader import extract_publication_data
```
which works, but `app.py` also does:
```python
from src.data_ingestion import extract_knowledge_from_chunk
```
If the package init ever fails, this crashes too.

**Required change:** Guard the `document_loader` import and correctly export
`extract_publication_data`:
```python
# BEFORE
from .document_loader import load_and_chunk_documents
from .knowledge_extractor import Entity, RelationshipTriple, extract_knowledge_from_chunk

# AFTER
try:
    from .document_loader import load_and_chunk_documents, extract_publication_data
except ImportError:
    load_and_chunk_documents = None
    extract_publication_data = None

from .knowledge_extractor import Entity, RelationshipTriple, extract_knowledge_from_chunk
```

---

### FIX-06 · `gradio>=4.0.0` open lower bound pulls incompatible version

**File:** `requirements.txt` — line 1  
**Current value:** `gradio>=4.0.0`  
**Root cause:** Without an upper bound, pip may resolve to Gradio 5.x which has
breaking API changes (`gr.File` `type` parameter changed, some component APIs
differ). The `sdk_version: 4.44.1` in README.md tells HF Spaces to use Gradio
4.x, but a loose requirement can pull 5.x into the installed environment, causing
a version mismatch and component errors.

**Required change:**
```
# BEFORE
gradio>=4.0.0

# AFTER
gradio>=4.44.1,<5.0.0
```

---

## SECTION 2 — RUNTIME ERRORS (Space starts but crashes on use)

---

### FIX-07 · `VectorStoreConnector()` called at module scope writes to read-only path

**File:** `app.py` — lines 33–34  
**Current code:**
```python
vs_connector = VectorStoreConnector()   # runs os.makedirs at __init__ time
```
**File:** `src/graph_rag/vector_connector.py` — lines 22–28  
```python
project_root = Path(__file__).parent.parent.parent
self.persist_directory = str(project_root / "data" / "chroma_db")
os.makedirs(self.persist_directory, exist_ok=True)  # called in __init__
```
**Root cause:** On HF Spaces (and Docker), the app directory `/app` is often
read-only after the build phase. Calling `os.makedirs` at import time (inside
`__init__`) attempts to create `/app/data/chroma_db` and raises
`PermissionError`, which prevents the Gradio app from loading entirely.

The only guaranteed writable location at runtime is `/tmp`.

**Required change in `vector_connector.py`:** Change the default persist path to
`/tmp/chroma_db` and move the `makedirs` call out of `__init__` into
`initialize_store` where it belongs:

```python
# __init__: only set the path, do NOT call makedirs
if persist_directory is None:
    self.persist_directory = os.environ.get(
        "CHROMA_PATH", "/tmp/chroma_db"
    )
else:
    self.persist_directory = str(persist_directory)

# initialize_store: create dir here, just before first use
os.makedirs(self.persist_directory, exist_ok=True)
```

**Required change in `src/core/config.py`:**
```python
# BEFORE
chroma_path: str = "./data/chroma"

# AFTER
chroma_path: str = "/tmp/chroma_db"
```

---

### FIX-08 · `kg_connector.connect()` return value never checked before querying

**File:** `app.py` — `query_bodhirag` function, lines ~50–54  
**Current code:**
```python
if use_kg:
    kg_connector.connect()          # return value ignored
# ... then agent.route_query() calls kg_connector.query_relationships()
# which calls self.driver.session() where self.driver is None → AttributeError
```
**Root cause:** `graph_connector.connect()` returns `True`/`False` and sets
`self.driver = None` on failure (caught exception). The caller ignores the return
value, so subsequent queries run against a `None` driver and raise
`AttributeError: 'NoneType' object has no attribute 'session'` — an unhelpful
crash with no user-facing explanation.

**Required change in `app.py`:** Check the return value and disable KG gracefully:
```python
if use_kg:
    kg_available = kg_connector.connect()
    if not kg_available:
        use_kg = False   # fall through to vector-only mode
```

**Required change in `graph_connector.py`:** Add a guard in `query_relationships`
and any other method that uses `self.driver`:
```python
def query_relationships(self, entity_name: str) -> List[Dict]:
    if not self.driver:
        return []
    ...
```

---

### FIX-09 · `triple.dict()` deprecated in Pydantic v2 — will error in strict mode

**File:** `src/data_ingestion/knowledge_extractor.py` — line 83  
**Current code:**
```python
triple_dict = triple.dict()
```
**Root cause:** Pydantic v2 renames `.dict()` to `.model_dump()`. Calling `.dict()`
still works in v2 but emits a `PydanticDeprecatedSince20` warning that is treated
as an error when `PYTHONWARNINGS=error` (which HF Spaces can trigger in strict
build environments). Safer to use the v2 API explicitly.

**Required change:**
```python
# BEFORE
triple_dict = triple.dict()

# AFTER
triple_dict = triple.model_dump()
```

---

### FIX-10 · `src/__init__.py` is missing — package imports may fail

**File:** `src/` directory (file does not exist)  
**Root cause:** Python requires each directory in an import chain to have an
`__init__.py` to be treated as a package (in non-namespace-package setups).
`app.py` does `from src.graph_rag.graph_connector import ...`. If `src/__init__.py`
is absent, this works only if the Python path is set up to treat `src` as a
namespace package. HF Spaces runs with a standard CPython install where this is
not guaranteed. Adding an empty `__init__.py` is the safe, explicit fix.

**Required change:** Create `src/__init__.py` as an empty file.

---

## SECTION 3 — DEPLOYMENT SCRIPT ISSUES (Generated files repeat the bugs)

---

### FIX-11 · `deployment/huggingface_deploy.py` generates stale `requirements.txt`

**File:** `deployment/huggingface_deploy.py` — `_create_hf_requirements` method  
**Current generated content:**
```
langchain==0.0.352
langchain-community==0.0.15
chromadb==0.4.22
gradio>=4.0.0
torch>=2.0.0
```
**Root cause:** The deploy script writes its own hardcoded requirements into
`deployment/hf_space/requirements.txt`. Running the script after fixing the root
`requirements.txt` would overwrite all the fixes with the old broken versions.

**Required change:** Update `_create_hf_requirements` to write the correct
dependency versions matching the root `requirements.txt` fixes (FIX-01 through
FIX-06). The method should also add `pydantic-settings`.

---

### FIX-12 · `deployment/huggingface_deploy.py` generates stale `README.md` with `sdk_version: 4.0.0`

**File:** `deployment/huggingface_deploy.py` — `_create_readme` method  
**Current generated content:**
```yaml
sdk_version: 4.0.0
```
**Root cause:** Same as FIX-01. The deploy script independently hardcodes the
outdated SDK version in the README it generates for the HF Space.

**Required change:** Update `_create_readme` to write `sdk_version: 4.44.1`.

---

### FIX-13 · `deployment/huggingface_deploy.py` generated `app.py` has module-scope connector init

**File:** `deployment/huggingface_deploy.py` — `_create_gradio_app` method  
**Root cause:** The generated `app.py` written by `_create_gradio_app` initialises
`KnowledgeGraphConnector`, `VectorStoreConnector`, and `HybridRAGAgent` at module
scope (same pattern as the bugs in FIX-07 and FIX-08). It also does not include
`src/__init__.py` creation or the corrected path for ChromaDB.

**Required change:** Update `_create_gradio_app` to use lazy/deferred
initialization of connectors inside a function call, not at module scope.

---

## SECTION 4 — QUALITY / CORRECTNESS

---

### FIX-14 · `torch>=2.0.0` without bounds pulls a 2.5GB CPU+CUDA wheel

**File:** `requirements.txt` — line 9  
**Current value:** `torch>=2.0.0`  
**Root cause:** An unbounded `torch` requirement will pull the latest version
including CUDA libraries, even on CPU-only HF Spaces. This bloats the Docker
image by ~2.5GB and causes build timeouts. The `--extra-index-url` for the
PyTorch CPU-only wheel must be added to keep the install under 1GB.

**Required change:**
```
# BEFORE
torch>=2.0.0

# AFTER
torch>=2.2.0,<3.0.0
--extra-index-url https://download.pytorch.org/whl/cpu
```
Note: for `requirements.txt` the extra-index-url line must appear before the
`torch` line, or be placed in a `pip.conf`. The cleanest HF Spaces approach is
to add it at the top of `requirements.txt`.

---

### FIX-15 · `neo4j_username` default is `"neo4j"` but `neo4j_password` default is `"password"`

**File:** `src/core/config.py` — lines 6–8  
**Root cause:** The default password `"password"` was valid for older Neo4j
Community editions (pre-5.x) but Neo4j 5.x requires the password to be changed
on first login and will not accept this default. If someone uses `config.py`
defaults instead of env vars, the Neo4j driver will connect but authentication
fails. The default should be empty/None to force explicit configuration.

**Required change:**
```python
# BEFORE
neo4j_password: str = "password"

# AFTER
neo4j_password: str = ""
```

---

## SUMMARY TABLE

| ID      | File(s)                                       | Category        | Impact if not fixed                        |
|---------|-----------------------------------------------|-----------------|--------------------------------------------|
| FIX-01  | `README.md`                                   | Build blocker   | Space rejected at HF validation stage      |
| FIX-02  | `requirements.txt`                            | Build blocker   | `pip install` fails, Space never builds    |
| FIX-03  | `requirements.txt`                            | Build blocker   | Pydantic conflict, ChromaDB import error   |
| FIX-04  | `requirements.txt`                            | Build blocker   | `ModuleNotFoundError` on startup           |
| FIX-05  | `src/data_ingestion/__init__.py`              | Build blocker   | Package import crashes, app won't load     |
| FIX-06  | `requirements.txt`                            | Build blocker   | Gradio version mismatch with sdk_version   |
| FIX-07  | `src/graph_rag/vector_connector.py`, `app.py` | Runtime error   | `PermissionError` on startup               |
| FIX-08  | `app.py`, `src/graph_rag/graph_connector.py`  | Runtime error   | `AttributeError` on every KG query        |
| FIX-09  | `src/data_ingestion/knowledge_extractor.py`   | Runtime error   | `DeprecationWarning`/error in Pydantic v2  |
| FIX-10  | `src/` (missing file)                         | Runtime error   | Import chain fails without `__init__.py`   |
| FIX-11  | `deployment/huggingface_deploy.py`            | Deploy script   | Script regenerates all broken requirements |
| FIX-12  | `deployment/huggingface_deploy.py`            | Deploy script   | Script regenerates wrong sdk_version       |
| FIX-13  | `deployment/huggingface_deploy.py`            | Deploy script   | Script regenerates bad module-scope init   |
| FIX-14  | `requirements.txt`                            | Quality         | 2.5GB+ build, timeout on free tier        |
| FIX-15  | `src/core/config.py`                          | Quality         | Silent auth failure with default password  |

---

## IMPLEMENTATION ORDER

1. FIX-01 — README.md sdk_version  
2. FIX-02, FIX-03, FIX-04, FIX-06, FIX-14 — requirements.txt (all at once)  
3. FIX-05 — src/data_ingestion/__init__.py  
4. FIX-10 — Create src/__init__.py  
5. FIX-07 — vector_connector.py path + config.py  
6. FIX-08 — graph_connector.py guard + app.py connect check  
7. FIX-09 — knowledge_extractor.py model_dump  
8. FIX-15 — config.py password default  
9. FIX-11, FIX-12, FIX-13 — deployment/huggingface_deploy.py  
