import pytest
from fastapi.testclient import TestClient

from app.llm import LLMError, LLMNotConfiguredError, LLMOverloadedError
from app.main import app, ask_rate_limiter, get_llm_client
from app.prompts import SYSTEM_PROMPT

BATTLE_ID = "battle-of-hastings"


class FakeLLM:
    """Records what the endpoint sends and returns a canned answer."""

    def __init__(self, answer: str = "Norman victory.", error: Exception | None = None):
        self.answer = answer
        self.error = error
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def fake_llm():
    llm = FakeLLM()
    app.dependency_overrides[get_llm_client] = lambda: llm
    ask_rate_limiter.reset()
    yield llm
    app.dependency_overrides.clear()
    ask_rate_limiter.reset()


@pytest.fixture
def client():
    return TestClient(app)


def ask(client: TestClient, question: str, battle_id: str = BATTLE_ID):
    return client.post(f"/api/battles/{battle_id}/ask", json={"question": question})


def test_returns_answer_from_llm(client, fake_llm):
    response = ask(client, "Who won?")

    assert response.status_code == 200
    assert response.json() == {"battleId": BATTLE_ID, "answer": "Norman victory."}


def test_prompt_is_grounded_in_battle_data(client, fake_llm):
    ask(client, "Who commanded the Normans?")

    system_prompt, user_prompt = fake_llm.calls[0]
    assert system_prompt == SYSTEM_PROMPT
    assert "<battle>" in user_prompt
    assert "Вильгельм Завоеватель" in user_prompt  # commander from battles.json
    assert "Who commanded the Normans?" in user_prompt


def test_question_is_trimmed(client, fake_llm):
    ask(client, "   Who won?   ")

    _, user_prompt = fake_llm.calls[0]
    assert "<question>\nWho won?\n</question>" in user_prompt


def test_unknown_battle_returns_404(client, fake_llm):
    response = ask(client, "Who won?", battle_id="battle-of-nowhere")

    assert response.status_code == 404
    assert fake_llm.calls == []


@pytest.mark.parametrize("question", ["", "  ", "ab", "   ab   ", "x" * 501])
def test_invalid_question_returns_422(client, fake_llm, question):
    response = ask(client, question)

    assert response.status_code == 422
    assert fake_llm.calls == []


def test_question_at_max_length_is_accepted(client, fake_llm):
    assert ask(client, "x" * 500).status_code == 200


def test_llm_failure_returns_502_and_logs_reason(client, fake_llm, caplog):
    fake_llm.error = LLMError("quota exceeded")

    response = ask(client, "Who won?")

    assert response.status_code == 502
    assert "quota" not in response.text  # provider details are not leaked to clients
    assert "quota exceeded" in caplog.text  # but the developer sees them in the log


def test_overloaded_provider_returns_504_and_logs_reason(client, fake_llm, caplog):
    fake_llm.error = LLMOverloadedError("503 UNAVAILABLE")

    response = ask(client, "Who won?")

    assert response.status_code == 504
    assert "UNAVAILABLE" not in response.text
    assert "503 UNAVAILABLE" in caplog.text


def test_missing_api_key_returns_503(client, monkeypatch):
    from app import main

    def not_configured():
        raise LLMNotConfiguredError("GEMINI_API_KEY is not set")

    main._cached_llm_client.cache_clear()
    monkeypatch.setattr(main, "create_llm_client", not_configured)
    ask_rate_limiter.reset()

    response = ask(client, "Who won?")

    assert response.status_code == 503
    main._cached_llm_client.cache_clear()


def test_rate_limit_returns_429(client, fake_llm):
    limit = ask_rate_limiter.max_requests
    for _ in range(limit):
        assert ask(client, "Who won?").status_code == 200

    response = ask(client, "Who won?")

    assert response.status_code == 429
    assert len(fake_llm.calls) == limit


def exhaust_rate_limit(client, headers):
    for _ in range(ask_rate_limiter.max_requests):
        client.post(
            f"/api/battles/{BATTLE_ID}/ask", json={"question": "Who won?"}, headers=headers
        )


def test_rate_limit_uses_real_ip_header_on_vercel(client, fake_llm, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    exhaust_rate_limit(client, {"x-real-ip": "1.1.1.1"})

    other_user = client.post(
        f"/api/battles/{BATTLE_ID}/ask",
        json={"question": "Who won?"},
        headers={"x-real-ip": "2.2.2.2"},
    )

    assert other_user.status_code == 200


def test_real_ip_header_is_ignored_outside_vercel(client, fake_llm, monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    exhaust_rate_limit(client, {"x-real-ip": "1.1.1.1"})

    # Without Vercel the header is client-controlled, so changing it must not help.
    spoofed = client.post(
        f"/api/battles/{BATTLE_ID}/ask",
        json={"question": "Who won?"},
        headers={"x-real-ip": "2.2.2.2"},
    )

    assert spoofed.status_code == 429


def test_battles_endpoint_still_works(client):
    response = client.get("/api/battles")

    assert response.status_code == 200
    assert any(battle["id"] == BATTLE_ID for battle in response.json())
