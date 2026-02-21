
import sqlite3
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()
DB_PATH = Path("data/tiger_research.db")

def inspect_db():
    if not DB_PATH.exists():
        console.print("[red]❌ Database not found![/]")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check process_timings
    console.print("\n[bold blue]📊 Process Timings:[/]")
    cursor.execute("SELECT COUNT(*) as count FROM process_timings")
    count = cursor.fetchone()['count']
    console.print(f"Total rows: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM process_timings ORDER BY created_at DESC LIMIT 5")
        table = Table(title="Recent Timings")
        table.add_column("Operation")
        table.add_column("Duration (s)")
        table.add_column("Time")
        for row in cursor.fetchall():
            table.add_row(row['operation'], str(row['duration_seconds']), row['created_at'])
        console.print(table)

    # Check logs
    console.print("\n[bold blue]📜 Application Logs:[/]")
    cursor.execute("SELECT COUNT(*) as count FROM logs")
    count = cursor.fetchone()['count']
    console.print(f"Total rows: {count}")
    
    if count > 0:
        cursor.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT 5")
        table = Table(title="Recent Logs")
        table.add_column("Module")
        table.add_column("Level")
        table.add_column("Message")
        for row in cursor.fetchall():
            table.add_row(row['module'], row['level'], row['message'])
        console.print(table)

    conn.close()

if __name__ == "__main__":
    inspect_db()
