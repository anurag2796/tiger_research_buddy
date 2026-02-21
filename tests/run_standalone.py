import sys
import os

print("--- STANDALONE RUNNER ---")
print("CWD:", os.getcwd())

try:
    import src.pipeline_v2
    print("SUCCESS: Imported src.pipeline_v2")
except Exception as e:
    print(f"CRASHED: {e}")
