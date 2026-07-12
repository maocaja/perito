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
from dataclasses import dataclass
from typing import Literal

from app.contracts.enums import EstadoCaso, ResultadoCobertura, TipoOrigen
from app.contracts.correlacion import CONFIANZA_DIVERGENCIA
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
    "c2_reextraccion":      ("Extractor · re-extrajo tras la crítica (loop reflexivo)", "🔁"),
    "c3_reverificacion":    ("Verificador · re-revisó la extracción", "✔️"),
    "orquestador_decision": ("Orquestador · dejó el caso listo para el humano", "🧑‍⚖️"),
    # Agentes que se suman cuando emitan traza (M1/M3/W19), sin tocar la vista (mapa extensible):
    "document_ai":          ("Document AI · leyó los adjuntos", "📎"),
    "evidence_correlator":  ("Correlación de evidencia · cruzó fuentes", "🧩"),
    "summary_agent":        ("Resumen · redactó la historia del caso", "✍️"),
}

_C3_RE = re.compile(r"confianza=([0-9.]+),\s*señales=(\d+)")
_TERMINALES = {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


def _red(v) -> str:
    return redact_pii_spans_es_co(str(v)) if v is not None else "—"


def _valor_operador(v) -> str:
    """Valor de un campo para la VISTA DEL OPERADOR. P5 (dos niveles): al LLM la PII se redacta SIEMPRE
    (nunca ve cédula/teléfono, ver `build_extraction_prompt_u2`); al operador —encargado del tratamiento con
    finalidad legítima (Ley 1581, 'acceso restringido a terceros autorizados')— se le muestra el dato REAL
    para que pueda trabajar (verificar identidad, contactar, cruzar fraude). El enmascarado + reveal por rol
    + log de acceso se justifica solo con múltiples roles/datos reales — no con un único analista autorizado."""
    return "—" if v is None else str(v)


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


def razon_cola(caso) -> str:
    """L4 · Razón OPERATIVA por la que el caso está en la cola — para elegir el siguiente sin abrirlo. El
    fraude va aparte (su propio flag 🕵️); aquí: qué falta / cobertura / listo. Passive, no decide (P1)."""
    falt = _faltantes(caso)
    if falt:
        extra = f" y {len(falt) - 1} más" if len(falt) > 1 else ""
        return "Falta " + _LABEL_CAMPO.get(falt[0], falt[0]).lower() + extra
    d = caso.dictamen
    if d and d.resultado.value == "NO_CUBIERTO":
        return "Cobertura no aplica"
    est = caso.estado  # alias local del estado: comparación passive, nunca mutación
    if est == EstadoCaso.LISTO_PARA_APROBAR:
        return "Listo para revisar"
    return ""


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


# Liga un documento requerido con un adjunto real por palabra clave (etiqueta/nombre/tipo del adjunto). M1
# cuelga adjuntos del caso → el checklist deja de ser ciego. Un doc sin criterio → no se puede afirmar (None).
_DOC_KEYWORD = {
    "Denuncia de tránsito": ("denuncia",), "Denuncia (si aplica)": ("denuncia",),
    "SOAT vigente": ("soat",),
    "Fotos del vehículo": ("foto",), "Fotos de los daños": ("foto",),
    "Licencia de conducción": ("licencia",),
    "Tarjeta de propiedad": ("tarjeta", "propiedad"),
    "Cotización del taller": ("cotiz", "factura"), "Cotización de reparación": ("cotiz", "factura"),
    "Soporte de propiedad/tenencia": ("propiedad", "tenencia"),
}


def _documento_presente(caso, doc: str) -> bool | None:
    """¿Hay un adjunto real que satisface `doc`? True/False si hay criterio; None si no se puede afirmar."""
    claves = _DOC_KEYWORD.get(doc)
    if not claves:
        return None
    for a in getattr(caso, "adjuntos", None) or []:
        heno = f"{a.etiqueta} {a.nombre} {a.tipo}".lower()
        if any(clave in heno for clave in claves):
            return True
    return False


def checklist_documentos(caso) -> dict:
    """Checklist de documentos por producto. `presente` se deriva de los adjuntos REALES del caso (M1): True
    si hay un adjunto que lo satisface, False si no, None si el caso aún no trae adjuntos (no se puede afirmar).

    P7: si el producto no está modelado → `disponible=False` (no inventa una lista).
    """
    prod = ramo_de(caso)
    docs = documentos_requeridos(prod)
    if not docs:
        return {"producto": prod, "disponible": False, "docs": []}
    tiene_adjuntos = bool(getattr(caso, "adjuntos", None))
    return {"producto": prod, "disponible": True,
            # 'docs' (no 'items': colisiona con dict.items en Jinja)
            "docs": [{"doc": d, "presente": _documento_presente(caso, d) if tiene_adjuntos else None} for d in docs]}


# -------------------------------------------- U1 · Clasificación + Prioridad + Routing (passive)

# L2 · Tipo de siniestro: código canónico (enum, el motor lo compara exacto — P2) → etiqueta HUMANA de display.
# Se cambia solo lo que ve el operador; el valor del dato/campo sigue siendo el enum.
_TIPO_LABEL = {
    "AUTO_COLISION": "Colisión vehicular", "AUTO_HURTO": "Hurto de vehículo",
    "HOGAR_AGUA": "Daño por agua (hogar)", "HOGAR_INCENDIO": "Incendio (hogar)",
    "SOAT_GASTOS_MEDICOS": "SOAT · gastos médicos", "SOAT_INCAPACIDAD": "SOAT · incapacidad",
}


def _tipo_humano(valor) -> str:
    """Etiqueta humana del tipo de siniestro (enum → legible); '—' si ausente. El enum no cambia (P2)."""
    if not valor or valor == "—":
        return "—"
    return _TIPO_LABEL.get(valor, valor.replace("_", " ").capitalize())


def clasificar(caso) -> dict:
    """Producto (derivado del ramo) + tipo del siniestro (código + etiqueta humana). Passive; sin match → '—'."""
    c = _campo(caso, "tipo_siniestro")
    tipo = (c.valor if c and not c.ausente else None) or "—"
    return {"producto": ramo_de(caso), "tipo": tipo, "tipo_humano": _tipo_humano(tipo)}


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


# --- W2 · providers del header (mock intercambiable hasta M2, rotulado P7) ---
_DEMO_NOMBRES = ["Juan Pérez", "María Gómez", "Carlos Ruiz", "Ana Torres", "Luis Marín", "Sofía Díaz"]


def asegurado_de(caso) -> dict:
    """Nombre del asegurado. Interfaz estable {nombre, origen}. **M2** lo vuelve real leyendo 'asegurado_nombre'
    (P7: si no está, cae al demo determinístico por caso). P5 defensa en profundidad: el nombre se redacta en el
    boundary (`_red`) — no oculta el nombre operacional, pero neutraliza un tel/email embebido en el campo."""
    c = _campo(caso, "asegurado_nombre")
    if c and not c.ausente and c.valor:
        return {"nombre": _red(c.valor), "origen": "real"}
    nombre = _DEMO_NOMBRES[sum(ord(ch) for ch in caso.id) % len(_DEMO_NOMBRES)]
    return {"nombre": nombre, "origen": "demo"}


def tiempo_estimado(caso) -> dict:
    """Tiempo estimado de revisión (heurística honesta: más faltantes/riesgo → más tiempo). Rotulado
    'estimado' (P7): no es una medición real. Interfaz {texto, segundos, es_estimado}."""
    segundos = 90 + 30 * len(faltantes(caso))
    if caso.alerta_fraude is not None:
        segundos += 45
    m, s = divmod(segundos, 60)
    texto = f"{m} min {s:02d} s" if m else f"{s} s"
    return {"texto": texto, "segundos": segundos, "es_estimado": True}


# --- W5 · Riesgos ("míralo") — reencuadre passive de alerta_fraude (P6: solo sugiere) ---
_RIESGO_LEGIBLE = {
    "FECHA_ANTERIOR_VIGENCIA": "La fecha del siniestro es anterior a la vigencia de la póliza.",
    "FECHA_POSTERIOR_VIGENCIA": "La fecha del siniestro es posterior a la vigencia de la póliza.",
    "FECHA_FUTURO": "La fecha del siniestro está en el futuro.",
    "MONTO_EXCEDE_SUMA": "El monto reclamado supera la suma asegurada.",
    "TIPO_NO_CUBIERTO": "El tipo de siniestro no está en las coberturas contratadas.",
    "FRECUENCIA": "Reclamaciones frecuentes en esta póliza.",
    "FOTO_REUTILIZADA": "Una foto coincide con un siniestro anterior.",
    "CO_OCURRENCIA": "Entidad compartida con otros casos.",
}


def _riesgo_legible(referencia: str) -> str:
    """Traduce la referencia interna a una frase 'míralo' humana. Genérica → sin PII (P5)."""
    prefijo = (referencia or "").split(":", 1)[0].strip()
    return _RIESGO_LEGIBLE.get(prefijo, "Inconsistencia detectada — revísala.")


def riesgos(caso) -> dict:
    """W5 · 'Riesgos a revisar' — reúne `alerta_fraude` (C6) + divergencias cross-fuente (M3). 🔒 P6: SOLO
    sugiere ('míralo'), nunca decide/bloquea. Passive: no toca estado. {hay, severidad, confianza, explicacion,
    lista[]} (clave 'lista', no 'items': colisiona con `dict.items` en Jinja)."""
    fr = caso.alerta_fraude
    lista = []
    if fr is not None and fr.inconsistencias:
        # P5 defensa en profundidad: la referencia cruda se REDACTA (además del |redact del template); el
        # 'legible' se calcula del prefijo crudo (que no lleva PII).
        lista += [{"texto": _riesgo_legible(e.referencia), "referencia": _red(e.referencia)}
                  for e in fr.inconsistencias]
    # M3: cada divergencia cross-fuente es un riesgo "míralo" (ya redactado en el correlador; _red por si acaso).
    lista += [{"texto": _red(c.inconsistencia), "referencia": f"Correlación · {c.campo_label}"}
              for c in getattr(caso, "correlaciones", None) or [] if not c.coincide and c.inconsistencia]

    if not lista:  # ni alerta ni divergencias → no hay riesgos
        return {"hay": False, "lista": []}
    return {
        "hay": True,
        # Sin alerta de fraude, el único riesgo son divergencias cross-fuente (M3): severidad MEDIA (una
        # inconsistencia entre fuentes merece más que 'BAJA', pero es 'míralo', no fraude — P6).
        "severidad": fr.severidad if fr is not None else "MEDIA",
        "confianza": fr.confianza if fr is not None else CONFIANZA_DIVERGENCIA,
        "explicacion": _red(fr.explicacion) if fr is not None else "Inconsistencias entre fuentes del caso — revísalas.",
        "lista": lista,
    }


# --- W8 · Cola inteligente por razón (carriles determinísticos, citables) ---
CARRILES = [  # orden de presentación (urgencia) — clave, icono, etiqueta
    ("rojo", "🔴", "Lesionados"),
    ("ambar", "🟠", "Cobertura dudosa"),
    ("amarillo", "🟡", "Documentos faltantes"),
    ("verde", "🟢", "Listo para radicar"),
]
_CARRIL_META = {k: {"icono": i, "etiqueta": e} for k, i, e in CARRILES}


def _lesionados(caso) -> bool:
    """¿Hay lesionados? M2: lee el campo REAL 'lesionados' del extractor determinístico (conteo > 0). Si no
    está (caso viejo/preset), cae a la heurística sobre el texto del aviso — misma señal, degradación honesta."""
    if getattr(caso, "extraccion", None):
        c = _campo(caso, "lesionados")
        if c and not c.ausente and c.valor:
            return c.valor.strip() not in ("", "0")
    t = (caso.aviso.texto_crudo or "").lower() if getattr(caso, "aviso", None) else ""
    return any(k in t for k in ("lesionad", "herido", "lesión", "lesion"))


def resumen_cola(caso) -> dict:
    """Campos de la TARJETA rica de la cola (como el mockup). Reales: póliza, % completo. Mock (rotulado en
    la UI): asegurado, placa, conteos de correos/docs — hasta M1/M2. {asegurado, poliza, placa, pct, correos, docs}."""
    presentes = _presentes(caso)
    poliza = None
    if caso.extraccion:
        poliza = next((c.valor for c in caso.extraccion.campos
                       if c.nombre == "numero_poliza" and not c.ausente), None)
    h = sum(ord(ch) for ch in caso.id)
    placa = _campo(caso, "placa")
    return {
        "asegurado": asegurado_de(caso)["nombre"],   # real si C2 lo extrajo (asegurado_de), si no mock
        "poliza": poliza or "—",                       # real
        "placa": placa.valor if (placa and not placa.ausente and placa.valor) else _demo_pick(caso, _DEMO_PLACA),
        "pct": round(100 * len(presentes) / len(CAMPOS)),  # real (completitud de campos)
        "correos": 1 + h % 3,                          # mock
        "docs": 6 + h % 12,                            # mock
    }


def clasificador_cola(caso) -> dict:
    """W8 · Carril de la cola por RAZÓN (determinístico, mutuamente excluyente, prioridad por urgencia).
    Passive (P1/P2): ORDENA el trabajo, no decide cobertura/estado. {carril, icono, etiqueta, motivo}.
    """
    d = caso.dictamen
    est = caso.estado
    falt = _faltantes(caso)
    if _lesionados(caso):
        carril, motivo = "rojo", "posibles lesionados (heurística) → atención prioritaria"
    elif (caso.alerta_fraude is not None
          or (d is not None and d.resultado == ResultadoCobertura.CUBIERTO_PARCIAL)
          or (est == EstadoCaso.REQUIERE_REVISION and not falt)):
        carril, motivo = "ambar", "cobertura/riesgo a revisar antes de decidir"
    elif falt:
        carril, motivo = "amarillo", f"faltan datos ({', '.join(falt)})"
    elif est in (EstadoCaso.APROBADO, EstadoCaso.RECHAZADO):
        carril, motivo = "verde", "caso cerrado (resuelto por humano)"
    elif est == EstadoCaso.LISTO_PARA_APROBAR:
        carril, motivo = "verde", "preparado — listo para tu firma"
    else:
        carril, motivo = "verde", "sin pendientes de preparación"
    return {"carril": carril, **_CARRIL_META[carril], "motivo": motivo}


def _frase_cobertura(d, pol) -> str:
    # P5 defensa en profundidad: `_red` sobre los valores (son de catálogo/montos, pero se blinda igual).
    partes = [f"Dictamen: {_label_cobertura(d)} (regla {d.regla_aplicada})."]
    if d.cobertura_aplicada:
        partes.append(f"Cobertura aplicada: {_red(str(d.cobertura_aplicada))}.")
    if d.sublimite_aplicado is not None:
        partes.append(f"Sublímite: {_red(str(d.sublimite_aplicado))}.")
    partes.append(f"Deducible: {_red(str(d.deducible_calculado))}.")
    if pol and getattr(pol, "vigencia", None):
        partes.append(f"Vigencia hasta {pol.vigencia.hasta}.")
    return " ".join(partes)


def explicacion_cobertura(caso) -> dict:
    """W7 · El 'por qué' del dictamen. 🔒 P2: SOLO PRESENTA la decisión del motor R1-R5 (no re-decide).
    Cita regla + cláusula + (U3) cobertura/sublímite/deducible/vigencia — todo tomado del `Dictamen`/`Poliza`."""
    d = caso.dictamen
    if d is None:
        return {"disponible": False}
    pol = caso.poliza_match.poliza if (caso.poliza_match and caso.poliza_match.poliza) else None
    return {
        "disponible": True,
        "resultado": d.resultado.value,
        "label": _label_cobertura(d),
        "nivel": _nivel_cobertura(d),
        "regla": d.regla_aplicada,
        "clausula": ({"texto": _red(d.clausula.texto), "referencia": d.clausula.referencia}
                     if d.clausula else None),
        "cobertura": d.cobertura_aplicada,
        "sublimite": str(d.sublimite_aplicado) if d.sublimite_aplicado is not None else None,
        "deducible": str(d.deducible_calculado),
        "vigencia_hasta": str(pol.vigencia.hasta) if pol and getattr(pol, "vigencia", None) else None,
        "frase": _frase_cobertura(d, pol),
    }


def resumen_ejecutivo(caso) -> dict:
    """W19 · La historia del caso vía el **Summary Agent** (LLM), con fallback determinístico a W4.
    {texto, origen}: origen="agente" (lo redactó el LLM) | "base" (plantilla W4). Rotulado en la UI (P7).

    El Summary Agent (LLM) solo corre en modo `real`; en `deterministic`/`off` usa la historia determinística
    (W4) DIRECTO — sin llamar a la API (respeta el modo: cero costo/latencia/ruido, no un fallback por error)."""
    from app.config import settings
    if settings.demo_live == "real":
        from app.llm.summary import call_summary_agent  # lazy: evita ciclo dashboard↔llm
        texto, origen = call_summary_agent(caso)
        return {"texto": texto, "origen": origen}
    return {"texto": resumen_narrativo(caso), "origen": "base"}


def health_check(caso, traza) -> dict:
    """W6 · Health Check del caso: % completo + checklist unificado (campos · verificación · cobertura ·
    documentos). Passive (P1): informativo, el gate real sigue en `hitl`. P7: no fabrica; los ítems que
    dependen de adjuntos van rotulados 'demo' y NO cuentan al % (no se puede validar sin M1). % reproducible."""
    checks = []
    for nombre in CAMPOS:
        c = _campo(caso, nombre)
        ok = c is not None and not c.ausente and c.valor is not None
        checks.append({"label": _LABEL_CAMPO.get(nombre, nombre.replace("_", " ").capitalize()),  # L2: label humano
                       "estado": "ok" if ok else "warn",
                       "detalle": "capturado" if ok else "falta", "demo": False})
    verif = hallazgos_verificador(caso, traza)
    checks.append({"label": "Coincidencia entre fuentes",
                   "estado": "ok" if verif["disponible"] else "na",
                   "detalle": f"confianza {verif['confianza']:.2f}" if verif["disponible"] else "no aplica (modo determinístico)",
                   "demo": False})
    d = caso.dictamen
    # Honesto (P7): solo CUBIERTO es ✔; PARCIAL/NO_CUBIERTO/REQUIERE se muestran ⚠ (no un falso 'todo bien').
    _cob_estado = {"CUBIERTO": "ok"}.get(d.resultado.value, "warn") if d else "warn"
    checks.append({"label": "Resultado de cobertura", "estado": _cob_estado,
                   "detalle": _label_cobertura(d) if d else "pendiente de datos", "demo": False})
    for it in checklist_documentos(caso)["docs"]:  # M1: los adjuntos reales del caso alimentan el checklist
        if it["presente"] is True:                 # hay un adjunto que lo satisface → ✔ real (cuenta al %)
            checks.append({"label": it["doc"], "estado": "ok", "detalle": "adjuntado", "demo": False})
        elif it["presente"] is False:              # el caso trae adjuntos, pero este no → honesto, sin badge demo
            checks.append({"label": it["doc"], "estado": "na", "detalle": "no adjuntado", "demo": False})
        else:                                       # el caso aún no trae adjuntos → no se puede validar (demo)
            checks.append({"label": it["doc"], "estado": "na", "detalle": "pendiente de validar", "demo": True})
    evaluables = [c for c in checks if c["estado"] != "na"]
    oks = sum(1 for c in evaluables if c["estado"] == "ok")
    return {"pct": round(100 * oks / len(evaluables)) if evaluables else 0, "checks": checks}


def resumen_narrativo(caso) -> str:
    """W4 · Resumen ejecutivo en PROSA, compuesto DETERMINÍSTICAMENTE desde los datos (no LLM libre).
    P1: sin `PALABRAS_PROHIBIDAS` (fail-closed a neutro). P7: nombra lo ausente, no lo inventa.
    """
    aseg = asegurado_de(caso)
    cl = clasificar(caso)
    tipo = cl["tipo_humano"].lower() if cl["tipo"] != "—" else "un siniestro"   # L2: tipo humano, no el enum
    # P5 defensa en profundidad: el view-model devuelve prosa YA redactada (no depender solo del |redact
    # del template). `_red` es no-op para el nombre demo, pero blinda el path real (M2) y el monto.
    partes = [f"{_red(aseg['nombre'])} reportó {tipo} ({cl['producto']})."]
    m = _campo(caso, "monto_reclamado")
    if m and not m.ausente and m.valor:
        partes.append(f"Valor de la reclamación: {_red(str(m.valor))}.")
    if caso.dictamen:  # P2: el resumen CITA el veredicto del motor (resultado + regla)
        partes.append(f"Cobertura: {_label_cobertura(caso.dictamen)} (regla {caso.dictamen.regla_aplicada}).")
    if caso.alerta_fraude:
        partes.append(f"Hay una señal de riesgo ({caso.alerta_fraude.severidad}) para revisar.")
    falt = faltantes(caso)
    if falt:
        partes.append("Falta: " + ", ".join(_LABEL_CAMPO.get(f, f).lower() for f in falt) + ".")
    texto = " ".join(partes)
    if any(p in texto.lower() for p in PALABRAS_PROHIBIDAS):  # P1 fail-closed
        return "Resumen no disponible; revisa el caso y decide (P1)."
    return texto


# ============================================================================
# W17 · Panel "Información Extraída" — dato · confianza · FUENTE (reales + ricos mock)
# ============================================================================

@dataclass(frozen=True)
class CampoUI:
    """DTO de un campo para el panel del copiloto. Interfaz ESTABLE que M2 llenará con datos reales (DIP).

    `origen="real"` ⟺ lo produjo un agente real (está en `extraccion.campos`); su confianza se muestra tal
    cual (aunque sea baja). `origen="demo"` = campo rico que aún no producimos (rotulado, P7).
    """
    label: str
    valor: str | None
    confianza: float | None
    fuente: str
    origen: Literal["real", "demo"]
    clase: str = "extraido"  # extraido | validado | relacionado (conexión W11)
    ausente: bool = False    # True ⇒ campo requerido aún no presente (fila REQUERIDO en la tabla fusionada)


# Nombre técnico del campo → etiqueta humana del panel. Los campos ricos de M2 (vehiculo/lugar/telefono/
# cédula/lesionados) mapean a las MISMAS etiquetas que los demos de `_CAMPOS_RICOS`, así un real desplaza al mock.
_LABEL_CAMPO = {
    "numero_poliza": "Póliza", "fecha_siniestro": "Fecha del evento",
    "tipo_siniestro": "Tipo de siniestro", "monto_reclamado": "Valor de la reclamación",
    "asegurado_nombre": "Asegurado", "placa": "Placa",
    "vehiculo": "Vehículo", "lugar": "Lugar", "telefono": "Teléfono",
    "asegurado_cedula": "Cédula", "lesionados": "Lesionados",
}


def label_campo(nombre: str) -> str:
    """Etiqueta humana de un campo — FUENTE ÚNICA (la comparten la Workbench y el panel vía filtro Jinja,
    para que un mismo campo se llame igual en todas las superficies)."""
    return _LABEL_CAMPO.get(nombre, nombre.replace("_", " ").capitalize())


# Estado del caso → etiqueta humana. FUENTE ÚNICA (Workbench y panel dicen lo mismo de cada estado).
_ESTADO_LABEL = {
    "LISTO_PARA_APROBAR": "Listo para firmar", "REQUIERE_REVISION": "Necesita revisión",
    "APROBADO": "Aprobado", "RECHAZADO": "Rechazado", "RECIBIDO": "Recibido",
    "EN_PROCESO": "En proceso", "EN_REVISION": "En revisión",
}


def label_estado(estado) -> str:
    """Etiqueta humana de un estado (fuente única compartida vía filtro Jinja)."""
    v = estado.value if hasattr(estado, "value") else estado
    return _ESTADO_LABEL.get(v, str(v).replace("_", " ").capitalize())


def label_cobertura(valor) -> str:
    """Etiqueta humana de un resultado de cobertura (fuente única; usa `_COBERTURA_LABEL`, definido abajo)."""
    v = valor.value if hasattr(valor, "value") else valor
    return _COBERTURA_LABEL.get(v, v)
# Tipo de evidencia → fuente legible (P3: cada dato dice de dónde viene).
_FUENTE_LEGIBLE = {
    TipoOrigen.SPAN: "Correo", TipoOrigen.PAGINA: "PDF", TipoOrigen.REGION: "Imagen",
    TipoOrigen.HUMANO: "Corrección humana",
}


def _fuente_de(origen) -> str:
    """Fuente legible de un `EvidenciaOrigen` real (no inventa; default al tipo crudo)."""
    if origen is None:
        return "—"
    base = _FUENTE_LEGIBLE.get(origen.tipo, str(getattr(origen.tipo, "value", origen.tipo)))
    ref = (getattr(origen, "referencia", "") or "").strip()
    return f"{base} · {ref}" if (origen.tipo == TipoOrigen.PAGINA and ref) else base


# Campos ricos que AÚN NO producimos → mock rotulado hasta M2. (label, fuente_demo, confianza_demo, generador).
_DEMO_LUGAR = ["Autopista Norte con Calle 153, Bogotá", "Carrera 7 con Calle 80, Bogotá", "Calle 26 con Cra 68, Bogotá"]
_DEMO_VEHICULO = ["Mazda CX-5 2021", "Chevrolet Onix 2022", "Renault Duster 2020", "Kia Sportage 2023"]
_DEMO_PLACA = ["ABC123", "XYZ789", "DEF456", "GHI321"]
_DEMO_TELEFONO = ["310 555 8899", "300 111 2233", "320 444 5566", "315 777 8899"]


def _demo_pick(caso, pool: list) -> str:
    return pool[sum(ord(c) for c in caso.id) % len(pool)]


_CAMPOS_RICOS = [  # (label, fuente, confianza, generador) — todos origen="demo" hasta M2
    ("Asegurado", "Correo", 0.99, lambda c: asegurado_de(c)["nombre"]),
    ("Vehículo", "SOAT", 0.98, lambda c: _demo_pick(c, _DEMO_VEHICULO)),
    ("Placa", "Fotos", 0.99, lambda c: _demo_pick(c, _DEMO_PLACA)),
    ("Lugar", "Denuncia", 0.95, lambda c: _demo_pick(c, _DEMO_LUGAR)),
    ("Teléfono", "Correo", 0.99, lambda c: _demo_pick(c, _DEMO_TELEFONO)),
]


def campos_extraidos(caso) -> list[CampoUI]:
    """W17 · Los campos del copiloto: **reales primero** (del extractor, con su confianza/fuente VERDADERAS),
    luego los ricos **mock** rotulados. Sin dedup por label (un real desplaza al demo del mismo label). P5:
    valores redactados. 🔴 Blindaje agéntico: lo real es real; el mock es solo el dato que aún no producimos.
    """
    overlay = {c.campo_nombre: c for c in (getattr(caso, "correlaciones", None) or [])}  # M3
    reales: list[CampoUI] = []
    labels_reales: set[str] = set()
    if caso.extraccion:
        for c in caso.extraccion.campos:
            if c.ausente or c.valor is None:
                continue
            label = _LABEL_CAMPO.get(c.nombre, c.nombre.replace("_", " ").capitalize())
            if label in labels_reales:  # dos reales con el mismo label → no duplicar (raro, pero robusto)
                continue
            # M3: si hay correlación cross-fuente, la confianza consolidada y la clase la manda el overlay
            # (coincide → 'validado' por varias fuentes; diverge → queda 'extraido' y el riesgo va a W5).
            corr = overlay.get(c.nombre)
            confianza = corr.confianza_ajustada if corr else c.confianza
            clase = "validado" if (corr and corr.coincide) else "extraido"
            # L2: el Tipo se muestra humano ("Colisión vehicular"); el valor del dato sigue siendo el enum (P2).
            valor = _tipo_humano(c.valor) if c.nombre == "tipo_siniestro" else _valor_operador(c.valor)
            reales.append(CampoUI(label=label, valor=valor, confianza=confianza,
                                  fuente=_fuente_de(c.origen), origen="real", clase=clase))
            labels_reales.add(label)
    demo = [CampoUI(label=lbl, valor=_valor_operador(gen(caso)), confianza=conf, fuente=fte, origen="demo")
            for (lbl, fte, conf, gen) in _CAMPOS_RICOS if lbl not in labels_reales]
    return reales + demo


def datos_principales(caso) -> list[CampoUI]:
    """Tabla ÚNICA de los datos del caso (Fase 0: fusiona 'Datos del siniestro' + 'Información extraída', antes
    duplicadas en dos columnas): campos presentes (ricos, con confianza·fuente) PRIMERO, luego los FALTANTES
    marcados REQUERIDO. Un solo lugar donde el operador lee los datos. Passive."""
    presentes = campos_extraidos(caso)
    labels_presentes = {c.label for c in presentes}
    faltan = [CampoUI(label=_LABEL_CAMPO.get(n, n.replace("_", " ").capitalize()),
                      valor=None, confianza=None, fuente="—", origen="real", ausente=True)
              for n in faltantes(caso)
              if _LABEL_CAMPO.get(n, n.replace("_", " ").capitalize()) not in labels_presentes]
    return presentes + faltan


def campos_corregibles(caso) -> list[dict]:
    """Los 4 campos base editables para la corrección inline (Fase 2), con su valor actual (o '' si ausente).
    El motor los re-dictamina en el servidor (P2); aquí solo se pre-llena el form. Passive."""
    base = {c.nombre: c for c in caso.extraccion.campos} if caso.extraccion else {}
    corregibles = []
    for n in CAMPOS:
        c = base.get(n)
        # P5 defensa en profundidad: se redacta en el boundary (además del |redact del template).
        corregibles.append({"nombre": n, "label": _LABEL_CAMPO.get(n, n),
                            "valor": _red(c.valor) if (c and not c.ausente and c.valor) else ""})
    return corregibles


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
        {"label": "Verificación", "valor": f"{verif['confianza']:.2f}" if verif["disponible"] else "No disponible", "nivel": verif["nivel"]},
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
    return _COBERTURA_LABEL.get(d.resultado.value, d.resultado.value) if d else "No disponible"


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

def _accion_primaria(caso, faltantes) -> dict | None:
    """L1 · La ÚNICA acción primaria por estado (recomendación == acción). 🔒P1: solo Radicar alcanza terminal
    (con firma); en estado bloqueado la primaria NO es terminal (solicitar / enviar a revisión). None = sin
    primaria (caso resuelto). {label, endpoint, kind, confirm, motivo}."""
    est = caso.estado
    if est in _TERMINALES:
        return None
    if est == EstadoCaso.REQUIERE_REVISION:
        if faltantes:
            return {"label": "Solicitar al asegurado", "endpoint": "solicitar_docs", "kind": "primary",
                    "confirm": None, "motivo": None}
        return {"label": "Enviar a revisión especializada", "endpoint": "escalar", "kind": "primary",
                "confirm": "¿Enviar a revisión especializada?", "motivo": "Enviado a revisión especializada"}
    if est == EstadoCaso.LISTO_PARA_APROBAR:   # explícito: Radicar SOLO aquí (un estado nuevo → sin primaria)
        return {"label": "Radicar caso", "endpoint": "radicar", "kind": "go",
                "confirm": "¿Radicar este caso? Se creará el expediente con tu firma.", "motivo": None}
    return None


def recomendacion(caso) -> dict:
    """Próximo paso del HUMANO. NUNCA decide (P1): no contiene PALABRAS_PROHIBIDAS ni estado terminal.
    Incluye `accion`: la ÚNICA acción primaria del estado (L1: recomendación == acción)."""
    faltantes = _faltantes(caso)
    est = caso.estado  # var local: comparación de enum sin el patrón de mutación (passive)
    if est in _TERMINALES:
        quien = f" por {_red(caso.aprobado_por)}" if getattr(caso, "aprobado_por", None) else ""  # P5: redacta en el boundary
        rec = {"icono": "🔒", "titulo": "Caso resuelto", "texto": f"Decisión humana registrada{quien}.", "tono": "neutral"}
    elif est == EstadoCaso.REQUIERE_REVISION:
        if faltantes:
            n = len(faltantes)
            humanos = [_LABEL_CAMPO.get(f, f).lower() for f in faltantes]   # L2: nombres humanos, no crudos
            if n == 1:
                titulo = f"Falta un dato: {humanos[0]}"   # neutral de género (sirve para monto/fecha/…)
                texto = ("Este dato no se encontró en el correo ni en los documentos. Solicítalo al "
                         "asegurado o ingrésalo abajo si ya lo conoces.")
            else:
                titulo = f"Faltan {n} datos para evaluar el caso"
                texto = (f"No se encontraron: {', '.join(humanos)}. Solicítalos al asegurado o ingrésalos abajo.")
            rec = {"icono": "📝", "titulo": titulo, "texto": texto, "tono": "warn"}
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
    # P1 fail-closed: si por algún cambio se colara una palabra de decisión, se degrada a texto neutro Y se
    # anula la acción primaria (que decida el humano a mano, sin un botón que no case con el texto degradado).
    degradado = any(p in rec["texto"].lower() or p in rec["titulo"].lower() for p in PALABRAS_PROHIBIDAS)
    if degradado:
        rec = {"icono": "🧑‍⚖️", "titulo": "Decisión humana requerida", "texto": "Revisa el caso y decide (P1).", "tono": "neutral"}
    rec["accion"] = None if degradado else _accion_primaria(caso, faltantes)  # L1: la única primaria del estado
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
            "label": "Coincidencia entre fuentes",
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
            "label": "Resultado de cobertura",
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
        nodo = (ev.get("nodo") or "").strip() or "desconocido"
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


# ---------------------------------------------------- W3 · Timeline visual de la IA

def conteo_adjuntos(caso) -> dict:
    """Conteo de adjuntos leídos por la IA. Interfaz {pdfs, fotos, origen}. Si el caso trae adjuntos REALES
    (M1) → conteo real (origen='real'); si no, mock determinístico por caso (origen='demo', P7)."""
    adjuntos = caso.adjuntos  # M1: siempre lista (default_factory); vacía ⇒ mock
    if adjuntos:
        return {"pdfs": sum(1 for a in adjuntos if a.tipo == "pdf"),
                "fotos": sum(1 for a in adjuntos if a.tipo == "foto"),
                "origen": "real"}
    h = sum(ord(c) for c in caso.id)
    return {"pdfs": 1 + h % 4, "fotos": 2 + h % 8, "origen": "demo"}


def timeline(caso, traza) -> list[dict]:
    """Timeline agent-native (W18): correo → docs (mock rotulado) → pasos de AGENTES (de la traza) → estado.
    Passive (P7): los pasos de agentes salen de la traza REAL (nunca se fabrican); los conteos van rotulados
    `demo` y distintos. P4: lee la traza sin re-ejecutar agentes; sin traza, no hay pasos de agente."""
    docs = conteo_adjuntos(caso)
    demo = docs["origen"] == "demo"
    pasos = [
        {"icono": "📬", "texto": "Correo recibido", "estado": "ok", "demo": False},
        {"icono": "📄", "texto": f"Leyó {docs['pdfs']} PDF(s)", "estado": "ok", "demo": demo},
        {"icono": "📷", "texto": f"Leyó {docs['fotos']} fotografía(s)", "estado": "ok", "demo": demo},
    ]
    for ev in actividad_agentes(traza):  # 🔴 pasos de AGENTES: SOLO de la traza real (nunca fabricados)
        pasos.append({"icono": ev["icono"], "texto": ev["etiqueta"],
                      "detalle": ev.get("resultado", ""), "tokens": ev.get("tokens", 0),
                      "hora": ev.get("hora", ""), "estado": "bad" if ev.get("error") else "ok", "demo": False})
    _final = {"LISTO_PARA_APROBAR": ("✅", "Caso listo", "ok"),
              "REQUIERE_REVISION": ("⚠️", "Escalado a revisión humana", "warn"),
              "APROBADO": ("🔒", "Caso aprobado por humano", "ok"),
              "RECHAZADO": ("🔒", "Caso rechazado por humano", "bad")}.get(caso.estado.value)
    if _final:
        pasos.append({"icono": _final[0], "texto": _final[1], "estado": _final[2], "demo": False})
    return pasos
