import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import sys
import traceback

print("Python executable:", sys.executable)
print("Python version:", sys.version)

print("\n--- Testing Surya Import ---")
try:
    import surya
    print("Surya imported successfully")
    from surya.recognition import RecognitionPredictor
    print("Surya RecognitionPredictor imported successfully")
except Exception:
    traceback.print_exc()

print("\n--- Testing Marker Import ---")
try:
    import marker
    print("Marker imported successfully")
    from marker.convert import convert_single_pdf
    print("Marker convert_single_pdf imported successfully")
except Exception:
    traceback.print_exc()
