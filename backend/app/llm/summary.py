"""app/llm/summary.py — Summary Agent (W19). El 6º agente: redacta la HISTORIA del caso con LLM.

🔒 P1: describe, NO decide. Guard fail-closed (sin `PALABRAS_PROHIBIDAS`; no afirma un veredicto de cobertura
distinto al del motor). Si el guard falla, el LLM no está disponible, o revienta → **fallback** a la plantilla
determinística de W4 (`resumen_narrativo`). Nunca error, nunca invención.

🔒 P5: el prompt se arma de **campos estructurados YA REDACTADOS**, NUNCA del `texto_crudo` del correo.
Mockeable/hermético: sin key real (o key de test) usa el fallback → los tests no tocan red.
"""

import logging
import re

from app.config import settings
from app.contracts.enums import ResultadoCobertura
from app.security.redaction import redact_pii_spans_es_co

logger = logging.getLogger(__name__)

_MAX_TOKENS = 400
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


def construir_prompt(caso) -> str:
    """Arma el prompt del Summary Agent desde campos REDACTADOS (P5). No incluye `texto_crudo`."""
    def val(nombre):
        c = _campo(caso, nombre)
        return redact_pii_spans_es_co(str(c.valor)) if c else "no disponible"

    dictamen = caso.dictamen.resultado.value if caso.dictamen else "aún sin dictaminar"
    fraude = f"señal {caso.alerta_fraude.severidad}" if caso.alerta_fraude else "sin señales"
    return (
        "Eres un operador senior de siniestros. Redacta en 2-3 frases la HISTORIA del caso, en prosa clara y "
        "neutral, para que un compañero lo entienda en segundos. DESCRIBE, no decidas: no apruebes, no rechaces, "
        "no afirmes cobertura por tu cuenta. Datos (ya anonimizados):\n"
        f"- Tipo de siniestro: {val('tipo_siniestro')}\n"
        f"- Fecha: {val('fecha_siniestro')}\n"
        f"- Monto reclamado: {val('monto_reclamado')}\n"
        f"- Póliza: {val('numero_poliza')}\n"
        f"- Dictamen del motor (cítalo si lo mencionas): {dictamen}\n"
        f"- Riesgo/fraude: {fraude}\n"
        "Devuelve SOLO la narrativa, sin viñetas ni encabezados."
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
        model=settings.extractor_model, max_tokens=_MAX_TOKENS,
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
