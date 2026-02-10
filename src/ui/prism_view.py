import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

def render_prism_graph(ideas, collaborators):
    """Render the Prism interaction graph."""
    nodes = []
    edges = []
    
    # 1. Add "Central" Node (The Idea)
    nodes.append(Node(id="IDEA", label="Your Idea", size=25, shape="diamond", color="#F76902"))
    
    # 2. Add Collaborators
    for i, collab in enumerate(collaborators):
        meta = collab.get("metadata", {})
        name = meta.get("name", "Unknown")
        cid = f"collab_{i}"
        
        # Node for Faculty
        nodes.append(Node(id=cid, label=name, size=15, shape="dot", color="#000000"))
        
        # Edge from Idea to Faculty
        similarity = 1 - collab.get("distance", 1) # Convert distance to similarity
        edges.append(Edge(source="IDEA", target=cid, label=f"{similarity:.2f}", color="#CCCCCC"))
        
    # 3. Config
    config = Config(width=600, 
                    height=400, 
                    directed=False, 
                    physics=True, 
                    hierarchical=False,
                    nodeHighlightBehavior=True, 
                    highlightColor="#F76902",
                    collapsible=True)
                    
    return agraph(nodes=nodes, edges=edges, config=config)
