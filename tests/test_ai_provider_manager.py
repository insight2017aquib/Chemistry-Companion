"""
tests/test_ai_provider_manager.py
==================================
Tests for the AIProviderManager (Phase 01 Foundation).

All tests use mocking — no real API keys or network access required.
"""

import json
import os
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from services.ai.models import AIResponse, HealthCheckResult
from services.ai.provider_manager import AIProviderManager, _call_gemini


# ═══════════════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def manager():
    """Create an AIProviderManager with default settings."""
    return AIProviderManager()


@pytest.fixture
def manager_custom():
    """Create an AIProviderManager with custom settings."""
    return AIProviderManager(
        fast_provider="deepseek",
        reasoning_provider="groq",
        fallback_chain=["deepseek", "groq"],
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Initialization Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestInitialization:
    def test_default_fast_provider(self, manager):
        assert manager.fast_provider == "groq"

    def test_default_reasoning_provider(self, manager):
        assert manager.reasoning_provider == "gemini"

    def test_custom_fast_provider(self, manager_custom):
        assert manager_custom.fast_provider == "deepseek"

    def test_custom_reasoning_provider(self, manager_custom):
        assert manager_custom.reasoning_provider == "groq"

    def test_custom_fallback_chain(self, manager_custom):
        assert manager_custom._fallback_chain == ["deepseek", "groq"]

    def test_env_var_fast_provider(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_FAST_PROVIDER", "openrouter")
        mgr = AIProviderManager()
        assert mgr.fast_provider == "openrouter"

    def test_env_var_reasoning_provider(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_REASONING_PROVIDER", "deepseek")
        mgr = AIProviderManager()
        assert mgr.reasoning_provider == "deepseek"

    def test_env_var_fallback_chain(self, monkeypatch):
        monkeypatch.setenv("FALLBACK_CHAIN", "groq,gemini")
        mgr = AIProviderManager()
        assert mgr._fallback_chain == ["groq", "gemini"]

    def test_get_fast_provider_method(self, manager):
        assert manager.get_fast_provider() == "groq"

    def test_get_reasoning_provider_method(self, manager):
        assert manager.get_reasoning_provider() == "gemini"


# ═══════════════════════════════════════════════════════════════════════════
#  Gemini Registration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGeminiRegistration:
    def test_gemini_in_provider_registry(self):
        """Gemini should be registered in the core provider registry."""
        from core.llm_utils import _PROVIDER_REGISTRY
        assert "gemini" in _PROVIDER_REGISTRY

    def test_gemini_registry_fields(self):
        from core.llm_utils import _PROVIDER_REGISTRY
        gemini = _PROVIDER_REGISTRY["gemini"]
        assert gemini["env_key"] == "GEMINI_API_KEY"
        assert "gemini" in gemini["default_model"].lower()
        assert gemini["display_name"]  # non-empty
        assert gemini["api_url"]  # non-empty

    def test_gemini_in_provider_status(self, manager):
        status = manager.get_provider_status()
        provider_ids = [s["id"] for s in status]
        assert "gemini" in provider_ids

    def test_all_four_providers_registered(self):
        from core.llm_utils import _PROVIDER_REGISTRY
        for prov in ("groq", "deepseek", "openrouter", "gemini"):
            assert prov in _PROVIDER_REGISTRY, f"{prov} not in registry"


# ═══════════════════════════════════════════════════════════════════════════
#  Query Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestQuery:
    def test_query_success_with_mock(self, manager, monkeypatch):
        """Successful query returns AIResponse with correct fields."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        with patch("services.ai.provider_manager._call_gemini") as mock_gemini, \
             patch("core.llm_utils._call_provider") as mock_call:
            mock_call.return_value = "Test response text"

            response = manager.query("Hello")

            assert isinstance(response, AIResponse)
            assert response.text == "Test response text"
            assert response.provider_used == "groq"
            assert response.error is None
            assert response.latency_ms is not None
            assert response.is_fallback is False

    def test_query_uses_specified_provider(self, manager, monkeypatch):
        """When provider is specified, it should be tried first."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        with patch("core.llm_utils._call_provider") as mock_call:
            mock_call.return_value = "DeepSeek response"

            response = manager.query("Hello", provider="deepseek")

            assert response.provider_used == "deepseek"
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args[0][0] == "deepseek"  # provider name

    def test_query_fallback_on_failure(self, manager, monkeypatch):
        """When primary fails, should try fallback providers."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

        call_count = 0

        def side_effect(provider, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if provider == "groq":
                raise ConnectionError("Groq unavailable")
            return "Fallback response"

        with patch("core.llm_utils._call_provider", side_effect=side_effect):
            response = manager.query("Hello")

            assert response.text == "Fallback response"
            assert response.provider_used == "deepseek"
            assert response.is_fallback is True
            assert call_count == 2

    def test_query_all_providers_fail(self, manager, monkeypatch):
        """When all providers fail, returns error AIResponse."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        with patch("core.llm_utils._call_provider", side_effect=ConnectionError("fail")), \
             patch("services.ai.provider_manager._call_gemini", side_effect=ConnectionError("fail")):
            response = manager.query("Hello")

            assert response.provider_used == "none"
            assert response.error is not None

    def test_query_no_providers_configured(self, monkeypatch):
        """When no API keys are set, returns a clear error message."""
        # Clear all provider env vars
        for var in ("GROQ_API_KEY", "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(var, raising=False)

        mgr = AIProviderManager()
        response = mgr.query("Hello")

        assert response.provider_used == "none"
        assert "No AI providers configured" in response.text

    def test_query_gemini_uses_gemini_adapter(self, manager, monkeypatch):
        """When Gemini is the provider, should use _call_gemini, not _call_provider."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        with patch("services.ai.provider_manager._call_gemini") as mock_gemini:
            mock_gemini.return_value = "Gemini response"

            response = manager.query("Hello", provider="gemini")

            assert response.provider_used == "gemini"
            mock_gemini.assert_called_once()

    def test_last_provider_used_tracking(self, manager, monkeypatch):
        """last_provider_used should be updated after each query."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        with patch("core.llm_utils._call_provider", return_value="response"):
            manager.query("Hello")
            assert manager.last_provider_used == "groq"


# ═══════════════════════════════════════════════════════════════════════════
#  Structured Query Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestStructuredQuery:
    def test_structured_query_parses_json(self, manager, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        json_response = json.dumps({"answer": "42", "confidence": "high"})

        with patch("core.llm_utils._call_provider", return_value=json_response):
            result = manager.query_structured("Return JSON", expected_keys=["answer"])

            assert result["answer"] == "42"
            assert result["confidence"] == "high"
            assert "_provider_used" in result
            assert "_missing_keys" not in result

    def test_structured_query_with_code_fences(self, manager, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        fenced_response = '```json\n{"answer": "hello"}\n```'

        with patch("core.llm_utils._call_provider", return_value=fenced_response):
            result = manager.query_structured("Return JSON")

            assert result["answer"] == "hello"

    def test_structured_query_reports_missing_keys(self, manager, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        json_response = json.dumps({"partial": True})

        with patch("core.llm_utils._call_provider", return_value=json_response):
            result = manager.query_structured(
                "Return JSON",
                expected_keys=["answer", "confidence"],
            )

            assert "_missing_keys" in result
            assert "answer" in result["_missing_keys"]
            assert "confidence" in result["_missing_keys"]

    def test_structured_query_handles_unparseable_response(self, manager, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        with patch("core.llm_utils._call_provider", return_value="This is not JSON at all"):
            result = manager.query_structured("Return JSON")

            assert "error" in result
            assert "raw_text" in result


# ═══════════════════════════════════════════════════════════════════════════
#  Health Check Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    def test_health_check_no_api_key(self, manager, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        results = manager.health_check("groq")

        assert len(results) == 1
        assert results[0].provider == "groq"
        assert results[0].available is False
        assert results[0].has_api_key is False

    def test_health_check_success(self, manager, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        with patch("core.llm_utils._call_provider", return_value="OK"):
            results = manager.health_check("groq")

            assert len(results) == 1
            assert results[0].available is True
            assert results[0].has_api_key is True
            assert results[0].latency_ms is not None

    def test_health_check_api_failure(self, manager, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")

        with patch("core.llm_utils._call_provider", side_effect=ConnectionError("nope")):
            results = manager.health_check("groq")

            assert len(results) == 1
            assert results[0].available is False
            assert results[0].has_api_key is True
            assert "ConnectionError" in results[0].error

    def test_health_check_unknown_provider(self, manager):
        results = manager.health_check("nonexistent_provider")

        assert len(results) == 1
        assert results[0].available is False
        assert "Unknown provider" in results[0].error

    def test_health_check_all_providers(self, manager, monkeypatch):
        # Clear all keys so health check is fast (no actual calls)
        for var in ("GROQ_API_KEY", "DEEPSEEK_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY"):
            monkeypatch.delenv(var, raising=False)

        results = manager.health_check()

        # Should check all 4 registered providers
        assert len(results) >= 4
        provider_names = [r.provider for r in results]
        assert "groq" in provider_names
        assert "gemini" in provider_names

    def test_health_check_gemini(self, manager, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        with patch("services.ai.provider_manager._call_gemini", return_value="OK"):
            results = manager.health_check("gemini")

            assert len(results) == 1
            assert results[0].available is True
            assert results[0].provider == "gemini"


# ═══════════════════════════════════════════════════════════════════════════
#  Provider Status Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestProviderStatus:
    def test_get_provider_status_returns_all_providers(self, manager):
        status = manager.get_provider_status()
        assert len(status) >= 4

    def test_provider_status_fields(self, manager):
        status = manager.get_provider_status()
        for entry in status:
            assert "id" in entry
            assert "display_name" in entry
            assert "has_api_key" in entry
            assert "default_model" in entry
            assert "note" in entry
            assert "roles" in entry

    def test_provider_status_roles(self, manager):
        status = manager.get_provider_status()
        groq_entry = next(s for s in status if s["id"] == "groq")
        assert "fast" in groq_entry["roles"]

        gemini_entry = next(s for s in status if s["id"] == "gemini")
        assert "reasoning" in gemini_entry["roles"]


# ═══════════════════════════════════════════════════════════════════════════
#  Gemini Adapter Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGeminiAdapter:
    def test_call_gemini_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Hello from Gemini"}
                        ]
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = _call_gemini("test-key", "gemini-2.0-flash", "Hello")
            assert result == "Hello from Gemini"

    def test_call_gemini_empty_candidates(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"candidates": []}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ValueError, match="empty candidates"):
                _call_gemini("test-key", "gemini-2.0-flash", "Hello")

    def test_call_gemini_url_format(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            _call_gemini("mykey123", "gemini-2.0-flash", "test")

            call_url = mock_post.call_args[0][0]
            assert "gemini-2.0-flash" in call_url
            assert "key=mykey123" in call_url
            assert "generateContent" in call_url


# ═══════════════════════════════════════════════════════════════════════════
#  JSON Extraction Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestJsonExtraction:
    def test_extract_pure_json(self):
        result = AIProviderManager._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_with_code_fence(self):
        text = '```json\n{"key": "value"}\n```'
        result = AIProviderManager._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_embedded_in_text(self):
        text = 'Here is the result: {"key": "value"} and some more text.'
        result = AIProviderManager._extract_json(text)
        assert result == {"key": "value"}

    def test_extract_json_returns_none_for_invalid(self):
        result = AIProviderManager._extract_json("This is not JSON")
        assert result is None

    def test_extract_json_returns_none_for_empty(self):
        assert AIProviderManager._extract_json("") is None
        assert AIProviderManager._extract_json(None) is None
