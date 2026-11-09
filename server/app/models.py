from pydantic import BaseModel, Field, field_validator


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


QUESTION_MIN_LENGTH = 3
QUESTION_MAX_LENGTH = 500


class AskRequest(BaseModel):
    question: str = Field(min_length=QUESTION_MIN_LENGTH, max_length=QUESTION_MAX_LENGTH)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        value = value.strip()
        if len(value) < QUESTION_MIN_LENGTH:
            raise ValueError(f"question must be at least {QUESTION_MIN_LENGTH} characters")
        return value


class AskResponse(BaseModel):
    battleId: str
    answer: str
