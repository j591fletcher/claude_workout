"""FastAPI app. Routes are added per phase: /ask (Module B), /hevy/* (Module C),
/chat (Module A). Bound to localhost/tailnet only — see docker-compose.yml."""

from functools import lru_cache

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.contract import Exercise
from app.hevy import service as hevy
from app.hevy.client import HevyError
from app.retriever.query import Retriever

app = FastAPI(title="Workout App", docs_url="/docs")


@lru_cache
def _retriever() -> Retriever:
    return Retriever()  # lazy singleton: loads embedder + Chroma on first use


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class AskRequest(BaseModel):
    question: str
    program: str | None = None
    week: int | None = None
    day: str | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[dict]
    exercises: list[Exercise]


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    clauses = [{k: {"$eq": v}} for k, v in
               (("program", req.program), ("week", req.week), ("day", req.day))
               if v is not None]
    where = clauses[0] if len(clauses) == 1 else ({"$and": clauses} if clauses else None)
    result = _retriever().ask(req.question, where)
    return AskResponse(answer=result.answer, sources=result.sources,
                       exercises=result.exercises)


@app.exception_handler(HevyError)
def _hevy_error(_, exc: HevyError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/hevy/working-weights", response_model=list[Exercise])
def hevy_working_weights() -> list[Exercise]:
    """Current working weight per exercise (max logged weight — NOT a 1RM)."""
    return hevy.working_weights()


@app.get("/hevy/summary/routines")
def hevy_routine_summaries() -> dict[str, list[str]]:
    """The five tracked routines as verifiable text summaries."""
    return {"routines": hevy.routine_summaries()}


@app.get("/hevy/summary/workouts")
def hevy_workout_summaries(limit: int = Query(default=5, ge=1, le=50)) -> dict[str, list[str]]:
    """Most recent logged sessions in the trainer's LIFT LOG format."""
    return {"workouts": hevy.recent_workout_summaries(limit)}
