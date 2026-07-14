"""app/dashboard/documentos.py — provider de documentos del caso (W11).

DIP: la UI depende de esta abstracción (`documentos_de`); mapea los adjuntos REALES del correo
(M1 · Document AI) al contrato `Documento` SIN que la vista cambie (Liskov). P5: la galería muestra
etiqueta/tipo/huella, NUNCA media cruda con PII.

🔒 Honestidad (P7): NO se inventan documentos. Si el correo no trajo adjuntos, `documentos_de`
devuelve lista vacía y la vista pinta un estado vacío — nunca un set de demostración fabricado (que
llegaba a mostrar fotos de un auto en un siniestro de vivienda).
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Documento:
    """Un documento/adjunto del caso. Contrato ESTABLE que M1 llena con datos reales."""
    nombre: str          # nombre de archivo (IMG_4231.jpg)
    tipo: str            # "foto" | "pdf" | "documento" | "audio" | "video" | "otro"
    etiqueta: str        # auto-etiqueta legible ("Foto Vehículo Frente")
    estado: str          # "extraido" | "validado" | "relacionado"
    huella: str | None   # huella perceptual (P5: la huella, no la imagen)
    texto: str           # texto REDACTADO del documento (P5); "" si no legible (p.ej. una foto)
    origen: Literal["real"]


# Tipos que muestra el "Centro de Documentos" (orden e íconos).
TIPOS_PANEL = [
    ("foto", "Fotos", "📷"), ("documento", "Documentos", "📄"), ("pdf", "PDFs", "📕"),
    ("audio", "Audios", "🎧"), ("video", "Videos", "🎬"), ("otro", "Otros", "🗂️"),
]
_ICONO_TIPO = {t: i for t, _, i in TIPOS_PANEL}


def icono_de(tipo: str) -> str:
    return _ICONO_TIPO.get(tipo, "🗂️")


def documentos_de(caso) -> list[Documento]:
    """PROVIDER (DIP). Mapea SOLO los adjuntos REALES del correo (M1) al contrato `Documento`.

    Si el correo no trajo adjuntos → lista vacía (P7: no se fabrica evidencia). La vista pinta un
    estado vacío honesto en ese caso."""
    return [Documento(nombre=a.nombre, tipo=a.tipo, etiqueta=a.etiqueta, estado=a.estado,
                      huella=a.huella, texto=a.texto, origen="real")
            for a in caso.adjuntos]  # M1: siempre lista (default_factory); vacía ⇒ galería vacía


def agrupar_por_tipo(docs: list[Documento]) -> list[dict]:
    """Conteo por tipo para el 'Centro de Documentos' ({tipo, label, icono, count})."""
    return [{"tipo": t, "label": lbl, "icono": ico, "count": sum(1 for d in docs if d.tipo == t)}
            for t, lbl, ico in TIPOS_PANEL]
