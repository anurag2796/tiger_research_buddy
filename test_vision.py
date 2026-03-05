import sys
from pathlib import Path
from src.crawlers.vision_crawler import VisionCrawler

pdf = "data/pdfs/connor_language_models_as_emotional_classifiers_for_textual_convers.pdf"
crawler = VisionCrawler(engine="apple_fast")
try:
    res = crawler.convert(pdf, force_reprocess=True)
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
