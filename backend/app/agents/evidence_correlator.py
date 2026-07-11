"""app/agents/evidence_correlator.py — Evidence Correlator (M3). 🔒 P6.

El agente que cruza FUENTES dentro de un caso: el MISMO campo lógico (placa/fecha/nombre) visto desde el
correo, un PDF, una foto. Si las fuentes **coinciden** → sube la confianza; si **divergen** → emite una
inconsistencia "míralo" citando ambas fuentes. Determinístico detecta; el LLM solo explica (no detecta).

INVARIANTES 🔒 P6 (por construcción):
- **Solo sugiere:** produce `Correlacion` (overlay), NUNCA toca `caso.estado`/dictamen/firma. `confianza_ajustada
  < 1.0` siempre (P7). Es un llamado de atención, no un veredicto.
- **Determinístico:** compara valores NORMALIZADOS (reusa `_norm_id`/`_norm_nombre` de U8, mismo criterio).
- **P5:** cita la fuente (etiqueta del documento), no PII cruda extra; los valores de adjunto ya vienen
  redactados (M1) — un `[REDACTED]` no se compara (evita divergencias falsas por la propia redacción).
- **P4:** correlación acotada (campos correlacionables fijos × fuentes acotadas por M1).
- **P7:** LATENTE sin fuentes múltiples reales (no inventa señales); hoy la foto es no-legible (huella) hasta
  la fase visual, así que en la práctica cruza correo ↔ PDF/texto.
"""

import logging
import re

from app.contracts.correlacion import Correlacion, CONFIANZA_COINCIDENCIA, CONFIANZA_DIVERGENCIA
from app.intake.entidades import extraer_entidades  # M2 (determinístico, NO mock): mismo extractor por fuente
from app.policy.lookup import _norm_id, _norm_nombre

logger = logging.getLogger(__name__)


def _norm_fecha(v: str) -> str:
    """Normaliza una fecha para comparar: quita separadores y ceros a la izquierda por componente.
    v1 (spec §7, exacto normalizado, sin fuzzy): '10/07/2024' == '10-7-2024'. Formatos muy distintos
    (ISO vs d/m) pueden marcar divergencia — es un 'míralo' P6-safe, no un veredicto (P7)."""
    partes = re.split(r"[/\-.\s]+", (v or "").strip())
    return "-".join(p.lstrip("0") or "0" for p in partes if p)


# Campos correlacionables: nombre técnico → (etiqueta humana, normalizador). Reusa la normalización de U8.
_CORRELACIONABLES = {
    "placa":            ("Placa", _norm_id),
    "asegurado_cedula": ("Cédula", _norm_id),
    "asegurado_nombre": ("Asegurado", _norm_nombre),
    "telefono":         ("Teléfono", _norm_id),
    "vehiculo":         ("Vehículo", _norm_nombre),
    "fecha_siniestro":  ("Fecha del evento", _norm_fecha),
}

_CONF_COINCIDE = CONFIANZA_COINCIDENCIA
_CONF_DIVERGE = CONFIANZA_DIVERGENCIA

FUENTE_CORREO = "Correo"

# P5: un valor redactado no se correlaciona (comparar '[REDACTED]' produciría divergencias falsas).
_MARCAS_REDACCION = ("[REDACTED]", "[NUM]")


def _valor_utilizable(valor: str) -> bool:
    return bool(valor) and not any(m in valor for m in _MARCAS_REDACCION)


def _valores_por_fuente(caso) -> dict[str, dict[str, str]]:
    """Agrupa {campo_nombre: {fuente: valor}} desde el aviso (extracción M2) y cada adjunto legible (M1)."""
    por_campo: dict[str, dict[str, str]] = {}

    def registrar(fuente: str, nombre: str, valor: str):
        if nombre in _CORRELACIONABLES and _valor_utilizable(valor):
            por_campo.setdefault(nombre, {})[fuente] = valor

    # Fuente 1: el correo (lo que M2 extrajo del aviso).
    if getattr(caso, "extraccion", None):
        for c in caso.extraccion.campos:
            if not c.ausente and c.valor:
                registrar(FUENTE_CORREO, c.nombre, c.valor)

    # Fuentes 2..N: cada adjunto legible → sus entidades (mismo extractor determinístico, M2).
    for a in getattr(caso, "adjuntos", None) or []:
        if a.confianza > 0 and a.texto:
            for c in extraer_entidades(a.texto):
                registrar(a.etiqueta, c.nombre, c.valor)

    return por_campo


def _redactar_valor(valor: str) -> str:
    """P5: los valores citados en la inconsistencia se redactan (tel/cédula/email); placa/fecha se ven."""
    from app.security.redaction import redact_pii_spans_es_co
    return redact_pii_spans_es_co(valor)


def correlacionar(caso) -> list[Correlacion]:
    """Correlación cross-fuente determinística (M3). Solo campos con ≥2 fuentes utilizables. 🔒 P6: solo
    produce overlay/sugerencias; jamás toca estado. Vacío si no hay multi-fuente (latente, P7)."""
    correlaciones: list[Correlacion] = []
    for nombre, por_fuente in _valores_por_fuente(caso).items():
        if len(por_fuente) < 2:  # correlación exige ≥2 fuentes
            continue
        label, norm = _CORRELACIONABLES[nombre]
        normalizados = {norm(v) for v in por_fuente.values()}
        coincide = len(normalizados) == 1
        fuentes = sorted(por_fuente.keys())

        inconsistencia = None
        if not coincide:
            detalle = "; ".join(f"{f} dice «{_redactar_valor(por_fuente[f])}»" for f in fuentes)
            inconsistencia = f"{label}: las fuentes no concuerdan — {detalle}."

        correlaciones.append(Correlacion(
            campo_nombre=nombre,
            campo_label=label,
            valores_por_fuente={f: _redactar_valor(v) for f, v in por_fuente.items()},  # P5
            fuentes=fuentes,
            coincide=coincide,
            confianza_ajustada=_CONF_COINCIDE if coincide else _CONF_DIVERGE,
            inconsistencia=inconsistencia,
        ))
    return correlaciones
