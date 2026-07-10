"""FastAPI application factory (Perito MVP).

Health check + CORS + el dashboard C11 (server-rendered, Jinja/HTMX, ADR-001).
El front lo sirve el propio backend (mismo origen); no hay SPA separada.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.dashboard.c11 import router as dashboard_router
from app.api.ingest import router as ingest_router
from app.api.hitl_actions import router as hitl_actions_router
from app.api.cartas import router as cartas_router
from app.demo.seed import seed_demo_casos
from app.intake.poller import iniciar_poller

_STATIC_DIR = Path(__file__).parent / "dashboard" / "static"


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI."""
    app = FastAPI(
        title="Perito",
        description="Copiloto agéntico de admisión de siniestros (FNOL)",
        version="0.1.0",
    )

    # CORS: el front es mismo-origen (HTMX server-rendered), pero se deja abierto en dev.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restringir en producción
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")
    app.include_router(dashboard_router)
    app.include_router(ingest_router)
    app.include_router(hitl_actions_router)
    app.include_router(cartas_router)

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        """Health check endpoint (liveness probe)."""
        return {"status": "ok", "service": "perito"}

    # Arranque (Unit H): en demo EN VIVO la bandeja se llena de correos (poller gated); si no, se
    # siembra la demo estática. `iniciar_poller` es self-gated (no-op si DEMO_LIVE=off o sin creds).
    if settings.demo_live == "off":
        seed_demo_casos()
    else:
        iniciar_poller()

    return app


# Instancia global (usada por uvicorn)
app = create_app()
