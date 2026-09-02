"""
Pytest configuration and shared fixtures for avatar_voice module.
"""

import os
import shutil
import tempfile
import pytest

@pytest.fixture
def temp_output_dir():
    """Provide an isolated temporary directory for test artifacts."""
    d = tempfile.mkdtemp(prefix="shikshak_test_av_")
    yield d
    shutil.rmtree(d, ignore_errors=True)
