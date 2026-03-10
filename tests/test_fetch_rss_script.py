"""Unit tests for RSS full-content extraction fallback logic."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType


def _module() -> ModuleType:
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "fetch_rss.py"
    spec = importlib.util.spec_from_file_location("fetch_rss_under_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/fetch_rss.py for testing.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_entry_content_uses_extracted_text_when_long(monkeypatch) -> None:
    module = _module()

    class _Requests:
        @staticmethod
        def get(url: str, timeout: int):
            assert url == "https://example.com/story"
            assert timeout == 10
            return SimpleNamespace(text="<html><body>Article</body></html>")

    class _Trafilatura:
        @staticmethod
        def extract(_html: str) -> str:
            return "A" * 220

    monkeypatch.setattr(module, "requests", _Requests)
    monkeypatch.setattr(module, "trafilatura", _Trafilatura)

    entry = SimpleNamespace(link="https://example.com/story", summary="Short RSS summary")
    assert module._resolve_entry_content(entry) == "A" * 220


def test_resolve_entry_content_falls_back_when_extracted_text_is_short(monkeypatch) -> None:
    module = _module()

    class _Requests:
        @staticmethod
        def get(_url: str, timeout: int):
            assert timeout == 10
            return SimpleNamespace(text="<html><body>Short</body></html>")

    class _Trafilatura:
        @staticmethod
        def extract(_html: str) -> str:
            return "Too short"

    monkeypatch.setattr(module, "requests", _Requests)
    monkeypatch.setattr(module, "trafilatura", _Trafilatura)

    entry = SimpleNamespace(link="https://example.com/story", summary="RSS fallback summary")
    assert module._resolve_entry_content(entry) == "RSS fallback summary"


def test_resolve_entry_content_falls_back_when_request_fails(monkeypatch) -> None:
    module = _module()

    class _Requests:
        @staticmethod
        def get(_url: str, timeout: int):
            assert timeout == 10
            raise TimeoutError("timeout")

    class _Trafilatura:
        @staticmethod
        def extract(_html: str) -> str:
            return "B" * 500

    monkeypatch.setattr(module, "requests", _Requests)
    monkeypatch.setattr(module, "trafilatura", _Trafilatura)

    entry = SimpleNamespace(link="https://example.com/story", summary="RSS fallback summary")
    assert module._resolve_entry_content(entry) == "RSS fallback summary"


def test_resolve_entry_content_falls_back_when_extraction_fails(monkeypatch) -> None:
    module = _module()

    class _Requests:
        @staticmethod
        def get(_url: str, timeout: int):
            assert timeout == 10
            return SimpleNamespace(text="<html><body>Article</body></html>")

    class _Trafilatura:
        @staticmethod
        def extract(_html: str) -> str:
            raise RuntimeError("extract failed")

    monkeypatch.setattr(module, "requests", _Requests)
    monkeypatch.setattr(module, "trafilatura", _Trafilatura)

    entry = SimpleNamespace(link="https://example.com/story", summary="RSS fallback summary")
    assert module._resolve_entry_content(entry) == "RSS fallback summary"
