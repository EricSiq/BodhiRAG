
import os
import json
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field
from langchain_core.documents import Document

# --- 1. Pydantic Schemas (The Knowledge Graph Ontology) ---
# These schemas strictly enforce the format of the LLM's output.

class Entity(BaseModel):
    """A scientific entity identified in the space bioscience domain."""
    name: str = Field(description="The canonical name of the entity, e.g., 'Microgravity', 'Arabidopsis'.")
    entity_type: str = Field(description="The type, strictly one of: Organism, Environment, Biological_Process, Biomolecule, Technology, Location.")

class RelationshipTriple(BaseModel):
    """A structured triple representing a verifiable relationship between two entities."""
    subject: str = Field(description="The canonical name of the subject entity (must match a name in the 'entities' list).")
    relationship: str = Field(description="The verb/link, strictly one of: causes, inhibits, affects, measured_in, mitigated_by, studied_in, shows_effect.")
    object: str = Field(description="The canonical name of the object entity (must match a name in the 'entities' list).")
    evidence_span: str = Field(description="The exact sentence or phrase from the source text supporting this relationship (Crucial for XAI).")

class ExtractionSchema(BaseModel):
    """The complete structured output for a single text chunk."""
    entities: List[Entity] = Field(description="A comprehensive list of all key entities found in the text chunk.")
    triples: List[RelationshipTriple] = Field(description="A list of all factual relationship triples found, linking entities.")


# --- 2. LLM Interface and Extraction Logic ---

# Placeholder for LLM integration (replace with actual LangChain/HuggingFace client)
def _call_structured_llm_api(text_chunk: str, schema: BaseModel) -> Optional[Dict[str, Any]]:
    """
    MOCKS the call to the GPU-accelerated LLM API for structured extraction.
    In production, this uses the LLM_ENDPOINT defined in the .env file.
    """
    # NOTE: This block would contain the LangChain call using the Pydantic schema
    # (e.g., chat.with_structured_output(ExtractionSchema).invoke(prompt))
    
    # We load the API key from the environment (loaded by run_pipeline.py)
    api_key = os.environ.get("LLM_API_KEY", "MOCK_KEY")
    
    if "MOCK_KEY" in api_key:
        # Simulate a realistic, high-quality output for the first paper's content
        if "Mice in Bion-M 1 space mission" in text_chunk:
             return {
                "entities": [
                    {"name": "Microgravity", "entity_type": "Environment"},
                    {"name": "Pelvic Bone Loss", "entity_type": "Biological_Process"},
                    {"name": "Osteoclastic Activity", "entity_type": "Biological_Process"}
                ],
                "triples": [
                    {
                        "subject": "Microgravity",
                        "relationship": "causes",
                        "object": "Pelvic Bone Loss",
                        "evidence_span": "Microgravity induces pelvic bone loss through osteoclastic activity."
                    }
                ]
             }
        else:
             # Simulate a successful extraction for generic content
             return {"entities": [], "triples": []} 
    
    print(f"--- Running actual LLM call using endpoint {os.environ.get('LLM_ENDPOINT')}...")
    # Add your actual LLM API call here
    return None # Returns None if actual API fails or is not mocked


def extract_knowledge_from_chunk(doc_chunk: Document) -> List[RelationshipTriple]:
    """
    Processes a single document chunk using the structured LLM, validates the output,
    and returns a list of verified triples.
    """
    try:
        # 1. Prepare LLM Prompt and Call API
        llm_response_data = _call_structured_llm_api(doc_chunk.page_content, ExtractionSchema)
        
        if not llm_response_data:
            print(f"  [Extraction] Skipped chunk {doc_chunk.metadata['doc_id']} (API failure or MOCK skip).")
            return []

        # 2. Validate and Parse (Pydantic does the heavy lifting here)
        extracted_data = ExtractionSchema.model_validate(llm_response_data)
        
        triples_count = len(extracted_data.triples)
        
        if triples_count > 0:
            print(f"  [Extraction] Found {triples_count} new triples for {doc_chunk.metadata['doc_id']}.")
            return extracted_data.triples
        else:
            return []

    except Exception as e:
        # This handles JSON parsing failures, Pydantic validation errors, or API timeouts
        print(f"  CRITICAL Pydantic/LLM Extraction Error on chunk {doc_chunk.metadata['doc_id']}: {e}")
        return []

# Example of how this function is used in run_pipeline.py:
# if __name__ == "__main__":
#     # Assumes CHUNKED_DOCUMENTS list is available
#     first_chunk = CHUNKED_DOCUMENTS[0]
#     triples = extract_knowledge_from_chunk(first_chunk)
#     # Triples are now ready to be written by graph_connector.py
