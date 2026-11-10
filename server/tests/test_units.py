import httpx2
import pytest

from app.llm import (
    AnthropicClient,
    GeminiClient,
    LLMError,
    LLMNotConfiguredError,
    LLMOverloadedError,
    create_llm_client,
)
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


class FakeGeminiModels:
    def __init__(self, response):
        self.response = response
        self.config = None

    def generate_content(self, model, contents, config):
        self.config = config
        return self.response


def make_gemini(model, response):
    from types import SimpleNamespace

    client = GeminiClient(api_key="test-key", model=model)
    models = FakeGeminiModels(response)
    client._client = SimpleNamespace(models=models)
    return client, models


def test_gemini_flash_disables_thinking():
    from types import SimpleNamespace

    client, models = make_gemini("gemini-2.5-flash", SimpleNamespace(text="Answer"))

    assert client.generate("system", "question") == "Answer"
    assert models.config.thinking_config.thinking_budget == 0
    assert models.config.max_output_tokens == 400


def test_gemini_3_uses_low_thinking_with_headroom():
    from types import SimpleNamespace

    client, models = make_gemini("gemini-3.8-flash", SimpleNamespace(text="Answer"))

    client.generate("system", "question")

    assert models.config.thinking_config.thinking_level == "LOW"
    assert models.config.max_output_tokens > 400


def test_gemini_other_models_get_room_for_thinking():
    from types import SimpleNamespace

    client, models = make_gemini("some-future-model", SimpleNamespace(text="Answer"))

    client.generate("system", "question")

    assert models.config.thinking_config is None
    assert models.config.max_output_tokens > 400


def test_gemini_client_fails_fast():
    client = GeminiClient(api_key="test-key", model="gemini-3.8-flash")
    http_options = client._client._api_client._http_options

    assert http_options.timeout == 25_000
    assert http_options.retry_options.attempts == 2


def test_gemini_empty_answer_reports_finish_reason():
    from types import SimpleNamespace

    from app.llm import LLMError

    response = SimpleNamespace(
        text=None, candidates=[SimpleNamespace(finish_reason="MAX_TOKENS")]
    )
    client, _ = make_gemini("gemini-2.5-flash", response)

    with pytest.raises(LLMError, match="MAX_TOKENS"):
        client.generate("system", "question")


def raises(error):
    def _raise(**kwargs):
        raise error

    return _raise


def failing_gemini(error):
    from types import SimpleNamespace

    client = GeminiClient(api_key="test-key", model="gemini-3.8-flash")
    client._client = SimpleNamespace(
        models=SimpleNamespace(generate_content=raises(error))
    )
    return client


def failing_anthropic(error):
    from types import SimpleNamespace

    client = AnthropicClient(api_key="test-key", model="claude-haiku-5-5")
    client._client = SimpleNamespace(messages=SimpleNamespace(create=raises(error)))
    return client


def anthropic_status_error(status):
    import anthropic
    import httpx2

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx2.Response(status, request=request)
    return anthropic.APIStatusError("provider error", response=response, body=None)


@pytest.mark.parametrize("code", [429, 503, 504])
def test_gemini_busy_statuses_are_overloaded(code):
    from google.genai import errors

    client = failing_gemini(errors.APIError(code, {"error": {"message": "busy"}}))

    with pytest.raises(LLMOverloadedError):
        client.generate("system", "question")


def test_gemini_client_runs_on_httpx2():
    client = GeminiClient(api_key="test-key", model="gemini-3.8-flash")

    assert isinstance(client._client._api_client._httpx_client, httpx2.Client)


def test_gemini_timeout_is_overloaded():
    with pytest.raises(LLMOverloadedError):
        failing_gemini(httpx2.ReadTimeout("slow")).generate("system", "question")


def test_gemini_connection_error_is_a_plain_failure():
    with pytest.raises(LLMError) as caught:
        failing_gemini(httpx2.ConnectError("down")).generate("system", "question")

    assert not isinstance(caught.value, LLMOverloadedError)


def test_gemini_bad_request_is_not_overloaded():
    from google.genai import errors

    client = failing_gemini(errors.APIError(400, {"error": {"message": "bad"}}))

    with pytest.raises(LLMError) as caught:
        client.generate("system", "question")

    assert not isinstance(caught.value, LLMOverloadedError)


class ScriptedGeminiModels:
    """Answers per model: an exception is raised, anything else is the reply text."""

    def __init__(self, outcomes, clock=None, durations=None):
        self.outcomes = outcomes
        self.clock = clock
        self.durations = durations or {}
        self.called = []
        self.timeouts = []

    def generate_content(self, model, contents, config):
        from types import SimpleNamespace

        self.called.append(model)
        self.timeouts.append(config.http_options.timeout)
        if self.clock is not None:
            self.clock.now += self.durations.get(model, 0)
        outcome = self.outcomes[model]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


def scripted_gemini(model_list, outcomes, clock=None, durations=None):
    from types import SimpleNamespace

    client = GeminiClient(api_key="test-key", model=model_list)
    models = ScriptedGeminiModels(outcomes, clock, durations)
    client._client = SimpleNamespace(models=models)
    return client, models


def gemini_busy():
    from google.genai import errors

    return errors.APIError(503, {"error": {"message": "high demand"}})


def test_gemini_falls_back_when_model_is_busy():
    client, models = scripted_gemini(
        "gemini-3.8-flash, gemini-3.5-flash",
        {"gemini-3.8-flash": gemini_busy(), "gemini-3.5-flash": "Answer"},
    )

    assert client.generate("system", "question") == "Answer"
    assert models.called == ["gemini-3.8-flash", "gemini-3.5-flash"]


def test_gemini_falls_back_on_timeout():
    client, models = scripted_gemini(
        "a,b", {"a": httpx2.ReadTimeout("slow"), "b": "Answer"}
    )

    assert client.generate("system", "question") == "Answer"


def test_gemini_does_not_fall_back_on_bad_request():
    from google.genai import errors

    client, models = scripted_gemini(
        "a,b", {"a": errors.APIError(400, {"error": {"message": "bad"}}), "b": "Answer"}
    )

    with pytest.raises(LLMError) as caught:
        client.generate("system", "question")

    assert not isinstance(caught.value, LLMOverloadedError)
    assert models.called == ["a"]


def test_gemini_all_models_busy_is_overloaded():
    client, models = scripted_gemini("a,b,c", {m: gemini_busy() for m in "abc"})

    with pytest.raises(LLMOverloadedError, match=r"\(c\)"):
        client.generate("system", "question")

    assert models.called == ["a", "b", "c"]


@pytest.fixture
def fake_clock(monkeypatch):
    from types import SimpleNamespace

    import app.llm as llm

    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(llm.time, "monotonic", lambda: clock.now)
    return clock


def test_gemini_first_request_gets_full_timeout(fake_clock):
    client, models = scripted_gemini("a,b", {"a": "Answer", "b": "Answer"}, fake_clock)

    client.generate("system", "question")

    assert models.timeouts == [25_000]


def test_gemini_falls_back_with_remaining_time_after_slow_busy_model(fake_clock):
    # Under high demand a model can take 20+ s before answering 503.
    client, models = scripted_gemini(
        "a,b", {"a": gemini_busy(), "b": "Answer"}, fake_clock, durations={"a": 30}
    )

    assert client.generate("system", "question") == "Answer"
    assert models.called == ["a", "b"]
    assert models.timeouts == [25_000, 15_000]  # 45 s budget - 30 s spent


def test_gemini_fallback_timeout_respects_api_minimum(monkeypatch):
    import app.llm as llm

    # Readings: budget start, first request, check after the failure (11 s left),
    # then the clock ticks to 9 s left before the second request starts.
    clock = iter([0, 0, 34, 36])
    monkeypatch.setattr(llm.time, "monotonic", lambda: next(clock))
    client, models = scripted_gemini("a,b", {"a": gemini_busy(), "b": "Answer"})

    assert client.generate("system", "question") == "Answer"
    assert models.timeouts == [25_000, 10_000]  # never under the API's 10 s minimum


def test_gemini_stops_falling_back_when_out_of_time(fake_clock):
    # Gemini rejects deadlines under 10 s, so 8 s left is not enough.
    client, models = scripted_gemini(
        "a,b", {"a": gemini_busy(), "b": "Answer"}, fake_clock, durations={"a": 37}
    )

    with pytest.raises(LLMOverloadedError):
        client.generate("system", "question")

    assert models.called == ["a"]


def test_gemini_fallback_list_skips_sdk_retries():
    client = GeminiClient(api_key="test-key", model="a,b")
    http_options = client._client._api_client._http_options

    assert http_options.retry_options.attempts == 1


def test_gemini_default_has_fallback_models(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    assert len(create_llm_client()._models) > 1


def test_gemini_empty_model_list_is_not_configured():
    with pytest.raises(LLMNotConfiguredError):
        GeminiClient(api_key="test-key", model=" , ")


@pytest.mark.parametrize("status", [429, 503, 529])
def test_anthropic_busy_statuses_are_overloaded(status):
    client = failing_anthropic(anthropic_status_error(status))

    with pytest.raises(LLMOverloadedError):
        client.generate("system", "question")


def test_anthropic_timeout_is_overloaded():
    import anthropic

    request = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")
    client = failing_anthropic(anthropic.APITimeoutError(request=request))

    with pytest.raises(LLMOverloadedError):
        client.generate("system", "question")


def test_anthropic_bad_request_is_not_overloaded():
    client = failing_anthropic(anthropic_status_error(400))

    with pytest.raises(LLMError) as caught:
        client.generate("system", "question")

    assert not isinstance(caught.value, LLMOverloadedError)
