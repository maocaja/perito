"""demo_mail.py — generador de correos FNOL sintéticos (Unit H, `make demo-mail`).

On-demand y ACOTADO (control de costo, riesgo #2): envía `MAIL_TOTAL` correos rotando los 4
escenarios de Unit G (reusa `demo_run.ESCENARIOS` → una sola fuente de verdad), ~5/min, y termina.
Cada asunto lleva `[DEMO:<escenario>]` → el modo `deterministic` del poller lo usa para mapear al preset.

Los correos son SINTÉTICOS (sin PII real). Uso (desde backend/):  python demo_mail.py
Requiere DEMO_GMAIL_ADDRESS + DEMO_GMAIL_APP_PASSWORD en `.env`.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.intake.mailbox import Mailbox

INTERVALO_S = 12  # ~5 correos/min


def main() -> int:
    if not settings.demo_gmail_address or not settings.demo_gmail_app_password:
        print("❌ Falta DEMO_GMAIL_ADDRESS / DEMO_GMAIL_APP_PASSWORD en .env (buzón demo).")
        return 1

    from demo_run import ESCENARIOS  # una sola fuente de verdad de los escenarios

    total = settings.mail_total
    mb = Mailbox.from_settings()
    print(f"Enviando {total} FNOL sintéticos a {settings.demo_gmail_address} (~5/min, ~{total * INTERVALO_S // 60} min)...")
    print("Marcador en el asunto: [DEMO:<escenario>] (lo usa el modo deterministic).\n")

    for i in range(total):
        esc = ESCENARIOS[i % len(ESCENARIOS)]
        asunto = f"[DEMO:{esc['key']}] Reporte de siniestro FNOL #{i + 1}"
        try:
            mb.enviar(asunto, esc["aviso"])
            print(f"  {i + 1}/{total} enviado · {esc['titulo']}")
        except Exception as e:  # un envío que falla no tumba el lote
            print(f"  {i + 1}/{total} ❌ falló: {e}")
        if i < total - 1:
            time.sleep(INTERVALO_S)

    print("\n✓ Generador terminó (tope MAIL_TOTAL alcanzado). Revisa la bandeja en /casos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
