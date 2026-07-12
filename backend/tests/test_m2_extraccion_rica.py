"""Tests M2 — Extracción rica determinística (asegurado/placa/teléfono/cédula/lugar/vehículo/lesionados). 🔒 P5.

Estrato: happy (entidades es-CO se extraen) + error/fail-closed (no-invención P4, PII no va al LLM P5, U8
fallback real, providers reales bajo la misma interfaz W2/W8/W17). Invariantes: P5 (determinístico, sin LLM),
P4 (solo lo hallado), P7 (confianza<1.0), Liskov (mock↔real).
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from app.contracts.caso import Caso
from app.contracts.enums import CalidadDoc, EstadoCaso
from app.contracts.extraccion import AvisoNormalizado, ExtraccionValidada
from app.intake.entidades import extraer_entidades
from app.dashboard.vista_caso import asegurado_de, _lesionados, campos_extraidos, resumen_cola

_AVISO = ("Buenos días, mi nombre es Carlos Andrés Ramírez, cédula 1032456789. Choqué mi "
          "Mazda CX-5 2021 placa DEF456 en la Autopista Norte con Calle 153. Hay 2 lesionados. "
          "Mi celular es 310 555 8899. Póliza POL-DEMO-0002.")


def _caso(texto=_AVISO, campos=None):
    campos = extraer_entidades(texto) if campos is None else campos
    return Caso(estado=EstadoCaso.RECIBIDO,
                aviso=AvisoNormalizado(texto_crudo=texto, calidad=CalidadDoc.LIMPIO),
                extraccion=ExtraccionValidada(campos=campos))


# ---------- happy: entidades es-CO ----------

def test_extrae_entidades_esperadas():
    d = {c.nombre: c.valor for c in extraer_entidades(_AVISO)}
    assert d["placa"] == "DEF456"
    assert d["asegurado_nombre"] == "Carlos Andrés Ramírez"
    assert d["asegurado_cedula"] == "1032456789"
    assert d["telefono"] == "310 555 8899"
    assert d["vehiculo"] == "Mazda CX-5 2021"
    assert "Calle 153" in d["lugar"]
    assert d["lesionados"] == "2"


def test_confianza_nunca_veredicto():
    """P7: toda entidad determinística lleva confianza < 1.0 (es heurística, no veredicto)."""
    for c in extraer_entidades(_AVISO):
        assert c.confianza is not None and c.confianza < 1.0


# ---------- fail-closed P4: no-invención ----------

def test_no_inventa_lo_que_no_esta():
    """P4: un aviso sin placa/teléfono/nombre no emite esos campos (no se inventan)."""
    campos = extraer_entidades("Reporto un daño en la puerta. Sin más detalles.")
    nombres = {c.nombre for c in campos}
    assert "placa" not in nombres and "telefono" not in nombres and "asegurado_nombre" not in nombres


def test_poliza_no_se_confunde_con_placa():
    """El prefijo de póliza 'POL-...' no se extrae como placa (falso positivo típico)."""
    campos = extraer_entidades("Póliza POL-DEMO-0002 sin más datos.")
    assert not any(c.nombre == "placa" for c in campos)


# ---------- P5: la PII NO va al LLM (extracción determinística) ----------

@patch("app.llm.extractor.Anthropic")
def test_pii_no_va_al_llm_y_se_apila_al_final(mock_anthropic_class):
    """🔒 P5: el LLM solo ve texto redactado (4 campos operacionales); las entidades PII las añade la capa
    determinística DESPUÉS, sin mandar el crudo al modelo."""
    from app.llm.extractor import call_c2_extractor

    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    respuesta = {"numero_poliza": "POL-DEMO-0002", "fecha_siniestro": None,
                 "monto_reclamado": None, "tipo_siniestro": "AUTO", "ausentes": ["fecha_siniestro", "monto_reclamado"]}
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(respuesta), type="text")]
    mock_resp.usage = MagicMock(input_tokens=100, output_tokens=50)
    mock_client.messages.create.return_value = mock_resp

    extraccion, _usage = call_c2_extractor(_AVISO)
    nombres = {c.nombre for c in extraccion.campos}
    # 4 operacionales (LLM) + entidades ricas (determinísticas)
    assert {"numero_poliza", "fecha_siniestro", "monto_reclamado", "tipo_siniestro"} <= nombres
    assert {"placa", "asegurado_nombre", "telefono", "vehiculo"} <= nombres
    # el prompt que se le pasó al LLM iba REDACTADO (sin la cédula cruda)
    prompt_enviado = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "1032456789" not in prompt_enviado


# ---------- Liskov: providers reales, misma interfaz ----------

def test_asegurado_de_real():
    """W2: con nombre extraído → asegurado_de real (misma interfaz {nombre, origen})."""
    r = asegurado_de(_caso())
    assert r == {"nombre": "Carlos Andrés Ramírez", "origen": "real"}


def test_lesionados_real_desde_campo():
    """W8: el carril rojo lee el campo real 'lesionados' (no solo la heurística de texto)."""
    # caso con campo real lesionados pero SIN la palabra en el aviso → prueba que usa el campo, no el texto
    from app.intake.entidades import _campo
    campos = [_campo("lesionados", "3", 0.8, "conteo de heridos")]
    caso = _caso(texto="Colisión en la vía.", campos=campos)
    assert _lesionados(caso) is True


def test_campos_extraidos_reales_desplazan_al_mock():
    """W17: los campos ricos reales (Vehículo/Lugar/Teléfono) desplazan a su demo (dedup por label)."""
    reales = {cu.label: cu.origen for cu in campos_extraidos(_caso())}
    for label in ("Asegurado", "Placa", "Vehículo", "Lugar", "Teléfono"):
        assert reales.get(label) == "real", f"{label} debería ser real, no demo"


def test_telefono_y_cedula_visibles_para_el_operador():
    """P5 (gobernanza): teléfono/cédula se EXTRAEN y se MUESTRAN al operador (dato real, no `[REDACTED]`) —
    los necesita para verificar identidad/contactar/cruzar fraude. La minimización es hacia el LLM, no al
    operador autorizado."""
    por_label = {cu.label: cu.valor for cu in campos_extraidos(_caso())}
    assert "310 555 8899" in (por_label.get("Teléfono") or "")
    assert "1032456789" in (por_label.get("Cédula") or "")


def test_resumen_cola_placa_real():
    """La tarjeta de la cola muestra la placa real si se extrajo."""
    assert resumen_cola(_caso())["placa"] == "DEF456"


# ---------- U8: el fallback de C4 deja de ser latente ----------

def test_u8_fallback_c4_usa_placa_extraida():
    """Entity resolution (U8): con la placa extraída, C4 resuelve la póliza por placa cuando no hay número."""
    from datetime import date
    from decimal import Decimal
    from app.policy.lookup import call_c4_policy_lookup, set_poliza_store
    from app.contracts.poliza import Poliza, RangoFechas

    # una póliza cuya placa coincide con la extraída
    poliza = Poliza(numero="POL-XYZ-1", placa="DEF456", asegurado_nombre="Carlos Ramírez",
                    vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2026, 12, 31)),
                    suma_asegurada=Decimal("50000000"), deducible=Decimal("500000"))
    set_poliza_store({poliza.numero: poliza})
    # extracción SIN numero_poliza pero CON placa (la que produce M2)
    campos = [c for c in extraer_entidades(_AVISO) if c.nombre == "placa"]
    resultado = call_c4_policy_lookup(ExtraccionValidada(campos=campos))
    assert resultado.encontrada is True
    assert resultado.poliza.numero == "POL-XYZ-1"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
