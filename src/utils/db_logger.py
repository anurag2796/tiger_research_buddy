import logging
import json
import time
import functools
import uuid
from datetime import datetime
from typing import Optional, Any
from contextlib import contextmanager
from contextvars import ContextVar
from .config import DATA_DIR
from ..database.database import ResearchDatabase

# Create a singleton database instance for logging to avoid re-creation
_db_instance = None

# Context variable to hold the current transaction/trace ID
current_trace_id: ContextVar[str] = ContextVar('trace_id', default='')

def generate_trace_id() -> str:
    """Generate a new UUID trace ID and set it for the current context."""
    new_id = str(uuid.uuid4())
    current_trace_id.set(new_id)
    return new_id
    
def get_trace_id() -> str:
    """Get the current trace ID if one exists, else empty."""
    return current_trace_id.get()

def get_db():
    global _db_instance
    if _db_instance is None:
        _db_instance = ResearchDatabase()
    return _db_instance

class TraceIdFilter(logging.Filter):
    """Injects the 'trace_id' attribute into LogRecords."""
    def filter(self, record):
        record.trace_id = get_trace_id()
        return True

class DatabaseHandler(logging.Handler):
    """
    Custom logging handler that writes logs to the SQLite database.
    """
    def __init__(self):
        super().__init__()
        self.db = get_db()

    def emit(self, record):
        try:
            msg = self.format(record)
            # print(f"DEBUG: Emitting log: {msg}") # Debug print
            
            # Extract metadata if available (e.g., passing extra={'meta': {...}})
            meta = getattr(record, 'meta', None)
            meta_json = json.dumps(meta) if meta else None
            
            row_id = self.db.log_message(
                level=record.levelname,
                module=record.name,
                message=msg,
                meta_json=meta_json,
                trace_id=getattr(record, 'trace_id', '')
            )
            # print(f"DEBUG: Logged to DB with ID: {row_id}") # Debug print
        except Exception:
            self.handleError(record)

def setup_db_logging(logger_name: Optional[str] = None, level=logging.INFO):
    """
    Configures a logger to use the DatabaseHandler.
    If logger_name is None, configures the root logger.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Formatter with timestamp and trace_id
    formatter = logging.Formatter(
        '%(asctime)s - [%(trace_id)s] - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    trace_filter = TraceIdFilter()
    logger.addFilter(trace_filter)
    
    # 1. Database Handler
    if not any(isinstance(h, DatabaseHandler) for h in logger.handlers):
        db_handler = DatabaseHandler()
        db_handler.setFormatter(formatter)
        logger.addHandler(db_handler)
        
    # 2. File Handler (logs/app.log)
    log_dir = DATA_DIR.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "tiger_buddy.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 3. Console Handler (for timestamped stdout)
    # Avoid duplicate console handlers if basicConfig was called
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger

class PerformanceTimer:
    """
    Context manager and decorator for timing operations and logging to DB.
    """
    def __init__(self, operation_name: str, meta: dict = None, use_rich: bool = False):
        self.operation_name = operation_name
        self.meta = meta or {}
        self.db = get_db()
        self.start_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        self.duration = end_time - self.start_time
        
        # Add error info to meta if exception occurred
        if exc_type:
            self.meta['error'] = str(exc_val)
            self.meta['error_type'] = exc_type.__name__

        self.db.log_timing(
            operation=self.operation_name,
            duration=self.duration,
            start_time=datetime.fromtimestamp(self.start_time).isoformat(),
            end_time=datetime.fromtimestamp(end_time).isoformat(),
            meta_json=json.dumps(self.meta),
            trace_id=get_trace_id()
        )

def log_timing(operation_name: str):
    """
    Decorator for timing functions.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get some context for meta
            meta = {
                "args": [str(a) for a in args], 
                "kwargs": {k: str(v) for k, v in kwargs.items()}
            }
            # Limit meta size
            if len(json.dumps(meta)) > 1000:
                 meta = {"note": "Args too large to index"}

            with PerformanceTimer(operation_name, meta=meta):
                return func(*args, **kwargs)
        return wrapper
    return decorator
