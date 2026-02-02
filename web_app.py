
import streamlit as st
import time
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.database import get_vector_store
from src.chatbot.ollama_client import get_ollama_client

# Page config
st.set_page_config(
    page_title="TigerResearchBuddy",
    page_icon="🐅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 10px;
        padding: 10px;
    }
    .stButton button {
        border-radius: 20px;
    }
    h1 {
        color: #F76902;
    }
</style>
""", unsafe_allow_html=True)

# Initialize resources (cached)
@st.cache_resource
def load_resources():
    try:
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
    st.image("https://brand.rit.edu/sites/rit.edu.brand/files/images/Brand%20Portal/Logos/RIT_logo_black.png", use_column_width=True)
    st.title("Research Hub")
    
    if store:
        stats = store.get_stats()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", stats.get('total_documents', 0))
        with col2:
            st.metric("Collection", "RIT Data")
            
            
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


# Main Chat Interface
st.header("🐅 TigerResearchBuddy")
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
    
    # Generate response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        if store and client:
            with st.spinner("Searching knowledge base..."):
                # RAG: Search
                results = store.search(prompt, n_results=4)
                context = "\n\n".join([r.get("content", "") for r in results])
                
                # RAG: Generate
                system_prompt = """You are TigerResearchBuddy, an AI assistant helping RIT students discover research opportunities.
                Use the context provided to answer questions about RIT Computing research, faculty, and opportunities.
                
                Formatting Rules:
                - Do NOT use large headers (like # or ##) for the main response body.
                - Use standard text for descriptions.
                - Use **Bold** for Faculty Names, Paper Titles, and Section Headers (e.g. **Research Interests:**).
                - Use bullet points for lists.
                - Be concise and avoid wall-of-text.

                Be helpful, accurate, and encouraging about research careers.
                If looking for faculty, include their contact info if available.
                """
                
                # Stream response (simulated streaming from Ollama if simple, or just wait)
                response = client.generate(prompt, context=context, system_prompt=system_prompt)
                
                # Simulate typing effect for the video demo 'feel'
                for chunk in response.split():
                    full_response += chunk + " "
                    time.sleep(0.02)
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                
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
