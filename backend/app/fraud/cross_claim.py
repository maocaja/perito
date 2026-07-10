"""app/fraud/cross_claim.py — Fraude cross-claim (CAPA 4, U6). 🔒 P6.

La cuarta capa: patrones ENTRE casos (no intra-caso como las capas 1-2). Da el valor real —
foto reutilizada de otro siniestro, frecuencia sospechosa, co-ocurrencia de entidades.

INVARIANTES (no negociables):
- 🔒 **P6 absoluto:** este módulo SOLO produce señales (`AlertaFraude`). NUNCA muta `caso.estado`,
  deshabilita la firma ni bloquea — **ni con foto idéntica (distancia 0)**. Las funciones reciben el
  caso/repo en modo lectura y devuelven una alerta; jamás retornan ni copian un `Caso` con estado nuevo.
- **P7:** toda señal lleva `confianza ∈ [0,1]` + evidencia. Falso positivo = sugerencia, no veredicto.
- **P5:** la evidencia referencia solo `caso_id` (uuid opaco) del caso previo, NUNCA su PII.
- **Determinístico:** la detección es pura (distancia de Hamming / conteos). El LLM solo explica (capa 3).
- **P4:** todas las consultas heredan las cotas duras de `historia.py` (U5).

HONESTIDAD DE SCOPE (P7):
- La **huella exacta** (bytes idénticos → distancia 0) detecta foto reutilizada HOY, sin dependencia nueva
  (`huella_perceptual`, stdlib). El **pHash perceptual real** de near-duplicados (DCT + lib de imagen) llega
  con la fase visual de U4 — la interfaz (Hamming sobre hex) NO cambia cuando exista.
- **Co-ocurrencia** depende de la extracción rica de entidad (placa/tercero); `casos_por_entidad` (U5) hoy
  devuelve `[]` → esta señal no dispara aún. Cableada y lista; no se inventa (P7).
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

from app.contracts.dictamen import AlertaFraude
from app.contracts.extraccion import EvidenciaOrigen, TipoOrigen
from app.fraud.historia import casos_por_entidad, casos_por_poliza

logger = logging.getLogger(__name__)

CAPA_CROSS_CLAIM = 4

# --- Umbrales explícitos (configurables; sin umbral mágico oculto) ---
HAMMING_ALTA = 3       # distancia ≤ 3  → señal ALTA (casi idéntica)
HAMMING_MEDIA = 7      # distancia 4-7 → señal MEDIA;  ≥ 8 → NO es señal
FRECUENCIA_MIN = 3     # ≥ 3 siniestros de la misma póliza…
FRECUENCIA_VENTANA_DIAS = 365  # …en 12 meses → señal de frecuencia
CO_OCURRENCIA_MIN = 2  # ≥ 2 casos con la misma entidad → señal (evita el taller legítimo puntual)


@dataclass(frozen=True)
class SenalCrossClaim:
    """Una señal cross-claim con su evidencia, severidad y confianza (P7)."""
    evidencia: EvidenciaOrigen
    severidad: str      # "ALTA" | "MEDIA" | "BAJA"
    confianza: float    # [0,1]


def huella_perceptual(datos: bytes) -> str:
    """Huella estable y reproducible de un adjunto (P5: se guarda la huella, no la media).

    FASE 1 (hoy): huella EXACTA — bytes idénticos → misma huella → distancia 0 (foto reutilizada literal).
    No es perceptual: no capta near-duplicados (recorte/recompresión). El pHash perceptual real (DCT) llega
    con la fase visual; la interfaz de búsqueda (Hamming sobre hex en `HuellaStore`) NO cambia. Determinístico
    (sha256, sin seed aleatorio) → verificable en test.
    """
    return hashlib.sha256(datos).hexdigest()[:16]


def _severidad_por_distancia(d: int) -> Optional[str]:
    if d <= HAMMING_ALTA:
        return "ALTA"
    if d <= HAMMING_MEDIA:
        return "MEDIA"
    return None  # ≥ 8 → no es señal


def _confianza_por_distancia(d: int) -> float:
    """Confianza decreciente con la distancia; distancia 0 ≈ 0.99 pero NUNCA 1.0 (nunca veredicto, P7)."""
    if d > HAMMING_MEDIA:  # ≥ 8 no es señal (y _hamming_hex nunca devuelve negativos: 10**9 si inválido)
        return 0.0
    return round(0.99 - (d / (HAMMING_MEDIA + 1)) * 0.6, 3)


def detectar_foto_reutilizada(hash_media: str, huella_store, caso_id: str) -> list[SenalCrossClaim]:
    """Señales por foto reutilizada: huellas a distancia ≤ HAMMING_MEDIA en el índice (excluye el propio caso)."""
    if not hash_media:
        return []
    señales: list[SenalCrossClaim] = []
    for prev_id, d in huella_store.buscar(hash_media, distancia_max=HAMMING_MEDIA, excluir_id=caso_id):
        sev = _severidad_por_distancia(d)
        if sev is None:
            continue
        señales.append(SenalCrossClaim(
            evidencia=EvidenciaOrigen(
                tipo=TipoOrigen.SPAN,
                # P5: solo caso_id (uuid opaco) del caso previo; nunca su PII.
                referencia=f"FOTO_REUTILIZADA: caso {prev_id} distancia {d}",
            ),
            severidad=sev,
            confianza=_confianza_por_distancia(d),
        ))
    return señales


def detectar_frecuencia(repo, numero_poliza: Optional[str], caso_id: str) -> list[SenalCrossClaim]:
    """Señal de frecuencia: ≥ FRECUENCIA_MIN siniestros de la misma póliza en la ventana (incluye el actual)."""
    if not numero_poliza:
        return []
    previos = casos_por_poliza(repo, numero_poliza, ventana_dias=FRECUENCIA_VENTANA_DIAS, excluir_id=caso_id)
    total = len(previos) + 1  # + el caso actual
    if total < FRECUENCIA_MIN:
        return []
    # Confianza sube con el conteo, topada (P7: nunca 1.0).
    confianza = min(0.5 + 0.1 * (total - FRECUENCIA_MIN), 0.9)
    return [SenalCrossClaim(
        evidencia=EvidenciaOrigen(
            tipo=TipoOrigen.SPAN,
            referencia=f"FRECUENCIA: {total} siniestros de la póliza en {FRECUENCIA_VENTANA_DIAS} días",
        ),
        severidad="MEDIA",
        confianza=round(confianza, 3),
    )]


def detectar_co_ocurrencia(repo, entidad: Optional[str], caso_id: str) -> list[SenalCrossClaim]:
    """Señal de co-ocurrencia: misma entidad (placa/tercero/taller) en ≥ CO_OCURRENCIA_MIN casos.

    HOY no dispara: `casos_por_entidad` (U5) devuelve [] hasta que exista la extracción rica de entidad
    (U4 fase visual / U8). Cableada y lista; no se inventa (P7).
    """
    if not entidad:
        return []
    otros = casos_por_entidad(repo, entidad)
    otros = [f for f in otros if f.caso_id != caso_id]
    if len(otros) < CO_OCURRENCIA_MIN:
        return []
    return [SenalCrossClaim(
        evidencia=EvidenciaOrigen(
            tipo=TipoOrigen.SPAN,
            referencia=f"CO_OCURRENCIA: entidad compartida en {len(otros)} casos",
        ),
        severidad="MEDIA",
        confianza=0.6,
    )]


_ORDEN_SEVERIDAD = {"ALTA": 3, "MEDIA": 2, "BAJA": 1}


def construir_alerta_cross_claim(
    *,
    caso_id: str,
    numero_poliza: Optional[str] = None,
    hash_media: Optional[str] = None,
    entidad: Optional[str] = None,
    repo=None,
    huella_store=None,
    explicacion: Optional[str] = None,
) -> Optional[AlertaFraude]:
    """Orquesta la capa 4 → una `AlertaFraude` (capa=4) con TODAS las señales cross-claim, o None si no hay.

    🔒 P6: devuelve una SUGERENCIA. NO recibe ni retorna un `Caso`; es imposible que cambie estado o firma
    desde aquí. El llamador (informativo) adjunta la alerta al caso sin alterar su `estado`.
    P7: cero señales → None (nunca una alerta vacía). La `explicacion` la puede redactar el LLM (capa 3);
    si no se pasa, se arma un resumen determinístico.
    """
    señales: list[SenalCrossClaim] = []
    if huella_store is not None:
        señales += detectar_foto_reutilizada(hash_media or "", huella_store, caso_id)
    if repo is not None:
        señales += detectar_frecuencia(repo, numero_poliza, caso_id)
        señales += detectar_co_ocurrencia(repo, entidad, caso_id)

    if not señales:
        return None

    # Severidad de la alerta = la más alta de sus señales; confianza = la máxima (la señal más fuerte).
    severidad = max((s.severidad for s in señales), key=lambda s: _ORDEN_SEVERIDAD.get(s, 0))
    confianza = max(s.confianza for s in señales)
    inconsistencias = sorted((s.evidencia for s in señales), key=lambda e: e.referencia)

    if explicacion is None:
        explicacion = (
            f"Señal cross-claim ({severidad}, capa 4): {len(señales)} coincidencia(s) con el histórico. "
            "Sugerencia de revisión / carril SIU — la decisión es humana (P1/P6)."
        )

    return AlertaFraude(
        severidad=severidad,
        inconsistencias=inconsistencias,
        explicacion=explicacion,
        confianza=confianza,
        capa=CAPA_CROSS_CLAIM,
    )
