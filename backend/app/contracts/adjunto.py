"""app/contracts/adjunto.py — contrato `Adjunto` (M1 · Document AI). 🔒 P5.

Un adjunto del correo ya **leído, redactado y con huella** — la forma estable que consumen los providers
`documentos_de` (W11), `conteo_adjuntos` (W3) y, más adelante, la extracción rica (M2) y el correlator (M3).

INVARIANTES 🔒 P5 (por construcción):
- **Nunca media cruda:** `Adjunto` guarda la HUELLA perceptual (`huella`) y el TEXTO REDACTADO (`texto`),
  jamás los bytes de la imagen/PDF. La media cruda no entra al contrato → no se persiste ni se muestra.
- **Texto redactado:** `texto` ya pasó por `redact_pii_extendida` (lo hace `document_ai.procesar_adjuntos`).
- **Sin PII en el display:** la UI muestra `etiqueta` (p.ej. "Foto 1"), nunca el `nombre` crudo del archivo.
- **P7 honestidad:** `confianza=0.0` ⇒ no legible (no se inventa contenido); `origen="real"` distingue del mock.
"""

from typing import Literal, Optional

from pydantic import Field

from app.contracts import Contract


class Adjunto(Contract):
    """Un adjunto del caso, ya leído/redactado/huellado (M1). Contrato ESTABLE (mismo shape que el mock W11)."""

    nombre: str                      # nombre de archivo REDACTADO (interno; nunca se muestra crudo — P5)
    tipo: str                        # galería: "foto"|"pdf"|"documento"|"audio"|"video"|"otro"
    etiqueta: str                    # etiqueta legible sin PII ("Foto 1", "PDF 1")
    texto: str = ""                  # texto REDACTADO (P5); "" si no_legible
    confianza: float = 0.0           # [0,1]; 0.0 ⇒ no legible (P7: no se inventa)
    huella: Optional[str] = None     # huella perceptual (P5: la huella, NO la media); None si no aplica
    estado: Literal["extraido", "validado", "relacionado"] = "extraido"  # galería; M3 promueve a "relacionado"
    origen: Literal["real", "demo"] = "real"


# Cotas duras de ingesta por caso (P4: nº y tamaño de adjuntos acotados; sin límite oculto).
MAX_ADJUNTOS_POR_CASO = 20
MAX_BYTES_POR_ADJUNTO = 15 * 1024 * 1024  # 15 MB
