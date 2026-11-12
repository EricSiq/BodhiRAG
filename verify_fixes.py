"""
Verification script for all FIXES.md items.
Run: python verify_fixes.py
"""
import os
import ast
import re


def r(p):
    return open(p, encoding="utf-8").read()


readme  = r("README.md")
req     = r("requirements.txt")
init    = r("src/data_ingestion/__init__.py")
vc      = r("src/graph_rag/vector_connector.py")
app     = r("app.py")
gc      = r("src/graph_rag/graph_connector.py")
ke      = r("src/data_ingestion/knowledge_extractor.py")
deploy  = r("deployment/huggingface_deploy.py")
cfg     = r("src/core/config.py")

# ── syntax checks ──────────────────────────────────────────────────────────────
print("=== SYNTAX CHECKS ===")
py_files = [
    "app.py",
    "app_with_pipeline.py",
    "src/__init__.py",
    "src/data_ingestion/__init__.py",
    "src/data_ingestion/knowledge_extractor.py",
    "src/graph_rag/vector_connector.py",
    "src/graph_rag/graph_connector.py",
    "src/core/config.py",
    "deployment/huggingface_deploy.py",
]
all_syntax_ok = True
for f in py_files:
    if not os.path.exists(f):
        print("  MISSING  " + f)
        all_syntax_ok = False
        continue
    try:
        ast.parse(open(f, encoding="utf-8").read())
        print("  OK       " + f)
    except SyntaxError as e:
        print("  SYNTAX!  " + f + "  ->  " + str(e))
        all_syntax_ok = False

# ── fix checks ─────────────────────────────────────────────────────────────────
print()
print("=== FIX STATUS ===")

results = []

def check(label, cond):
    results.append((label, cond))
    print("  " + ("DONE  " if cond else "NEEDS ") + label)


check("FIX-01  README sdk_version=4.44.1",          "sdk_version: 4.44.1" in readme)
check("FIX-02  langchain==0.0.352 removed",          "langchain==0.0.352" not in req)
check("FIX-02  langchain-community removed",         "langchain-community" not in req)
check("FIX-02  langchain-core added",                "langchain-core" in req)
check("FIX-03  chromadb==0.4.22 removed",            "chromadb==0.4.22" not in req)
check("FIX-03  chromadb>=0.5.3 added",               "chromadb>=0.5.3" in req)
check("FIX-04  pydantic-settings in req",            "pydantic-settings" in req)
check("FIX-05  ImportError guard in __init__",       "ImportError" in init)
check("FIX-05  extract_publication_data exported",   "extract_publication_data" in init)
check("FIX-06  gradio upper bound <5",               "gradio>=4.44.1,<5.0.0" in req)
check("FIX-07  /tmp/chroma_db default in vc",        "/tmp/chroma_db" in vc)

# AST-based check: no os.makedirs call inside __init__ method of VectorStoreConnector
vc_tree = ast.parse(vc)
makedirs_in_init = False
for node in ast.walk(vc_tree):
    if isinstance(node, ast.FunctionDef) and node.name == "__init__":
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and child.attr == "makedirs":
                makedirs_in_init = True
check("FIX-07  makedirs NOT in VectorStore.__init__", not makedirs_in_init)
check("FIX-07  config chroma_path=/tmp/chroma_db",    "/tmp/chroma_db" in cfg)
check("FIX-08  kg_available check in app.py",         "kg_available = kg_connector.connect()" in app)
check("FIX-08  driver guard in graph_connector",      "Neo4j unavailable" in gc)
check("FIX-09  triple.model_dump() used",             "triple.model_dump()" in ke)
check("FIX-09  triple.dict() removed",                "triple.dict()" not in ke)
check("FIX-10  src/__init__.py exists",               os.path.exists("src/__init__.py"))
check("FIX-11  deploy req has chromadb>=0.5.3",       "chromadb>=0.5.3" in deploy)
check("FIX-11  deploy req no old langchain",          "langchain==0.0.352" not in deploy)
check("FIX-12  deploy README sdk_version=4.44.1",     "sdk_version: 4.44.1" in deploy)
check("FIX-13  deploy uses lazy _get_connectors",     "_get_connectors" in deploy)

# FIX-13: the generated app.py lines list must assign to _kg_connector, not bare kg_connector
# Extract the lines list from the deploy script and inspect the KnowledgeGraphConnector line
lines_block = re.search(r"lines = \[(.*?)\]\s*app_path", deploy, re.DOTALL)
generated_uses_underscore = False
if lines_block:
    for raw_line in lines_block.group(1).split("\n"):
        if "KnowledgeGraphConnector(" in raw_line:
            generated_uses_underscore = "_kg_connector" in raw_line
check("FIX-13  generated app uses _kg_connector (not bare kg_connector)", generated_uses_underscore)

check("FIX-14  pytorch cpu wheel index",              "download.pytorch.org/whl/cpu" in req)

# FIX-15: password default must be empty string (double or single quotes)
pw_match = re.search(r'neo4j_password:\s*str\s*=\s*(["\'])([^"\']*)\1', cfg)
pw_is_empty = pw_match is not None and pw_match.group(2) == ""
check("FIX-15  config empty default password",        pw_is_empty)

# Bonus: password default in app.py and app_with_pipeline.py must also be ""
app_pw = re.search(r'NEO4J_PASSWORD.*?,\s*(["\'])([^"\']*)\1\s*\)', app)
app_pw_empty = app_pw is not None and app_pw.group(2) == ""
check("FIX-15  app.py NEO4J_PASSWORD default is empty",  app_pw_empty)

awp = r("app_with_pipeline.py")
awp_pw = re.search(r'NEO4J_PASSWORD.*?,\s*(["\'])([^"\']*)\1\s*\)', awp)
awp_pw_empty = awp_pw is not None and awp_pw.group(2) == ""
check("FIX-15  app_with_pipeline.py NEO4J_PASSWORD default is empty", awp_pw_empty)

# ── summary ────────────────────────────────────────────────────────────────────
print()
failed = [label for label, ok in results if not ok]
if all_syntax_ok and not failed:
    print("ALL CHECKS PASSED - ready to deploy")
else:
    if not all_syntax_ok:
        print("SYNTAX ERRORS found - fix before deploying")
    for label in failed:
        print("STILL NEEDS: " + label)
