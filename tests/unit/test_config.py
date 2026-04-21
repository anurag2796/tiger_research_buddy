import pytest
from src.utils.config import HW_PROFILE, RESTRICTED_CONFIG, FULL_CONFIG

def test_config_hw_profile():
    assert HW_PROFILE.is_linux is True
    assert HW_PROFILE.context_window > 0

def test_config_modes():
    assert RESTRICTED_CONFIG.MODE == "restricted"
    assert RESTRICTED_CONFIG.MAX_PROFILES == 10
    assert FULL_CONFIG.MODE == "full"
    assert FULL_CONFIG.MAX_PROFILES == 1000
