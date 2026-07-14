"""app/llm/summary.py — Analista del caso (interno: W19 Summary). Redacta un ANÁLISIS del caso con LLM.

A diferencia de un narrador, recibe TODA la info del caso (extracción, faltantes, póliza, veredicto del
motor con su regla/cláusula, señal de fraude con su porqué, adjuntos) y produce, en lenguaje de OPERADOR,
qué pasó · qué revisar · dónde quedó y por qué. Usa un modelo capaz (Sonnet), no el de extracción.

🔒 P1/P2: describe, NO decide. Guard fail-closed (sin `PALABRAS_PROHIBIDAS`; no afirma un veredicto de
cobertura distinto al del motor). Si el guard falla, el LLM no está disponible, o revienta → **fallback** a
la plantilla determinística de W4 (`resumen_narrativo`). Nunca error, nunca invención.

🔒 P5: el prompt se arma de **campos estructurados YA REDACTADOS**, NUNCA del `texto_crudo` del correo.
Mockeable/hermético: sin key real (o key de test) usa el fallback → los tests no tocan red.
"""

import logging
import re

from app.config import settings
from app.contracts.enums import ResultadoCobertura
from app.security.redaction import redact_pii_spans_es_co

logger = logging.getLogger(__name__)

_MAX_TOKENS = 500
# Etiquetas de cobertura que, si aparecen en la narrativa, DEBEN coincidir con el veredicto del motor (P2).
# ORDEN: de más específica a menos (la primera que matchea manda) + límites de palabra, para que "cubierto"
# NO haga falso match dentro de "no cubierto"/"cubierto parcial".
_COBERTURA_PATRONES = [
    (re.compile(r"\bno\s+cubierto\b"), ResultadoCobertura.NO_CUBIERTO),
    (re.compile(r"\bcubierto\s+parcial\b"), ResultadoCobertura.CUBIERTO_PARCIAL),
    (re.compile(r"\bcubierto\b"), ResultadoCobertura.CUBIERTO),
]


def _llm_disponible() -> bool:
    """Hay LLM real usable (no en tests herméticos, que usan key='test')."""
    key = settings.anthropic_api_key
    return bool(key) and key != "test"


def _campo(caso, nombre: str):
    if not caso.extraccion:
        return None
    return next((c for c in caso.extraccion.campos if c.nombre == nombre and not c.ausente and c.valor), None)


def _faltantes(caso) -> str:
    """Campos que el aviso NO trajo (para que el analista diga EN CONCRETO qué revisar)."""
    if not caso.extraccion:
        return "todos (no se pudo leer el aviso)"
    faltan = [c.nombre for c in caso.extraccion.campos if c.ausente]
    return ", ".join(faltan) if faltan else "ninguno"


def _dictamen_detalle(caso) -> str:
    """Veredicto del motor CON su regla y cláusula citada (P2: el analista lo cita, no lo inventa)."""
    d = caso.dictamen
    if not d:
        return "aún sin dictaminar"
    detalle = f"{d.resultado.value} (regla {d.regla_aplicada}"
    if d.clausula:
        detalle += f", cláusula {d.clausula.referencia}: {d.clausula.texto}"
    detalle += ")"
    if d.cobertura_aplicada:
        detalle += f"; cobertura aplicada: {d.cobertura_aplicada}"
    return detalle


def _fraude_detalle(caso) -> str:
    """Señal de fraude con su EXPLICACIÓN (el porqué), redactada (P5). Informativa: solo sugiere (P6)."""
    a = caso.alerta_fraude
    if not a:
        return "sin señales"
    return f"severidad {a.severidad} — {redact_pii_spans_es_co(a.explicacion)}"


def _docs_detalle(caso) -> str:
    """Qué documentos trajo el correo (conteo por tipo), o que no trajo ninguno (P7)."""
    adjuntos = getattr(caso, "adjuntos", None) or []
    if not adjuntos:
        return "el correo no trajo adjuntos"
    por_tipo: dict[str, int] = {}
    for a in adjuntos:
        por_tipo[a.tipo] = por_tipo.get(a.tipo, 0) + 1
    return ", ".join(f"{n} {tipo}" for tipo, n in por_tipo.items())


def construir_prompt(caso) -> str:
    """Prompt del Analista del caso: arma TODA la info del caso (ya REDACTADA, P5) para un análisis
    orientado a la decisión del operador. No incluye `texto_crudo`; los valores van redactados."""
    def val(nombre):
        c = _campo(caso, nombre)
        return redact_pii_spans_es_co(str(c.valor)) if c else "no disponible"

    poliza_estado = "encontrada" if (caso.poliza_match and caso.poliza_match.encontrada) else "NO encontrada"
    return (
        "Eres un analista senior de siniestros. Escribes para el OPERADOR que va a REVISAR y FIRMAR el caso.\n"
        "Tu trabajo: leer TODO lo que produjo el análisis y entregarle, en 3-4 frases, un resumen CLARO que le "
        "permita decidir en segundos. Español natural de siniestros. PROHIBIDO: jerga técnica, nombres de "
        "agentes/modelos, números sueltos sin significado (p.ej. 'confianza 0.6').\n"
        "🔒 REGLAS DURAS: DESCRIBE, no decidas — no apruebes, no rechaces, no afirmes una cobertura por tu "
        "cuenta. La cobertura la decide el motor de reglas: cítala EXACTA, no la inventes ni la contradigas.\n\n"
        "Estructura tu prosa así: (1) qué pasó (tipo, monto, en una frase); (2) qué debe REVISAR el operador "
        "— lo que falta o no cuadra, EN CONCRETO — o di que no hay pendientes; (3) dónde quedó el caso y POR "
        "QUÉ, citando la regla del motor.\n\n"
        "INFORMACIÓN DEL CASO (ya anonimizada):\n"
        f"- Tipo de siniestro: {val('tipo_siniestro')}\n"
        f"- Fecha del siniestro: {val('fecha_siniestro')}\n"
        f"- Monto reclamado: {val('monto_reclamado')}\n"
        f"- Póliza: {val('numero_poliza')} ({poliza_estado})\n"
        f"- Datos que FALTAN en el aviso: {_faltantes(caso)}\n"
        f"- Veredicto del motor de cobertura: {_dictamen_detalle(caso)}\n"
        f"- Señal de fraude/riesgo: {_fraude_detalle(caso)}\n"
        f"- Documentos adjuntos: {_docs_detalle(caso)}\n\n"
        "Devuelve SOLO el análisis en prosa, sin viñetas ni encabezados."
    )


def _guard_ok(texto: str, caso) -> bool:
    """🔒 P1/P2 fail-closed: la narrativa no decide ni contradice al motor."""
    from app.dashboard.vista_caso import PALABRAS_PROHIBIDAS  # lazy: evita ciclo de import
    low = texto.lower()
    if any(p in low for p in PALABRAS_PROHIBIDAS):
        return False
    # Si menciona una etiqueta de cobertura, DEBE ser la del motor (no inventar/contradecir, P2).
    # La primera (más específica) que matchea determina el veredicto afirmado; si no es el del motor → rechaza.
    resultado = caso.dictamen.resultado if caso.dictamen else None
    for patron, esperado in _COBERTURA_PATRONES:
        if patron.search(low):
            return resultado == esperado
    return True


def _llm_redacta(caso) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=settings.anthropic_api_key)
    resp = client.messages.create(
        # Análisis/síntesis → modelo capaz (Sonnet), no el barato de extracción. El Analista es el que le
        # habla al operador; aquí SÍ se le da protagonismo al LLM (dentro del guard P1/P2).
        model=settings.verifier_model, max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": construir_prompt(caso)}],
    )
    return next((b.text for b in resp.content if hasattr(b, "text")), "") or ""


def call_summary_agent(caso) -> tuple[str, str]:
    """Redacta la historia. Devuelve (texto, origen) con origen ∈ {"agente","base"} (P7: se rotula cuál).

    Fail-closed: sin LLM disponible / guard falla / excepción → fallback determinístico W4 (origen="base").
    """
    from app.dashboard.vista_caso import resumen_narrativo  # lazy: fallback (W4)
    if _llm_disponible():
        try:
            texto = redact_pii_spans_es_co(_llm_redacta(caso).strip())  # P5 también en la salida
            if texto and _guard_ok(texto, caso):
                return texto, "agente"
            logger.info("Summary Agent: guard/salida no válida → fallback determinístico (W4).")
        except Exception as e:
            logger.warning("Summary Agent falló (%s) → fallback W4.", type(e).__name__)
    return resumen_narrativo(caso), "base"
