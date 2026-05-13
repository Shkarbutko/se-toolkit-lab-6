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

def test_query_api_uses_env_and_api_key(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = '{"ok": true}'

    def fake_request(method, url, headers, json, timeout):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("LMS_API_KEY", "test-lms-key")
    monkeypatch.setenv("AGENT_API_BASE_URL", "http://example.com")
    monkeypatch.setattr(agent.requests, "request", fake_request)

    result = agent.query_api("get", "/items/")

    assert captured["method"] == "GET"
    assert captured["url"] == "http://example.com/items/"
    assert captured["headers"] == {"X-API-Key": "test-lms-key"}
    assert captured["json"] is None
    assert captured["timeout"] == 15
    assert '"status_code": 200' in result


def test_query_api_parses_json_body(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 201
        text = '{"created": true}'

    def fake_request(method, url, headers, json, timeout):
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setenv("LMS_API_KEY", "test-lms-key")
    monkeypatch.setenv("AGENT_API_BASE_URL", "http://example.com")
    monkeypatch.setattr(agent.requests, "request", fake_request)

    agent.query_api("post", "/items/", '{"name": "Test"}')

    assert captured["json"] == {"name": "Test"}
