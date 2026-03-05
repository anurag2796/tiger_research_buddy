import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import logging
import time
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.db_logger import setup_db_logging, log_timing
from src.database.database import ResearchDatabase, get_connection

def test_db_logging():
    print("Testing Database Logging...")
    
    # Setup
    test_logger = setup_db_logging("test_logger")
    db = ResearchDatabase()
    
    # 0. Test Direct DB Write
    print("Testing Direct DB Write...")
    direct_msg = f"Direct Message {time.time()}"
    db.log_message("INFO", "test_direct", direct_msg)
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs WHERE message = ?", (direct_msg,))
        row = cursor.fetchone()
        assert row is not None, "Direct log message not found in DB"
        print("✅ Direct DB Write verified")

    # 1. Test Log Message
    test_message = f"Test Log Message {time.time()}"
    test_logger.info(test_message, extra={'meta': {'test': True}})
    print(f"Logged: {test_message}")
    
    # Verify
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM logs WHERE message LIKE ?", (f"%{test_message}%",))
        row = cursor.fetchone()
        assert row is not None, "Log message not found in DB"
        assert row['level'] == 'INFO', f"Expected INFO, got {row['level']}"
        print("✅ Log Message verified")

    # 2. Test Timing
    print("Testing Timing...")
    
    @log_timing("Test Operation")
    def sleepy_function():
        time.sleep(0.5)
        return "Done"
        
    sleepy_function()
    
    # Verify
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM process_timings WHERE operation = 'Test Operation' ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        assert row is not None, "Timing record not found in DB"
        assert 0.4 < row['duration_seconds'] < 0.6, f"Expected ~0.5s, got {row['duration_seconds']}"
        print(f"✅ Timing verified: {row['duration_seconds']}s")

if __name__ == "__main__":
    try:
        test_db_logging()
        print("🎉 All Tests Passed!")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
