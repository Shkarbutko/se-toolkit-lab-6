import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import get_env


def test_get_env_reads_primary_variable(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    assert get_env("LLM_API_KEY") == "test-key"


def test_get_env_reads_fallback_variable(monkeypatch):
    monkeypatch.delenv("LLM_API_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_API_BASE", "https://example.com")

    assert get_env("LLM_API_BASE_URL", "LLM_API_BASE") == "https://example.com"


def test_get_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)

    with pytest.raises(RuntimeError):
        get_env("MISSING_VAR")
