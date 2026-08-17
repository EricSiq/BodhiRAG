"""
BodhiRAG Evidence Formatter
Formats retrieval results as evidence cards with citations.
Implements UX from FRONTEND_UX_DESIGN.md
"""

from typing import List, Dict, Any, Optional
import html
import re


class EvidenceCard:
    """A single evidence card with citation marker."""
    
    def __init__(self, card_id: str, card_type: str, title: str, content: str,
                 metadata: Optional[Dict] = None, evidence: Optional[str] = None):
        self.card_id = card_id
        self.card_type = card_type  # "literature" or "graph"
        self.title = title
        self.content = content
        self.metadata = metadata or {}
        self.evidence = evidence
    
    def to_markdown(self) -> str:
        """Format as markdown for Gradio display."""
        md = f"**[{self.card_id}]** "
        
        if self.card_type == "graph":
            # Graph relationship
            md += f"**{self.title}**\n"
            if self.evidence:
                md += f"> *\"{self.evidence[:150]}...\"*\n"
            if self.metadata.get("source"):
                md += f"*(from {self.metadata['source'][:60]})*\n"
        else:
            # Literature passage
            url = self.metadata.get("source_url", "")
            score = self.metadata.get("score", 0)
            score_pct = int(score * 100)
            
            if url:
                md += f"[**{self.title[:70]}**]({url}) "
            else:
                md += f"**{self.title[:70]}** "
            
            md += f"(`{score_pct}%` match)\n"
            md += f"> {self.content[:200]}...\n"
        
        return md


class EvidenceFormatter:
    """
    Formats retrieval results into structured evidence display.
    Implements the evidence panel from FRONTEND_UX_DESIGN.md.
    """
    
    def __init__(self):
        self.literature_cards: List[EvidenceCard] = []
        self.graph_cards: List[EvidenceCard] = []
    
    def format_retrieval_results(
        self,
        kg_results: List[Dict],
        vs_results: List[Dict],
        route: str = "hybrid"
    ) -> str:
        """
        Format all retrieval results as evidence cards.
        Returns markdown string with route badge and numbered cards.
        """
        self.literature_cards = []
        self.graph_cards = []
        
        # Create literature cards
        seen_titles = set()
        for i, doc in enumerate(vs_results[:6], 1):
            title = doc.get("metadata", {}).get("source_title", "NASA Publication")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            card = EvidenceCard(
                card_id=f"S{i}",
                card_type="literature",
                title=title,
                content=doc.get("content", ""),
                metadata={
                    "source_url": doc.get("metadata", {}).get("source_url", ""),
                    "score": doc.get("score", 0),
                    "doc_id": doc.get("metadata", {}).get("doc_id", ""),
                }
            )
            self.literature_cards.append(card)
        
        # Create graph cards
        for i, rel in enumerate(kg_results[:5], 1):
            s = rel.get("subject", "?")
            p = rel.get("relationship", "→")
            o = rel.get("object", "?")
            
            card = EvidenceCard(
                card_id=f"G{i}",
                card_type="graph",
                title=f"{s} → {p} → {o}",
                content="",
                evidence=rel.get("evidence", ""),
                metadata={
                    "source": rel.get("source", rel.get("source_title", "")),
                    "confidence": rel.get("confidence", 0.8),
                }
            )
            self.graph_cards.append(card)
        
        # Build formatted output
        return self._build_evidence_panel(route)
    
    def _build_evidence_panel(self, route: str) -> str:
        """Build the complete evidence panel with route badge."""
        parts = []
        
        # Route badge
        route_display = {
            "semantic": "Literature Search",
            "graph": "Graph Retrieval",
            "hybrid": "Hybrid"
        }.get(route, route)
        
        badge_parts = [f"**{route_display}**"]
        if self.graph_cards:
            badge_parts.append(f"{len(self.graph_cards)} graph relationships")
        if self.literature_cards:
            badge_parts.append(f"{len(self.literature_cards)} literature passages")
        
        parts.append(f"### Route: {' • '.join(badge_parts)}\n")
        
        # No results case
        if not self.graph_cards and not self.literature_cards:
            parts.append("*No supporting sources found. Try rephrasing your query or running the data pipeline.*\n")
            return "\n".join(parts)
        
        # Literature sources
        if self.literature_cards:
            parts.append("#### Literature Sources\n")
            for card in self.literature_cards:
                parts.append(card.to_markdown())
                parts.append("")
        
        # Graph relationships
        if self.graph_cards:
            parts.append("#### Graph Relationships\n")
            for card in self.graph_cards:
                parts.append(card.to_markdown())
                parts.append("")
        
        return "\n".join(parts)
    
    def format_graph_path_disclosure(self, kg_results: List[Dict]) -> str:
        """Format graph paths for disclosure panel (textual equivalent to visualization)."""
        if not kg_results:
            return "*No graph relationships available.*"
        
        parts = ["### Graph Paths\n"]
        parts.append("Each relationship is backed by evidence from source documents:\n")
        
        for i, rel in enumerate(kg_results[:8], 1):
            s = rel.get("subject", "?")
            p = rel.get("relationship", "→")
            o = rel.get("object", "?")
            evidence = rel.get("evidence", "No evidence span recorded")
            source = rel.get("source", rel.get("source_title", "Unknown source"))
            
            parts.append(f"**{i}. {s}** *{p}* **{o}**\n")
            parts.append(f"   - Evidence: *\"{evidence[:120]}...\"*\n")
            parts.append(f"   - Source: {source[:60]}\n")
        
        return "\n".join(parts)
    
    def get_citation_ids(self) -> List[str]:
        """Get all citation IDs from current cards."""
        ids = [card.card_id for card in self.literature_cards]
        ids.extend([card.card_id for card in self.graph_cards])
        return ids


def build_answer_with_citations(
    direct_answer: str,
    kg_results: List[Dict],
    vs_results: List[Dict],
    route: str,
    model_available: bool = True
) -> str:
    """
    Build the complete answer format from FRONTEND_UX_DESIGN.md:
    1. Direct answer (2-5 sentences)
    2. What the evidence shows (bullets with source markers)
    3. Limits or disagreement
    4. Sources (expandable cards)
    5. Next questions
    """
    formatter = EvidenceFormatter()
    evidence_panel = formatter.format_retrieval_results(kg_results, vs_results, route)
    
    parts = []
    
    # Label if no model
    if not model_available:
        parts.append("### Retrieved Evidence Summary\n")
        parts.append("*Answer generation is unavailable; showing retrieved evidence.*\n\n")
    else:
        parts.append("### Answer\n\n")
    
    # Direct answer (already generated by LLM or template)
    parts.append(direct_answer)
    parts.append("\n\n---\n\n")
    
    # Evidence panel
    parts.append(evidence_panel)
    
    return "".join(parts)


def sanitize_for_html(text: str) -> str:
    """Sanitize retrieved content before rendering in HTML/Markdown."""
    # Escape HTML
    text = html.escape(text)
    # Remove potential script injections
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    return text


def format_status_bar(
    vector_available: bool,
    graph_available: bool,
    generation_available: bool,
    vector_count: int = 0,
    graph_count: int = 0,
    model_name: str = "none",
    operating_mode: str = "demo"
) -> str:
    """
    Generate the status bar HTML with user-facing language.
    Implements status bar from FRONTEND_UX_DESIGN.md.
    """
    badges = []
    
    # Service state badge
    if not vector_available or vector_count == 0:
        state_badge = '<span class="badge badge-gray" title="No searchable corpus installed">⚠️ Setup Required</span>'
    elif not generation_available:
        state_badge = '<span class="badge badge-blue" title="Answer generation unavailable">📚 Evidence Only</span>'
    elif not graph_available:
        state_badge = '<span class="badge badge-yellow" title="Graph unavailable, literature search active">📖 Literature Ready</span>'
    else:
        state_badge = '<span class="badge badge-green" title="Literature and relationship evidence ready">✅ Ready</span>'
    badges.append(state_badge)
    
    # Vector store badge
    if vector_available and vector_count > 0:
        badges.append(f'<span class="badge badge-blue" title="Vector store ready">{vector_count:,} literature chunks</span>')
    
    # Graph badge
    if graph_available:
        badges.append(f'<span class="badge badge-purple" title="Knowledge graph connected">{graph_count:,} relationships</span>')
    
    # Model badge
    if generation_available:
        model_display = "Qwen" if "qwen" in model_name.lower() else "Mistral"
        badges.append(f'<span class="badge badge-green" title="Answer synthesis active">🤖 {model_display}</span>')
    
    # Operating mode badge
    mode_labels = {
        "demo": ("Demo", "badge-blue", "Pre-built corpus, no credentials needed"),
        "local_opensource": ("Local", "badge-green", "Full local stack"),
        "hosted_freetier": ("Hosted", "badge-purple", "Using free hosted services"),
        "maintainer_ingest": ("Maintainer", "badge-gold", "Corpus build enabled")
    }
    mode_label, mode_class, mode_title = mode_labels.get(operating_mode, ("Demo", "badge-blue", ""))
    badges.append(f'<span class="badge {mode_class}" title="{mode_title}">⚙️ {mode_label} Mode</span>')
    
    return f'<div class="status-bar">{"".join(badges)}</div>'
