import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import sys
import os
print("CWD:", os.getcwd())
print("sys.path:", sys.path)
try:
    import src.pipeline
    print("Successfully imported src.pipeline")
    print("File:", src.pipeline.__file__)
except Exception as e:
    print("Import failed/crashed:", e)
