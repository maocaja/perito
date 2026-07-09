"""Tests del tablero agent-native (Unit I) — view-models de vista_caso.

Cubre: P1 (la recomendación NUNCA decide), P2/P7 (el resumen cita el motor / dice "no disponible"),
el mapeo de nodos en ambos esquemas, y C3 leído de la traza (o ausente).
"""

import pytest

from app.contracts.enums import EstadoCaso
from app.dashboard import vista_caso
from app.demo.scenarios import construir_caso_preset

TODOS = ["feliz", "fraude", "cobertura-negativa", "no-encontrada", "campos-faltantes"]


# ---------------- P1: la recomendación nunca decide (fail-closed) ----------------

@pytest.mark.parametrize("escenario", TODOS)
def test_recomendacion_nunca_decide_when_cualquier_escenario(escenario):
    caso = construir_caso_preset(escenario)
    rec = vista_caso.recomendacion(caso)
    blob = (rec["titulo"] + " " + rec["texto"]).lower()
    for prohibida in vista_caso.PALABRAS_PROHIBIDAS:
        assert prohibida not in blob, f"P1: '{prohibida}' apareció en la recomendación de {escenario}"


def test_recomendacion_terminal_nunca_decide():
    """Aun en estado terminal (APROBADO), la recomendación no contiene palabras de decisión."""
    caso = construir_caso_preset("feliz").model_copy(update={"estado": EstadoCaso.APROBADO, "aprobado_por": "ana"})
    rec = vista_caso.recomendacion(caso)
    blob = (rec["titulo"] + " " + rec["texto"]).lower()
    assert not any(p in blob for p in vista_caso.PALABRAS_PROHIBIDAS)


def test_recomendacion_faltantes_pide_el_dato():
    caso = construir_caso_preset("campos-faltantes")
    rec = vista_caso.recomendacion(caso)
    assert "monto_reclamado" in rec["texto"]
    assert rec["tono"] == "warn"


# ---------------- A: resumen cita el motor, dice lo que falta ----------------

def test_resumen_feliz_cita_cobertura():
    caso = construir_caso_preset("feliz")
    r = vista_caso.resumen_copiloto(caso)
    cob = " ".join(l["texto"] for l in r["lineas"])
    assert caso.dictamen.resultado.value in cob  # cita LITERAL el veredicto del motor (P2)
    assert caso.dictamen.regla_aplicada in cob


def test_resumen_faltantes_dice_que_falta():
    caso = construir_caso_preset("campos-faltantes")
    r = vista_caso.resumen_copiloto(caso)
    txt = " ".join(l["texto"] for l in r["lineas"])
    assert "falta" in txt.lower() and "monto_reclamado" in txt


# ---------------- B: actividad mapea ambos esquemas + fallback ----------------

def test_actividad_mapea_determinístico_y_real_y_fallback():
    traza = {"trace_events": [
        {"nodo": "extractor", "resultado": "ok", "tokens_in": 420, "tokens_out": 110, "timestamp": "2026-07-09T17:00:05+00:00"},
        {"nodo": "c5_motor_cobertura", "resultado": "dictamen=CUBIERTO", "timestamp": "2026-07-09T17:00:06+00:00"},
        {"nodo": "nodo_raro", "resultado": "x", "timestamp": ""},
    ], "token_summary": {"tokens_total": 530}}
    feed = vista_caso.actividad_agentes(traza)
    assert feed[0]["etiqueta"].startswith("Extractor")     # determinístico
    assert feed[0]["hora"] == "17:00:05" and feed[0]["tokens"] == 530
    assert feed[1]["etiqueta"].startswith("Motor")          # real
    assert feed[2]["etiqueta"] == "nodo_raro"               # fallback al nombre técnico


def test_actividad_sin_traza_vacia():
    assert vista_caso.actividad_agentes(None) == []


# ---------------- E: C3 leído de la traza (o ausente) ----------------

def test_hallazgos_verificador_parsea_evento_c3():
    traza = {"trace_events": [{"nodo": "c3_verificador", "resultado": "confianza=0.97, señales=0"}]}
    h = vista_caso.hallazgos_verificador(None, traza)
    assert h["disponible"] and h["confianza"] == 0.97 and h["senales"] == 0


def test_hallazgos_verificador_ausente_no_disponible():
    h = vista_caso.hallazgos_verificador(None, {"trace_events": [{"nodo": "motor", "resultado": "x"}]})
    assert h["disponible"] is False and h["confianza"] is None


# ---------------- C: strip de confianza ----------------

def test_confianza_riesgo_cuatro_celdas():
    caso = construir_caso_preset("fraude")
    strip = vista_caso.confianza_riesgo(caso, None)
    labels = [c["label"] for c in strip]
    assert labels == ["Extracción", "Verificación", "Fraude", "Cobertura"]
    assert strip[2]["valor"] == "ALTA"  # fraude preset → severidad ALTA


# ---------------- P5: el detalle redacta los campos de display (defensa en profundidad) ----------------

def test_detalle_redacta_pii_en_display():
    """Un campo solo-display (explicación de fraude) con PII se muestra REDACTADO en el detalle (P5)."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dashboard.store import get_caso_repository, reset_caso_repository

    reset_caso_repository()
    caso = construir_caso_preset("fraude")
    object.__setattr__(caso.alerta_fraude, "explicacion", "Verificar con el asegurado C.C. 1.098.765.432")
    get_caso_repository().save(caso)
    html = TestClient(app).get(f"/casos/{caso.id}").text
    assert "1.098.765.432" not in html   # la cédula NO aparece cruda
    assert "[REDACTED]" in html            # se redactó
