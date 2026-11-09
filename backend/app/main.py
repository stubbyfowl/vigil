"""FastAPI app. Serves the API and, when built, the frontend."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config

app = FastAPI(title="Vigil", version="1.0.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data": "simulated"}


if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="ui")
