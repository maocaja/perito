"""Tests M3 — Evidence Correlator: cruza fuentes dentro de un caso. 🔒 P6.

Estrato: happy (coincidencia sube confianza) + fraude/inconsistencia (divergencia cita ambas fuentes) +
fail-closed (P6 no cambia estado/firma; latente sin multi-fuente; redacción no genera divergencia falsa).
Invariantes: P6 (solo sugiere, confianza<1.0), P5 (cita fuente, valores redactados), P7 (latente).
"""

import pytest

from app.contracts.adjunto import Adjunto
from app.contracts.caso import Caso
from app.contracts.correlacion import Correlacion
from app.contracts.enums import CalidadDoc, EstadoCaso
from app.contracts.extraccion import AvisoNormalizado, ExtraccionValidada
from app.intake.entidades import extraer_entidades
from app.agents.evidence_correlator import correlacionar
from app.dashboard.vista_caso import riesgos, campos_extraidos


def _adjunto(etiqueta, texto):
    return Adjunto(nombre="doc.pdf", tipo="pdf", etiqueta=etiqueta, texto=texto, confianza=1.0, origen="real")


def _caso(aviso, adjuntos=()):
    caso = Caso(estado=EstadoCaso.RECIBIDO,
                aviso=AvisoNormalizado(texto_crudo=aviso, calidad=CalidadDoc.LIMPIO),
                extraccion=ExtraccionValidada(campos=extraer_entidades(aviso)),
                adjuntos=list(adjuntos))
    return caso.model_copy(update={"correlaciones": correlacionar(caso)})


# ---------- happy: coincidencia sube confianza ----------

def test_coincidencia_sube_confianza_sin_inconsistencia():
    caso = _caso("Choque placa DEF456.", [_adjunto("PDF 1", "Reporte, placa DEF456 del vehículo.")])
    [corr] = caso.correlaciones
    assert corr.campo_nombre == "placa"
    assert corr.coincide is True
    assert corr.inconsistencia is None
    assert 0 <= corr.confianza_ajustada < 1.0        # 🔒 P7: nunca 1.0
    assert corr.confianza_ajustada > 0.9              # sube por concordancia


def test_coincidencia_normalizada_ignora_formato():
    """'DEF-456' y 'DEF456' se consideran la misma placa (normalización U8 quita el guion, no fuzzy)."""
    caso = _caso("Placa DEF-456.", [_adjunto("PDF 1", "placa DEF456")])
    assert caso.correlaciones and caso.correlaciones[0].coincide is True


# ---------- divergencia: inconsistencia citando ambas fuentes ----------

def test_divergencia_emite_inconsistencia_con_ambas_fuentes():
    caso = _caso("Choque placa DEF456.", [_adjunto("PDF 1", "placa DEF124")])
    [corr] = caso.correlaciones
    assert corr.coincide is False
    assert corr.inconsistencia is not None
    assert "Correo" in corr.inconsistencia and "PDF 1" in corr.inconsistencia  # ambas fuentes citadas
    assert corr.confianza_ajustada < 1.0


def test_divergencia_va_a_riesgos():
    """La inconsistencia cross-fuente aparece en el panel Riesgos (W5/P6)."""
    caso = _caso("Placa DEF456.", [_adjunto("PDF 1", "placa DEF124")])
    r = riesgos(caso)
    assert r["hay"] is True
    assert any("no concuerdan" in item["texto"] for item in r["lista"])
    assert r["confianza"] < 1.0


# ---------- 🔒 P6: passive, no cambia estado ----------

def test_correlacion_no_cambia_estado_ni_firma():
    caso = _caso("Placa DEF456.", [_adjunto("PDF 1", "placa DEF124")])
    assert caso.estado == EstadoCaso.RECIBIDO         # la divergencia NO transiciona (solo HITL, P1/P6)
    assert caso.aprobado_por is None


def test_divergencia_no_escala_desde_listo_para_aprobar():
    """🔒 P6: una divergencia sobre un caso ya LISTO_PARA_APROBAR no lo escala ni deshabilita la firma."""
    caso = _caso("Placa DEF456.", [_adjunto("PDF 1", "placa DEF124")])
    caso = caso.model_copy(update={"estado": EstadoCaso.LISTO_PARA_APROBAR})
    # re-correlacionar sobre el caso listo → sigue listo (el correlador es passive)
    caso = caso.model_copy(update={"correlaciones": correlacionar(caso)})
    assert caso.estado == EstadoCaso.LISTO_PARA_APROBAR
    assert riesgos(caso)["hay"] is True   # el riesgo se muestra, pero el estado no cambia


def test_contrato_correlacion_rechaza_confianza_1():
    """🔒 P6/P7: el contrato prohíbe confianza_ajustada == 1.0 (nunca veredicto)."""
    with pytest.raises(Exception):
        Correlacion(campo_nombre="placa", campo_label="Placa",
                    valores_por_fuente={"Correo": "X", "PDF": "X"}, fuentes=["Correo", "PDF"],
                    coincide=True, confianza_ajustada=1.0)


def test_contrato_divergencia_exige_inconsistencia():
    """coincide=False sin inconsistencia → inválido (evidencia obligatoria, P6)."""
    with pytest.raises(Exception):
        Correlacion(campo_nombre="placa", campo_label="Placa",
                    valores_por_fuente={"Correo": "A", "PDF": "B"}, fuentes=["Correo", "PDF"],
                    coincide=False, confianza_ajustada=0.4, inconsistencia=None)


# ---------- P7: latente sin fuentes múltiples ----------

def test_latente_sin_adjuntos():
    """Sin ≥2 fuentes → no inventa señales (latente)."""
    assert correlacionar(_caso("Placa DEF456.")) == []


def test_latente_con_adjunto_ilegible():
    """Un adjunto no legible (confianza 0, sin texto) no aporta fuente → latente."""
    ilegible = Adjunto(nombre="foto.jpg", tipo="foto", etiqueta="Foto 1", texto="", confianza=0.0,
                       huella="abc123", origen="real")
    assert correlacionar(_caso("Placa DEF456.", [ilegible])) == []


# ---------- 🔒 P5: la redacción no produce divergencia falsa ----------

def test_valor_redactado_no_genera_divergencia_falsa():
    """El nombre en el adjunto viene REDACTADO (M1) → no se compara contra el nombre crudo del correo (si no,
    daría una divergencia falsa 'Juan Pérez' vs '[REDACTED]'). Solo la placa (no redactada) se correlaciona."""
    aviso = "Mi nombre es Juan Pérez, placa DEF456."
    # adjunto con el nombre YA redactado (como lo deja M1) pero la misma placa
    adj = _adjunto("PDF 1", "Asegurado [REDACTED], placa DEF456.")
    caso = _caso(aviso, [adj])
    nombres = {c.campo_nombre for c in caso.correlaciones}
    assert "asegurado_nombre" not in nombres  # no se correlaciona el nombre redactado
    assert "placa" in nombres and caso.correlaciones[0].coincide is True


# ---------- W17: overlay de confianza consolidada ----------

def test_overlay_confianza_en_campos_extraidos():
    """W17: un campo con correlación 'coincide' se muestra 'validado' con la confianza consolidada."""
    caso = _caso("Placa DEF456.", [_adjunto("PDF 1", "placa DEF456")])
    placa_ui = next(cu for cu in campos_extraidos(caso) if cu.label == "Placa")
    assert placa_ui.origen == "real"
    assert placa_ui.clase == "validado"
    assert placa_ui.confianza == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
