import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import os
import sys
# Add src to path
sys.path.append(os.getcwd())

from src.utils.document_processor import load_det_model, load_rec_model, load_det_processor, load_rec_processor

print("Attempting to load Surya models...")

try:
    print("Loading Detection Model...")
    det_model = load_det_model()
    print("Detection Model loaded.")
except Exception as e:
    print(f"Error loading Detection Model: {e}")

try:
    print("Loading Recognition Model...")
    rec_model = load_rec_model()
    print("Recognition Model loaded.")
except Exception as e:
    print(f"Error loading Recognition Model: {e}")
