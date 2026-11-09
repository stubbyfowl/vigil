"""FastAPI app. Serves the API and, when built, the frontend."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .routes import admin, astronaut, mission, sync_views

app = FastAPI(title="Vigil", version="1.0.0")
for module in (astronaut, mission, sync_views, admin):
    app.include_router(module.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "data": "simulated"}


if config.FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="ui")
