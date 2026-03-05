from gmft.auto import AutoTableDetector, AutoTableFormatter
import os

pdf_path = "data/pdfs/connor_language_models_as_emotional_classifiers_for_textual_convers.pdf"
if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    import sys
    sys.exit(1)

print("Initing detector")
detector = AutoTableDetector()
print("Extracting from PDF")
try:
    tables = detector.extract(pdf_path)
    print(f"Extracted {len(tables)} tables")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
