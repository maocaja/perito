"""app/dashboard/comparativa.py — provider de la vista de cruce de fuentes del expediente (W13 · M3).

Cuando un caso tiene varias FUENTES de un mismo dato (el correo + la denuncia + el SOAT), el Evidence
Correlator (M3) las cruza y dice qué **coincide** (varias fuentes concuerdan) y qué **diverge** (una
inconsistencia "míralo", P6). Este provider adapta ese overlay real (`caso.correlaciones`) a la forma que
la vista consume (DIP: la vista depende de `comparativa_de(caso)`, no de M3).

P6: una divergencia solo SUGIERE (nunca decide). P5: los valores citados ya vienen redactados de M3; aquí
se citan campos/fuentes por etiqueta, nunca PII cruda. P7: LATENTE — sin ≥2 fuentes reales `disponible=False`
(no se fabrica una comparativa de una sola fuente).
"""

from dataclasses import dataclass
from typing import TypedDict

# Cotas duras de presentación (P4): un expediente muy cruzado puede traer muchas fuentes/campos; se acotan.
MAX_FUENTES = 10
MAX_CAMBIOS = 20


@dataclass(frozen=True)
class FuenteCorreo:
    """Una fuente del expediente (correo o adjunto legible) y qué aportó. Etiqueta legible, sin PII."""
    etiqueta: str       # "Correo", "Denuncia", "SOAT"
    resumen: str        # qué campos aportó esta fuente (redactado/por etiqueta)
    fecha: str = ""     # subtítulo opcional; vacío en el cruce de fuentes M3 (no hay fecha por fuente)


@dataclass(frozen=True)
class CambioDetectado:
    """Un hallazgo del cruce: una coincidencia (✅) o una divergencia (⚠️). Referencia campos, no PII cruda."""
    icono: str
    texto: str


class Comparativa(TypedDict):
    """Contrato de retorno estable (DIP): la vista depende de esta forma, no de la implementación (mock↔M3)."""
    disponible: bool
    fuentes: list[FuenteCorreo]
    cambios: list[CambioDetectado]
    origen: str  # "real" (M3); el DTO admite otros orígenes si un clustering multi-correo llega después


def comparativa_de(caso) -> Comparativa:
    """Cruce de fuentes del expediente desde el overlay REAL de M3 (`caso.correlaciones`). Contrato
    `Comparativa` estable (DIP). LATENTE (P7): sin ≥2 fuentes reales `disponible=False` — no se fabrica un
    cruce de una sola fuente. Cotas duras `MAX_FUENTES`/`MAX_CAMBIOS` (P4).
    """
    correlaciones = getattr(caso, "correlaciones", None) or []
    if not correlaciones:
        return {"disponible": False, "fuentes": [], "cambios": [], "origen": "real"}

    # Fuentes: cada fuente distinta y los campos que aportó al cruce (etiquetas legibles, sin PII).
    aportes: dict[str, list[str]] = {}
    for c in correlaciones:
        for fuente in c.fuentes:
            campos = aportes.setdefault(fuente, [])
            if c.campo_label not in campos:
                campos.append(c.campo_label)
    fuentes = [FuenteCorreo(etiqueta=fuente, resumen="Aportó: " + ", ".join(campos))
               for fuente, campos in sorted(aportes.items())][:MAX_FUENTES]

    # Cambios: por campo correlacionado, una coincidencia o la divergencia (que M3 ya trae con evidencia, P6).
    cambios: list[CambioDetectado] = []
    for c in correlaciones:
        if c.coincide:
            cambios.append(CambioDetectado("✅", f"{c.campo_label}: {len(c.fuentes)} fuentes concuerdan"))
        else:
            cambios.append(CambioDetectado("⚠️", c.inconsistencia))
    cambios = cambios[:MAX_CAMBIOS]

    return {"disponible": True, "fuentes": fuentes, "cambios": cambios, "origen": "real"}
