"""Router de ingesta de avisos (Unit de Evolución: Front Demo).

Va APARTE de `dashboard/` a propósito: este router SÍ corre el pipeline (`orquestar_fnol`),
mientras que `dashboard/` es passive (no importa `orchestrator/`). El test estructural verifica
la simetría: ingest NO importa `dashboard`, dashboard NO importa `orchestrator`.

- `GET  /nuevo` → formulario (textarea + 4 presets).
- `POST /nuevo` → texto libre → pipeline REAL (Haiku+Sonnet+motor+fraude) → detalle.
- `POST /nuevo/preset/{escenario}` → caso demo determinístico (sin LLM) → detalle.

Invariantes: el pipeline nunca alcanza terminal (P1); el dictamen sale del motor (P2); caps de
terminación (P4). **NFR:** valida tamaño del aviso (≤5000, no-vacío); resiliente a inyección de
prompt porque la cobertura es determinística (P2) y el estado nunca es terminal (P1).
"""

from pathlib import Path

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.contracts.dictamen import Cotas
from app.contracts.enums import CalidadDoc, EstadoCaso, RolUsuario
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.orchestrator.c7 import orquestar_fnol
from app.hitl import c8
from app.observability.tracer import Tracer
from app.observability.replay import get_replay_store
from app.dashboard.store import get_caso_repository
from app.demo.scenarios import construir_caso_preset, PRESETS
from app.demo.seed import sembrar_traza_demo

router = APIRouter(tags=["ingest"])
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent / "dashboard" / "templates"))

MAX_AVISO_CHARS = 5000


@router.get("/nuevo", response_class=HTMLResponse)
def formulario_nuevo(request: Request, rol: str = RolUsuario.ANALISTA.value):
    return _TEMPLATES.TemplateResponse(request, "nuevo.html", {
        "rol": rol, "presets": PRESETS, "error": None, "max_chars": MAX_AVISO_CHARS,
    })


@router.post("/nuevo", response_class=HTMLResponse)
def crear_desde_texto(request: Request, aviso_texto: str = Form(...), rol: str = Form(RolUsuario.ANALISTA.value)):
    """Texto libre → pipeline REAL. NFR: valida tamaño; una inyección NO cambia el dictamen (motor, P2)."""
    texto = (aviso_texto or "").strip()
    if not texto or len(texto) > MAX_AVISO_CHARS:
        return _TEMPLATES.TemplateResponse(request, "nuevo.html", {
            "rol": rol, "presets": PRESETS, "max_chars": MAX_AVISO_CHARS,
            "error": f"El aviso debe ser no vacío y de máximo {MAX_AVISO_CHARS} caracteres.",
        }, status_code=400)

    caso = intake_crear_caso(AvisoNormalizado(texto_crudo=texto, calidad=CalidadDoc.LIMPIO))
    tracer = Tracer(caso.id)
    try:
        resultado = orquestar_fnol(caso, c8, Cotas(max_rondas=1, presupuesto_tokens=50000), tracer)
    except Exception as e:  # fail-closed (P4): si el pipeline falla, escala — nunca 500 ni inventa
        resultado = caso.model_copy(update={
            "estado": EstadoCaso.REQUIERE_REVISION,
            "motivo_escalamiento": f"Orquestación falló: {e}",
        })
    get_caso_repository().save(resultado)
    get_replay_store().save(tracer, resultado.estado.value, resultado.motivo_escalamiento)
    return RedirectResponse(f"/casos/{resultado.id}?rol={rol}", status_code=303)


@router.post("/nuevo/preset/{escenario}", response_class=HTMLResponse)
def crear_desde_preset(escenario: str, rol: str = Form(RolUsuario.ANALISTA.value)):
    """Preset determinístico (sin LLM) → caso demo con su camino esperado."""
    try:
        caso = construir_caso_preset(escenario)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"escenario desconocido: {escenario}")
    get_caso_repository().save(caso)
    sembrar_traza_demo(caso)
    return RedirectResponse(f"/casos/{caso.id}?rol={rol}", status_code=303)
