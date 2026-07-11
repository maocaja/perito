"""app/dashboard/comparativa.py — provider de la vista comparativa multi-correo (W13).

Cuando llegan varios correos del mismo cliente, la IA los relaciona y resume **qué cambió** entre versiones.
DIP: la UI depende de `comparativa_de(caso)`; HOY es un mock rotulado, y **U8 (entity resolution) + U7 (triage
PERTENECE_A_CASO) + M1** lo vuelven real (agrupar correos del mismo expediente) SIN tocar la vista.
P5: las fuentes se citan por etiqueta/fecha (redactadas); el diff referencia campos, nunca PII cruda. P7: mock.
"""

from dataclasses import dataclass
from typing import TypedDict

# Cotas duras de presentación (P4): el clustering real (M1/U8) puede traer muchos correos; se acotan.
MAX_FUENTES = 10
MAX_CAMBIOS = 20


@dataclass(frozen=True)
class FuenteCorreo:
    """Un correo/fuente del expediente. Contrato estable que el clustering real (U7/U8) llenará."""
    etiqueta: str    # "Correo 1"
    fecha: str       # "11/07/2026 08:45 p.m."
    resumen: str     # resumen corto (redactado)


@dataclass(frozen=True)
class CambioDetectado:
    """Un cambio detectado por la IA entre versiones. Referencia campos, no PII."""
    icono: str
    texto: str


class Comparativa(TypedDict):
    """Contrato de retorno estable (DIP): la vista depende de esta forma, no de la implementación."""
    disponible: bool
    fuentes: list[FuenteCorreo]
    cambios: list[CambioDetectado]
    origen: str  # "demo" hoy; "real" con U7/U8/M1


# Mock rotulado (P7): el expediente con 3 correos del mockup + los cambios detectados.
_FUENTES_DEMO = [
    FuenteCorreo("Correo 1", "11/07/2026 08:45 p.m.", "Aviso inicial del siniestro con 6 fotografías."),
    FuenteCorreo("Correo 2", "12/07/2026 09:15 a.m.", "Amplía la descripción del accidente."),
    FuenteCorreo("Correo 3", "12/07/2026 10:02 a.m.", "Adjunta la factura de reparación del taller."),
]
_CAMBIOS_DEMO = [
    CambioDetectado("🖼️", "Se agregó una nueva foto del costado izquierdo."),
    CambioDetectado("✏️", "Cambió la descripción del accidente."),
    CambioDetectado("📎", "Se adjuntó la factura de reparación."),
]


def comparativa_de(caso) -> Comparativa:
    """Vista comparativa del expediente. Contrato `Comparativa` estable (DIP).

    HOY: mock rotulado `origen="demo"` que **sí** muestra la comparativa (es el objetivo de la demo). El
    clustering multi-correo real llega con U7/U8/M1: entonces `caso` se usará para agrupar los correos del
    expediente y `disponible` reflejará el conteo real (`False` con < 2 correos, sin fabricar una comparativa
    de un solo correo — P7). Cotas duras `MAX_FUENTES`/`MAX_CAMBIOS` (P4).
    """
    _ = caso  # reservado: el clustering real (U7/U8/M1) agrupará los correos del expediente
    return {
        "disponible": True,
        "fuentes": _FUENTES_DEMO[:MAX_FUENTES],
        "cambios": _CAMBIOS_DEMO[:MAX_CAMBIOS],
        "origen": "demo",
    }
