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

# Vehículo por escenario, ALINEADO con el cuerpo del correo → M3 cruza también 'Vehículo' (además de 'Placa').
# En 'fraude', el vehículo COINCIDE (mismo carro descrito) pero la placa del SOAT difiere → la divergencia
# aísla la placa: "el mismo carro, con una placa que no concuerda" (señal de fraude realista).
_VEHICULOS_DEMO = {
    "feliz": "Mazda 3", "fraude": "Chevrolet Onix", "no-encontrada": "Renault Logan",
    "campos-faltantes": "Kia Picanto",
}

# Foto REAL por escenario (archivos en `demo_assets/`), alineada con el daño que narra cada correo. Si el
# archivo no existe, se cae a la foto sintética compartida (bytes estables → cross-claim foto reutilizada).
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo_assets")
_FOTO_POR_ESCENARIO = {
    "feliz": "Colisión_Delantera.png",             # "golpe en la parte delantera derecha"
    "fraude": "Colision_lateral_derecha.png",      # "me impactó de lado, pérdida total"
    "no-encontrada": "Colision_lateral_izquierda.png",  # "raspó todo el costado izquierdo"
    "campos-faltantes": "Colisión_Trasera.png",    # "golpe en el bómper trasero"
}


def _leer_asset(nombre: str) -> bytes | None:
    """Bytes de un asset real de `demo_assets/` si existe; None si no (→ fallback sintético)."""
    ruta = os.path.join(_ASSETS_DIR, nombre)
    if os.path.isfile(ruta):
        with open(ruta, "rb") as f:
            return f.read()
    return None


def _foto_de(key: str) -> tuple[str, bytes] | None:
    """Foto del escenario: la REAL de `demo_assets/` si existe; si no, la sintética compartida para los
    escenarios de auto; None para vivienda (P7: no se le inventa una foto de carro)."""
    nombre = _FOTO_POR_ESCENARIO.get(key)
    if nombre:
        datos = _leer_asset(nombre)
        if datos is not None:
            return (nombre, datos)
    return ("foto_siniestro.jpg", _FOTO_COMPARTIDA) if key in _PLACAS_DEMO else None


def _adjuntos_demo(key: str) -> list[tuple[str, bytes]]:
    """Adjuntos por escenario para ejercitar M1 (huella/galería/render) y M3 (cruce de fuentes).

    - Foto REAL del escenario (o sintética compartida de fallback) → galería + visor + huella.
    - denuncia + soat SINTÉTICOS con placa Y vehículo → M3 cruza dos campos entre Correo/Denuncia/SOAT
      ('fraude' diverge en la placa; el vehículo coincide → aísla la señal). El visor pinta `SOAT.png`
      (demo_assets) por etiqueta, pero el texto sintético es el que M3 lee (sin OCR, la imagen no da texto).
    - El escenario de vivienda (sin placa) no lleva foto de auto (honesto).
    """
    adjuntos: list[tuple[str, bytes]] = []
    foto = _foto_de(key)
    if foto:
        adjuntos.append(foto)
    placas = _PLACAS_DEMO.get(key)
    if placas:
        p_denuncia, p_soat = placas
        vehiculo = _VEHICULOS_DEMO[key]
        adjuntos.append(("denuncia.txt",
                         f"DENUNCIA POLICIAL (sintética)\nVehículo involucrado: {vehiculo}, placa {p_denuncia}.\n"
                         f"Descripción: colisión reportada por el conductor.\n".encode("utf-8")))
        adjuntos.append(("soat.txt",
                         f"SOAT (sintético)\nVehículo: {vehiculo}.\nPlaca: {p_soat}.\n"
                         f"Vigencia: 2026-01-01 a 2026-12-31.\n".encode("utf-8")))
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
