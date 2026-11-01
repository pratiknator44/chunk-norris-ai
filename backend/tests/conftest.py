# Test suite configuration for DocExtract backend
import pytest


@pytest.fixture
def sample_markdown() -> str:
    return """# Sample Document

This is paragraph 1 mentioning Alice from Wonderland.

This is paragraph 2 mentioning Bob from Atlantis.
"""
