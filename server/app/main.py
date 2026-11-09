import json
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .llm import LLMClient, LLMError, LLMNotConfiguredError, create_llm_client
from .models import AskRequest, AskResponse, Battle
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .rate_limit import RateLimiter

load_dotenv()

app = FastAPI(title="War Atlas API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

DATA_FILE = Path(__file__).parent / "data" / "battles.json"

ask_rate_limiter = RateLimiter(
    max_requests=int(os.getenv("ASK_RATE_LIMIT", "10")),
    window_seconds=60,
)


def load_battles() -> list[Battle]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [Battle.model_validate(item) for item in raw]


def find_battle(battle_id: str) -> Battle:
    for battle in load_battles():
        if battle.id == battle_id:
            return battle
    raise HTTPException(status_code=404, detail="Battle not found")


@lru_cache
def _cached_llm_client() -> LLMClient:
    return create_llm_client()


def get_llm_client() -> LLMClient:
    try:
        return _cached_llm_client()
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail="AI assistant is not configured") from exc


def check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if not ask_rate_limiter.allow(client_ip):
        raise HTTPException(
            status_code=429, detail="Too many questions, please wait a minute"
        )


@app.get("/api/battles", response_model=list[Battle])
def get_battles() -> list[Battle]:
    return load_battles()


@app.post(
    "/api/battles/{battle_id}/ask",
    response_model=AskResponse,
    dependencies=[Depends(check_rate_limit)],
)
def ask_about_battle(
    battle_id: str,
    body: AskRequest,
    llm: LLMClient = Depends(get_llm_client),
) -> AskResponse:
    battle = find_battle(battle_id)
    try:
        answer = llm.generate(SYSTEM_PROMPT, build_user_prompt(battle, body.question))
    except LLMError as exc:
        raise HTTPException(
            status_code=502, detail="AI assistant failed to answer, try again later"
        ) from exc
    return AskResponse(battleId=battle.id, answer=answer)
