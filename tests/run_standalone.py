import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import sys
import os

print("--- STANDALONE RUNNER ---")
print("CWD:", os.getcwd())

try:
    import src.pipeline_v2
    print("SUCCESS: Imported src.pipeline_v2")
except Exception as e:
    print(f"CRASHED: {e}")
