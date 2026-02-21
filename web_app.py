
import streamlit as st
import time
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.database import get_vector_store
from src.chatbot.ollama_client import get_ollama_client
from src.utils.db_logger import setup_db_logging, PerformanceTimer as Timer

# Setup Logger
logger = setup_db_logging("WebApp")

# Page config
st.set_page_config(
    page_title="TigerResearchBuddy",
    page_icon="🐅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Star Wars Theme Assets & CSS
def get_base64_image(image_path):
    logger.info(f"Loading asset: {image_path}")
    try:
        import base64
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

# Background Image Path (Generated Asset)
bg_path = "/Users/anurag/.gemini/antigravity/brain/fe0d4a0b-a288-48ba-bd14-eb9d95d5ab4b/star_wars_background_1770169098001.png"
bg_base64 = get_base64_image(bg_path)

st.markdown(f"""
<style>
    /* IMPORT ORBITRON FONT (Star Wars / Sci-Fi Style) */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Roboto:wght@300;400;700&display=swap');

    /* SKYWALKER BLUE & SITH RED PALETTE */
    :root {{
        --neon-blue: #4EC5F1;
        --neon-yellow: #FFE81F;
        --neon-red: #FF0000;
        --deep-space: #000000;
        --star-white: #FFFFFF;
        --hud-bg: rgba(0, 20, 40, 0.85);
        --user-bg: rgba(78, 197, 241, 0.15);
        --bot-bg: rgba(0, 0, 0, 0.7);
    }}

    /* GLOBAL FONT FIX - SCOPED TO TEXT ELEMENTS ONLY TO PREVENT BROKEN ICONS */
    html, body, p, h1, h2, h3, h4, h5, h6, li, span, div {{
        font-family: 'Roboto', sans-serif;
        color: var(--star-white);
    }}
    
    h1, h2, h3, .stButton button {{
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 1px;
    }}

    /* APP BACKGROUND */
    .stApp {{
        background-image: url("data:image/png;base64,{bg_base64}");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }}

    /* HEADERS */
    h1 {{
        color: var(--neon-yellow) !important;
        text-shadow: 0 0 10px rgba(255, 232, 31, 0.5);
    }}

    h2, h3 {{
        color: var(--neon-blue) !important;
        text-shadow: 0 0 8px rgba(78, 197, 241, 0.4);
    }}

    /* CHAT MESSAGES - HOLOGRAPHIC CARDS */
    .stChatMessage {{
        background-color: var(--bot-bg) !important;
        border: 1px solid var(--neon-blue) !important;
        border-radius: 4px !important;
        box-shadow: 0 0 15px rgba(78, 197, 241, 0.1);
        backdrop-filter: blur(5px);
    }}

    /* USER MESSAGE - REBEL ALLIANCE STYLE */
    .stChatMessage[data-testid="user-message"] {{
        background-color: var(--user-bg) !important;
        border-left: 4px solid var(--neon-yellow) !important;
        border-right: none !important;
        border-top: none !important;
        border-bottom: none !important;
    }}
    
    /* ASSISTANT MESSAGE - JEDI ARCHIVE STYLE */
    .stChatMessage[data-testid="assistant-message"] {{
        border-left: 4px solid var(--neon-blue) !important;
        border-right: none !important;
        border-top: none !important;
        border-bottom: none !important;
    }}
    
    /* TEXT VISIBILITY */
    .stChatMessage p {{
        color: #E0E0E0 !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
    }}
    
    .stChatMessage strong {{
        color: var(--neon-yellow) !important;
    }}

    /* SIDEBAR - DARK SIDE */
    section[data-testid="stSidebar"] {{
        background-color: rgba(0, 0, 0, 0.9) !important;
        border-right: 1px solid var(--neon-blue);
    }}
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {{
        color: var(--neon-yellow) !important;
    }}
    
    /* BUTTONS - HYPERDRIVE ACTIVATORS */
    .stButton button {{
        background: transparent !important;
        border: 2px solid var(--neon-yellow) !important;
        color: var(--neon-yellow) !important;
        border-radius: 0px !important; /* Sci-fi square corners */
        text-transform: uppercase;
        font-weight: bold;
        transition: all 0.3s ease;
    }}
    
    .stButton button:hover {{
        background: var(--neon-yellow) !important;
        color: black !important;
        box-shadow: 0 0 20px var(--neon-yellow);
        transform: scale(1.05);
    }}

    /* INPUT FIELD - COMMAND CONSOLE */
    .stChatInput textarea {{
        background-color: rgba(0, 0, 0, 0.8) !important;
        border: 1px solid var(--neon-blue) !important;
        color: var(--neon-blue) !important;
        font-family: 'Orbitron', monospace !important;
    }}
    
    .stChatInput textarea:focus {{
        box-shadow: 0 0 15px var(--neon-blue) !important;
    }}

    /* EXPANDERS - DATA HOLOCRONS */
    .streamlit-expanderHeader {{
        background-color: rgba(0, 20, 40, 0.9) !important;
        border: 1px solid var(--neon-blue) !important;
        color: var(--neon-blue) !important;
        font-family: 'Orbitron', sans-serif !important;
    }}
    
    /* METRICS */
    [data-testid="stMetricLabel"] {{
        color: var(--neon-blue) !important;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--neon-yellow) !important;
        font-family: 'Orbitron', sans-serif !important;
    }}

    /* LINKS */
    a {{
        color: var(--neon-yellow) !important;
        text-decoration: none;
        border-bottom: 1px dotted var(--neon-yellow);
    }}
    a:hover {{
        color: white !important;
        text-shadow: 0 0 5px white;
    }}
</style>
""", unsafe_allow_html=True)

# Initialize resources (cached)
@st.cache_resource
def load_resources():
    try:
        with Timer("Initializing Resources", use_rich=False):
            store = get_vector_store()
            store.initialize()
            
            client = get_ollama_client()
            client.initialize()
        return store, client
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        return None, None

store, client = load_resources()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm TigerResearchBuddy. I can help you find research opportunities, faculty advisors, and papers at RIT. Ask me anything!"}
    ]

# Sidebar
with st.sidebar:
    st.title("🌌 TIGER SQUADRON")
    st.caption("Rebel Alliance Intelligence Hub")
    
    if store:
        stats = store.get_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", stats.get('total_documents', 0))
        with col2:
            st.metric("Collection", "RIT Data")
            
            
    st.markdown("---")
    
    # Persona Selector
    if "persona" not in st.session_state:
        st.session_state.persona = "tiger"
    
    st.subheader("🎭 Agent Persona")
    persona = st.selectbox(
        "Select AI Mode:",
        ["tiger", "analyzer", "critique"],
        index=["tiger", "analyzer", "critique"].index(st.session_state.persona),
        format_func=lambda x: {
            "tiger": "🐅 Tiger (Friendly)",
            "analyzer": "📊 Analyzer (Technical)",
            "critique": "🔍 Critique (Critical)"
        }[x]
    )
    
    if persona != st.session_state.persona:
        st.session_state.persona = persona
        if client:
            client.set_persona(persona)
        st.success(f"Switched to {persona} mode!")
    
    st.markdown("---")
    st.subheader("Capabilities")
    st.markdown("""
    - 🔍 **Faculty Search**: Find professors by research area
    - 📄 **Paper Analysis**: Ask about specific papers
    - 📧 **Contact Info**: Get emails and office locations
    - 💡 **Idea Generation**: Brainstorm research topics
    """)
    
    st.markdown("---")
    if st.button("🔄 Reload Data"):
        st.cache_resource.clear()
        st.success("Cache cleared! Reloading...")
        time.sleep(1)
        st.rerun()
        
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()


# TABS
tab1, tab2 = st.tabs(["💬 Chat", "🤝 Collaboration Hub"])

with tab1:
    # Main Chat Interface
    st.header("🐅 TigerResearchBuddy Chat")
    st.caption("AI Research Assistant for RIT Computing")

    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about research opportunities..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Log user query
    logger.info(f"User Query: {prompt}", extra={"meta": {"persona": st.session_state.persona}})
    
    # Generate response
    with st.chat_message("assistant"):
        # Stop Button Placeholder (Top of message for visibility)
        stop_btn_placeholder = st.empty()
        message_placeholder = st.empty()
        full_response = ""
        
        if store and client:
            with st.spinner("Searching knowledge base..."):
                # Chitchat Guard
                is_chitchat = len(prompt.split()) < 3 and any(w in prompt.lower().split() for w in ["hi", "hello", "hey", "thanks", "bye", "good"])
                
                context = ""
                results = []
                graph_insights = None
                expanded_query = prompt

                if not is_chitchat:
                    # RAG: Search
                    from src.chatbot.query_engine import QueryEngine
                    query_engine = QueryEngine()
                    expanded_query = query_engine.expand_query(prompt)
                    
                    with Timer("Vector Search", use_rich=False):
                        results = store.search(expanded_query, n_results=15)
                    
                    # Build base context
                    context_parts = [r.get("content", "") for r in results]
                    
                    # ADD KNOWLEDGE GRAPH ENRICHMENT
                    try:
                        graph_insights = query_engine.get_graph_insights(prompt)
                        graph_enrichment = query_engine.enrich_context(prompt, results)
                        if graph_enrichment:
                            context_parts.append(f"\n### Knowledge Graph Insights:{graph_enrichment}")
                    except Exception as e:
                        print(f"Graph enrichment skipped: {e}")
                    
                    context = "\n\n".join(context_parts)
                
                # RAG: Generate
                # Load System Prompts
                try:
                    with open("data/prompts/role.md", "r") as f:
                        role_prompt = f.read()
                    with open("data/prompts/skills.md", "r") as f:
                        skills_prompt = f.read()
                    system_prompt = f"{role_prompt}\n\n{skills_prompt}"
                except FileNotFoundError:
                    # Fallback if files missing
                    system_prompt = """You are TigerResearchBuddy, an AI assistant helping RIT students.
                    Use the context provided to answer questions about RIT Computing research.
                    Be helpful, accurate, and encouraging."""
                
                # Add specific formatting rules
                if is_chitchat:
                     system_prompt += "\n\nUSER IS GREETING YOU. Respond naturally, briefly, and politely. Do not make up facts."
                else:
                    system_prompt += f"""
    
    Context from knowledge base:
    {context}
    
    ---
    CRITICAL RESPONSE RULES (FOLLOW EXACTLY):
    
    1. **NO HALLUCINATION**: Only use facts from the Context above. If Context is empty or doesn't answer the question, say "I don't have information about that in my database."
    
    2. **NO LARGE HEADERS**: Don't use # or ## headers in your response. Use normal paragraphs with **bold** for emphasis.
    
    3. **FORMATTING**:
       - Keep responses 2-4 short paragraphs
       - Use **bold** for faculty names: **Professor John Smith**
       - Use *italics* for paper titles: *Deep Learning Paper*  
       - Use bullet points for lists
       - Include email/office when available
    
    4. **ACCURACY**: If Context mentions multiple people, don't mix them up. Verify names match exactly.
    
    5. **USER QUESTION**: {prompt}
    
    Respond naturally and helpfully based ONLY on the Context above.
    """
                
                # Stream response
                with Timer("LLM Response Generation", use_rich=False):
                    stop_btn = stop_btn_placeholder.button("⏹️ Stop Generation", key="stop_gen")
                    
                    # Create generator
                    stream = client.generate_stream(prompt, context=context, system_prompt=system_prompt)
                    
                    for chunk in stream:
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                        
                        # Note: Streamlit doesn't support immediate interruption via button during a loop easily 
                        # without experimental reruns or session state hacks, 
                        # but rendering the button beforehand allows the user to click it.
                        # If clicked, the script reruns and this loop is aborted in the new run.
                    
                    message_placeholder.markdown(full_response)
                    stop_btn_placeholder.empty()
                
                # 🧠 BOT THINKING SECTION
                with st.expander("🧠 Bot Thinking Process", expanded=False):
                    st.markdown("### 🔍 Query Expansion")
                    st.code(f"Original: {prompt}\nExpanded: {expanded_query}", language="text")
                    
                    if graph_insights:
                        st.markdown("### 🕸️ Knowledge Graph Insights")
                        for key, value in graph_insights.items():
                            st.markdown(f"**{key.replace('_', ' ').title()}:**")
                            if isinstance(value, list):
                                if len(value) > 0:
                                    st.json(value[:3])  # Show first 3 items
                                else:
                                    st.caption("_None found_")
                            elif isinstance(value, dict):
                                st.json(value)
                            else:
                                st.write(value)
                    
                    st.markdown("### 📄 Vector Search Results")
                    st.caption(f"Found {len(results)} relevant documents")
                    for i, res in enumerate(results, 1):
                        meta = res.get("metadata", {})
                        st.markdown(f"**{i}.** {meta.get('doc_type', 'document').title()}")
                        st.caption(res.get("content", "")[:200] + "...")
                    
                    st.markdown("### 💬 Context Sent to LLM")
                    st.text_area("Full Context", context, height=200, disabled=True)
                
                # Show sources
                if results:
                    with st.expander("📚 View Sources"):
                        for i, res in enumerate(results, 1):
                            meta = res.get("metadata", {})
                            doctype = meta.get("doc_type", "unknown").replace("_", " ").title()
                            source_line = f"**{i}. {doctype}**"
                            if meta.get("title"):
                                source_line += f": *{meta['title']}*"
                            elif meta.get("name"):
                                source_line += f": *{meta['name']}*"
                            
                            st.markdown(source_line)
                            if meta.get("has_pdf"):
                                st.caption("📄 PDF Available Locally")
                            st.text(res.get("content", "")[:200] + "...")

        else:
            message_placeholder.error("System not initialized. Is Ollama running?")
            full_response = "Error: System not initialized."
            
                
        st.session_state.messages.append({"role": "assistant", "content": full_response})

with tab2:
    st.header("🤝 Collaboration Hub")
    st.markdown("Share your research ideas and find collaborators across RIT.")
    
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.subheader("💡 Post an Idea")
        with st.form("idea_form"):
            idea_title = st.text_input("Title", placeholder="e.g. AI for Sustainable Farming")
            idea_college = st.selectbox("College", ["Computing", "Science", "Engineering", "Liberal Arts", "Business", "Technology"])
            idea_desc = st.text_area("Description", placeholder="Describe your research idea...", height=150)
            idea_tags = st.text_input("Tags (comma separated)", placeholder="ai, sustainability, agriculture")
            
            submitted = st.form_submit_button("🚀 Find Collaborators")
            
            if submitted and idea_title and idea_desc:
                from src.database.models import Idea
                from src.collaboration.matcher import IdeaMatcher
                
                # Create Idea Object
                new_idea = Idea(
                    title=idea_title,
                    description=idea_desc,
                    author_name="Student/Faculty (You)",
                    college=idea_college,
                    tags=[t.strip() for t in idea_tags.split(",") if t.strip()]
                )
                
                # Match
                matcher = IdeaMatcher()
                matches = matcher.match_idea(new_idea)
                
                # Impact Analysis
                from src.analysis.impact_analyzer import ImpactAnalyzer
                analyzer = ImpactAnalyzer()
                with st.spinner("Analyzing Research Impact..."):
                    impact = analyzer.analyze_impact(new_idea.title, new_idea.description)
                
                # Save to session state for Prism view
                st.session_state.last_matches = matches
                
                div1, div2 = st.columns(2)
                with div1: 
                    st.success("Idea analyzed! Here are your potential collaborators:")
                    st.metric("Impact Score", f"{impact.get('score', 0)}/10")
                    st.caption(impact.get('summary', ''))
                    st.write(f"**SDGs**: {', '.join(impact.get('sdgs', []))}")
                with div2:
                    st.info("Check the Prism View on the right!")
                
                # Display Results
                collaborators = matches.get("collaborators", [])
                if collaborators:
                    for collab in collaborators:
                        meta = collab.get("metadata", {})
                        with st.expander(f"👤 {meta.get('name', 'Unknown')} ({meta.get('doc_type', 'Faculty')})"):
                            st.markdown(f"**College**: {meta.get('college', 'Unknown')}")
                            st.markdown(f"**Relevance**: {1 - collab.get('distance', 1):.2f}")
                            st.write(collab.get("content"))
                else:
                    st.info("No direct faculty matches found yet. Try expanding your description.")
                    
                # Save to DB (Implicitly simulated for now, normally would call store.add_idea(new_idea))
                # store.add_idea(new_idea)

    with col_b:
        st.subheader("🔭 Prism View")
        st.caption("Visualizing research connections.")
        
        # If we have matches from the form submission state
        if 'last_matches' in st.session_state:
            from src.ui.prism_view import render_prism_graph
            matches = st.session_state.last_matches
            collaborators = matches.get("collaborators", [])
            
            if collaborators:
                render_prism_graph([], collaborators)
            else:
                st.info("No connections to visualize yet.")
        else:
             st.info("Post an idea to see the knowledge graph build up!")
             st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Network_representation_of_brain.png/640px-Network_representation_of_brain.png", caption="Example Connectivity")
