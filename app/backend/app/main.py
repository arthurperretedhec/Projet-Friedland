"""FastAPI backend of the walking skeleton.

Every backend route lives under /api so the frontend can call it on the same origin: in development
Next.js forwards /api/* to this server (see frontend/next.config.ts).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.score import build_scoring_base
from app.api.score import router as score_router
from app.data.investors import load_investors

APP_NAME = "Friedland Buyer Screening"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.investor_data = load_investors()
    # Moteur de score : les 153 fiches sont traduites une seule fois, ici, pas à chaque appel.
    app.state.scoring_base = build_scoring_base(app.state.investor_data)
    yield


app = FastAPI(title=APP_NAME, lifespan=lifespan)
register_error_handlers(app)
app.include_router(score_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Tells the frontend (and the launch scripts) that the backend is up."""
    return {"status": "ok", "app": APP_NAME}
