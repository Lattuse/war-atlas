import pytest

from app.llm import AnthropicClient, GeminiClient, LLMNotConfiguredError, create_llm_client
from app.rate_limit import RateLimiter

PROVIDER_VARS = [
    "LLM_PROVIDER",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in PROVIDER_VARS:
        monkeypatch.delenv(var, raising=False)


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.allow("ip", now=0)
    assert limiter.allow("ip", now=1)
    assert not limiter.allow("ip", now=2)


def test_rate_limiter_window_expires():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("ip", now=0)
    assert not limiter.allow("ip", now=59)
    assert limiter.allow("ip", now=60)


def test_rate_limiter_is_per_client():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    assert limiter.allow("a", now=0)
    assert limiter.allow("b", now=0)


def test_default_provider_is_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    assert isinstance(create_llm_client(), GeminiClient)


def test_anthropic_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    assert isinstance(create_llm_client(), AnthropicClient)


def test_missing_key_raises(monkeypatch):
    with pytest.raises(LLMNotConfiguredError, match="GEMINI_API_KEY"):
        create_llm_client()


def test_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "skynet")

    with pytest.raises(LLMNotConfiguredError, match="Unknown LLM_PROVIDER"):
        create_llm_client()
