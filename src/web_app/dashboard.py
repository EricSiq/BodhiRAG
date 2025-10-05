
"""
NASA BodhiRAG - Interactive Dashboard
Plotly Dash web application with Hybrid RAG Chatbot and Knowledge Visualizations
"""

import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.graph_rag import KnowledgeGraphConnector, VectorStoreConnector, HybridRAGAgent
from src.graph_rag.topic_modeler import TopicModeler, ResearchGapAnalyzer

class BodhiRAGDashboard:
    def __init__(self):
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.CYBORG],
            meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
            title="BodhiRAG"
        )
        
        # Initialize backend connectors
        self.kg_connector = KnowledgeGraphConnector()
        self.vs_connector = VectorStoreConnector()
        self.agent = HybridRAGAgent(self.kg_connector, self.vs_connector)
        self.topic_modeler = TopicModeler()
        
        # Connect to databases
        self._initialize_backend()
        
        # Setup layout
        self.app.layout = self._create_layout()
        
        # Register callbacks
        self._register_callbacks()
    
    def _initialize_backend(self):
        # Initialize database connections 
        try:
            self.kg_connector.connect()
            self.vs_connector.initialize_store()
            print("Backend services initialized")
        except Exception as e:
            print(f"Backend initialization warning: {e}")
    
    def _create_layout(self):
        # Create the main dashboard layout
        return dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("BodhiRAG", 
                           className="text-center mb-4",
                           style={'color': '#ffffff', 'marginTop': '20px'}),
                    html.P("Space Biology Research Intelligence Platform", 
                          className="text-center lead",
                          style={'color': '#cccccc'})
                ])
            ]),
            
            # Navigation Tabs
            dbc.Row([
                dbc.Col([
                    dcc.Tabs(id="main-tabs", value='tab-chat', children=[
                        dcc.Tab(label='🤖 Hybrid RAG Chat', value='tab-chat',
                               style={'backgroundColor': '#1e2130', 'color': 'white'},
                               selected_style={'backgroundColor': '#2d5c7f'}),
                        dcc.Tab(label='🔍 Knowledge Graph Explorer', value='tab-kg',
                               style={'backgroundColor': '#1e2130', 'color': 'white'},
                               selected_style={'backgroundColor': '#2d5c7f'}),
                        dcc.Tab(label='📊 Research Analytics', value='tab-analytics',
                               style={'backgroundColor': '#1e2130', 'color': 'white'},
                               selected_style={'backgroundColor': '#2d5c7f'}),
                        dcc.Tab(label='🎯 Research Gaps', value='tab-gaps',
                               style={'backgroundColor': '#1e2130', 'color': 'white'},
                               selected_style={'backgroundColor': '#2d5c7f'})
                    ])
                ])
            ], className="mb-4"),
            
            # Tab Content
            html.Div(id="tab-content"),
            
            # Footer
            dbc.Row([
                dbc.Col([
                    html.Hr(style={'borderColor': '#444'}),
                    html.P("NASA Space Apps Challenge 2025 - BodhiRAG", 
                          className="text-center",
                          style={'color': '#888', 'fontSize': '12px'})
                ])
            ])
        ], fluid=True, style={'backgroundColor': '#0e1117', 'minHeight': '100vh'})
    
    def _create_chat_tab(self):
        """Create the Hybrid RAG Chat interface"""
        return dbc.Row([
            # Left Column - Chat Interface
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔬 Ask NASA Space Biology Questions", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        # Chat messages container
                        html.Div(id="chat-messages", style={
                            'height': '400px', 
                            'overflowY': 'auto', 
                            'border': '1px solid #444',
                            'padding': '10px',
                            'backgroundColor': '#0e1117',
                            'marginBottom': '15px'
                        }),
                        
                        # Input area
                        dbc.InputGroup([
                            dbc.Input(
                                id="user-input",
                                placeholder="Ask about space biology effects, mechanisms, or research...",
                                type="text",
                                style={'backgroundColor': '#1a1d29', 'color': 'white', 'border': '1px solid #444'}
                            ),
                            dbc.Button("Send", id="send-button", color="primary", n_clicks=0)
                        ]),
                        
                        # Examples
                        html.Div([
                            html.P("Try asking:", style={'color': '#888', 'marginTop': '15px', 'marginBottom': '5px'}),
                            html.Div([
                                dbc.Badge("What are the effects of microgravity on bone loss?", 
                                         color="secondary", className="me-2 mb-2",
                                         style={'cursor': 'pointer'},
                                         id="example-1"),
                                dbc.Badge("How does space radiation affect gene expression?", 
                                         color="secondary", className="me-2 mb-2",
                                         style={'cursor': 'pointer'},
                                         id="example-2"),
                                dbc.Badge("What countermeasures exist for muscle atrophy?", 
                                         color="secondary", className="me-2 mb-2",
                                         style={'cursor': 'pointer'},
                                         id="example-3"),
                            ])
                        ])
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=8),
            
            # Right Column - Retrieval Insights
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Retrieval Insights", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        html.Div(id="retrieval-stats", style={'color': '#ccc'}),
                        html.Hr(style={'borderColor': '#444'}),
                        html.Div(id="kg-relationships", style={'color': '#ccc', 'fontSize': '14px'}),
                        html.Hr(style={'borderColor': '#444'}),
                        html.Div(id="source-documents", style={'color': '#ccc', 'fontSize': '14px'})
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=4)
        ])
    
    def _create_kg_explorer_tab(self):
        #  Create Knowledge Graph visualization interface 
        return dbc.Row([
            # Controls
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔍 Graph Explorer Controls", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        dbc.InputGroup([
                            dbc.Input(
                                id="entity-search",
                                placeholder="Search entities (e.g., Microgravity, Bone Loss...)",
                                style={'backgroundColor': '#1a1d29', 'color': 'white', 'border': '1px solid #444'}
                            ),
                            dbc.Button("Explore", id="search-entity", color="primary")
                        ]),
                        html.Br(),
                        html.Label("Explore Network Depth:", style={'color': '#ccc'}),
                        dcc.Slider(
                            id="network-depth",
                            min=1,
                            max=3,
                            step=1,
                            value=2,
                            marks={1: '1', 2: '2', 3: '3'}
                        ),
                        html.Br(),
                        html.Div(id="entity-info", style={'color': '#ccc', 'fontSize': '14px'})
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=3),
            
            # Visualization
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🌐 Knowledge Network", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        dcc.Graph(id="kg-network-graph", style={'height': '500px'})
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=9)
        ])
    
    def _create_analytics_tab(self):
        # Create research analytics dashboard
        return dbc.Row([
            # Entity Statistics
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 Entity Statistics", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        dcc.Graph(id="entity-type-chart", style={'height': '300px'})
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=6),
            
            # Relationship Types
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🔗 Relationship Types", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        dcc.Graph(id="relationship-chart", style={'height': '300px'})
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=6)
        ])
    
    def _create_gaps_tab(self):
        # Create research gap analysis interface"
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🎯 Research Gap Analysis", 
                                 style={'backgroundColor': '#1a1d29', 'color': 'white'}),
                    dbc.CardBody([
                        dbc.Button("Analyze Research Gaps", id="analyze-gaps", color="warning", className="mb-3"),
                        html.Div(id="gap-analysis-results", style={'color': '#ccc', 'whiteSpace': 'pre-wrap'})
                    ])
                ], style={'backgroundColor': '#1a1d29', 'border': '1px solid #444'})
            ], width=12)
        ])
    
    def _register_callbacks(self):
        # Register all Dash callbacks
        
        @self.app.callback(
            Output("tab-content", "children"),
            Input("main-tabs", "value")
        )
        def render_tab_content(active_tab):
            if active_tab == 'tab-chat':
                return self._create_chat_tab()
            elif active_tab == 'tab-kg':
                return self._create_kg_explorer_tab()
            elif active_tab == 'tab-analytics':
                return self._create_analytics_tab()
            elif active_tab == 'tab-gaps':
                return self._create_gaps_tab()
        
        # Chat functionality
        @self.app.callback(
            [Output("chat-messages", "children"),
             Output("retrieval-stats", "children"),
             Output("kg-relationships", "children"),
             Output("source-documents", "children")],
            [Input("send-button", "n_clicks"),
             Input("example-1", "n_clicks"),
             Input("example-2", "n_clicks"),
             Input("example-3", "n_clicks")],
            [State("user-input", "value")]
        )
        def handle_chat(*args):
            ctx = callback_context
            if not ctx.triggered:
                return [], "", "", ""
            
            # Get the input text
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'send-button':
                query = args[-1]  # Last argument is user input
            elif button_id == 'example-1':
                query = "What are the effects of microgravity on bone loss?"
            elif button_id == 'example-2':
                query = "How does space radiation affect gene expression?"
            elif button_id == 'example-3':
                query = "What countermeasures exist for muscle atrophy?"
            else:
                query = ""
            
            if not query:
                return [], "", "", ""
            
            # Process query through Hybrid RAG agent
            try:
                result = self.agent.query(query)
                
                # Create chat messages
                messages = [
                    html.Div([
                        html.Strong("You: ", style={'color': '#4dabf7'}),
                        html.Span(query, style={'color': '#ccc'})
                    ], style={'marginBottom': '10px', 'padding': '10px', 'backgroundColor': '#1a1d29', 'borderRadius': '5px'}),
                    
                    html.Div([
                        html.Strong("Assistant: ", style={'color': '#51cf66'}),
                        html.Span(result['final_answer'], style={'color': '#ccc'})
                    ], style={'marginBottom': '10px', 'padding': '10px', 'backgroundColor': '#1a1d29', 'borderRadius': '5px'})
                ]
                
                # Create retrieval stats
                stats = result['retrieval_stats']
                stats_html = html.Div([
                    html.H6("Retrieval Summary", style={'color': '#4dabf7'}),
                    html.P(f"🔗 KG Relationships: {stats['kg_relationships']}"),
                    html.P(f"📄 VS Documents: {stats['vs_documents']}"),
                    html.P(f"🎯 Query Type: {result['query_type']}")
                ])
                
                # KG relationships
                kg_html = html.Div([
                    html.H6("Key Relationships", style={'color': '#4dabf7'}),
                    *[html.P(f"• {rel['subject']} → {rel['relationship']} → {rel['object']}", 
                            style={'fontSize': '12px', 'marginBottom': '5px'})
                      for rel in result['kg_results'][:3]]
                ]) if result['kg_results'] else html.P("No KG relationships found")
                
                # Source documents
                sources_html = html.Div([
                    html.H6("Source Documents", style={'color': '#4dabf7'}),
                    *[html.P(f"• {doc['metadata'].get('source_title', 'Unknown')[:50]}...", 
                            style={'fontSize': '12px', 'marginBottom': '5px'})
                      for doc in result['vs_results'][:2]]
                ]) if result['vs_results'] else html.P("No source documents retrieved")
                
                return messages, stats_html, kg_html, sources_html
                
            except Exception as e:
                error_msg = html.Div([
                    html.Strong("Error: ", style={'color': '#ff6b6b'}),
                    html.Span(f"Failed to process query: {str(e)}", style={'color': '#ccc'})
                ])
                return [error_msg], "", "", ""
        
        # Knowledge Graph Explorer
        @self.app.callback(
            [Output("kg-network-graph", "figure"),
             Output("entity-info", "children")],
            [Input("search-entity", "n_clicks")],
            [State("entity-search", "value"),
             State("network-depth", "value")]
        )
        def explore_entity(n_clicks, entity_name, depth):
            if not n_clicks or not entity_name:
                # Return empty graph
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    title="Enter an entity name to explore relationships",
                    paper_bgcolor='#1a1d29',
                    plot_bgcolor='#1a1d29',
                    font_color='white',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                )
                return empty_fig, "Enter an entity name above to explore the knowledge graph"
            
            try:
                # Get entity network
                network_data = self.kg_connector.get_entity_network(entity_name, depth)
                
                if not network_data:
                    empty_fig = go.Figure()
                    empty_fig.update_layout(
                        title=f"No relationships found for '{entity_name}'",
                        paper_bgcolor='#1a1d29',
                        plot_bgcolor='#1a1d29',
                        font_color='white'
                    )
                    return empty_fig, f"No relationships found for '{entity_name}'"
                
                # Create network visualization (simplified - in production use networkx + plotly)
                relationships = network_data['relationships']
                
                # Create nodes and edges for visualization
                nodes = set()
                edges = []
                
                for rel in relationships:
                    nodes.add(rel['subject'])
                    nodes.add(rel['object'])
                    edges.append((rel['subject'], rel['object'], rel['relationship']))
                
                # Simple force-directed layout simulation
                node_positions = {}
                import math
                for i, node in enumerate(nodes):
                    angle = 2 * math.pi * i / len(nodes)
                    node_positions[node] = (math.cos(angle), math.sin(angle))
                
                # Create Plotly figure
                fig = go.Figure()
                
                # Add edges
                edge_x = []
                edge_y = []
                for edge in edges:
                    x0, y0 = node_positions[edge[0]]
                    x1, y1 = node_positions[edge[1]]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])
                
                fig.add_trace(go.Scatter(
                    x=edge_x, y=edge_y,
                    line=dict(width=2, color='#555'),
                    hoverinfo='none',
                    mode='lines',
                    name='relationships'
                ))
                
                # Add nodes
                node_x = []
                node_y = []
                node_text = []
                for node in nodes:
                    x, y = node_positions[node]
                    node_x.append(x)
                    node_y.append(y)
                    node_text.append(node)
                
                fig.add_trace(go.Scatter(
                    x=node_x, y=node_y,
                    mode='markers+text',
                    hoverinfo='text',
                    text=node_text,
                    textposition="middle center",
                    marker=dict(
                        size=20,
                        color='#2d5c7f',
                        line=dict(width=2, color='#4dabf7')
                    ),
                    name='entities'
                ))
                
                fig.update_layout(
                    title=f"Knowledge Network: {entity_name} (Depth: {depth})",
                    showlegend=False,
                    paper_bgcolor='#1a1d29',
                    plot_bgcolor='#1a1d29',
                    font_color='white',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=500
                )
                
                # Entity info
                entity_info = html.Div([
                    html.H6(f"Entity: {entity_name}", style={'color': '#4dabf7'}),
                    html.P(f"Connected to {len(nodes)-1} other entities"),
                    html.P(f"Found {len(edges)} relationships")
                ])
                
                return fig, entity_info
                
            except Exception as e:
                error_fig = go.Figure()
                error_fig.update_layout(
                    title=f"Error exploring entity: {str(e)}",
                    paper_bgcolor='#1a1d29',
                    plot_bgcolor='#1a1d29',
                    font_color='white'
                )
                return error_fig, f"Error: {str(e)}"
        
        # Analytics charts
        @self.app.callback(
            [Output("entity-type-chart", "figure"),
             Output("relationship-chart", "figure")],
            Input("main-tabs", "value")
        )
        def update_analytics_charts(active_tab):
            if active_tab != 'tab-analytics':
                return {}, {}
            
            try:
                # Get graph statistics
                stats = self.kg_connector.export_graph_stats()
                
                # Entity type chart
                entity_type_data = stats.get('entity_types', [])
                if entity_type_data:
                    entity_df = pd.DataFrame(entity_type_data)
                    entity_fig = px.pie(
                        entity_df, 
                        values='count', 
                        names='type',
                        title="Entity Type Distribution",
                        color_discrete_sequence=px.colors.qualitative.Set3
                    )
                else:
                    entity_fig = px.pie(
                        values=[1], 
                        names=['No Data'],
                        title="Entity Type Distribution"
                    )
                
                # Relationship type chart  
                relationship_data = stats.get('relationship_types', [])
                if relationship_data:
                    rel_df = pd.DataFrame(relationship_data)
                    rel_fig = px.bar(
                        rel_df,
                        x='type',
                        y='count',
                        title="Relationship Type Distribution",
                        color='count',
                        color_continuous_scale='viridis'
                    )
                else:
                    rel_fig = px.bar(
                        x=['No Data'],
                        y=[1],
                        title="Relationship Type Distribution"
                    )
                
                # Update styling
                for fig in [entity_fig, rel_fig]:
                    fig.update_layout(
                        paper_bgcolor='#1a1d29',
                        plot_bgcolor='#1a1d29',
                        font_color='white',
                        title_font_color='white'
                    )
                
                return entity_fig, rel_fig
                
            except Exception as e:
                # Return empty figures on error
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    title=f"Error loading analytics: {str(e)}",
                    paper_bgcolor='#1a1d29',
                    plot_bgcolor='#1a1d29',
                    font_color='white'
                )
                return empty_fig, empty_fig
        
        # Research gap analysis
        @self.app.callback(
            Output("gap-analysis-results", "children"),
            Input("analyze-gaps", "n_clicks")
        )
        def analyze_research_gaps(n_clicks):
            if not n_clicks:
                return "Click 'Analyze Research Gaps' to identify under-researched areas in space biology."
            
            try:
                # This would require actual document data - for demo, return mock analysis
                mock_gaps = [
                    {
                        'type': 'underrepresented_topic',
                        'description': "Topic 'Mitochondrial Function in Microgravity' is underrepresented",
                        'evidence': "Only 15 documents (2.1% of corpus)",
                        'priority_score': 0.8,
                        'suggested_research': "Expand research on mitochondrial adaptations to space environments"
                    },
                    {
                        'type': 'high_centrality_low_coverage', 
                        'description': "Entity 'Circadian Rhythm Disruption' is central but under-researched",
                        'evidence': "Centrality score: 0.72, Coverage: 15%",
                        'priority_score': 0.7,
                        'suggested_research': "Focus studies on circadian rhythm mechanisms in long-duration missions"
                    }
                ]
                
                gap_analyzer = ResearchGapAnalyzer(self.kg_connector, self.topic_modeler)
                report = gap_analyzer.generate_gap_report(mock_gaps)
                
                return html.Div([
                    html.H5("Research Gap Analysis Results", style={'color': '#4dabf7'}),
                    html.Pre(report, style={
                        'backgroundColor': '#0e1117',
                        'padding': '15px',
                        'borderRadius': '5px',
                        'border': '1px solid #444',
                        'whiteSpace': 'pre-wrap',
                        'fontSize': '14px'
                    })
                ])
                
            except Exception as e:
                return f"Error analyzing research gaps: {str(e)}"
    
    def run_server(self, debug: bool = True, port: int = 8050):
        """Run the Dash server"""
        print(f"Starting BodhiRAG Dashboard...")
        print(f"Access at: http://localhost:{port}")
        self.app.run_server(debug=debug, port=port)

# Easy deployment function
def create_and_run_dashboard(debug=True, port=8050):
    """One-line function to create and run the dashboard"""
    dashboard = BodhiRAGDashboard()
    dashboard.run_server(debug=debug, port=port)
    return dashboard

# Command line execution
if __name__ == "__main__":
    create_and_run_dashboard()