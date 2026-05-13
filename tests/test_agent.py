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

from pathlib import Path

import agent


def test_list_files_returns_wiki_files(tmp_path, monkeypatch):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()
    file_path = wiki_dir / "example.md"
    file_path.write_text("# Example", encoding="utf-8")

    monkeypatch.setattr(agent, "WIKI_DIR", wiki_dir)

    assert agent.list_files() == ["example.md"]


def test_read_file_blocks_path_traversal(tmp_path, monkeypatch):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir()

    monkeypatch.setattr(agent, "WIKI_DIR", wiki_dir)

    with pytest.raises(ValueError):
        agent.read_file("../secret.txt")
