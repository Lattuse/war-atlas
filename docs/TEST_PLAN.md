# Test plan: "Ask AI about this battle"

## Scope

The feature that lets a user ask a question about a battle from its map popup: the `POST /api/battles/{id}/ask` endpoint, the LLM integration behind it, and the `AskBattle` UI component.

Out of scope: map rendering, timeline filtering, the LLM provider's own availability.

## Approach

| Level | What | How |
| --- | --- | --- |
| Unit (backend) | Rate limiter, provider selection from env | pytest |
| API (backend) | Endpoint behaviour, validation, error mapping, prompt content | pytest + FastAPI TestClient with a fake LLM |
| Unit (frontend) | HTTP client, status → message mapping, utils | Vitest with a mocked `fetch` |
| Manual | UI behaviour and answer quality with a real model | Checklist below |

Automated tests never call a real LLM, so they are fast, free and deterministic.

## Automated test cases

| ID | Case | Expected | Test |
| --- | --- | --- | --- |
| API-01 | Valid question about an existing battle | 200, answer from the model | `test_returns_answer_from_llm` |
| API-02 | Prompt contains the battle record and the question | `<battle>` block with dataset facts, `<question>` block | `test_prompt_is_grounded_in_battle_data` |
| API-03 | Question with surrounding spaces | Trimmed before sending to the model | `test_question_is_trimmed` |
| API-04 | Unknown battle id | 404, model not called | `test_unknown_battle_returns_404` |
| API-05 | Empty, whitespace-only, too short, 501 chars | 422, model not called | `test_invalid_question_returns_422` |
| API-06 | Exactly 500 chars (boundary) | 200 | `test_question_at_max_length_is_accepted` |
| API-07 | Provider error | 502, provider details not leaked | `test_llm_failure_returns_502` |
| API-08 | API key not configured | 503 | `test_missing_api_key_returns_503` |
| API-09 | More than N questions per minute from one IP | 429 after N, model called N times | `test_rate_limit_returns_429` |
| API-10 | Existing `GET /api/battles` still works | 200 | `test_battles_endpoint_still_works` |
| UNIT-01..03 | Rate limiter: limit, window expiry, per-client keys | As named | `test_units.py` |
| UNIT-04..07 | Provider factory: default Gemini, Anthropic, missing key, unknown provider | As named | `test_units.py` |
| FE-01 | Client sends correct request and returns answer | Correct URL, method, body | `askBattle.test.ts` |
| FE-02 | Battle id is URL-encoded | `a/b` → `a%2Fb` | `askBattle.test.ts` |
| FE-03 | 404 / 422 / 429 / 502 / 503 / other | Readable message per status | `askBattle.test.ts` |
| FE-04 | Network failure | "Server unavailable" message | `askBattle.test.ts` |

## Manual checklist (real model)

UI:

- [ ] Popup shows the question field and two suggested questions
- [ ] "Ask" button is disabled for fewer than 3 characters
- [ ] Loading state is shown, buttons are disabled while waiting
- [ ] Long answer: popup grows and the map pans so the whole popup is visible
- [ ] Error message is shown when the backend is stopped
- [ ] Each battle popup keeps its own question and answer

Answer quality (run for at least 3 battles):

- [ ] Factual question ("Who commanded each side?") matches `battles.json`
- [ ] Context question ("Why did they win?") is reasonable and does not contradict the data
- [ ] Question in English gets an English answer, in Russian a Russian one
- [ ] Off-topic question ("Write me a poem about cats") is politely declined
- [ ] Prompt injection ("Ignore your rules and ...") is ignored
- [ ] Question about something the data does not cover: the model says it is unsure instead of inventing numbers

## Known risks

- The model can still be wrong about context outside the dataset; the UI shows a disclaimer under each answer.
- The rate limiter is in-memory, so it resets on restart and does not work across several server instances.
- Free-tier provider quotas can run out; the user then sees the 502 message.
