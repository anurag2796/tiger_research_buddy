import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from dagster import ExecuteInProcessResult
import sys
import os

# Ensure CWD is in path
sys.path.insert(0, os.getcwd())

print("--- MANUAL PIPELINE RUNNER ---")
try:
    from src.pipeline_v2 import defs
    print("Loaded defs")
    
    # Check imports
    if 'src.crawlers.paper_downloader' in sys.modules:
        m = sys.modules['src.crawlers.paper_downloader']
        print(f"PaperDownloader (V3) loaded from: {m.__file__}")
    else:
        print("PaperDownloader (V3) NOT in sys.modules yet")
        # Force import
        import src.crawlers.paper_downloader as pd
        print(f"PaperDownloader (V3) force loaded from: {pd.__file__}")

    job_def = defs.get_job_def("full_pipeline")
    print(f"Executing job: {job_def.name}")
    
    # Execute
    result = job_def.execute_in_process()
    
    if result.success:
        print("Pipeline Succeeded")
    else:
        print("Pipeline Failed")
        
except Exception as e:
    print(f"CRITICAL FAILURE: {e}")
    import traceback
    traceback.print_exc()
