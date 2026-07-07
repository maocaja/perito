"""Redactores PII deny-by-default (PATTERN-U1-01, P5).

Dos componentes:
1. PIIRedactingLogSerializer — redacta logs estructurados (JSON)
2. LLMPayloadBuilder — construye prompts al LLM redactando PII

Regla: Un campo marcado PII (vía pii.py) se redacta SALVO whitelist explícita.
"""

from typing import Any, TypeVar

from app.contracts.pii import pii_fields


T = TypeVar("T")


class PIIRedactingLogSerializer:
    """Serializa eventos estructurados redactando PII por defecto.

    Uso: antes de escribir logs, pasar el evento por este serializador.
    Redacta automáticamente campos marcados con PII.

    Ejemplo:
        serializer = PIIRedactingLogSerializer()
        event = {"usuario_id": "u123", "texto_crudo": "Juan Pérez, cédula 12345..."}
        safe_event = serializer.redact(event, AvisoNormalizado)
        # Retorna: {"usuario_id": "u123", "texto_crudo": "[REDACTED]"}
    """

    REDACTION_MARKER = "[REDACTED]"

    def redact(self, data: dict[str, Any], model: type[T], whitelist: set[str] | None = None) -> dict[str, Any]:
        """Redacta campos PII en un dict según modelo.

        Args:
            data: diccionario con datos a redactar
            model: modelo Pydantic con marcas PII
            whitelist: campos PII que SÍ se permiten (vacío por defecto = deny-by-default)

        Returns:
            dict con campos PII redactados (salvo whitelist)
        """
        whitelist = whitelist or set()
        pii_field_names = pii_fields(model)
        redacted = data.copy()

        for field_name in pii_field_names:
            if field_name not in whitelist and field_name in redacted:
                redacted[field_name] = self.REDACTION_MARKER

        return redacted


class LLMPayloadBuilder:
    """Construye payloads al LLM redactando PII deny-by-default (PATTERN-U1-01).

    El LLM nunca debe ver PII a menos que la tarea lo requiera explícitamente.
    Cada caso de uso define su whitelist (qué campos PII permiten).

    Ejemplo:
        builder = LLMPayloadBuilder()
        caso = Caso(...)
        # Sin whitelist: LLM no ve PII
        payload = builder.build_extraction_prompt(caso)
        # Con whitelist: LLM ve solo los campos explícitos
        payload = builder.build_extraction_prompt(caso, whitelist={"usuario_id"})
    """

    def __init__(self):
        """Inicializa builder con redactor de logs."""
        self.serializer = PIIRedactingLogSerializer()

    def build_extraction_prompt(
        self,
        aviso: Any,  # AvisoNormalizado
        whitelist: set[str] | None = None,
    ) -> str:
        """Construye prompt de extracción redactando texto_crudo por defecto.

        Args:
            aviso: AvisoNormalizado para extraer
            whitelist: campos de AvisoNormalizado que SÍ se envían al LLM

        Returns:
            Prompt seguro para enviar al LLM
        """
        from app.contracts.extraccion import AvisoNormalizado

        # Redactar: deny-by-default, whitelist vacía = solo "[REDACTED]" en PII
        safe_aviso = self.serializer.redact(
            {"texto_crudo": aviso.texto_crudo, "calidad": aviso.calidad.value},
            AvisoNormalizado,
            whitelist=whitelist or set(),
        )

        prompt = (
            f"Extrae campos del aviso (solo datos públicos):\n"
            f"Calidad: {safe_aviso.get('calidad')}\n"
            f"Texto: {safe_aviso.get('texto_crudo')}\n\n"
            f"Campos esperados: números de póliza, montos, fechas, tipos de siniestro."
        )

        return prompt

    def build_fraud_detection_prompt(
        self,
        caso: Any,  # Caso
        whitelist: set[str] | None = None,
    ) -> str:
        """Construye prompt de detección de fraude redactando PII.

        Args:
            caso: Caso para analizar
            whitelist: campos que SÍ se envían (empty = deny-by-default)

        Returns:
            Prompt seguro para detección de fraude
        """
        # Fraude no necesita PII — deny-by-default total
        prompt = (
            f"Analiza inconsistencias en el caso (no necesitas PII):\n"
            f"Campos extraídos: {caso.extraccion is not None}\n"
            f"Póliza encontrada: {caso.poliza_match is not None}\n"
            f"Dictamen generado: {caso.dictamen is not None}\n\n"
            f"Busca: fechas inconsistentes, montos fuera de límites, "
            f"cobertura no contratada, exclusiones aplicables."
        )

        return prompt
