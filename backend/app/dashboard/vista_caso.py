"""app/dashboard/vista_caso.py — view-models agent-native para el detalle (Unit I).

Presentación PURA: arma "lo que hizo el copiloto" a partir de las salidas REALES del pipeline
(extracción, dictamen, fraude) + la traza (ReplayStore). Determinístico, sin LLM, sin lógica de
dominio: NO importa `rules/` ni `orchestrator/`, NO decide, NO recalcula cobertura. Passive.

INVARIANTES:
- **P1:** `recomendacion` describe un PASO del humano; nunca "aprobar/rechazar" ni estado terminal.
- **P2:** el resumen CITA el veredicto del motor (resultado + regla + cláusula), no lo re-deriva.
- **P3/P7:** cada dato sale de una salida real; si falta, dice "no disponible" (no inventa).
- **P5:** cada valor de campo se redacta con `redact_pii_spans_es_co` antes de mostrar.
"""

import re

from app.contracts.enums import EstadoCaso
from app.security.redaction import redact_pii_spans_es_co

CAMPOS = ["numero_poliza", "fecha_siniestro", "tipo_siniestro", "monto_reclamado"]

# P1 fail-closed: la recomendación del copiloto NUNCA contiene estas palabras (no decide).
PALABRAS_PROHIBIDAS = {"aprobado", "rechazado", "admitido", "cerrado", "aprobar", "rechazar"}

# Nombre técnico de nodo → (etiqueta amigable, icono). Cubre AMBOS esquemas: determinístico
# (seed.sembrar_traza_demo: intake/extractor/policy/motor/fraude) y real (orchestrator/c7:
# c2_extraccion/c3_verificador/c4_policy_lookup/c5_motor_cobertura/c6_fraude/orquestador_*).
_NODOS = {
    "intake":               ("Intake · recibió el aviso", "📥"),
    "orquestador_inicio":   ("Orquestador · inició el flujo", "▶️"),
    "extractor":            ("Extractor · Haiku leyó el aviso", "🔍"),
    "c2_extraccion":        ("Extractor · Haiku leyó el aviso", "🔍"),
    "verifier":             ("Verificador · Sonnet revisó la extracción", "✔️"),
    "c3_verificador":       ("Verificador · Sonnet revisó la extracción", "✔️"),
    "policy":               ("Grounding · buscó la póliza", "📄"),
    "c4_policy_lookup":     ("Grounding · buscó la póliza", "📄"),
    "motor":                ("Motor R1–R5 · dictaminó la cobertura", "⚖️"),
    "c5_motor_cobertura":   ("Motor R1–R5 · dictaminó la cobertura", "⚖️"),
    "fraude":               ("Fraude · revisó inconsistencias", "🕵️"),
    "c6_fraude":            ("Fraude · revisó inconsistencias", "🕵️"),
    "orquestador_decision": ("Orquestador · dejó el caso listo para el humano", "🧑‍⚖️"),
}

_C3_RE = re.compile(r"confianza=([0-9.]+),\s*señales=(\d+)")
_TERMINALES = {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


def _red(v) -> str:
    return redact_pii_spans_es_co(str(v)) if v is not None else "—"


def _campo(caso, nombre):
    if not caso.extraccion:
        return None
    return next((c for c in caso.extraccion.campos if c.nombre == nombre), None)


def _presentes(caso) -> list[str]:
    return [n for n in CAMPOS if (c := _campo(caso, n)) and not c.ausente and c.valor is not None]


def _faltantes(caso) -> list[str]:
    return [n for n in CAMPOS if n not in _presentes(caso)]


def faltantes(caso) -> list[str]:
    """Campos requeridos aún ausentes. Público: lo usan el banner, el checklist y la tabla fusionada."""
    return _faltantes(caso)


# Ramo DERIVADO de tipo_siniestro (dato real) para la bandeja. Honesto (P7): agrupa un dato existente;
# sin match o ausente → "—" (no inventa). No hay "Vida" en el dominio, así que nunca se muestra.
_RAMO_PREFIJOS = (("AUTO", "Autos"), ("HOGAR", "Hogar"))


def ramo_de(caso) -> str:
    """Ramo (Autos/Hogar) derivado del prefijo de `tipo_siniestro`. Ausente/sin match → '—' (P7)."""
    c = _campo(caso, "tipo_siniestro")
    valor = ((c.valor if c and not c.ausente else "") or "").upper()
    for prefijo, label in _RAMO_PREFIJOS:
        if valor.startswith(prefijo):
            return label
    return "—"


# Señal de fraude en lenguaje plano para la bandeja (el "por qué"). P6: informativo, no decide.
# P5: se devuelve una etiqueta FIJA, nunca el `referencia` crudo (que trae montos/fechas).
_SENAL_FRAUDE = {
    "MONTO_EXCEDE_SUMA": "monto excede la suma",
    "FECHA_FUTURO": "fecha en el futuro",
    "FECHA_ANTERIOR_VIGENCIA": "fecha antes de vigencia",
    "FECHA_POSTERIOR_VIGENCIA": "fecha fuera de vigencia",
    "TIPO_NO_CUBIERTO": "tipo no cubierto",
}


def senal_fraude(caso) -> str | None:
    """Etiqueta legible de la inconsistencia de fraude principal. None si no hay alerta (P6)."""
    fr = caso.alerta_fraude
    if not fr or not fr.inconsistencias:
        return None
    tipo = (fr.inconsistencias[0].referencia or "").split(":", 1)[0].strip()
    return _SENAL_FRAUDE.get(tipo, "señal detectada")


# --------------------------------------- N · Visibilidad Tier-1 (todo determinístico, P7)

_COB_TERMINAL = {"CUBIERTO", "CUBIERTO_PARCIAL", "NO_CUBIERTO"}


def verificacion_trayectoria(caso, traza) -> list[dict]:
    """Checks DETERMINÍSTICOS de calidad de la trayectoria, en runtime. Cero LLM en vivo, cero fabricación.

    El juez Claude (faithfulness/tool-correctness) corre OFFLINE en CI (`pytest -m agentic`) — aquí solo
    se comprueban hechos verificables del caso + su traza (P7). Cada ítem: {label, ok, detalle}.
    """
    eventos = traza.get("trace_events", []) if traza else []
    presentes = [c for c in (caso.extraccion.campos if caso.extraccion else []) if not c.ausente and c.valor is not None]
    con_origen = [c for c in presentes if c.origen is not None]
    d = caso.dictamen
    es_terminal_cob = d is not None and d.resultado.value in _COB_TERMINAL
    return [
        {"label": "Recorrió el pipeline agéntico", "ok": len(eventos) > 0,
         "detalle": f"{len(eventos)} nodos" if eventos else "sin traza"},
        {"label": "Sin campos inventados (todos con origen)", "ok": len(con_origen) == len(presentes) and bool(presentes),
         "detalle": f"{len(con_origen)}/{len(presentes)} con origen" if presentes else "sin campos"},
        {"label": "El dictamen cita cláusula", "ok": bool(d and d.clausula),
         "detalle": (d.clausula.id if d and d.clausula else ("no aplica" if not es_terminal_cob else "sin cláusula"))},
    ]


def latencia_caso(traza) -> str | None:
    """Latencia total del pipeline (suma de `latencia_ms` de la traza). None si no hay traza."""
    if not traza:
        return None
    total = sum((ev.get("latencia_ms") or 0) for ev in traza.get("trace_events", []))
    if total <= 0:
        return None
    return f"{total / 1000:.1f} s" if total >= 1000 else f"{total} ms"


def razon_escalamiento(caso) -> str | None:
    """Por qué se escaló a humano (solo en REQUIERE_REVISION). None si no está escalado."""
    if caso.estado != EstadoCaso.REQUIERE_REVISION:
        return None
    falt = _faltantes(caso)
    if falt:
        return f"faltan datos: {', '.join(falt)}"
    if getattr(caso, "motivo_escalamiento", None):
        return caso.motivo_escalamiento
    return "escalado a revisión humana (dato ambiguo o póliza sin match)"


# ------------------------------------------------ U2 · Documentos requeridos por producto (passive)

# Catálogo determinístico producto → documentos requeridos (ejemplares reales). Productos no modelados → [].
_DOCS_POR_PRODUCTO = {
    "Autos": ["Denuncia de tránsito", "Licencia de conducción", "Tarjeta de propiedad",
              "SOAT vigente", "Fotos del vehículo", "Cotización del taller"],
    "Hogar": ["Soporte de propiedad/tenencia", "Fotos de los daños", "Cotización de reparación",
              "Denuncia (si aplica)"],
}


def documentos_requeridos(producto: str) -> list[str]:
    """Documentos requeridos por producto (catálogo determinístico). Sin catálogo → [] (P7, no inventa)."""
    return _DOCS_POR_PRODUCTO.get(producto, [])


def checklist_documentos(caso) -> dict:
    """Checklist de documentos por producto. `presente=None` hasta que U4 (multimodal) detecte adjuntos.

    P7: si el producto no está modelado → `disponible=False` (no inventa una lista).
    """
    prod = ramo_de(caso)
    docs = documentos_requeridos(prod)
    if not docs:
        return {"producto": prod, "disponible": False, "docs": []}
    return {"producto": prod, "disponible": True,
            "docs": [{"doc": d, "presente": None} for d in docs]}  # 'docs' (no 'items': colisiona con dict.items en Jinja)


# -------------------------------------------- U1 · Clasificación + Prioridad + Routing (passive)

def clasificar(caso) -> dict:
    """Producto (derivado del ramo) + tipo del siniestro. Passive; sin match → '—' (P7)."""
    c = _campo(caso, "tipo_siniestro")
    tipo = (c.valor if c and not c.ausente else None) or "—"
    return {"producto": ramo_de(caso), "tipo": tipo}


def prioridad(caso) -> dict:
    """Prioridad por REGLAS citables (P2-style). Cita la regla que la disparó. Passive, no decide (P1).

    Con los datos actuales (sin 'lesionados' aún — llega con U4) se prioriza por fraude, escalamiento y
    dictamen. La regla queda explícita en 'motivo'.
    """
    est = caso.estado  # var local: comparación de enum sin el patrón de mutación (passive)
    fr = caso.alerta_fraude
    if fr and fr.severidad == "ALTA":
        return {"nivel": "ALTA", "motivo": "señal de fraude alta → revisión prioritaria"}
    if est == EstadoCaso.REQUIERE_REVISION:
        return {"nivel": "MEDIA", "motivo": "requiere revisión (dato faltante o póliza)"}
    if fr:
        return {"nivel": "MEDIA", "motivo": f"señal de fraude {fr.severidad.lower()}"}
    return {"nivel": "BAJA", "motivo": "sin señales críticas"}


_EQUIPO = {"Autos": "Equipo Autos", "Hogar": "Equipo Hogar"}


def equipo(caso) -> dict:
    """Equipo destino por producto (mapping determinístico) + sugerencia SIU si hay fraude (P6: solo sugiere)."""
    dest = _EQUIPO.get(ramo_de(caso), "Ajustadores")
    siu = caso.alerta_fraude is not None  # sugerencia de carril SIU, no cambia estado
    return {"equipo": dest, "siu": siu}


def tipo_carta(caso) -> str | None:
    """Qué carta aplica según el estado (Unit M): 'resolucion' | 'datos' | None. Passive."""
    est = caso.estado  # var local para comparar el enum sin el patrón de mutación (passive)
    if est in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO):
        return "resolucion"
    if est == EstadoCaso.REQUIERE_REVISION and _faltantes(caso):
        return "datos"
    return None


def _nivel_conf(x: float) -> str:
    return "ok" if x >= 0.9 else ("warn" if x >= 0.7 else "bad")


# ---------------------------------------------------------------- A · Resumen

def resumen_copiloto(caso) -> dict:
    """Briefing en lenguaje plano armado de las salidas reales. Cita el motor LITERAL (P2)."""
    presentes, faltantes = _presentes(caso), _faltantes(caso)
    lineas = [{
        "icono": "🔍",
        "texto": f"Leí el aviso y extraje {len(presentes)} de {len(CAMPOS)} campos"
                 + (f" — falta: {', '.join(faltantes)}." if faltantes else "."),
    }]

    d = caso.dictamen
    if d is not None:
        if d.clausula is not None:  # cita literal: resultado + regla + cláusula (P2)
            cob = f"Cobertura: {d.resultado.value} (regla {d.regla_aplicada}) · cláusula {d.clausula.id}, {d.clausula.referencia}."
        else:
            cob = f"Cobertura: {d.resultado.value} (regla {d.regla_aplicada}) · sin cláusula (escalado)."
        lineas.append({"icono": "⚖️", "texto": cob})
    else:
        lineas.append({"icono": "⚖️", "texto": "Cobertura: no disponible (el motor no dictaminó)."})

    if caso.alerta_fraude is not None:
        lineas.append({"icono": "🕵️", "texto": f"Señal de fraude {caso.alerta_fraude.severidad}: {_red(caso.alerta_fraude.explicacion)}"})
    else:
        lineas.append({"icono": "🕵️", "texto": "Sin señales de fraude."})

    est = caso.estado  # var local: comparación de enum sin el patrón de mutación (passive)
    if est == EstadoCaso.LISTO_PARA_APROBAR:
        headline = "Caso preparado — listo para tu decisión"
    elif est == EstadoCaso.REQUIERE_REVISION:
        headline = "Escalado a revisión humana"  # el detalle específico va en el banner (no duplicar)
    else:
        headline = f"Caso {est.value.lower()}"
    return {"headline": headline, "lineas": lineas, "estado": caso.estado.value}


# ------------------------------------------------- E · Hallazgos del verificador

def hallazgos_verificador(caso, traza) -> dict:
    """C3 se lee de la TRAZA (no del Caso). Si el evento no existe → no disponible (P7)."""
    if traza:
        for ev in traza.get("trace_events", []):
            if "c3" in ev.get("nodo", "") or ev.get("nodo") == "verifier":
                m = _C3_RE.search(ev.get("resultado", "") or "")
                if m:
                    conf = float(m.group(1))
                    return {"disponible": True, "confianza": conf, "senales": int(m.group(2)), "nivel": _nivel_conf(conf)}
    return {"disponible": False, "confianza": None, "senales": None, "nivel": "neutral"}


# ---------------------------------------------------------- C · Confianza y riesgo

def confianza_riesgo(caso, traza) -> list[dict]:
    """Strip de un vistazo: extracción · verificación · fraude · cobertura."""
    presentes, falt = _presentes(caso), _faltantes(caso)
    verif = hallazgos_verificador(caso, traza)
    fr = caso.alerta_fraude
    d = caso.dictamen
    return [
        # Extracción = completitud de campos (la confianza por campo va en la tabla, no aquí).
        {"label": "Extracción", "valor": f"{len(presentes)} / {len(CAMPOS)} campos", "nivel": "ok" if not falt else "warn"},
        {"label": "Verificación", "valor": f"{verif['confianza']:.2f}" if verif["disponible"] else "n/d", "nivel": verif["nivel"]},
        {"label": "Fraude", "valor": (fr.severidad if fr else "sin señales"), "nivel": ("bad" if fr and fr.severidad == "ALTA" else ("warn" if fr else "ok"))},
        {"label": "Cobertura", "valor": _label_cobertura(d), "nivel": _nivel_cobertura(d)},
    ]


# Enum de cobertura → etiqueta humana (para las superficies de un vistazo: tira + checklist).
# El resumen del copiloto SÍ cita el enum crudo (P2: cita literal del veredicto del motor).
_COBERTURA_LABEL = {
    "CUBIERTO": "Cubierto", "CUBIERTO_PARCIAL": "Cubierto parcial",
    "NO_CUBIERTO": "No cubierto", "REQUIERE_REVISION": "Requiere revisión",
}


def _label_cobertura(d) -> str:
    return _COBERTURA_LABEL.get(d.resultado.value, d.resultado.value) if d else "n/d"


def _nivel_cobertura(d) -> str:
    if d is None:
        return "neutral"
    v = d.resultado.value
    if v == "CUBIERTO":
        return "ok"
    if v == "CUBIERTO_PARCIAL":
        return "warn"
    if v == "NO_CUBIERTO":
        return "bad"
    return "neutral"  # REQUIERE_REVISION


# ---------------------------------------------------- D · Recomendación (P1-safe)

def recomendacion(caso) -> dict:
    """Próximo paso del HUMANO. NUNCA decide (P1): no contiene PALABRAS_PROHIBIDAS ni estado terminal."""
    faltantes = _faltantes(caso)
    est = caso.estado  # var local: comparación de enum sin el patrón de mutación (passive)
    if est in _TERMINALES:
        quien = f" por {caso.aprobado_por}" if getattr(caso, "aprobado_por", None) else ""
        rec = {"icono": "🔒", "titulo": "Caso resuelto", "texto": f"Decisión humana registrada{quien}.", "tono": "neutral"}
    elif est == EstadoCaso.REQUIERE_REVISION:
        if faltantes:
            n = len(faltantes)
            titulo = ("Falta 1 dato para poder dictaminar este caso" if n == 1
                      else f"Faltan {n} datos para poder dictaminar este caso")
            rec = {"icono": "📝", "titulo": titulo,
                   "texto": f"El copiloto no pudo completar: falta {', '.join(faltantes)}. Sugerencia: pídelo al asegurado antes de decidir.", "tono": "warn"}
        else:
            rec = {"icono": "🔎", "titulo": "Verifica la póliza",
                   "texto": "No se encontró la póliza referida. Verifícala antes de decidir.", "tono": "warn"}
    else:  # LISTO_PARA_APROBAR
        if caso.alerta_fraude is not None:
            rec = {"icono": "🕵️", "titulo": "Revisa la señal de fraude",
                   "texto": f"Hay una señal de fraude ({caso.alerta_fraude.severidad}). Revísala antes de firmar; la decisión es tuya (P1).", "tono": "warn"}
        else:
            rec = {"icono": "✅", "titulo": "Listo para tu firma",
                   "texto": "El copiloto preparó el dictamen citando la cláusula. Revísalo y fírmalo — la decisión es tuya (P1).", "tono": "ok"}
    # P1 fail-closed: si por algún cambio se colara una palabra de decisión, se degrada a texto neutro.
    if any(p in rec["texto"].lower() or p in rec["titulo"].lower() for p in PALABRAS_PROHIBIDAS):
        rec = {"icono": "🧑‍⚖️", "titulo": "Decisión humana requerida", "texto": "Revisa el caso y decide (P1).", "tono": "neutral"}
    return rec


# ---------------------------------------------- F · Checklist de aprobación (P1)

def checklist_aprobacion(caso, traza) -> list[dict]:
    """Requisitos para habilitar la aprobación. PASSIVE (P1): refleja el estado real, NO decide.

    `ok` es informativo (azúcar de UI); el gate real de la aprobación sigue siendo `hitl` en el servidor.
    Cada ítem: {label, ok, detalle}. Cero fabricación: si un dato falta, el detalle lo dice (P7).
    """
    verif = hallazgos_verificador(caso, traza)
    falt = _faltantes(caso)
    presentes = _presentes(caso)
    d = caso.dictamen
    cobertura_ok = d is not None and d.resultado.value != "REQUIERE_REVISION"
    return [
        {
            # `na` (no aplica): en modo determinístico/preset no hay verificación adversarial; no es un
            # requisito pendiente que vaya a llegar, así que se muestra neutro, no como bloqueo.
            "label": "Verificación de fidelidad",
            "ok": verif["disponible"],
            "na": not verif["disponible"],
            "detalle": f"confianza {verif['confianza']:.2f}" if verif["disponible"] else "no aplica (modo determinístico)",
        },
        {
            "label": "Datos del siniestro completos",
            "ok": not falt,
            "na": False,
            "detalle": f"{len(presentes)} / {len(CAMPOS)} campos" if not falt else f"faltan {len(falt)}",
        },
        {
            "label": "Cobertura dictaminada",
            "ok": cobertura_ok,
            "na": False,
            "detalle": _label_cobertura(d) if d else "pendiente de datos",
        },
    ]


# ---------------------------------------------------- B · Actividad de los agentes

def actividad_agentes(traza) -> list[dict]:
    """La traza como feed legible por agente. Mapea ambos esquemas de nombres; fallback al técnico."""
    if not traza:
        return []
    feed = []
    for ev in traza.get("trace_events", []):
        nodo = ev.get("nodo", "")
        etiqueta, icono = _NODOS.get(nodo, (nodo, "•"))  # fallback: nombre técnico
        toks = (ev.get("tokens_in", 0) or 0) + (ev.get("tokens_out", 0) or 0)
        ts = ev.get("timestamp") or ""
        feed.append({
            "icono": icono,
            "etiqueta": etiqueta,
            "resultado": _red(ev.get("resultado", "")),
            "tokens": toks,
            "hora": ts[11:19] if len(ts) >= 19 else "",
            "error": ev.get("error"),
        })
    return feed
