"""app/intake/entidades.py — extracción rica DETERMINÍSTICA de entidades es-CO (M2). 🔒 P5.

C2 (LLM) extrae los campos operacionales (póliza/fecha/monto/tipo) de texto **redactado**. Pero los campos
PII (nombre/placa/teléfono/cédula) NO pueden salir del LLM: su prompt va redactado por P5, así que el LLM
jamás los ve. Este módulo los extrae con **regex/NER es-CO sobre el texto crudo** — determinístico, sin red,
sin mandar PII a ningún LLM. Reusa los patrones del redactor (`redaction.py`): donde el redactor los BORRA,
aquí se EXTRAEN.

INVARIANTES:
- 🔒 **P5:** función pura determinística; el texto crudo nunca va a un LLM. Los valores son PII → la capa de
  display los redacta (`_red`); aquí solo se estructuran. El valor no se muestra crudo en logs.
- **P4 no-invención:** solo se emite un `CampoExtraido` para lo que se HALLA; un campo no hallado no se emite
  (equivale a ausente, valor=None) — nunca se inventa.
- **P7:** confianza < 1.0 siempre (es un match heurístico, no un veredicto). `origen` cita el método, sin PII.
"""

import re

from app.contracts.enums import TipoOrigen
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen

# --- Patrones es-CO (reusan/espejan los del redactor) -------------------------------------------------
# Placa: carro LLLNNN o moto LLLNNL. Se excluye el prefijo de póliza "POL" (falso positivo típico).
_PLACA = re.compile(r"\b(?!POL\b)([A-Z]{3})[\s-]?(\d{3}|\d{2}[A-Z])\b")
# Celular CO: 3XX XXX XXXX (con o sin +57). Mismo patrón que redact_pii_spans_es_co.
_TELEFONO = re.compile(r"(?:\+57\s*)?\b(3\d{2}[\s-]?\d{3}[\s-]?\d{4})\b")
# Cédula tras marcador (mismo patrón del redactor).
_CEDULA = re.compile(
    r"(?:C\.?C\.?|cedula|cédula|CEDULA)\s*(?:No\.?)?\s*(?:\.?\s*)?(\d{1,4}(?:[\.\-\s]\d{3}){2,3}|\d{6,10})",
    re.IGNORECASE,
)
# Nombre tras marcador de introducción (1-3 palabras Capitalizadas).
_NOMBRE = re.compile(
    r"(?:me llamo|mi nombre es|asegurad[oa][:\s]+|propietari[oa][:\s]+|conductor[a]?[:\s]+|"
    r"Sr\.?|Sra\.?|señor|señora)\s+"
    r"((?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})",
    re.IGNORECASE,
)
# Dirección/lugar es-CO. Cubre "Calle 5 # 10-20", "Cra 7 No 45-12" y vías con nombre
# ("Autopista Norte con Calle 153"): la vía + un nombre opcional + un "con <vía> <n>" opcional.
_LUGAR = re.compile(
    r"(?:Calle|Cll\.?|Carrera|Cra\.?|Kr\.?|Avenida|Av\.?|Autopista|Diagonal|Dg\.?|Transversal|Tv\.?)"
    r"\s+(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+)?(?:\d+[A-Za-z]?)?"
    r"(?:\s*(?:#|No\.?|N°|con)\s*(?:Calle|Carrera|Cra\.?|Kr\.?)?\s*\d+[A-Za-z]?(?:\s*[-–]\s*\d+)?)?",
    re.IGNORECASE,
)
# Vehículo: marca conocida + hasta 2 tokens (modelo/año).
_MARCAS = ("Mazda", "Chevrolet", "Renault", "Kia", "Toyota", "Nissan", "Ford", "Volkswagen",
           "Hyundai", "Suzuki", "BMW", "Mercedes", "Mercedes-Benz", "Honda", "Jeep", "Audi", "Fiat")
_VEHICULO = re.compile(r"\b(" + "|".join(_MARCAS) + r")\b(\s+[A-Za-z0-9][\w-]*){0,2}", re.IGNORECASE)
# P4: cota de longitud del texto a escanear (higiene — acota el trabajo ante un correo enorme). Las regex son
# lineales (sin backtracking catastrófico, medido), pero igual se acota el input no confiable por defensa.
MAX_TEXTO_ESCANEO = 20_000

# Lesionados: conteo explícito ("2 lesionados") si lo hay; si no, mención suelta → "Sí".
_LESIONADOS_CONTEO = re.compile(r"\b(\d+)\s+(?:personas?\s+)?(?:lesionad[oa]s?|herid[oa]s?)\b", re.IGNORECASE)
_LESIONADOS_MENCION = re.compile(r"\b(?:lesionad[oa]s?|herid[oa]s?|lesión|lesiones)\b", re.IGNORECASE)


def _campo(nombre: str, valor: str, confianza: float, metodo: str) -> CampoExtraido:
    """CampoExtraido determinístico (P3: origen = método, sin PII; P7: confianza < 1.0)."""
    return CampoExtraido(
        nombre=nombre,
        valor=valor.strip(),
        origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia=f"det: {metodo}"),
        confianza=confianza,
        ausente=False,
    )


def extraer_entidades(texto_crudo: str) -> list[CampoExtraido]:
    """Entidades ricas es-CO por regex/NER sobre el texto crudo (determinístico, P5). Solo emite lo hallado
    (no-invención, P4). Nombres canónicos que el resto del sistema ya espera (W2/W17/C4-U8)."""
    texto = (texto_crudo or "")[:MAX_TEXTO_ESCANEO]  # P4: acota el input no confiable
    campos: list[CampoExtraido] = []

    m = _PLACA.search(texto)
    if m:
        campos.append(_campo("placa", (m.group(1) + m.group(2)).upper(), 0.9, "placa es-CO"))

    m = _TELEFONO.search(texto)
    if m:
        campos.append(_campo("telefono", m.group(1), 0.9, "celular es-CO"))

    m = _CEDULA.search(texto)
    if m:
        campos.append(_campo("asegurado_cedula", m.group(1), 0.85, "cédula es-CO"))

    m = _NOMBRE.search(texto)
    if m:
        campos.append(_campo("asegurado_nombre", m.group(1), 0.75, "NER-lite nombre"))

    m = _LUGAR.search(texto)
    if m:
        campos.append(_campo("lugar", m.group(0), 0.7, "dirección es-CO"))

    m = _VEHICULO.search(texto)
    if m:
        campos.append(_campo("vehiculo", m.group(0), 0.72, "marca+modelo"))

    m = _LESIONADOS_CONTEO.search(texto)
    if m:
        campos.append(_campo("lesionados", m.group(1), 0.8, "conteo de heridos"))
    elif _LESIONADOS_MENCION.search(texto):
        campos.append(_campo("lesionados", "Sí", 0.7, "mención de heridos"))

    return campos
