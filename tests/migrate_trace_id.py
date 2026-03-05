import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import sqlite3
from pathlib import Path

db_path = Path("data/tiger_research.db")

def migrate_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Migrate logs table
    try:
        cursor.execute("SELECT trace_id FROM logs LIMIT 1")
    except sqlite3.OperationalError:
        print("Migrating logs table from log_id to trace_id...")
        cursor.execute("ALTER TABLE logs RENAME TO logs_old;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                level TEXT NOT NULL,
                module TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                meta_json TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO logs (id, trace_id, level, module, message, created_at, meta_json)
            SELECT id, log_id, level, module, message, created_at, meta_json FROM logs_old;
        """)
        cursor.execute("DROP TABLE logs_old;")
        conn.commit()

    # 2. Migrate process_timings table
    try:
        cursor.execute("SELECT trace_id FROM process_timings LIMIT 1")
    except sqlite3.OperationalError:
        print("Migrating process_timings table from log_id to trace_id...")
        cursor.execute("ALTER TABLE process_timings RENAME TO process_timings_old;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_timings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT,
                operation TEXT NOT NULL,
                duration_seconds REAL,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                meta_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT INTO process_timings (id, trace_id, operation, duration_seconds, start_time, end_time, meta_json, created_at)
            SELECT id, log_id, operation, duration_seconds, start_time, end_time, meta_json, created_at FROM process_timings_old;
        """)
        cursor.execute("DROP TABLE process_timings_old;")
        conn.commit()

    # Recreate indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_process_timings_trace_id ON process_timings(trace_id)")
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    if db_path.exists():
        migrate_db()
    else:
        print("DB does not exist.")
