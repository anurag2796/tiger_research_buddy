import streamlit as st
import time
import json
from pathlib import Path
from rich.console import Console

# Import backend components
from src.database.vector_store import get_vector_store, process_data_into_documents
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.synthesizer import ResponseSynthesizer
from src.utils.config import RESTRICTED_CONFIG

# Page Config
st.set_page_config(
    page_title="TigerBrain Advisor",
    page_icon="🐅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* RIT Colors: Orange #F76902, Black #000000 */
    .stApp {
        background-color: #f8f9fa;
    }
    .stChatMessage {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    h1, h2, h3 {
        color: #F76902;
    }
    .stSidebar {
        background-color: #2c2c2c;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://www.rit.edu/sites/default/files/styles/embedded_media_100pc_width/public/2020-03/RIT_logo_2018.png?itok=WkZl6p1b", width=150)
    st.title("TigerStack 2.0 🧠")
    st.markdown("---")
    st.markdown("**Status**: ✅ System Online")
    
    # Get stats placeholder
    stats_placeholder = st.empty()
    stats_placeholder.markdown("**Docs**: Loading...")
    
    st.markdown("**Model**: `tigerbuddy:latest`")
    st.markdown("---")
    use_cod = st.checkbox("🧬 Deep Analysis (CoD)", value=False, help="Use Chain of Density prompting for deeper, denser answers. (Slower)")
    if st.button("Reset Chat"):
        st.session_state.messages = []
        st.rerun()

# Initialization (Cached)
@st.cache_resource
def get_engine():
    """Load backend components once."""
    print("Loading Engine...")
    
    # 1. Initialize Vector Store
    vector_store = get_vector_store(RESTRICTED_CONFIG)
    vector_store.initialize()
    
    # 2. Load Documents for BM25
    # We load the source JSON to build the BM25 index
    data_path = RESTRICTED_CONFIG.OUTPUT_FILE
    documents = []
    
    if data_path.exists():
        with open(data_path, "r") as f:
            data = json.load(f)
        documents = process_data_into_documents(data)
    else:
        print("Warning: Data file not found. BM25 will be empty.")
        
    # 3. Initialize Hybrid Retriever
    retriever = HybridRetriever(
        vector_store=vector_store,
        documents=documents
    )
    
    synthesizer = ResponseSynthesizer()
    return retriever, synthesizer, len(documents)

try:
    retriever, synthesizer, doc_count = get_engine()
    # Update sidebar stats
    if stats_placeholder:
        stats_placeholder.markdown(f"**Docs**: {doc_count}")
        
except Exception as e:
    st.error(f"Failed to load system: {e}")
    st.stop()

# Chat Logic
st.title("🎓 TigerBrain Academic Advisor")
st.markdown("Ask me about **Research**, **Faculty**, or **Thesis Topics** at Golisano College.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Add initial greeting
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Hello! I'm your AI Research Advisor. Accessing RIT faculty profiles and papers. How can I help you today?"
    })

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🐅" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Ex: Who works on Spiking Neural Networks?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # Chitchat Handler
    low_prompt = prompt.lower().strip().strip('?!.')
    if low_prompt in ["hi", "hello", "hey", "how are you", "who are you", "help"]:
        full_response = (
            "Hello! I'm your AI Research Advisor for Golisano College. 🐅\n\n"
            "I can help you:\n"
            "- Find **Faculty** aligning with your interests.\n"
            "- Explore **Research Papers** and topics.\n"
            "- Suggest **Capstone/Thesis** ideas.\n\n"
            "Try asking: *\"Who works on Computer Vision?\"* or *\"Tell me about Professor Kinsman\"*."
        )
        with st.chat_message("assistant", avatar="🐅"):
            st.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.stop() # Stop execution to skip retrieval

    # Generate response
    with st.chat_message("assistant", avatar="🐅"):
        message_placeholder = st.empty()
        full_response = ""
        
        with st.spinner("Searching RIT Database (Hybrid)..."):
            try:
                # 1. Hybrid Search (Vector + BM25 + RRF)
                results = retriever.hybrid_search(prompt, k=5)
                
                # 2. Synthesize
                full_response = synthesizer.synthesize(prompt, results, use_cod=use_cod)
                
                message_placeholder.markdown(full_response)
                
            except Exception as e:
                full_response = f"❌ **Error**: {str(e)}"
                message_placeholder.markdown(full_response)
        
        # Add to history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
