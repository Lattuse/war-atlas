# War Atlas

An interactive map of historical battles. Pick a time period on the timeline, click a battle on the map, read the key facts, and ask an AI assistant follow-up questions about that battle.

Built as a learning and portfolio project: React + TypeScript on the frontend, FastAPI on the backend, with an LLM integration that stays grounded in the project's own data.

## Features

- Map of battles from antiquity to WWII (Leaflet + OpenStreetMap)
- Timeline range slider that filters battles by period
- Battle cards with war, dates, sides and outcome
- "Ask AI about this battle": free-form questions or one-click suggested questions, answered by an LLM

## How the AI feature works

```
React popup ──POST /api/battles/{id}/ask──▶ FastAPI ──▶ LLM (Gemini or Claude)
                  { "question": "..." }        │
                                               └─ battle record from battles.json
                                                  is put into the prompt
```

Design decisions:

- **Grounded answers.** The backend looks up the battle in `battles.json` and sends that record to the model inside a `<battle>` block. The system prompt tells the model to treat it as the primary source, not to invent numbers or names, and to say so when it is unsure. The user's question goes in a separate `<question>` block, and the prompt tells the model to ignore instructions hidden inside it (basic prompt-injection hygiene).
- **Scoped assistant.** Off-topic questions get a polite refusal instead of a general chatbot answer.
- **API key stays on the server.** The browser never talks to the LLM provider directly.
- **Swappable provider.** The app depends on a small `LLMClient` protocol (`server/app/llm.py`). Gemini is the default because it has a free tier; set `LLM_PROVIDER=anthropic` to use Claude instead. The same protocol lets tests inject a fake model.
- **Cost and abuse control.** Questions are limited to 3–500 characters, answers to ~400 tokens, and each client IP to 10 questions per minute (configurable).
- **Clear errors.** Provider failures return `502` without leaking provider details, a missing API key returns `503`, and the UI turns each status into a readable message.

## Tech stack

| Part | Stack |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, react-leaflet, Radix UI |
| Backend | Python, FastAPI, Pydantic |
| AI | Google Gemini API (`google-genai`) or Anthropic API (`anthropic`) |
| Tests | pytest + FastAPI TestClient, Vitest |

## Running locally

Requirements: Node.js 20.19+ (or 22+), Python 3.11+.

**1. Backend**

```bash
cd server
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env             # then put your API key into .env
fastapi dev app/main.py          # http://localhost:8000, docs at /docs
```

A free Gemini API key can be created at [Google AI Studio](https://aistudio.google.com/apikey).

**2. Frontend**

```bash
cd client
npm install
npm run dev                      # http://localhost:5173
```

In development Vite proxies `/api` to `localhost:8000`. In production, set `VITE_API_URL` to the backend URL and add the frontend URL to `ALLOWED_ORIGINS` on the backend.

## Tests

```bash
cd server && pytest              # API, validation, error handling, rate limiting
cd client && npm test            # API client and utils
```

The backend tests never call a real LLM: a fake client is injected through FastAPI dependency overrides, which also lets the tests check exactly what prompt is sent to the model. See [docs/TEST_PLAN.md](docs/TEST_PLAN.md) for the full test plan, including the manual checks of answer quality.

## Project structure

```
client/
  src/api/askBattle.ts           HTTP client for the ask endpoint
  src/components/AskBattle.tsx   question form + answer inside the battle popup
  src/components/                map, markers, battle card, timeline slider
server/
  app/main.py                    FastAPI routes
  app/llm.py                     LLM provider clients (Gemini, Anthropic)
  app/prompts.py                 system prompt and prompt building
  app/rate_limit.py              in-memory rate limiter
  app/data/battles.json          battle dataset
  tests/                         pytest suite
docs/TEST_PLAN.md
```

## Roadmap

- Frontend loads battles from the API instead of a bundled JSON copy
- More battles and army movement visualisation
- Streaming AI answers
- Filters by war and nation, search, battle detail pages
