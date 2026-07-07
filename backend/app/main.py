"""FastAPI application factory (Perito MVP).

Scaffold mínimo: health check, CORS, documentación automática.
La lógica de orquestación se añade en U4 (LangGraph).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI."""
    app = FastAPI(
        title="Perito",
        description="Copiloto agéntico de admisión de siniestros (FNOL)",
        version="0.1.0",
    )

    # CORS: permite requests desde el frontend (Next.js en localhost:3000 en dev)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restringir en producción
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        """Health check endpoint (liveness probe)."""
        return {"status": "ok", "service": "perito"}

    return app


# Instancia global (usada por uvicorn)
app = create_app()
