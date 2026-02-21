
import sys
from pathlib import Path
import pandas as pd
import sqlite3
from rich.console import Console
from rich.table import Table

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))
from src.utils.config import DATA_DIR
from src.database.database import DB_PATH

console = Console()

def analyze_timings():
    """Analyze process timings."""
    conn = sqlite3.connect(str(DB_PATH))
    
    query = """
    SELECT operation, duration_seconds, start_time 
    FROM process_timings 
    WHERE created_at > datetime('now', '-1 day')
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            console.print("[yellow]No timing data found for the last 24 hours.[/]")
            return

        # Aggregate stats
        stats = df.groupby('operation')['duration_seconds'].agg(
            Count='count',
            Mean='mean',
            Min='min',
            Max='max',
            Total='sum'
        ).reset_index()
        
        # Sort by total time
        stats = stats.sort_values(by='Total', ascending=False)
        
        # Display Table
        table = Table(title="⏱️ Process Performance Analysis (Last 24h)")
        table.add_column("Operation", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Mean (s)", justify="right", style="green")
        table.add_column("Max (s)", justify="right", style="red")
        table.add_column("Total Time (s)", justify="right", style="magenta")
        
        for _, row in stats.iterrows():
            table.add_row(
                row['operation'],
                str(int(row['Count'])),
                f"{row['Mean']:.4f}",
                f"{row['Max']:.4f}",
                f"{row['Total']:.2f}"
            )
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error analyzing timings: {e}[/]")
    finally:
        conn.close()

def show_recent_errors(limit=10):
    """Show recent error logs."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    query = """
    SELECT created_at, module, message 
    FROM logs 
    WHERE level = 'ERROR' 
    ORDER BY created_at DESC 
    LIMIT ?
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        
        if not rows:
            console.print("[green]No errors found in logs.[/]")
            return

        table = Table(title=f"❌ Recent Errors (Last {limit})")
        table.add_column("Time", style="dim")
        table.add_column("Module", style="cyan")
        table.add_column("Message", style="red")
        
        for row in rows:
            table.add_row(
                row['created_at'],
                row['module'],
                row['message']
            )
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error fetching logs: {e}[/]")
    finally:
        conn.close()

if __name__ == "__main__":
    console.print("[bold blue]📊 Analyzing System Performance[/]")
    analyze_timings()
    print("\n")
    show_recent_errors()
