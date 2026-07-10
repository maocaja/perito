"""app/dashboard/copiloto.py — copiloto conversacional contextual (W15). **MOCK rotulado**.

P7 (clave): es un MOCK — respuestas guionadas sobre datos REALES del caso donde se puede (dictamen, faltantes,
riesgos). La UI lo rotula "Demo"; ni el código ni el demo lo presentan como IA funcional. Interfaz estable
`responder(pregunta, caso)` lista para conectar un backend real (mejora futura). P1/P6: solo EXPLICA — no
decide, no aprueba, no ejecuta acciones. P5: la respuesta se redacta.
"""

from app.dashboard.vista_caso import faltantes
from app.security.redaction import redact_pii_spans_es_co


def responder(pregunta: str, caso) -> str:
    """Responde una pregunta sobre ESTE caso (mock guionado + datos reales). Solo explica (P1/P6). Redactada.

    Nota (mock): el enrutado por palabras clave es una aproximación de demo; el backend real usaría un LLM con
    intención. Interfaz estable para el swap (DIP)."""
    p = (pregunta or "").strip().lower()
    if not p:
        respuesta = "Escríbeme una pregunta sobre este caso (campos, cobertura, riesgos o documentos faltantes)."
    elif "licencia" in p:
        respuesta = ("Encontré la licencia del vehículo, pero no la licencia del conductor; por eso el checklist "
                     "la marca pendiente. Puedes solicitarla con la acción “Solicitar documentos”.")
    elif "cobertura" in p or "cubierto" in p or "deducible" in p:
        if caso.dictamen:
            respuesta = (f"El motor determinístico dictaminó “{caso.dictamen.resultado.value}” con la regla "
                         f"{caso.dictamen.regla_aplicada}. La cobertura la decide el motor, no el LLM (P2).")
        else:
            respuesta = "Aún no hay dictamen de cobertura para este caso (faltan datos o la póliza)."
    elif "riesgo" in p or "fraude" in p or "inconsist" in p:
        if caso.alerta_fraude:
            respuesta = (f"Hay una señal de riesgo {caso.alerta_fraude.severidad}. Es una sugerencia para "
                         "revisar, no un veredicto — la decisión es tuya (P1/P6).")
        else:
            respuesta = "No detecté señales de riesgo en este caso."
    elif "falta" in p or "pendiente" in p or "documento" in p:
        falt = faltantes(caso)
        respuesta = ("Faltan estos datos: " + ", ".join(falt) + ".") if falt else \
                    "No faltan datos obligatorios; el caso está completo."
    else:
        respuesta = ("Puedo explicarte los campos extraídos, la cobertura, los riesgos o qué documentos faltan "
                     "de este caso. Prueba: “¿por qué falta la licencia?”.")
    return redact_pii_spans_es_co(respuesta)
