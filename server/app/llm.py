"""Thin wrapper around LLM providers.

The rest of the app only talks to the `LLMClient` protocol, so the provider
can be swapped with an env variable and tests can inject a fake client
without touching the network.
"""

import logging
import os
import time
from typing import Protocol

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """The provider failed to produce an answer (network, quota, bad response)."""


class LLMOverloadedError(LLMError):
    """The provider is busy or out of quota for now; asking later may work."""


class LLMNotConfiguredError(Exception):
    """No API key is set for the selected provider."""


class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


MAX_OUTPUT_TOKENS = 400
THINKING_HEADROOM_TOKENS = 2048

# A user is waiting in the UI, so fail fast instead of hanging.
# Without these, the Gemini SDK retries 429/5xx up to 5 times with growing
# pauses and has no timeout, which can turn one failure into minutes of waiting.
REQUEST_TIMEOUT_SECONDS = 25
MAX_ATTEMPTS = 2  # the original request + one retry

# Total time for walking the Gemini fallback chain. The frontend gives up after
# 60 s. A busy model can take 20+ s to answer 503, so the next model gets
# whatever time is left (capped by the request timeout) instead of being
# skipped because a full request no longer fits.
FALLBACK_BUDGET_SECONDS = 45

# The Gemini API rejects a request deadline under 10 s with 400 INVALID_ARGUMENT,
# so a fallback model is only started when at least this much time is left.
MIN_FALLBACK_SECONDS = 10

# Provider statuses that mean "busy right now" rather than "request is broken".
# 429 is the free-tier quota, 529 is Anthropic's "overloaded".
OVERLOADED_STATUS_CODES = {429, 503, 504, 529}


class GeminiClient:
    """Google Gemini. Has a free tier, so it is the default provider.

    `model` may be a comma-separated list. The newest free models are often
    overloaded (503), so when one is busy we move on to the next.
    """

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai
        from google.genai import types

        self._models = [name.strip() for name in model.split(",") if name.strip()]
        if not self._models:
            raise LLMNotConfiguredError("GEMINI_MODEL is empty")

        # With fallbacks, moving to the next model beats retrying a busy one.
        attempts = MAX_ATTEMPTS if len(self._models) == 1 else 1
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_SECONDS * 1000,  # milliseconds
                retry_options=types.HttpRetryOptions(attempts=attempts),
            ),
        )

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        deadline = time.monotonic() + FALLBACK_BUDGET_SECONDS

        for index, model in enumerate(self._models):
            time_left = deadline - time.monotonic()
            # The floor guards against the clock ticking past the check below.
            timeout = max(MIN_FALLBACK_SECONDS, min(REQUEST_TIMEOUT_SECONDS, time_left))
            try:
                return self._generate_with(model, system_prompt, user_prompt, timeout)
            except LLMOverloadedError as exc:
                next_models = self._models[index + 1 :]
                time_left = deadline - time.monotonic()
                if not next_models or time_left < MIN_FALLBACK_SECONDS:
                    raise
                logger.warning(
                    "Gemini model %s is busy, falling back to %s: %s",
                    model,
                    next_models[0],
                    exc,
                )

        raise AssertionError("unreachable: the loop returns or raises")

    def _generate_with(
        self, model: str, system_prompt: str, user_prompt: str, timeout: float
    ) -> str:
        import httpx2  # the SDK's HTTP library; plain httpx exceptions never reach us
        from google.genai import errors, types

        # Gemini 2.5+ models "think" before answering, and thinking tokens count
        # toward max_output_tokens, so a small limit can be used up by thinking
        # and leave an empty answer. A short Q&A needs little thinking: turn it
        # off or down where the model allows it, and always leave room for it.
        if "2.5-flash" in model:
            thinking_config = types.ThinkingConfig(thinking_budget=0)
            max_tokens = MAX_OUTPUT_TOKENS
        elif model.startswith("gemini-3"):
            thinking_config = types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
            max_tokens = MAX_OUTPUT_TOKENS + THINKING_HEADROOM_TOKENS
        else:
            thinking_config = None
            max_tokens = MAX_OUTPUT_TOKENS + THINKING_HEADROOM_TOKENS

        try:
            response = self._client.models.generate_content(
                model=model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=max_tokens,
                    temperature=0.3,
                    thinking_config=thinking_config,
                    # Overrides the client-wide timeout for this request only.
                    http_options=types.HttpOptions(timeout=int(timeout * 1000)),
                ),
            )
        except (errors.APIError, httpx2.HTTPError) as exc:
            overloaded = (
                isinstance(exc, httpx2.TimeoutException)
                or getattr(exc, "code", None) in OVERLOADED_STATUS_CODES
            )
            error_cls = LLMOverloadedError if overloaded else LLMError
            raise error_cls(f"Gemini API error ({model}): {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            finish_reason = (
                response.candidates[0].finish_reason if response.candidates else None
            )
            raise LLMError(
                f"Gemini ({model}) returned an empty answer (finish_reason={finish_reason})"
            )
        return text


class AnthropicClient:
    """Anthropic Claude. Needs a paid API key."""

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        import anthropic

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as exc:
            overloaded = (
                isinstance(exc, anthropic.APITimeoutError)
                or getattr(exc, "status_code", None) in OVERLOADED_STATUS_CODES
            )
            error_cls = LLMOverloadedError if overloaded else LLMError
            raise error_cls(f"Anthropic API error: {exc}") from exc

        text = "".join(
            block.text for block in message.content if block.type == "text"
        ).strip()
        if not text:
            raise LLMError("Anthropic returned an empty answer")
        return text


_PROVIDERS = {
    "gemini": (
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        # 3.8-flash is left out: only 20 free requests a day and often overloaded.
        "gemini-3.5-flash,gemini-3.5-flash-lite,gemini-3.1-flash-lite",
        GeminiClient,
    ),
    "anthropic": (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "claude-haiku-5-5",
        AnthropicClient,
    ),
}


def create_llm_client() -> LLMClient:
    """Build a client from env: LLM_PROVIDER, <PROVIDER>_API_KEY, <PROVIDER>_MODEL."""
    provider = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
    if provider not in _PROVIDERS:
        raise LLMNotConfiguredError(
            f"Unknown LLM_PROVIDER '{provider}'. Use one of: {', '.join(_PROVIDERS)}"
        )

    key_var, model_var, default_model, client_cls = _PROVIDERS[provider]
    api_key = os.getenv(key_var)
    if not api_key:
        raise LLMNotConfiguredError(f"{key_var} is not set")

    return client_cls(api_key=api_key, model=os.getenv(model_var, default_model))
