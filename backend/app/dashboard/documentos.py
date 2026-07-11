"""app/dashboard/documentos.py — provider de documentos del caso (W11).

DIP: la UI depende de esta abstracción (`documentos_de`); HOY devuelve un mock rotulado (`origen="demo"`),
y **M1 (Document AI)** la implementa con adjuntos reales SIN tocar la vista (Liskov: mismo contrato
`Documento`). P5: la galería muestra etiqueta/tipo/huella, NUNCA media cruda con PII. P7: todo `demo`.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Documento:
    """Un documento/adjunto del caso. Contrato ESTABLE que M1 llenará con datos reales."""
    nombre: str          # nombre de archivo (IMG_4231.jpg)
    tipo: str            # "foto" | "pdf" | "documento" | "audio" | "video" | "otro"
    etiqueta: str        # auto-etiqueta legible ("Foto Vehículo Frente")
    estado: str          # "extraido" | "validado" | "relacionado"
    huella: str | None   # huella perceptual (P5: la huella, no la imagen); None en el mock
    origen: Literal["real", "demo"]


# Set de demostración (rotulado). Cubre los tipos del mockup: foto/pdf/documento/audio/video/otro.
_DOCS_DEMO = [
    ("IMG_4231.jpg", "foto",       "Foto Vehículo Frente",   "validado"),
    ("IMG_4232.jpg", "foto",       "Foto Vehículo Posterior","validado"),
    ("IMG_4233.jpg", "foto",       "Costado Derecho",        "extraido"),
    ("IMG_4234.jpg", "foto",       "Motor",                  "extraido"),
    ("denuncia.pdf", "pdf",        "Denuncia Policía",       "validado"),
    ("soat.pdf",     "pdf",        "SOAT",                   "relacionado"),
    ("licencia.jpg", "foto",       "Licencia Conductor",     "extraido"),
    ("factura.pdf",  "documento",  "Factura del taller",     "relacionado"),
    ("nota.m4a",     "audio",      "Nota de voz",            "extraido"),
]

# Tipos que muestra el "Centro de Documentos" (orden e íconos).
TIPOS_PANEL = [
    ("foto", "Fotos", "📷"), ("documento", "Documentos", "📄"), ("pdf", "PDFs", "📕"),
    ("audio", "Audios", "🎧"), ("video", "Videos", "🎬"), ("otro", "Otros", "🗂️"),
]
_ICONO_TIPO = {t: i for t, _, i in TIPOS_PANEL}


def icono_de(tipo: str) -> str:
    return _ICONO_TIPO.get(tipo, "🗂️")


def documentos_de(caso) -> list[Documento]:
    """PROVIDER (DIP). Si el caso trae adjuntos REALES (M1) → los mapea (`origen="real"`, huella poblada);
    si no, cae al mock rotulado `origen="demo"` (P7). Mismo contrato `Documento` en ambos casos (Liskov)."""
    adjuntos = caso.adjuntos  # M1: siempre lista (default_factory); vacía ⇒ cae al mock
    if adjuntos:
        return [Documento(nombre=a.nombre, tipo=a.tipo, etiqueta=a.etiqueta, estado=a.estado,
                          huella=a.huella, origen="real")
                for a in adjuntos]
    return [Documento(nombre=n, tipo=t, etiqueta=e, estado=s, huella=None, origen="demo")
            for (n, t, e, s) in _DOCS_DEMO]


def agrupar_por_tipo(docs: list[Documento]) -> list[dict]:
    """Conteo por tipo para el 'Centro de Documentos' ({tipo, label, icono, count})."""
    return [{"tipo": t, "label": lbl, "icono": ico, "count": sum(1 for d in docs if d.tipo == t)}
            for t, lbl, ico in TIPOS_PANEL]
