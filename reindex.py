from src.database.vector_store import load_data_to_vectorstore, get_vector_store
from src.utils.config import RESTRICTED_CONFIG, FULL_CONFIG, DATA_DIR
import shutil, json

# Use whichever config matches API_MODE in .env
import os
api_mode = os.getenv("API_MODE", "restricted")
config = FULL_CONFIG if api_mode == "full" else RESTRICTED_CONFIG
print(f"Using config: {api_mode} → CHROMA_DIR={config.CHROMA_DIR}")

chroma_path = config.CHROMA_DIR
if chroma_path.exists():
    shutil.rmtree(chroma_path)
    print(f"Cleared {chroma_path}")

# Index faculty + papers
store = load_data_to_vectorstore(config)

# Index ALL research cards from the full data directory
cards_dir = DATA_DIR / "research_cards"
cards = []
for card_file in sorted(cards_dir.glob("*.json")):
    try:
        with open(card_file) as f:
            cards.append(json.load(f))
    except Exception:
        pass

if cards:
    store.add_research_cards(cards)
    print(f"Indexed {len(cards)} research cards from {cards_dir}")
else:
    print(f"No research cards found in {cards_dir}")

print("Done.")
