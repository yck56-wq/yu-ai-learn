import pytest

from app.grounding import Source, normalize_sources, extract_urls
from app import retrieval


def test_extracts_urls_from_user_input():
    assert extract_urls('请学习 https://example.com/docs?a=1。') == ['https://example.com/docs?a=1']


def test_normalizes_and_deduplicates_sources():
    sources = normalize_sources([
        {'title': 'A', 'url': 'https://example.com/page?utm_source=x', 'content': 'Harness Engineering 是工程实践。', 'score': 0.9},
        {'title': 'A duplicate', 'url': 'https://example.com/page', 'content': 'duplicate', 'score': 0.8},
    ], query='Harness Engineering')
    assert len(sources) == 1
    assert sources[0].url == 'https://example.com/page'
    assert sources[0].snippet


def test_empty_sources_are_allowed_for_fallback():
    assert normalize_sources([], query='new topic') == []


def test_retrieval_failure_falls_back_without_leaking_error(monkeypatch, caplog):
    monkeypatch.setitem(__import__('sys').modules, 'langchain_tavily', None)
    assert retrieval.retrieve_sources('Harness Engineering') == []


def test_agent_exposes_search_and_extract_tools(monkeypatch):
    monkeypatch.setenv('TAVILY_API_KEY', 'test-only-placeholder')
    captured = {}
    import langchain.agents
    monkeypatch.setattr(langchain.agents, 'create_agent', lambda **kwargs: captured.update(kwargs) or object())
    retrieval.build_grounding_agent(object())
    names = {tool.name for tool in captured['tools']}
    assert {'tavily_search_basic', 'tavily_search_deep', 'tavily_extract'} <= names
