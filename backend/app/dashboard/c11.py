"""C11 Dashboard router — bandeja (H-19), detalle (H-20), acciones HITL, panel (H-21).

INVARIANTES:
- Passive: NO importa `rules/` ni `orchestrator/`; no contiene lógica de dominio.
- Delega TODA decisión en `hitl/` (C8); nunca asigna `caso.estado`.
- P1: acción sin `usuario` → 400 (firma humana obligatoria).
- P5: el detalle muestra el aviso REDACTADO (redact_pii_spans_es_co).
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.contracts.enums import EstadoCaso, ResultadoCobertura, RolUsuario
from app.security.redaction import redact_pii_spans_es_co
from app.hitl.c8 import aprobar as hitl_aprobar, rechazar as hitl_rechazar
from app.observability.replay import get_replay_store
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso

router = APIRouter(tags=["dashboard"])
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# Filtro de redacción P5 para plantillas: cualquier valor mostrado pasa por el redactor (defensa
# en profundidad). No aplicar a los inputs del form de corrección (el analista edita el valor real).
_TEMPLATES.env.filters["redact"] = lambda v: redact_pii_spans_es_co(str(v)) if v is not None else v

# Tasa blended ESTIMADA (Haiku ~$1/$5, Sonnet ~$3/$15 in/out por 1M) — NO facturable, solo orientativa.
COSTO_USD_POR_1M_TOKENS = 8.0
_TERMINAL_COBERTURA = {ResultadoCobertura.CUBIERTO, ResultadoCobertura.CUBIERTO_PARCIAL, ResultadoCobertura.NO_CUBIERTO}


def calcular_metricas(casos, replays) -> dict:
    """Agregación de presentación (H-21) — cuenta campos YA calculados (passive, cero dominio, cero PII).

    Pública (la reusa `demo_run.py` para el resumen de `make demo`, Unit G).

    Separa MÉTRICAS MEDIDAS (operación) de GARANTÍAS (invariantes verificadas por validador/tests).
    Robusto ante 0 casos (sin división por cero).
    """
    total = len(casos)
    por_estado = {e.value: sum(1 for c in casos if c.estado == e) for e in EstadoCaso}
    por_dictamen: dict[str, int] = {}
    for c in casos:
        if c.dictamen:
            k = c.dictamen.resultado.value
            por_dictamen[k] = por_dictamen.get(k, 0) + 1
    fraude: dict[str, int] = {}
    for c in casos:
        if c.alerta_fraude:
            fraude[c.alerta_fraude.severidad] = fraude.get(c.alerta_fraude.severidad, 0) + 1

    escalado = por_estado.get(EstadoCaso.REQUIERE_REVISION.value, 0)
    tokens = sum((r.get("token_summary") or {}).get("tokens_total", 0) for r in replays)

    # GARANTÍA (no métrica): dictámenes terminales de cobertura que citan cláusula (RULE-CTR-03).
    terminales = [c for c in casos if c.dictamen and c.dictamen.resultado in _TERMINAL_COBERTURA]
    clausula_ok = sum(1 for c in terminales if c.dictamen.clausula is not None)

    return {
        "total": total,
        "por_estado": por_estado,
        "por_dictamen": por_dictamen,
        "fraude": fraude,
        "escalado": escalado,
        "pct_escalado": round(100 * escalado / total) if total else 0,
        "tokens": tokens,
        "costo_estimado": round(tokens / 1_000_000 * COSTO_USD_POR_1M_TOKENS, 4),
        "clausula_ok": clausula_ok,
        "clausula_total": len(terminales),
    }


def _detalle_context(caso, rol: str) -> dict:
    """Contexto del detalle: aviso REDACTADO (P5) + traza + view-models agent-native (Unit I, passive)."""
    traza = get_replay_store().load(caso.id)  # {trace_events, token_summary} o None
    return {
        "rol": rol,
        "caso": caso,
        "aviso_redactado": redact_pii_spans_es_co(caso.aviso.texto_crudo),
        "traza": traza,
        "resumen": vista_caso.resumen_copiloto(caso),
        "confianza": vista_caso.confianza_riesgo(caso, traza),
        "recomendacion": vista_caso.recomendacion(caso),
        "verificador": vista_caso.hallazgos_verificador(caso, traza),
        "actividad": vista_caso.actividad_agentes(traza),
        "faltantes": vista_caso.faltantes(caso),  # banner + tabla fusionada + regla de habilitación
        "checklist": vista_caso.checklist_aprobacion(caso, traza),  # "Para aprobar se requiere"
        "trayectoria": vista_caso.verificacion_trayectoria(caso, traza),  # N: checks determinísticos
        "latencia": vista_caso.latencia_caso(traza),  # N: latencia real del pipeline
        "razon_escalamiento": vista_caso.razon_escalamiento(caso),  # N: por qué escaló
        "carta_tipo": vista_caso.tipo_carta(caso),  # M: qué carta aplica (o None)
    }


def _get_o_404(caso_id: str):
    caso = get_caso_repository().get(caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return caso


def _filtrar_bandeja(casos, estado: Optional[str]):
    """Filtro de PRESENTACIÓN (passive): estados reales + pseudo-filtros de los KPIs clicables.

    `RESUELTOS` (APROBADO+RECHAZADO) y `FRAUDE_ALTA` no son EstadoCaso: son agregados de UI que los
    KPIs mapean. Cero lógica de dominio — solo agrupa lo que ya está en el caso.
    """
    if not estado:
        return casos
    if estado == "RESUELTOS":
        return [c for c in casos if c.estado in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO)]
    if estado == "FRAUDE_ALTA":
        return [c for c in casos if c.alerta_fraude and c.alerta_fraude.severidad == "ALTA"]
    try:
        e = EstadoCaso(estado)
    except ValueError:
        return casos
    return [c for c in casos if c.estado == e]


@router.get("/", response_class=HTMLResponse)
@router.get("/casos", response_class=HTMLResponse)
def bandeja(request: Request, estado: Optional[str] = Query(None), rol: str = Query(RolUsuario.ANALISTA.value)):
    """H-19: bandeja de casos con filtro por estado + KPIs clicables (toggle) + selector de rol stub."""
    repo = get_caso_repository()
    todos = repo.list()
    casos = _filtrar_bandeja(todos, estado)
    # Más reciente arriba (efecto "van entrando") + hora de proceso + flag de recién llegado (<20s).
    casos = sorted(casos, key=lambda c: c.timestamp_actualizacion, reverse=True)
    ahora = datetime.now(timezone.utc)
    filas = [{
        "caso": c,
        "hora": c.timestamp_actualizacion.strftime("%H:%M:%S"),
        "reciente": (ahora - c.timestamp_actualizacion).total_seconds() < 20,
        "ramo": vista_caso.ramo_de(c),  # derivado de tipo_siniestro (passive, P7)
        "senal_fraude": vista_caso.senal_fraude(c),  # el "por qué" del fraude (passive, P6)
    } for c in casos]

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
        "filas": filas,
        "counts": counts,
        "nav_total": counts["total"],
        "estado_actual": estado or "",
        "rol": rol,
        "en_vivo": settings.demo_live != "off",  # Unit H: activa el auto-refresh de la bandeja
    })


@router.get("/casos/{caso_id}", response_class=HTMLResponse)
def detalle(request: Request, caso_id: str, rol: str = Query(RolUsuario.ANALISTA.value),
            enviado: Optional[str] = Query(None)):
    """H-20: detalle con evidencia enlazada (campo→origen, dictamen→cláusula) y aviso redactado (P5)."""
    caso = _get_o_404(caso_id)
    ctx = _detalle_context(caso, rol)
    if enviado:  # PRG tras enviar la carta (Unit M)
        ctx["carta_enviada"] = True
    return _TEMPLATES.TemplateResponse(request, "detalle.html", ctx)


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
    """H-21: métricas agregadas de cumplimiento + trazas por nodo/tokens desde C9 (ReplayStore)."""
    store = get_replay_store()
    replays = [r for r in (store.load(cid) for cid in store.get_all_cases()) if r is not None]
    metricas = calcular_metricas(get_caso_repository().list(), replays)
    return _TEMPLATES.TemplateResponse(request, "panel.html", {"replays": replays, "rol": rol, "metricas": metricas})


@router.get("/panel/export/{caso_id}")
def export_pia(caso_id: str):
    """H-15/H-21: export de evidencia (traza+tokens) del caso como JSON."""
    rec = get_replay_store().load(caso_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Sin traza para el caso")
    return JSONResponse(content=rec)
