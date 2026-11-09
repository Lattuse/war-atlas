"""Thin wrapper around LLM providers.

The rest of the app only talks to the `LLMClient` protocol, so the provider
can be swapped with an env variable and tests can inject a fake client
without touching the network.
"""

import os
from typing import Protocol


class LLMError(Exception):
    """The provider failed to produce an answer (network, quota, bad response)."""


class LLMNotConfiguredError(Exception):
    """No API key is set for the selected provider."""


class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


MAX_OUTPUT_TOKENS = 400


class GeminiClient:
    """Google Gemini. Has a free tier, so it is the default provider."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        import httpx
        from google.genai import errors, types

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                    temperature=0.3,
                ),
            )
        except (errors.APIError, httpx.HTTPError) as exc:
            raise LLMError(f"Gemini API error: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise LLMError("Gemini returned an empty answer")
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
            raise LLMError(f"Anthropic API error: {exc}") from exc

        text = "".join(
            block.text for block in message.content if block.type == "text"
        ).strip()
        if not text:
            raise LLMError("Anthropic returned an empty answer")
        return text


_PROVIDERS = {
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "gemini-2.5-flash", GeminiClient),
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
