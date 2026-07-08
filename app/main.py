"""FastAPI app. Routes are added per phase: /ask (Module B), /hevy/* (Module C),
/chat (Module A). Bound to localhost/tailnet only — see docker-compose.yml."""

from functools import lru_cache

from fastapi import FastAPI
from pydantic import BaseModel

from app.contract import Exercise
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
