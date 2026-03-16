import logging
from src.chatbot.query_engine import GraphEnhancedQueryEngine

# Set logging level
logging.basicConfig(level=logging.INFO)

try:
    engine = GraphEnhancedQueryEngine()
    
    print("Testing query 1: 'What are the research areas in computing?'")
    insights1 = engine.get_graph_insights("What are the research areas in computing?")
    print(f"Insights 1 keys: {insights1.keys()}")
    
    print("\nTesting query 2: 'Who is Christopher Kanan?'")
    insights2 = engine.get_graph_insights("Who is Christopher Kanan?")
    print(f"Insights 2 keys: {insights2.keys()}")
    
    print("\nSUCCESS: No binder exceptions thrown!")
    
except Exception as e:
    print(f"FAILED with error: {e}")
