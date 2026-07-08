"""FastAPI app. Routes are added per phase: /ask (Module B), /hevy/* (Module C),
/chat (Module A). Bound to localhost/tailnet only — see docker-compose.yml."""

from fastapi import FastAPI

app = FastAPI(title="Workout App", docs_url="/docs")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
