"""app/dashboard/evidencia.py — provider de anclas de evidencia (W12) para el visor "salto a la fuente".

DIP: la UI depende de `ancla_de(caso, campo_label)`; HOY devuelve un mock rotulado, y **M1/M2** lo implementan
con anclas reales (página/coordenada del OCR) SIN tocar la vista. Fail-closed (P7): campo sin ancla → None →
"sin fuente localizada", nunca un salto falso. P5: el ancla cita el documento por su **etiqueta** (no el nombre
crudo) y una ubicación; el visor sirve contenido **mock/redactado**, jamás PII cruda.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Ancla:
    """Ubicación de un dato en su fuente. Contrato ESTABLE que M1/M2 llenarán con coordenadas reales."""
    documento: str          # etiqueta legible del documento (P5: no el nombre crudo)
    tipo: str               # "pdf" | "foto" | "documento" | …
    pagina: Optional[int]   # página (PDF) o None
    linea: Optional[int]    # línea aproximada o None
    zona_top: int           # % del resaltado mock (top)
    zona_alto: int          # % del resaltado mock (alto)
    origen: str             # "demo" hoy; "real" con M1/M2


# Zona del resaltado mock (%): sin magic numbers. El OCR real (M1/M2) traerá coordenadas verdaderas.
_ZONA_TOP_MIN = 18       # margen superior mínimo del resaltado en la página mock
_ZONA_TOP_RANGO = 55     # dispersión determinística por campo (para que cada uno resalte en distinto lugar)
_ZONA_ALTO = 11          # alto del resaltado (banda ≈ una línea)

# Anclas de demostración por campo (etiqueta → documento/ubicación). Un campo no listado → None (fail-closed).
# Las claves calzan con las etiquetas de `vista_caso._LABEL_CAMPO` (reales) y `_CAMPOS_RICOS` (Vehículo/Lugar/
# Teléfono, ricos hasta M2). Contrato entre `vista_caso` y `evidencia`: si cambia una etiqueta, actualizar aquí.
_ANCLAS_DEMO = {
    "Póliza":            ("Correo original", "documento", None, 5),
    "Fecha del evento":  ("Denuncia Policía", "pdf", 2, 3),
    "Tipo de siniestro": ("Correo original", "documento", None, 8),
    "Monto reclamado":   ("Denuncia Policía", "pdf", 3, 12),
    "Asegurado":         ("Correo original", "documento", None, 1),
    "Vehículo":          ("SOAT", "pdf", 1, 4),
    "Placa":             ("Foto Vehículo Posterior", "foto", None, None),
    "Lugar":             ("Denuncia Policía", "pdf", 2, 7),
    "Teléfono":          ("Correo original", "documento", None, 2),
}


def ancla_de(caso, campo_label: str) -> Optional[Ancla]:
    """Ancla de evidencia de un campo (mock). None si no hay fuente localizada (fail-closed, P7).

    `caso` no se usa hoy (el mock es por etiqueta); **M1/M2 lo usarán** para acceder a los documentos reales
    y devolver coordenadas verdaderas — misma firma, sin tocar la vista (DIP/Liskov).
    """
    _ = caso  # reservado para M1/M2 (OCR real sobre los adjuntos del caso)
    datos = _ANCLAS_DEMO.get(campo_label)
    if datos is None:
        return None
    documento, tipo, pagina, linea = datos
    top = _ZONA_TOP_MIN + (sum(ord(c) for c in campo_label) % _ZONA_TOP_RANGO)  # determinística por campo
    return Ancla(documento=documento, tipo=tipo, pagina=pagina, linea=linea,
                 zona_top=top, zona_alto=_ZONA_ALTO, origen="demo")
