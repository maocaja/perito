"""C11 Dashboard router — bandeja (H-19), detalle (H-20), acciones HITL, panel (H-21).

INVARIANTES:
- Passive: NO importa `rules/` ni `orchestrator/`; no contiene lógica de dominio.
- Delega TODA decisión en `hitl/` (C8); nunca asigna `caso.estado`.
- P1: acción sin `usuario` → 400 (firma humana obligatoria).
- P5: el detalle muestra el aviso REDACTADO (redact_pii_spans_es_co).
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.contracts.enums import EstadoCaso, RolUsuario
from app.security.redaction import redact_pii_spans_es_co
from app.hitl.c8 import aprobar as hitl_aprobar, rechazar as hitl_rechazar
from app.observability.replay import get_replay_store
from app.dashboard.store import get_caso_repository

router = APIRouter(tags=["dashboard"])
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _detalle_context(caso, rol: str) -> dict:
    """Contexto del detalle con el aviso REDACTADO (P5)."""
    return {
        "rol": rol,
        "caso": caso,
        "aviso_redactado": redact_pii_spans_es_co(caso.aviso.texto_crudo),
    }


def _get_o_404(caso_id: str):
    caso = get_caso_repository().get(caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return caso


@router.get("/", response_class=HTMLResponse)
@router.get("/casos", response_class=HTMLResponse)
def bandeja(request: Request, estado: Optional[str] = Query(None), rol: str = Query(RolUsuario.ANALISTA.value)):
    """H-19: bandeja de casos con filtro por estado + selector de rol stub."""
    filtro = None
    if estado:
        try:
            filtro = EstadoCaso(estado)
        except ValueError:
            filtro = None
    repo = get_caso_repository()
    todos = repo.list()
    casos = repo.list(estado=filtro)

    # Conteos para los KPIs y los chips (agregación de presentación, no lógica de dominio).
    def _n(e):
        return sum(1 for c in todos if c.estado == e)
    counts = {
        "total": len(todos),
        "LISTO_PARA_APROBAR": _n(EstadoCaso.LISTO_PARA_APROBAR),
        "REQUIERE_REVISION": _n(EstadoCaso.REQUIERE_REVISION),
        "APROBADO": _n(EstadoCaso.APROBADO),
        "RECHAZADO": _n(EstadoCaso.RECHAZADO),
        "fraude_alta": sum(1 for c in todos if c.alerta_fraude and c.alerta_fraude.severidad == "ALTA"),
    }
    counts["resueltos"] = counts["APROBADO"] + counts["RECHAZADO"]

    return _TEMPLATES.TemplateResponse(request, "bandeja.html", {
        "casos": casos,
        "counts": counts,
        "nav_total": counts["total"],
        "estado_actual": estado or "",
        "rol": rol,
    })


@router.get("/casos/{caso_id}", response_class=HTMLResponse)
def detalle(request: Request, caso_id: str, rol: str = Query(RolUsuario.ANALISTA.value)):
    """H-20: detalle con evidencia enlazada (campo→origen, dictamen→cláusula) y aviso redactado (P5)."""
    caso = _get_o_404(caso_id)
    return _TEMPLATES.TemplateResponse(request, "detalle.html", _detalle_context(caso, rol))


@router.post("/casos/{caso_id}/aprobar", response_class=HTMLResponse)
def aprobar(request: Request, caso_id: str, usuario: Optional[str] = Form(None)):
    """H-12: delega en hitl.aprobar. P1: usuario obligatorio (firma humana) → 400 si falta."""
    if not usuario or not usuario.strip():
        raise HTTPException(status_code=400, detail="usuario requerido (firma válida, P1)")
    caso = _get_o_404(caso_id)
    try:
        actualizado = hitl_aprobar(caso, usuario)  # única vía de mutación de estado (C8)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    get_caso_repository().save(actualizado)
    return _TEMPLATES.TemplateResponse(request, "detalle.html", _detalle_context(actualizado, RolUsuario.ANALISTA.value))


@router.post("/casos/{caso_id}/rechazar", response_class=HTMLResponse)
def rechazar(request: Request, caso_id: str, usuario: Optional[str] = Form(None), motivo: Optional[str] = Form(None)):
    """H-12: delega en hitl.rechazar. P1: usuario + motivo obligatorios."""
    if not usuario or not usuario.strip():
        raise HTTPException(status_code=400, detail="usuario requerido (firma válida, P1)")
    if not motivo or not motivo.strip():
        raise HTTPException(status_code=400, detail="motivo requerido para rechazar")
    caso = _get_o_404(caso_id)
    try:
        actualizado = hitl_rechazar(caso, usuario, motivo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    get_caso_repository().save(actualizado)
    return _TEMPLATES.TemplateResponse(request, "detalle.html", _detalle_context(actualizado, RolUsuario.ANALISTA.value))


@router.get("/panel", response_class=HTMLResponse)
def panel(request: Request, rol: str = Query(RolUsuario.CUMPLIMIENTO.value)):
    """H-21 básico: trazas por nodo + tokens/costo desde C9 (ReplayStore)."""
    store = get_replay_store()
    replays = [store.load(cid) for cid in store.get_all_cases()]
    replays = [r for r in replays if r is not None]
    return _TEMPLATES.TemplateResponse(request, "panel.html", {"replays": replays, "rol": rol})


@router.get("/panel/export/{caso_id}")
def export_pia(caso_id: str):
    """H-15/H-21: export de evidencia (traza+tokens) del caso como JSON."""
    rec = get_replay_store().load(caso_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Sin traza para el caso")
    return JSONResponse(content=rec)
