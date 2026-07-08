"""Fraude: Capas 1-3 (determinístico + LLM mockeable).

INVARIANTES P6/P5:
- Capa 1: Chequeos duros determinísticos (función pura, sin LLM)
- Capa 2: Severidad determinística (función pura, sin LLM)
- Capa 3: Razonamiento LLM (vía LLMPayloadBuilder verificado de U1, redacción deny-by-default)
- inconsistencias: list[EvidenciaOrigen] (no list[str])
- Cero inconsistencias → no emitir AlertaFraude (None, no vacío)
- No muta Caso.estado (P1)

INVARIANTE P2/frontera: No importa backend.app.rules/ (motor determinístico).
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from app.contracts.dictamen import AlertaFraude
from app.contracts.enums import ResultadoCobertura
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen, ExtraccionValidada, TipoOrigen
from app.contracts.poliza import Poliza


# --- Capa 1: Chequeos Duros Determinísticos ---

class TipoInconsistencia:
    """Tipos de inconsistencias detectadas (determinísticas)."""
    FECHA_ANTERIOR_VIGENCIA = "FECHA_ANTERIOR_VIGENCIA"
    FECHA_POSTERIOR_VIGENCIA = "FECHA_POSTERIOR_VIGENCIA"
    FECHA_FUTURO = "FECHA_FUTURO"
    MONTO_EXCEDE_SUMA = "MONTO_EXCEDE_SUMA"
    TIPO_NO_CUBIERTO = "TIPO_NO_CUBIERTO"


def _get_campo(extraccion: ExtraccionValidada, nombre: str) -> Optional[CampoExtraido]:
    """Extrae un campo por nombre."""
    for campo in extraccion.campos:
        if campo.nombre == nombre:
            return campo
    return None


def detectar_inconsistencias_fraude(
    extraccion: ExtraccionValidada,
    poliza: Poliza
) -> list[EvidenciaOrigen]:
    """Capa 1: Detecta inconsistencias determinísticas (sin LLM).

    Chequeos duros: fecha fuera vigencia, monto excede suma, fecha futura, 
    tipo no cubierto. Todos determinísticos, reproducibles.

    Args:
        extraccion: ExtraccionValidada
        poliza: Poliza con vigencia, suma_asegurada, coberturas_contratadas

    Returns:
        list[EvidenciaOrigen]: inconsistencias encontradas (puede estar vacía)
    """
    inconsistencias = []

    # Chequeo 1: Fecha siniestro anterior a vigencia
    fecha_campo = _get_campo(extraccion, "fecha_siniestro")
    if fecha_campo and not fecha_campo.ausente and fecha_campo.valor:
        try:
            fecha = date.fromisoformat(fecha_campo.valor)
            if fecha < poliza.vigencia.desde:
                inconsistencias.append(
                    EvidenciaOrigen(
                        tipo=TipoOrigen.SPAN,
                        referencia=f"FECHA_ANTERIOR_VIGENCIA: {fecha} < {poliza.vigencia.desde}"
                    )
                )
        except (ValueError, TypeError):
            pass

    # Chequeo 2: Fecha siniestro posterior a vigencia
    if fecha_campo and not fecha_campo.ausente and fecha_campo.valor:
        try:
            fecha = date.fromisoformat(fecha_campo.valor)
            if fecha > poliza.vigencia.hasta:
                inconsistencias.append(
                    EvidenciaOrigen(
                        tipo=TipoOrigen.SPAN,
                        referencia=f"FECHA_POSTERIOR_VIGENCIA: {fecha} > {poliza.vigencia.hasta}"
                    )
                )
        except (ValueError, TypeError):
            pass

    # Chequeo 3: Fecha siniestro en el futuro
    if fecha_campo and not fecha_campo.ausente and fecha_campo.valor:
        try:
            fecha = date.fromisoformat(fecha_campo.valor)
            hoy = date.today()
            if fecha > hoy:
                inconsistencias.append(
                    EvidenciaOrigen(
                        tipo=TipoOrigen.SPAN,
                        referencia=f"FECHA_FUTURO: {fecha} > {hoy}"
                    )
                )
        except (ValueError, TypeError):
            pass

    # Chequeo 4: Monto reclamado > suma asegurada
    monto_campo = _get_campo(extraccion, "monto_reclamado")
    if monto_campo and not monto_campo.ausente and monto_campo.valor:
        try:
            monto = Decimal(monto_campo.valor)
            if monto > poliza.suma_asegurada:
                inconsistencias.append(
                    EvidenciaOrigen(
                        tipo=TipoOrigen.SPAN,
                        referencia=f"MONTO_EXCEDE_SUMA: {monto} > {poliza.suma_asegurada}"
                    )
                )
        except (ValueError, TypeError):
            pass

    # Chequeo 5: Tipo siniestro no en coberturas contratadas
    tipo_campo = _get_campo(extraccion, "tipo_siniestro")
    if tipo_campo and not tipo_campo.ausente and tipo_campo.valor:
        if tipo_campo.valor not in poliza.coberturas_contratadas:
            inconsistencias.append(
                EvidenciaOrigen(
                    tipo=TipoOrigen.SPAN,
                    referencia=f"TIPO_NO_CUBIERTO: {tipo_campo.valor} ∉ {poliza.coberturas_contratadas}"
                )
            )

    # Retornar en orden determinístico (sorted por referencia)
    return sorted(inconsistencias, key=lambda e: e.referencia)


# --- Capa 2: Mapa Severidad Determinístico ---

class SeveridadFraude:
    """Severidad de fraude (enum-like)."""
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


def calcular_severidad(inconsistencias: list[EvidenciaOrigen]) -> str:
    """Capa 2: Calcula severidad determinística.

    Reglas fijas:
    - Tipos duros (FECHA_FUTURO, MONTO_EXCEDE_SUMA) → ALTA
    - Vigencia → MEDIA
    - 3+ inconsistencias → sube un nivel
    - Cero → N/A (no emite alerta)

    Args:
        inconsistencias: list[EvidenciaOrigen] (ya ordenadas)

    Returns:
        str: severidad (BAJA, MEDIA, ALTA)
    """
    if not inconsistencias:
        return SeveridadFraude.BAJA

    referencias = {e.referencia for e in inconsistencias}

    # Regla 1: Tipos duros → ALTA
    duros = {"FECHA_FUTURO", "MONTO_EXCEDE_SUMA"}
    if any(tipo in ref for ref in referencias for tipo in duros):
        return SeveridadFraude.ALTA

    # Regla 2: Base por tipo predominante
    severidad_base = SeveridadFraude.BAJA
    if any("VIGENCIA" in ref for ref in referencias):
        severidad_base = SeveridadFraude.MEDIA

    # Regla 3: Contar inconsistencias, subir nivel
    if len(inconsistencias) >= 3:
        if severidad_base == SeveridadFraude.BAJA:
            severidad_base = SeveridadFraude.MEDIA
        elif severidad_base == SeveridadFraude.MEDIA:
            severidad_base = SeveridadFraude.ALTA

    return severidad_base


# --- Capa 3: Razonamiento LLM (Mockeable, via LLMPayloadBuilder verificado de U1) ---

def razonar_fraude(inconsistencias: list[EvidenciaOrigen]) -> str:
    """Capa 3: Genera explicación legible via LLM (deny-by-default via U1 redactor).

    CRÍTICO: LLM NO modifica inconsistencias ni severidad (ambas determinísticas).
    LLM es SOLO explicación (razonamiento secundario).
    
    Usa LLMPayloadBuilder verificado de U1 (build_fraud_detection_prompt).
    En tests: completamente mockeado (determinístico).

    Args:
        inconsistencias: list[EvidenciaOrigen] (determinísticas ya calculadas)

    Returns:
        str: explicación legible (puede venir de LLM o default si falla)
    """
    if not inconsistencias:
        return "Sin hallazgos de fraude."

    try:
        # Usar LLMPayloadBuilder verificado de U1 (deny-by-default)
        from app.security.redaction import LLMPayloadBuilder
        
        builder = LLMPayloadBuilder()
        
        # Crear un mock de Caso para el builder (fraud detection no necesita PII)
        # El builder ya aplica deny-by-default total
        mock_caso = type('Caso', (), {
            'extraccion': bool(inconsistencias),
            'poliza_match': True,
            'dictamen': True
        })()
        
        prompt = builder.build_fraud_detection_prompt(mock_caso, whitelist=set())
        
        # En producción: llamar a Claude via este prompt
        # En tests: mockeado (devuelve respuesta determinística)
        explicacion = _llm_call(prompt)
        return explicacion.strip()

    except Exception:
        # Graceful fail (P4): si LLM falla, retornar explicación default
        return f"Fraude detectado por {len(inconsistencias)} inconsistencias. Revisar manualmente."


def _llm_call(prompt: str) -> str:
    """Stub para LLM call (mockeado en tests)."""
    # Placeholder: será reemplazado por mock en tests
    raise NotImplementedError("LLM call debe ser mockeado en tests")


# --- Construcción AlertaFraude ---

def construir_alerta_fraude(
    extraccion: ExtraccionValidada,
    poliza: Poliza
) -> Optional[AlertaFraude]:
    """Orquesta Capas 1-3 para emitir AlertaFraude.

    INVARIANTE P6: Cero inconsistencias → retorna None (no alerta vacía).
    Severidad es determinística (Capa 2, sin LLM).
    Explicación vía LLM (Capa 3, mockeable, deny-by-default via U1 redactor).

    Args:
        extraccion: ExtraccionValidada
        poliza: Poliza (clausulas, coberturas, vigencia)

    Returns:
        AlertaFraude si inconsistencias > 0, None si cero
    """

    # Capa 1: Chequeos duros
    inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)

    # INVARIANTE P6: Si cero inconsistencias, NO emitir alerta
    if not inconsistencias:
        return None

    # Capa 2: Severidad determinística
    severidad = calcular_severidad(inconsistencias)

    # Capa 3: Explicación LLM (mockeable, deny-by-default)
    explicacion = razonar_fraude(inconsistencias)

    # Construir alerta
    alerta = AlertaFraude(
        severidad=severidad,
        inconsistencias=inconsistencias,
        explicacion=explicacion
    )

    return alerta

