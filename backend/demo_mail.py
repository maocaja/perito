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

# Foto sintética COMPARTIDA (mismos bytes) → al llegar en ≥2 correos dispara "foto reutilizada" cross-claim
# (M1: misma huella en dos casos). No es una imagen real; solo bytes estables para la huella.
_FOTO_COMPARTIDA = b"PERITO-DEMO-FOTO-SINIESTRO-" + bytes(range(64)) * 8

# Placas por escenario: denuncia vs SOAT. En 'fraude' DIFIEREN → M3 emite divergencia; en el resto coinciden
# (sube la confianza). Todo sintético, sin PII real (P7).
_PLACAS_DEMO = {
    "feliz":            ("FBC123", "FBC123"),
    "fraude":           ("GHT456", "GHT457"),   # ← divergencia (el "aha" de M3)
    "no-encontrada":    ("JKL789", "JKL789"),
    "campos-faltantes": ("MNO321", "MNO321"),
}


def _adjuntos_demo(key: str) -> list[tuple[str, bytes]]:
    """Adjuntos sintéticos por escenario para ejercitar M1 (huella/galería) y M3 (cruce de fuentes).

    - Foto compartida en todos → foto reutilizada (M1) al segundo correo.
    - denuncia.txt + soat.txt con placa → M3 correlaciona las dos fuentes ('fraude' diverge, resto coincide).
    - El escenario de vivienda (sin placa) solo lleva la foto (honesto: no se le inventan papeles de auto).
    """
    adjuntos: list[tuple[str, bytes]] = [("foto_siniestro.jpg", _FOTO_COMPARTIDA)]
    placas = _PLACAS_DEMO.get(key)
    if placas:
        p_denuncia, p_soat = placas
        adjuntos.append(("denuncia.txt",
                         f"DENUNCIA POLICIAL (sintética)\nVehículo involucrado placa {p_denuncia}.\n"
                         f"Fecha del siniestro 2026-06-10.\n".encode("utf-8")))
        adjuntos.append(("soat.txt",
                         f"SOAT (sintético)\nPlaca {p_soat}\nVigencia 2026-01-01 a 2026-12-31.\n".encode("utf-8")))
    return adjuntos


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
            mb.enviar(asunto, esc["aviso"], adjuntos=_adjuntos_demo(esc["key"]))
            print(f"  {i + 1}/{total} enviado · {esc['titulo']}")
        except Exception as e:  # un envío que falla no tumba el lote
            print(f"  {i + 1}/{total} ❌ falló: {e}")
        if i < total - 1:
            time.sleep(INTERVALO_S)

    print("\n✓ Generador terminó (tope MAIL_TOTAL alcanzado). Revisa la bandeja en /casos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
