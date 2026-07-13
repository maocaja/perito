"""app/dashboard/demo_assets.py — servir assets REALES de demo (fotos/PDF) al visor y la galería.

Solo-demo (P5): sirve ÚNICAMENTE archivos físicamente presentes en `backend/demo_assets/` (sintéticos, sin
PII real); JAMÁS la media cruda de un correo real (que por P5 no se persiste). En producción no hay asset
que calce → `None` → el visor cae a la huella/mock. La media del correo nunca entra a esta ruta.
"""

import os

_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "demo_assets"))
_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".pdf")  # renderizables en el navegador (img/pdf)


def _ruta_segura(nombre: str) -> str | None:
    """Ruta absoluta dentro de `_DIR` para un basename con extensión permitida; None si no aplica.
    Blindaje anti-traversal: solo basename, y la ruta resuelta debe quedar DENTRO de `_DIR`."""
    base = os.path.basename(nombre or "")
    if not base or os.path.splitext(base)[1].lower() not in _EXTS:
        return None
    ruta = os.path.realpath(os.path.join(_DIR, base))
    if not ruta.startswith(_DIR + os.sep) or not os.path.isfile(ruta):
        return None
    return ruta


def ruta_de_asset(nombre: str) -> str | None:
    """Ruta del archivo a servir (para FileResponse), o None si no existe / no permitido."""
    return _ruta_segura(nombre)


def url_de(documento) -> str | None:
    """URL del asset real para un `Documento`, o None (→ el visor usa el mock/huella). Calza primero por el
    NOMBRE del adjunto (una foto real adjuntada) y, si no, por la ETIQUETA semántica (p.ej. 'SOAT' → SOAT.png)
    — así la imagen se pinta aunque el adjunto que alimenta M3 sea el texto sintético del documento."""
    if not documento:
        return None
    candidatos = [os.path.basename(getattr(documento, "nombre", "") or "")]
    candidatos += [f"{getattr(documento, 'etiqueta', '')}{ext}" for ext in _EXTS]
    for candidato in candidatos:
        if _ruta_segura(candidato):
            return f"/workbench/asset/{candidato}"
    return None
