import time
import functools
import logging
from typing import Optional, Any
from contextlib import ContextDecorator
from rich.console import Console

# Configure rich console
console = Console()

# Configure standard logger as fallback
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TigerTimer")

class Timer(ContextDecorator):
    """
    A timer class that can be used as a context manager or decorator.
    
    Usage:
        with Timer("my_operation"):
            # code to time
            
        @Timer("my_function")
        def my_function():
            # code to time
    """
    
    def __init__(self, name: str, level: str = "INFO", use_rich: bool = True):
        """
        Initialize the timer.
        
        Args:
            name: The name of the operation being timed.
            level: The logging level (INFO, DEBUG, etc.).
            use_rich: Whether to use rich console for output.
        """
        self.name = name
        self.level = level.upper()
        self.use_rich = use_rich
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        if self.use_rich:
            console.print(f"[dim]⏱️  Starting {self.name}...[/]")
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time
        
        message = f"✅ {self.name} finished in {self.duration:.4f}s"
        
        if self.use_rich:
            style = "bold green" if self.duration < 1.0 else "bold yellow"
            if self.duration > 5.0:
                style = "bold red"
            console.print(f"[{style}]{message}[/]")
        else:
            if self.level == "DEBUG":
                logger.debug(message)
            else:
                logger.info(message)
                
        # Optional: We could log to a file or metrics system here
        
        return False  # Propagate exceptions

    # The __call__ method is provided by ContextDecorator
