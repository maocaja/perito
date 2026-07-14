"""C11 Dashboard router — Workbench (W1, `/workbench`), detalle (H-20), acciones HITL, panel (H-21).

W20/A6: el board legacy (`bandeja.html`, `/casos`) se retiró; `/` redirige a la Workbench (única superficie
del operador). `detalle` (`/casos/{id}`) se conserva hasta que Bolt-2 porte carta+rechazar a la Workbench.

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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.contracts.enums import EstadoCaso, ResultadoCobertura, RolUsuario
from app.security.redaction import redact_pii_spans_es_co
from app.observability.replay import get_replay_store
from app.dashboard.store import get_caso_repository
from app.dashboard import vista_caso
from app.dashboard import documentos as _documentos
from app.dashboard import evidencia as _evidencia
from app.dashboard import comparativa as _comparativa
from app.dashboard import productividad as _productividad
from app.dashboard import copiloto as _copiloto
from app.dashboard import demo_assets as _demo_assets

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
# Demo: URL del asset real (foto/PDF) de un documento si existe en `demo_assets/`; None → mock (P5).
_TEMPLATES.env.filters["asset_url"] = _demo_assets.url_de
# L2: etiquetas humanas — FUENTE ÚNICA compartida (Workbench y panel), sin mapas duplicados.
_TEMPLATES.env.filters["icono_fuente"] = vista_caso.icono_fuente  # N5/N9: glifo de la fuente de un campo
_TEMPLATES.env.filters["label_campo"] = vista_caso.label_campo
_TEMPLATES.env.filters["label_estado"] = vista_caso.label_estado
_TEMPLATES.env.filters["label_cobertura"] = vista_caso.label_cobertura

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
        # Vista del operador (encargado autorizado): el correo ORIGINAL tal cual llegó. La minimización P5 es
        # hacia el LLM (el prompt va redactado, `build_extraction_prompt_u2`), no hacia el operador legítimo.
        "aviso_texto": caso.aviso.texto_crudo,
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
        "datos_principales": vista_caso.datos_principales(caso),  # Fase 0: tabla única (presentes + REQUERIDO)
        "campos_corregibles": vista_caso.campos_corregibles(caso),  # Fase 2: valores para la corrección inline
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


@router.get("/", response_class=RedirectResponse)
def raiz(rol: str = Query(RolUsuario.ANALISTA.value)):
    """W20/A6: la Workbench es la única superficie del operador. La raíz redirige a la estación (el board
    legacy `/casos` + `bandeja.html` se retiraron; su cola vive en `/workbench`)."""
    return RedirectResponse(f"/workbench?rol={rol}", status_code=303)


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
        "razon": vista_caso.razon_cola(c),            # L4: razón operativa (para elegir sin abrir)
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


@router.get("/workbench/actividad/{caso_id}", response_class=HTMLResponse)
def workbench_actividad(request: Request, caso_id: str, rol: str = Query(RolUsuario.ANALISTA.value)):
    """Fase 1: parcial (drawer) de la actividad detallada de la orquesta (tokens/hora por AGENTE real)."""
    caso = _get_o_404(caso_id)
    traza = get_replay_store().load(caso.id)
    ctx = {"actividad": vista_caso.actividad_agentes(traza), "latencia": vista_caso.latencia_caso(traza)}
    return _TEMPLATES.TemplateResponse(request, "workbench_actividad.html", ctx)


@router.get("/workbench/comparativa/{caso_id}", response_class=HTMLResponse)
def workbench_comparativa(request: Request, caso_id: str, rol: str = Query(RolUsuario.ANALISTA.value)):
    """Fase 1: parcial (drawer) de la vista comparativa multi-correo (mock rotulado)."""
    caso = _get_o_404(caso_id)
    return _TEMPLATES.TemplateResponse(request, "workbench_comparativa.html", {"comparativa": _comparativa.comparativa_de(caso)})


@router.get("/workbench/documento/{caso_id}", response_class=HTMLResponse)
def workbench_documento(request: Request, caso_id: str, doc: int = Query(...),
                        rol: str = Query(RolUsuario.ANALISTA.value)):
    """W20·A3: visor overlay (drawer) de un documento del caso. Reusa el drawer de W12. Fail-closed: índice
    fuera de rango → 'documento no encontrado' (P7). P5: el visor sirve etiqueta/huella/mock redactado del
    provider (`documentos_de`), NUNCA la media cruda con PII (la redacción visual real llega con M1)."""
    caso = _get_o_404(caso_id)
    docs = _documentos.documentos_de(caso)
    documento = docs[doc] if 0 <= doc < len(docs) else None
    return _TEMPLATES.TemplateResponse(request, "workbench_documento.html",
                                       {"documento": documento, "asset_url": _demo_assets.url_de(documento)})


@router.get("/workbench/asset/{nombre}")
def workbench_asset(nombre: str):
    """Sirve un asset de DEMO desde `demo_assets/` (solo-demo). 🔒P5: sirve ÚNICAMENTE archivos físicamente
    presentes en esa carpeta (sintéticos, sin PII); nunca la media cruda de un correo (que no se persiste).
    Blindaje anti-traversal en `ruta_de_asset` (basename + dentro de la carpeta)."""
    ruta = _demo_assets.ruta_de_asset(nombre)
    if not ruta:
        raise HTTPException(status_code=404, detail="asset de demo no encontrado")
    return FileResponse(ruta)


@router.post("/workbench/identificar", response_class=RedirectResponse)
def workbench_identificar(request: Request, firmante: str = Form(""),
                         next: str = Form("/workbench?rol=ANALISTA")):
    """Firma de estación (identidad de sesión ligera): guarda quién es el analista UNA vez; a partir de ahí
    cada acción se firma sola (P1). Sin passwords. `firmante` vacío → limpia la identidad ('cambiar')."""
    nombre = (firmante or "").strip()
    if nombre:
        request.session["firmante"] = nombre
    else:
        request.session.pop("firmante", None)
    destino = next if next.startswith("/") else "/workbench?rol=ANALISTA"   # evita open-redirect
    return RedirectResponse(destino, status_code=303)


@router.post("/workbench/corregir/{caso_id}", response_class=HTMLResponse)
def workbench_corregir(request: Request, caso_id: str,
                       usuario: Optional[str] = Form(None), rol: str = Form(RolUsuario.ANALISTA.value),
                       numero_poliza: Optional[str] = Form(None), fecha_siniestro: Optional[str] = Form(None),
                       tipo_siniestro: Optional[str] = Form(None), monto_reclamado: Optional[str] = Form(None)):
    """Fase 2: corrección inline. Delega en `aplicar_correccion` (SERVER re-corre C4 + motor determinístico,
    P2; firma P1; 409 si terminal) y devuelve el partial `#wb-caso` re-renderizado (sin recarga)."""
    from app.api.hitl_actions import _firma, _validar_corregible, aplicar_correccion
    firma = _firma(request, usuario)              # P1 firma: sesión (UI) o fallback usuario (compat) → 400 si falta
    caso = _validar_corregible(caso_id, firma)    # 404 · 409 · 400
    actualizado = aplicar_correccion(caso, firma, {
        "numero_poliza": numero_poliza, "fecha_siniestro": fecha_siniestro,
        "tipo_siniestro": tipo_siniestro, "monto_reclamado": monto_reclamado,
    })
    ctx = {"rol": rol, "detalle": _detalle_context(actualizado, rol), "caso_activo_id": actualizado.id}
    return _TEMPLATES.TemplateResponse(request, "workbench_caso.html", ctx)


@router.get("/workbench/caso/{caso_id}", response_class=HTMLResponse)
def workbench_caso(request: Request, caso_id: str, rol: str = Query(RolUsuario.ANALISTA.value)):
    """W1: parcial del caso (centro + derecha) para el swap HTMX al seleccionar en la cola."""
    caso = _get_o_404(caso_id)
    ctx = {"rol": rol, "detalle": _detalle_context(caso, rol), "caso_activo_id": caso.id}
    return _TEMPLATES.TemplateResponse(request, "workbench_caso.html", ctx)


# W20/A6+A7: la página `detalle` y sus acciones legacy (`aprobar`/`rechazar` que renderizaban detalle) se
# retiraron. La Workbench es la única superficie: radicar (→APROBADO) y rechazar (→RECHAZADO) viven en
# `hitl_actions.py` y redirigen a `/workbench` (PRG). La carta se porta como drawer (cartas.py).


@router.get("/panel", response_class=HTMLResponse)
def panel(request: Request, rol: str = Query(RolUsuario.CUMPLIMIENTO.value)):
    """H-21: métricas agregadas de cumplimiento + trazas por nodo/tokens desde C9 (ReplayStore)."""
    store = get_replay_store()
    replays = [r for r in (store.load(cid) for cid in store.get_all_cases()) if r is not None]
    metricas = calcular_metricas(get_caso_repository().list(), replays)
    # W20/A1: la productividad del operador vive aquí (Reportes), no en la Workbench (estación de decisión).
    return _TEMPLATES.TemplateResponse(request, "panel.html", {
        "replays": replays, "rol": rol, "metricas": metricas,
        "productividad": _productividad.productividad(rol),
    })


@router.get("/panel/export/{caso_id}")
def export_pia(caso_id: str):
    """H-15/H-21: export de evidencia (traza+tokens) del caso como JSON."""
    rec = get_replay_store().load(caso_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Sin traza para el caso")
    return JSONResponse(content=rec)
