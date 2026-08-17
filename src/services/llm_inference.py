"""
BodhiRAG LLM Service
Supports both Mistral (current) and Qwen (target) models.
Implements model configuration from PROJECT_VISION_AND_SCOPE.md

Primary: Qwen Instruct (open weights, local-first)
Fallback: Mistral-7B via HF Inference API
Final fallback: Template-based synthesis
"""

import os
import json
import time
import logging
import requests
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    MISTRAL_HF = "mistral"
    QWEN_LOCAL = "qwen"
    TEMPLATE = "template"


# ---------------------------------------------------------------------------
# Model configuration - configurable via environment
# ---------------------------------------------------------------------------
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mistral").lower()

# Model endpoints
MISTRAL_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
QWEN_MODEL = os.environ.get("QWEN_MODEL", "Qwen/Qwen2.5-7B-Instruct")

HF_API_URL_MISTRAL = f"https://api-inference.huggingface.co/models/{MISTRAL_MODEL}"
HF_API_URL_QWEN = f"https://api-inference.huggingface.co/models/{QWEN_MODEL}"

HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Local model path (for Qwen)
QWEN_LOCAL_PATH = os.environ.get("QWEN_LOCAL_PATH", "")
QWEN_LOCAL_ENABLED = os.environ.get("QWEN_LOCAL_ENABLED", "false").lower() == "true"


# ---------------------------------------------------------------------------
# Routing schema for Qwen structured output
# ---------------------------------------------------------------------------

ROUTING_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {
            "type": "string",
            "enum": ["semantic", "graph", "hybrid", "clarify"]
        },
        "reason": {"type": "string"},
        "entities": {
            "type": "array",
            "items": {"type": "string"}
        },
        "filters": {"type": "object"},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": "string"}
    },
    "required": ["route"]
}


# ---------------------------------------------------------------------------
# Core inference function
# ---------------------------------------------------------------------------

def _get_api_url() -> str:
    """Get the appropriate API URL based on provider."""
    if LLM_PROVIDER == "qwen" and not QWEN_LOCAL_ENABLED:
        return HF_API_URL_QWEN
    return HF_API_URL_MISTRAL


def _hf_inference(prompt: str, max_new_tokens: int = 512, temperature: float = 0.3) -> str:
    """
    Call the HF Inference API.
    Returns the generated text, or raises an exception on unrecoverable error.
    """
    if not HF_TOKEN:
        logger.warning("HF_TOKEN not set - cannot call HF API")
        return ""
    
    api_url = _get_api_url()
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "return_full_text": False,
            "do_sample": True,
            "top_p": 0.9,
        },
        "options": {"wait_for_model": True},
    }

    for attempt in range(3):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=90)

            if response.status_code == 503:
                # Model is loading: wait and retry
                wait = int(response.headers.get("X-WaitFor", 20))
                logger.info(f"Model loading, waiting {wait}s (attempt {attempt + 1})")
                time.sleep(min(wait, 30))
                continue

            if response.status_code == 429:
                logger.warning("Rate limited, waiting 10s")
                time.sleep(10)
                continue

            response.raise_for_status()
            data = response.json()

            if isinstance(data, list) and data:
                return data[0].get("generated_text", "").strip()
            elif isinstance(data, dict) and "generated_text" in data:
                return data["generated_text"].strip()
            else:
                logger.error(f"Unexpected API response format: {data}")
                return ""

        except requests.exceptions.Timeout:
            logger.warning(f"Request timeout (attempt {attempt + 1})")
            if attempt == 2:
                raise
            time.sleep(5)
        except Exception as e:
            logger.error(f"HF Inference error: {e}")
            if attempt == 2:
                raise
            time.sleep(3)

    return ""


def _local_qwen_inference(prompt: str, max_new_tokens: int = 512, temperature: float = 0.3) -> str:
    """
    Call local Qwen model if available.
    Falls back to HF API if local model not configured.
    """
    if not QWEN_LOCAL_ENABLED:
        return _hf_inference(prompt, max_new_tokens, temperature)
    
    try:
        # Import transformers only if local model is enabled
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        # Load model (cached after first load)
        if not hasattr(_local_qwen_inference, '_model'):
            logger.info(f"Loading local Qwen model from {QWEN_LOCAL_PATH or QWEN_MODEL}")
            tokenizer = AutoTokenizer.from_pretrained(QWEN_LOCAL_PATH or QWEN_MODEL)
            model = AutoModelForCausalLM.from_pretrained(
                QWEN_LOCAL_PATH or QWEN_MODEL,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None
            )
            _local_qwen_inference._model = model
            _local_qwen_inference._tokenizer = tokenizer
        
        tokenizer = _local_qwen_inference._tokenizer
        model = _local_qwen_inference._model
        
        inputs = tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
            )
        
        generated = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return generated.strip()
        
    except Exception as e:
        logger.error(f"Local Qwen inference failed: {e}")
        logger.info("Falling back to HF API")
        return _hf_inference(prompt, max_new_tokens, temperature)


# ---------------------------------------------------------------------------
# Routing with Qwen (structured output)
# ---------------------------------------------------------------------------

ROUTING_PROMPT = """Analyze this research question and determine the best retrieval strategy.

Question: {query}

Return a JSON object with these fields:
- route: "semantic" (search literature), "graph" (explore relationships), "hybrid" (both), or "clarify" (ambiguous)
- reason: brief explanation of the routing decision
- entities: list of named entities mentioned
- needs_clarification: true if question is ambiguous

Examples:
- "What causes bone loss?" → graph (causal relationship)
- "Describe microgravity effects" → semantic (overview)
- "How does radiation affect DNA repair?" → hybrid (mechanism + literature)
- "What about space?" → clarify (too vague)

Return ONLY the JSON object, no other text."""


def classify_route_with_qwen(query: str) -> Dict[str, Any]:
    """
    Use Qwen to classify query routing with structured output.
    Returns dict with route, reason, entities, needs_clarification.
    Falls back to keyword routing if Qwen unavailable.
    """
    if LLM_PROVIDER not in ["qwen", "mistral"] or (not HF_TOKEN and not QWEN_LOCAL_ENABLED):
        return _fallback_route_classification(query)
    
    try:
        prompt = ROUTING_PROMPT.format(query=query)
        raw = _local_qwen_inference(prompt, max_new_tokens=300, temperature=0.1) if QWEN_LOCAL_ENABLED else _hf_inference(prompt, max_new_tokens=300, temperature=0.1)
        
        if not raw:
            return _fallback_route_classification(query)
        
        # Extract JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
            # Validate route is valid
            if result.get("route") not in ["semantic", "graph", "hybrid", "clarify"]:
                result["route"] = "hybrid"
            return result
        
        return _fallback_route_classification(query)
        
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Route classification failed: {e}")
        return _fallback_route_classification(query)


def _fallback_route_classification(query: str) -> Dict[str, Any]:
    """Keyword-based fallback routing."""
    q = query.lower()
    
    # Graph patterns (relationships, mechanisms, causality)
    graph_patterns = [
        "relationship", "effect", "cause", "impact", "influence",
        "how does", "what causes", "what affects", "mechanism",
        "interaction", "pathway", "link between", "connection",
    ]
    
    # Semantic patterns (descriptions, overviews)
    semantic_patterns = [
        "describe", "what is", "explain", "overview", "summary",
        "information about", "details about", "tell me about",
        "background", "introduction", "review",
    ]
    
    if any(p in q for p in graph_patterns):
        return {"route": "graph", "reason": "Query asks about relationships or mechanisms", "entities": [], "needs_clarification": False}
    elif any(p in q for p in semantic_patterns):
        return {"route": "semantic", "reason": "Query asks for description or overview", "entities": [], "needs_clarification": False}
    else:
        return {"route": "hybrid", "reason": "Query may benefit from both sources", "entities": [], "needs_clarification": False}


# ---------------------------------------------------------------------------
# RAG answer synthesis
# ---------------------------------------------------------------------------

RAG_SYSTEM_PROMPT_MISTRAL = """You are BodhiRAG, an expert AI assistant specializing in NASA space biology research. 
You answer questions based on peer-reviewed research from NASA's Bioscience program.
Be precise, cite the provided context, and note limitations clearly.
If the context is insufficient, say so rather than hallucinating."""

RAG_SYSTEM_PROMPT_QWEN = """You are BodhiRAG, an expert AI assistant specializing in NASA space biology research.
You answer questions based on peer-reviewed research from NASA's Bioscience program.

Guidelines:
1. Provide direct, evidence-based answers
2. Use [S1], [S2] citations to reference sources
3. Note when evidence is incomplete or conflicting
4. Suggest 1-2 follow-up questions based on the corpus

Do not make claims without citation support."""


def build_rag_prompt(
    query: str,
    kg_results: list,
    vs_results: list,
    provider: str = "mistral",
) -> str:
    """Build a structured RAG prompt for the appropriate model format."""
    
    # Build context sections
    context_parts = []

    if kg_results:
        kg_section = "## Knowledge Graph Relationships\n"
        for i, rel in enumerate(kg_results[:6], 1):
            subj = rel.get("subject", "")
            pred = rel.get("relationship", "")
            obj = rel.get("object", "")
            evidence = rel.get("evidence", "")
            kg_section += f"{i}. **{subj}** → *{pred}* → **{obj}**"
            if evidence:
                kg_section += f"\n   Evidence: \"{evidence[:150]}\""
            kg_section += "\n"
        context_parts.append(kg_section)

    if vs_results:
        vs_section = "## Research Literature\n"
        for i, doc in enumerate(vs_results[:4], 1):
            content = doc.get("content", "")[:400]
            title = doc.get("metadata", {}).get("source_title", "NASA Publication")
            score = doc.get("score", 0)
            vs_section += f"**[S{i}]** *{title}* (relevance: {score:.2f})\n{content}\n\n"
        context_parts.append(vs_section)

    if not context_parts:
        context_str = "No specific context retrieved from the knowledge base."
    else:
        context_str = "\n".join(context_parts)

    # Different prompt formats for different models
    if provider == "qwen":
        # Qwen instruct format
        system_prompt = RAG_SYSTEM_PROMPT_QWEN
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n## Research Context\n{context_str}\n\n## Question\n{query}\n\nProvide a comprehensive, evidence-based answer with citations.<|im_end|>\n<|im_start|>assistant\n"
    else:
        # Mistral instruct format
        system_prompt = RAG_SYSTEM_PROMPT_MISTRAL
        prompt = f"[INST] {system_prompt}\n\n## Research Context\n{context_str}\n\n## Question\n{query}\n\nProvide a comprehensive, evidence-based answer referencing the sources above. [/INST]"
    
    return prompt


def generate_answer(
    query: str,
    kg_results: list,
    vs_results: list,
) -> str:
    """
    Generate an LLM-powered answer using configured provider.
    Falls back to template synthesis if no model is available.
    """
    # Check if any model is available
    if LLM_PROVIDER == "template" or (not HF_TOKEN and not QWEN_LOCAL_ENABLED):
        return _template_fallback(query, kg_results, vs_results)

    try:
        provider = LLM_PROVIDER if LLM_PROVIDER in ["mistral", "qwen"] else "mistral"
        prompt = build_rag_prompt(query, kg_results, vs_results, provider)
        
        if QWEN_LOCAL_ENABLED:
            answer = _local_qwen_inference(prompt, max_new_tokens=800, temperature=0.3)
        else:
            answer = _hf_inference(prompt, max_new_tokens=800, temperature=0.3)
        
        if not answer:
            logger.warning("Empty response from LLM, using fallback")
            return _template_fallback(query, kg_results, vs_results)
        
        return answer

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return _template_fallback(query, kg_results, vs_results)


# ---------------------------------------------------------------------------
# Knowledge extraction via LLM
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT_TEMPLATE = """Extract structured knowledge from this NASA space biology text.

Return ONLY valid JSON with this exact format:
{{
  "entities": [
    {{"name": "entity name", "entity_type": "Environment|Organism|Biological_Process|Biomolecule|Technology|Location"}}
  ],
  "triples": [
    {{"subject": "entity1", "relationship": "causes|inhibits|affects|measured_in|mitigated_by|studied_in|shows_effect", "object": "entity2", "evidence_span": "exact quote from text"}}
  ]
}}

Text to analyze:
{text}

Rules:
- Only use the exact relationship types listed
- Only extract relationships explicitly stated in the text
- evidence_span must be a real quote from the text
- Return valid JSON only, no other text"""


def extract_triples_from_text(text: str) -> dict:
    """
    Use LLM to extract entities and relationship triples from text.
    Returns dict with 'entities' and 'triples' lists.
    """
    if not HF_TOKEN and not QWEN_LOCAL_ENABLED:
        return {"entities": [], "triples": []}

    try:
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(text=text[:1500])
        
        if QWEN_LOCAL_ENABLED:
            raw = _local_qwen_inference(prompt, max_new_tokens=800, temperature=0.1)
        else:
            raw = _hf_inference(prompt, max_new_tokens=800, temperature=0.1)
        
        # Extract JSON from response
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        
        # Find first { and last }
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = raw[start:end]
            return json.loads(json_str)
        
        return {"entities": [], "triples": []}
    
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Triple extraction failed: {e}")
        return {"entities": [], "triples": []}


# ---------------------------------------------------------------------------
# Template fallback (no HF_TOKEN or Qwen)
# ---------------------------------------------------------------------------

def _template_fallback(query: str, kg_results: list, vs_results: list) -> str:
    """High-quality template synthesis when LLM is unavailable."""
    
    lines = []
    lines.append(f"**Query:** {query}\n")
    lines.append("*Note: Set HF_TOKEN or enable Qwen for model-based answer generation.*\n")

    if kg_results:
        lines.append("\n**Established Relationships from Knowledge Graph:**")
        for rel in kg_results[:5]:
            s, p, o = rel.get("subject", "?"), rel.get("relationship", "→"), rel.get("object", "?")
            lines.append(f"• {s} **{p}** {o}")
            if rel.get("evidence"):
                lines.append(f"  *\"{rel['evidence'][:120]}...\"*")
    
    if vs_results:
        lines.append("\n**Relevant Research Findings:**")
        for i, doc in enumerate(vs_results[:3], 1):
            title = doc.get("metadata", {}).get("source_title", "NASA Publication")
            content = doc.get("content", "")[:250]
            lines.append(f"\n**[{i}] {title}**")
            lines.append(f"{content}...")
    
    if not kg_results and not vs_results:
        lines.append(
            "\nNo specific information found in the knowledge base. "
            "Try running the data pipeline to populate the database, "
            "or rephrase your query."
        )
    
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Model status utilities
# ---------------------------------------------------------------------------

def get_model_status() -> Dict[str, Any]:
    """Get current model configuration and availability status."""
    return {
        "provider": LLM_PROVIDER,
        "model": QWEN_MODEL if LLM_PROVIDER == "qwen" else MISTRAL_MODEL,
        "hf_token_set": bool(HF_TOKEN),
        "qwen_local_enabled": QWEN_LOCAL_ENABLED,
        "qwen_local_path": QWEN_LOCAL_PATH if QWEN_LOCAL_ENABLED else None,
    }

