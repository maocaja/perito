"""Mock de IMAP para los tests del poller de correo (Unit H) — sin red ni Gmail real."""

from email.message import EmailMessage


def build_raw(subject: str, body: str, sender: str = "remitente@ejemplo.com") -> bytes:
    """Construye un correo crudo (bytes) con remitente — para probar que el parser lo OMITE (P5)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = "perito.demo@ejemplo.com"
    msg.set_content(body)
    return msg.as_bytes()


class FakeIMAP:
    """Imita la porción de imaplib que usa Mailbox: uid('search'|'fetch'|'store'), close, logout."""

    def __init__(self, mensajes):
        self._mensajes = list(mensajes)  # list[(uid_bytes, raw_bytes)]
        self.seen: list = []             # uids marcados \\Seen (para asertar idempotencia)

    def uid(self, cmd, *args):
        cmd = cmd.lower()
        if cmd == "search":
            return ("OK", [b" ".join(u for u, _ in self._mensajes)])
        if cmd == "fetch":
            uid = args[0]
            for u, raw in self._mensajes:
                if u == uid:
                    return ("OK", [(b"1 (BODY[] {%d}" % len(raw), raw)])
            return ("NO", [None])
        if cmd == "store":
            self.seen.append(args[0])
            return ("OK", [b""])
        return ("OK", [None])

    def close(self):
        pass

    def logout(self):
        pass
