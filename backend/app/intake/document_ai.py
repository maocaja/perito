"""app/intake/document_ai.py — Document AI (M1): adjuntos del correo → contrato `Adjunto`. 🔒 P5.

Cierra el puente que faltaba: los bytes del adjunto (capturados en `mailbox`) se **leen** (U4 `multimodal`),
se **redactan** (P5) y se les calcula la **huella** perceptual (P5: la huella, no la media). El resultado es
una lista de `Adjunto` que se cuelga del `Caso` y alimenta la galería/conteos reales (W11/W3) y — vía la
huella registrada en `HuellaStore` — la detección **foto reutilizada** cross-claim (U6).

INVARIANTES:
- 🔒 **P5:** solo entra/sale texto YA redactado + la huella; la media cruda no se guarda en el `Adjunto`.
  El `nombre` de archivo también se redacta (un filename puede llevar una cédula).
- **P4:** ingesta acotada — `MAX_ADJUNTOS_POR_CASO` y `MAX_BYTES_POR_ADJUNTO` (sin límite oculto).
- **P7:** `confianza=0.0` ⇒ no legible; nunca se inventa contenido. Todo `origen="real"`.
- **Passive:** este módulo no decide nada (P6); solo lee/registra. La detección la hace la capa cross-claim.
"""

import logging
import re

from app.contracts.adjunto import Adjunto, MAX_ADJUNTOS_POR_CASO, MAX_BYTES_POR_ADJUNTO
from app.fraud.cross_claim import huella_perceptual
from app.intake.multimodal import leer_adjunto
from app.security.redaction import redact_pii_extendida

logger = logging.getLogger(__name__)

# P5: corrida de dígitos larga en un nombre de archivo (cédula/teléfono sin marcador). El redactor de dominio
# preserva números a propósito (pólizas/montos, P2); en un NOMBRE ningún dígito largo aporta → se enmascara.
# Umbral 6: cubre cédula (6-10) y celular (10); no toca sufijos cortos de cámara (IMG_4231 → 4 dígitos, intacto).
_DIGITOS_SENSIBLES = re.compile(r"\d{6,}")


def _redactar_nombre(nombre: str) -> str:
    """Redacta un nombre de archivo (P5). Redactor de dominio + enmascarado de dígitos largos (fail-closed:
    un `Documento_52987654.pdf` sin marcador de cédula igual se enmascara)."""
    return _DIGITOS_SENSIBLES.sub("[NUM]", redact_pii_extendida(nombre or ""))

# Extensión de archivo → tipo de galería (mismos tipos que el panel W11: foto/pdf/documento/audio/video/otro).
_EXT_TIPO = {
    ".jpg": "foto", ".jpeg": "foto", ".png": "foto", ".gif": "foto", ".webp": "foto", ".heic": "foto",
    ".pdf": "pdf",
    ".doc": "documento", ".docx": "documento", ".txt": "documento", ".text": "documento", ".rtf": "documento",
    ".m4a": "audio", ".mp3": "audio", ".wav": "audio", ".ogg": "audio", ".aac": "audio",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
}

# Tipos que llevan huella perceptual para la detección "foto reutilizada" (U6). Hoy: imágenes.
_TIPOS_CON_HUELLA = {"foto"}


def _tipo_galeria(nombre: str) -> str:
    """Tipo de galería por extensión; 'otro' si no se reconoce."""
    n = (nombre or "").lower()
    for ext, tipo in _EXT_TIPO.items():
        if n.endswith(ext):
            return tipo
    return "otro"


# Tipo de documento reconocible por su nombre → etiqueta semántica legible (M1-lite, determinístico). Un
# keyword de TIPO ('denuncia', 'soat') NO es PII (no identifica a nadie): se usa solo para nombrar la fuente
# en el cruce/galería, nunca se muestra el filename crudo (P5). Da al operador "Denuncia dice X; SOAT dice Y".
_ETIQUETA_SEMANTICA = {
    "denuncia": "Denuncia", "soat": "SOAT", "factura": "Factura",
    "cotizacion": "Cotización", "cotización": "Cotización", "peritaje": "Peritaje",
}


def _etiqueta(nombre: str, tipo: str, indice_por_tipo: int) -> str:
    """Etiqueta legible SIN PII. Si el nombre de archivo delata un TIPO conocido de documento (denuncia/soat/…)
    se usa su nombre semántico; si no, honesto: tipo + posición ('Foto 1', 'PDF 2') (P7)."""
    n = (nombre or "").lower()
    for clave, etiqueta in _ETIQUETA_SEMANTICA.items():
        if clave in n:
            return etiqueta
    nombre_tipo = {"foto": "Foto", "pdf": "PDF", "documento": "Documento",
                   "audio": "Audio", "video": "Video", "otro": "Adjunto"}.get(tipo, "Adjunto")
    return f"{nombre_tipo} {indice_por_tipo}"


def procesar_adjuntos(crudos: list[tuple[str, bytes]]) -> list[Adjunto]:
    """Bytes de adjuntos → `list[Adjunto]` (leídos, redactados, huellados). Acotado (P4). 🔒 P5.

    `crudos`: pares (nombre_archivo, contenido_bytes) tal como llegaron del correo. La media cruda NO sobrevive
    a esta función: solo su texto redactado y su huella entran al `Adjunto`.
    """
    adjuntos: list[Adjunto] = []
    conteo_por_tipo: dict[str, int] = {}
    for nombre, contenido in crudos[:MAX_ADJUNTOS_POR_CASO]:  # P4: cota de nº
        if not contenido or len(contenido) > MAX_BYTES_POR_ADJUNTO:  # P4: cota de tamaño
            # P5: el filename puede llevar PII (cédula sin marcador) → se redacta antes de loguear.
            logger.info("Document AI: adjunto '%s' omitido (vacío o > %s bytes).",
                        _redactar_nombre(nombre), MAX_BYTES_POR_ADJUNTO)
            continue
        tipo = _tipo_galeria(nombre)
        conteo_por_tipo[tipo] = conteo_por_tipo.get(tipo, 0) + 1

        leido = leer_adjunto(nombre, contenido)          # U4: lee (pdf/txt) + redacta; imagen → no_legible
        huella = huella_perceptual(contenido) if tipo in _TIPOS_CON_HUELLA else None
        adjuntos.append(Adjunto(
            nombre=_redactar_nombre(nombre),             # P5: un filename puede llevar PII (cédula sin marcador)
            tipo=tipo,
            etiqueta=_etiqueta(nombre, tipo, conteo_por_tipo[tipo]),
            texto=leido.texto,                            # ya redactado por leer_adjunto (P5)
            confianza=leido.confianza,
            huella=huella,
            estado="extraido",
            origen="real",
        ))
    return adjuntos


def registrar_huellas(adjuntos: list[Adjunto], caso_id: str, store=None) -> int:
    """Registra las huellas de los adjuntos en el `HuellaStore` (U6) → habilita foto reutilizada cross-claim.

    Devuelve cuántas huellas registró. Passive (P6): registrar no decide nada; solo indexa `huella → caso_id`.
    """
    from app.fraud.historia import get_huella_store

    store = store or get_huella_store()
    vistas: set[str] = set()  # dedup: una misma huella repetida en el caso se indexa una sola vez
    for a in adjuntos:
        if a.huella and a.huella not in vistas:
            store.registrar(a.huella, caso_id)
            vistas.add(a.huella)
    return len(vistas)


def hash_media_de(adjuntos: list[Adjunto]) -> str | None:
    """Huella representativa para la consulta cross-claim (primera foto con huella). None si no hay."""
    return next((a.huella for a in adjuntos if a.huella), None)
