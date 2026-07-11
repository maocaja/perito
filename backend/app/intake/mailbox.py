"""app/intake/mailbox.py — buzón de correo para la demo en vivo (Unit H). Solo stdlib.

IMAP: lee los correos NO leídos → `(uid, asunto, cuerpo)`, donde **cuerpo = el aviso FNOL** (texto
plano). Usa `BODY.PEEK[]` para NO marcar leído al leer (el poller decide cuándo marcar, idempotencia).
**El remitente (email = PII) se OMITE** a propósito (P5: el redactor de dominio no cubre headers de
correo; el aviso solo necesita el cuerpo). SMTP: `enviar` (lo usa el generador `demo_mail.py`).

Credenciales desde `settings` (buzón demo dedicado). Ninguna dep nueva.
"""

import email
import imaplib
import smtplib
from dataclasses import dataclass, field
from email.header import decode_header, make_header
from email.message import EmailMessage
from typing import Optional

from app.config import settings


@dataclass
class CorreoEntrante:
    """Un correo no-leído, ya despojado del remitente (P5)."""
    uid: str
    asunto: str   # decodificado; puede llevar el marcador [DEMO:<escenario>]
    cuerpo: str   # texto plano = el aviso FNOL
    adjuntos: list[tuple[str, bytes]] = field(default_factory=list)  # M1: (nombre, bytes) de cada adjunto MIME


def _decode_header(raw: Optional[str]) -> str:
    if not raw:
        return ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return str(raw)


def _extraer_cuerpo(msg: email.message.Message) -> str:
    """Texto plano del correo (el aviso). Ignora adjuntos y partes no-texto."""
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition") or "")
            if part.get_content_type() == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace").strip()
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode(msg.get_content_charset() or "utf-8", errors="replace").strip()
    return ""


_MIME_POR_EXT = {
    ".jpg": ("image", "jpeg"), ".jpeg": ("image", "jpeg"), ".png": ("image", "png"),
    ".pdf": ("application", "pdf"), ".txt": ("text", "plain"),
}


def _mime_de(nombre: str) -> tuple[str, str]:
    """Tipo MIME (maintype, subtype) por extensión; default binario opaco."""
    n = (nombre or "").lower()
    for ext, mime in _MIME_POR_EXT.items():
        if n.endswith(ext):
            return mime
    return ("application", "octet-stream")


def _extraer_adjuntos(msg: email.message.Message) -> list[tuple[str, bytes]]:
    """Adjuntos MIME del correo → [(nombre, bytes)] (M1). Solo partes marcadas como attachment con nombre.

    P5: aquí solo se CAPTURAN los bytes; la redacción/huella/omisión de media cruda la hace `document_ai`
    (los bytes no se persisten: se convierten en texto redactado + huella). Vacío si el correo no es multipart.
    """
    if not msg.is_multipart():
        return []
    adjuntos: list[tuple[str, bytes]] = []
    for part in msg.walk():
        disp = str(part.get("Content-Disposition") or "")
        if "attachment" not in disp:
            continue
        nombre = _decode_header(part.get_filename())
        contenido = part.get_payload(decode=True)
        if nombre and contenido:
            adjuntos.append((nombre, contenido))
    return adjuntos


class Mailbox:
    """Acceso IMAP/SMTP al buzón demo. Context manager para el ciclo de lectura del poller."""

    def __init__(self, address: str, password: str, imap_host: str, smtp_host: str):
        self.address = address
        self.password = password
        self.imap_host = imap_host
        self.smtp_host = smtp_host
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    @classmethod
    def from_settings(cls) -> "Mailbox":
        return cls(
            settings.demo_gmail_address,
            settings.demo_gmail_app_password,
            settings.imap_host,
            settings.smtp_host,
        )

    # --- IMAP (lectura) ---
    def __enter__(self) -> "Mailbox":
        self._imap = imaplib.IMAP4_SSL(self.imap_host)
        self._imap.login(self.address, self.password)
        self._imap.select("INBOX")
        return self

    def __exit__(self, *exc) -> None:
        if self._imap is not None:
            try:
                self._imap.close()
                self._imap.logout()
            except Exception:
                pass
            self._imap = None

    def fetch_unseen(self, limite: int = 20) -> list[CorreoEntrante]:
        """Correos no-leídos (SIN marcarlos — BODY.PEEK). El remitente se omite (P5)."""
        assert self._imap is not None, "usar dentro de 'with Mailbox(...)'"
        typ, data = self._imap.uid("search", None, "UNSEEN")
        if typ != "OK" or not data or not data[0]:
            return []
        uids = data[0].split()[:limite]
        correos: list[CorreoEntrante] = []
        for uid in uids:
            typ, msgdata = self._imap.uid("fetch", uid, "(BODY.PEEK[])")
            if typ != "OK" or not msgdata or not msgdata[0]:
                continue
            msg = email.message_from_bytes(msgdata[0][1])
            correos.append(CorreoEntrante(
                uid=uid.decode() if isinstance(uid, bytes) else str(uid),
                asunto=_decode_header(msg.get("Subject")),
                cuerpo=_extraer_cuerpo(msg),
                adjuntos=_extraer_adjuntos(msg),  # M1: captura los adjuntos (antes se descartaban)
            ))
        return correos

    def marcar_leido(self, uid: str) -> None:
        """Marca un correo como leído (idempotencia del poller: se llama SIEMPRE, éxito o error)."""
        assert self._imap is not None, "usar dentro de 'with Mailbox(...)'"
        self._imap.uid("store", uid, "+FLAGS", "(\\Seen)")

    # --- SMTP (envío, para el generador) ---
    def enviar(self, asunto: str, cuerpo: str, to: Optional[str] = None,
               adjuntos: Optional[list[tuple[str, bytes]]] = None) -> None:
        """Envía un correo al buzón demo (por default a sí mismo). `adjuntos`: (nombre, bytes) → los adjunta
        con su tipo MIME por extensión (para ejercitar M1/M3 en la demo). No requiere el context IMAP."""
        msg = EmailMessage()
        msg["Subject"] = asunto
        msg["From"] = self.address
        msg["To"] = to or self.address
        msg.set_content(cuerpo)
        for nombre, contenido in adjuntos or []:
            maintype, subtype = _mime_de(nombre)
            msg.add_attachment(contenido, maintype=maintype, subtype=subtype, filename=nombre)
        with smtplib.SMTP_SSL(self.smtp_host, 465) as smtp:
            smtp.login(self.address, self.password)
            smtp.send_message(msg)
