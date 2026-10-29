import json
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="War Atlas API")

DATA_FILE = Path(__file__).parent / "data" / "battles.json"


class Coordinates(BaseModel):
    lat: float
    lng: float


class BattleSide(BaseModel):
    name: str
    commanders: list[str]


class Battle(BaseModel):
    id: str
    name: str
    war: str
    startYear: int
    endYear: int
    coordinates: Coordinates
    sides: list[BattleSide]
    outcome: str
    description: str


def load_battles() -> list[Battle]:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return [Battle.model_validate(item) for item in raw]


@app.get("/api/battles", response_model=list[Battle])
def get_battles() -> list[Battle]:
    return load_battles()