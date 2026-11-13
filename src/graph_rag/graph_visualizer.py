#BodhiRAG/src/graph_rag/graph_visualizer.py
"""
Knowledge Graph Visualizer: creates interactive Plotly network graphs
from KG query results to display in Gradio.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Color palette for entity types
ENTITY_COLORS = {
    "Environment":         "#60a5fa",   # Sky blue
    "Organism":            "#34d399",   # Emerald green  
    "Biological_Process":  "#a78bfa",   # Violet
    "Biomolecule":         "#f59e0b",   # Amber
    "Technology":          "#fb923c",   # Orange
    "Location":            "#f472b6",   # Pink
    "Unknown":             "#94a3b8",   # Slate gray
}

RELATIONSHIP_COLORS = {
    "causes":      "#ef4444",   # Red
    "inhibits":    "#22c55e",   # Green
    "affects":     "#f59e0b",   # Amber
    "mitigated_by":"#3b82f6",   # Blue
    "measured_in": "#8b5cf6",   # Purple
    "studied_in":  "#06b6d4",   # Cyan
    "shows_effect":"#ec4899",   # Pink
}


def build_kg_graph(kg_results: List[Dict], title: str = "Knowledge Graph") -> Any:
    """
    Build an interactive Plotly network graph from KG relationship results.
    
    Args:
        kg_results: List of relationship dicts with subject/relationship/object keys
        title: Graph title
    
    Returns:
        Plotly Figure object (for use with gr.Plot)
    """
    try:
        import plotly.graph_objects as go
        import math
    except ImportError:
        logger.warning("Plotly not installed: cannot render graph")
        return None

    if not kg_results:
        return _empty_graph(title)

    # Collect unique nodes
    nodes = {}
    edges = []

    for rel in kg_results:
        subj = rel.get("subject", "?")
        obj = rel.get("object", "?")
        relationship = rel.get("relationship", "→")
        evidence = rel.get("evidence", "")

        if subj not in nodes:
            nodes[subj] = {
                "id": len(nodes),
                "label": subj,
                "type": rel.get("subject_type", "Unknown"),
                "connections": 0,
            }
        if obj not in nodes:
            nodes[obj] = {
                "id": len(nodes),
                "label": obj,
                "type": rel.get("object_type", "Unknown"),
                "connections": 0,
            }

        nodes[subj]["connections"] += 1
        nodes[obj]["connections"] += 1
        edges.append({
            "source": subj,
            "target": obj,
            "relationship": relationship,
            "evidence": evidence[:100] if evidence else "",
        })

    # Layout: circular for small graphs, force-directed approximation for larger
    n = len(nodes)
    positions = {}
    node_list = list(nodes.keys())

    if n <= 12:
        # Circular layout
        for i, name in enumerate(node_list):
            angle = 2 * math.pi * i / n
            positions[name] = (math.cos(angle), math.sin(angle))
    else:
        # Grid layout
        cols = math.ceil(math.sqrt(n))
        for i, name in enumerate(node_list):
            row, col = divmod(i, cols)
            positions[name] = (col / cols, -row / math.ceil(n / cols))

    # Build edge traces
    edge_traces = []
    for edge in edges:
        src, tgt = edge["source"], edge["target"]
        if src not in positions or tgt not in positions:
            continue
        x0, y0 = positions[src]
        x1, y1 = positions[tgt]
        color = RELATIONSHIP_COLORS.get(edge["relationship"], "#94a3b8")

        edge_trace = go.Scatter(
            x=[x0, x1, None],
            y=[y0, y1, None],
            mode="lines",
            line=dict(width=2, color=color),
            hoverinfo="text",
            hovertext=f"{src} <b>{edge['relationship']}</b> {tgt}<br>{edge['evidence']}",
            showlegend=False,
        )
        edge_traces.append(edge_trace)

        # Add relationship label at midpoint
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        label_trace = go.Scatter(
            x=[mx],
            y=[my],
            mode="text",
            text=[f"<i>{edge['relationship']}</i>"],
            textfont=dict(size=9, color=color),
            hoverinfo="none",
            showlegend=False,
        )
        edge_traces.append(label_trace)

    # Build node trace
    node_x = [positions[n][0] for n in node_list]
    node_y = [positions[n][1] for n in node_list]
    node_colors = [
        ENTITY_COLORS.get(nodes[n]["type"], ENTITY_COLORS["Unknown"])
        for n in node_list
    ]
    node_sizes = [
        12 + min(nodes[n]["connections"] * 4, 20)
        for n in node_list
    ]
    node_labels = node_list
    node_hover = [
        f"<b>{name}</b><br>Type: {nodes[name]['type']}<br>Connections: {nodes[name]['connections']}"
        for name in node_list
    ]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color="#1e293b"),
            opacity=0.9,
        ),
        text=node_labels,
        textposition="top center",
        textfont=dict(size=10, color="#e2e8f0"),
        hovertext=node_hover,
        hoverinfo="text",
        name="Entities",
    )

    # Compose layout
    fig = go.Figure(
        data=edge_traces + [node_trace],
        layout=go.Layout(
            title=dict(
                text=title,
                font=dict(size=14, color="#e2e8f0"),
                x=0.5,
            ),
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="closest",
            height=400,
        ),
    )

    return fig


def _empty_graph(title: str) -> Any:
    """Return a placeholder graph when there are no results."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return None

    fig = go.Figure(
        layout=go.Layout(
            title=dict(
                text=f"{title}: No relationships to display",
                font=dict(size=13, color="#64748b"),
                x=0.5,
            ),
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=20, r=20, t=40, b=20),
            annotations=[
                dict(
                    text="Run the knowledge graph query to see relationships here",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=13, color="#475569"),
                )
            ],
            height=400,
        )
    )
    return fig
