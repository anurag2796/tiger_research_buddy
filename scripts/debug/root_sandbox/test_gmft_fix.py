from gmft.auto import AutoTableDetector
from gmft.pdf_bindings import PyPDFium2Document

pdf_path = "data/pdfs/connor_language_models_as_emotional_classifiers_for_textual_convers.pdf"
print("Initing detector")
detector = AutoTableDetector()
print("Extracting")
try:
    doc = PyPDFium2Document(pdf_path)
    tables = []
    for page in doc:
        tables.extend(detector.extract(page))
    print(f"Extracted {len(tables)} tables")
except Exception as e:
    import traceback
    traceback.print_exc()
