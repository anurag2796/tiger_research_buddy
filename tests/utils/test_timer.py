import sys, os; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src.utils.timer import Timer
import time
import pytest

def test_timer_context_manager(capsys):
    with Timer("context_manager_test"):
        time.sleep(0.1)
    # capturing rich output is tricky with capsys as it might write to stdout/stderr directly
    # but we can at least ensure no exception is raised

def test_timer_decorator():
    @Timer("decorator_test")
    def sleepy():
        time.sleep(0.1)
    
    sleepy()
