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
from app.dashboard import documentos as _documentos
from app.dashboard import evidencia as _evidencia
from app.dashboard import comparativa as _comparativa
from app.dashboard import productividad as _productividad
from app.dashboard import copiloto as _copiloto

router = APIRouter(tags=["dashboard"])
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
# Filtro de redacción P5 para plantillas: cualquier valor mostrado pasa por el redactor (defensa
# en profundidad). No aplicar a los inputs del form de corrección (el analista edita el valor real).
_TEMPLATES.env.filters["redact"] = lambda v: redact_pii_spans_es_co(str(v)) if v is not None else v
# W16: marca/nav desde la fuente única de branding (DIP) — sin literales dispersos en las plantillas.
from app.dashboard import branding  # noqa: E402
branding.registrar(_TEMPLATES)
# W11: la plantilla depende de la fuente de verdad tipo→ícono (DRY/OCP), no de un hardcode.
_TEMPLATES.env.filters["icono_tipo"] = _documentos.icono_de

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
    docs = _documentos.documentos_de(caso)  # W11: una sola vez (DRY)
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
        "prioridad": vista_caso.prioridad(caso),  # U1: nivel + motivo (citable)
        "equipo": vista_caso.equipo(caso),  # U1: routing a equipo (+ SIU si fraude)
        "clasificacion": vista_caso.clasificar(caso),  # W2: producto + tipo
        "asegurado": vista_caso.asegurado_de(caso),  # W2: asegurado (mock/real, rotulado)
        "tiempo_estimado": vista_caso.tiempo_estimado(caso),  # W2: estimado de revisión
        "timeline": vista_caso.timeline(caso, traza),  # W3: pasos de la IA + conteos (mock)
        "documentos": docs,  # W11: galería (provider mock, M1 lo vuelve real)
        "documentos_tipos": _documentos.agrupar_por_tipo(docs),  # W11: por tipo
        "comparativa": _comparativa.comparativa_de(caso),  # W13: multi-correo (mock, U7/U8 lo vuelven real)
        "resumen_narrativo": vista_caso.resumen_narrativo(caso),  # W4: fallback determinístico
        "resumen_ejecutivo": vista_caso.resumen_ejecutivo(caso),  # W19: Summary Agent (LLM) + fallback
        "riesgos": vista_caso.riesgos(caso),  # W5: 'Riesgos a revisar' (P6, solo sugiere)
        "campos_extraidos": vista_caso.campos_extraidos(caso),  # W17: dato·confianza·fuente (real+demo)
        "health": vista_caso.health_check(caso, traza),  # W6: % completo + checklist unificado
        "cobertura": vista_caso.explicacion_cobertura(caso),  # W7: 'por qué' del dictamen (P2, presenta)
        "docs_checklist": vista_caso.checklist_documentos(caso),  # U2: documentos requeridos por producto
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
def bandeja(request: Request, estado: Optional[str] = Query(None), rol: str = Query(RolUsuario.ANALISTA.value),
            orden: Optional[str] = Query(None)):
    """H-19: bandeja con filtro por estado + KPIs clicables + orden (recientes | prioridad, U1)."""
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
        "prioridad": vista_caso.prioridad(c),  # U1: nivel de prioridad (chip + acento)
    } for c in casos]
    # Orden secundario OPT-IN por prioridad (default: cronológico, para no romper el efecto en vivo).
    if orden == "prioridad":
        _rank = {"ALTA": 0, "MEDIA": 1, "BAJA": 2}
        filas.sort(key=lambda f: (_rank.get(f["prioridad"]["nivel"], 3),
                                  -f["caso"].timestamp_actualizacion.timestamp()))

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
        "orden": orden or "",
        "rol": rol,
        "en_vivo": settings.demo_live != "off",  # Unit H: activa el auto-refresh de la bandeja
    })


def _tiempo_relativo(ts, ahora) -> str:
    """'hace X' compacto para la tarjeta de la cola (como el mockup: '2 min')."""
    segs = max(0, int((ahora - ts).total_seconds()))
    if segs < 60:
        return f"{segs}s"
    if segs < 3600:
        return f"{segs // 60} min"
    if segs < 86400:
        return f"{segs // 3600} h"
    return f"{segs // 86400} d"


def _cola_filas(rol: str):
    """Filas de la cola (columna izq de la Workbench). Passive: reusa prioridad/clasificar/carril/resumen."""
    todos = get_caso_repository().list()
    casos = sorted(todos, key=lambda c: c.timestamp_actualizacion, reverse=True)
    ahora = datetime.now(timezone.utc)
    filas = [{
        "caso": c,
        "hora": c.timestamp_actualizacion.strftime("%H:%M:%S"),
        "hace": _tiempo_relativo(c.timestamp_actualizacion, ahora),
        "ramo": vista_caso.ramo_de(c),
        "senal_fraude": vista_caso.senal_fraude(c),
        "prioridad": vista_caso.prioridad(c),
        "clasificacion": vista_caso.clasificar(c),
        "carril": vista_caso.clasificador_cola(c),   # W8: carril por razón
        "resumen": vista_caso.resumen_cola(c),        # tarjeta rica (asegurado/póliza/placa/%/conteos)
    } for c in casos]
    return casos, filas


def _coincide_busqueda(fila, termino: str) -> bool:
    """W16: ¿la fila calza el término de búsqueda? (id de caso · póliza · tipo · asegurado). Passive.

    P5: el nombre del asegurado se usa SOLO para el match en memoria (no se loguea ni se persiste aquí); ya
    viene por el boundary redactado de `asegurado_de` (tel/email neutralizados)."""
    caso = fila["caso"]
    poliza = next((c.valor for c in caso.extraccion.campos
                   if c.nombre == "numero_poliza" and not c.ausente), "") if caso.extraccion else ""
    campos = [caso.id, poliza or "", fila["clasificacion"]["tipo"], vista_caso.asegurado_de(caso)["nombre"]]
    return any(termino in (v or "").lower() for v in campos)


@router.get("/workbench", response_class=HTMLResponse)
def workbench(request: Request, rol: str = Query(RolUsuario.ANALISTA.value),
              caso_id: Optional[str] = Query(None), carril: Optional[str] = Query(None),
              avanzar: Optional[str] = Query(None), q: Optional[str] = Query(None),
              estado: Optional[str] = Query(None)):
    """W1+W8: la estación unificada 3-columnas (cola izq por carriles · historia centro · acciones der).

    Server-rendered (ADR-001). Selecciona un caso → el centro/derecha se cargan por HTMX sin recargar el
    shell. Passive: reusa los view-models; cero lógica de decisión en cliente (P1).
    """
    casos, filas = _cola_filas(rol)
    # W8: conteos por carril (sobre TODA la cola) + filtro opcional por carril.
    carriles = [{"key": k, "icono": i, "etiqueta": e,
                 "count": sum(1 for f in filas if f["carril"]["carril"] == k)} for k, i, e in vista_caso.CARRILES]
    if carril:
        filas = [f for f in filas if f["carril"]["carril"] == carril]
    if estado:  # nav lateral (Inbox/En Proceso/Radicados/Escalados) → filtra SIN salir del workbench
        visibles_por_estado = set(id(c) for c in _filtrar_bandeja([f["caso"] for f in filas], estado))
        filas = [f for f in filas if id(f["caso"]) in visibles_por_estado]
    if q and q.strip():  # W16: búsqueda global (póliza/cliente/placa/caso)
        termino = q.strip().lower()
        filas = [f for f in filas if _coincide_busqueda(f, termino)]
    casos_visibles = [f["caso"] for f in filas]
    # Caso activo: el pedido explícito, o el primero de la cola visible (para que la estación no arranque vacía).
    # W10: `avanzar=1` (tras una acción) → salta al SIGUIENTE de la cola visible (flujo "actúa → siguiente").
    activo = None
    if caso_id:
        idx = next((i for i, f in enumerate(filas) if f["caso"].id == caso_id), None)
        if avanzar and idx is not None and idx + 1 < len(filas):
            activo = filas[idx + 1]["caso"]
        elif idx is not None:
            activo = filas[idx]["caso"]
        else:  # el caso ya no está en la cola visible (p.ej. cambió de carril) → primero visible
            activo = casos_visibles[0] if casos_visibles else None
    elif casos_visibles:
        activo = casos_visibles[0]
    ctx = {
        "rol": rol,
        "filas": filas,
        "carriles": carriles,
        "carril_actual": carril or "",
        "q_actual": q or "",
        "estado_wb": estado or "",
        "filtrado": bool(carril or estado or (q and q.strip())),  # hay un filtro activo en la cola
        "productividad": _productividad.productividad(rol),  # W14: métricas del operador (real + mock)
        "nav_total": len(casos),
        "en_vivo": settings.demo_live != "off",
        "caso_activo_id": activo.id if activo else None,
    }
    if activo is not None:
        ctx["detalle"] = _detalle_context(activo, rol)
    return _TEMPLATES.TemplateResponse(request, "workbench.html", ctx)


@router.post("/workbench/preguntar/{caso_id}", response_class=HTMLResponse)
def workbench_preguntar(request: Request, caso_id: str, pregunta: str = Form("")):
    """W15: copiloto conversacional (MOCK). Responde sobre el caso; solo EXPLICA, no decide ni muta (P1/P6)."""
    caso = _get_o_404(caso_id)
    respuesta = _copiloto.responder(pregunta, caso)
    return _TEMPLATES.TemplateResponse(request, "workbench_chat.html",
                                       {"pregunta": pregunta, "respuesta": respuesta})


@router.get("/workbench/evidencia/{caso_id}", response_class=HTMLResponse)
def workbench_evidencia(request: Request, caso_id: str, campo: str = Query(...),
                        rol: str = Query(RolUsuario.ANALISTA.value)):
    """W12: parcial del visor de evidencia de un campo (salto a la fuente). Fail-closed: sin ancla → aviso."""
    caso = _get_o_404(caso_id)
    ancla = _evidencia.ancla_de(caso, campo)
    ui = next((c for c in vista_caso.campos_extraidos(caso) if c.label == campo), None)
    ctx = {"campo": campo, "ancla": ancla, "confianza": ui.confianza if ui else None}
    return _TEMPLATES.TemplateResponse(request, "workbench_evidencia.html", ctx)


@router.get("/workbench/caso/{caso_id}", response_class=HTMLResponse)
def workbench_caso(request: Request, caso_id: str, rol: str = Query(RolUsuario.ANALISTA.value)):
    """W1: parcial del caso (centro + derecha) para el swap HTMX al seleccionar en la cola."""
    caso = _get_o_404(caso_id)
    ctx = {"rol": rol, "detalle": _detalle_context(caso, rol), "caso_activo_id": caso.id}
    return _TEMPLATES.TemplateResponse(request, "workbench_caso.html", ctx)


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
