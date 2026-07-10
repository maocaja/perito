"""Tests U9 — Loop reflexivo C2↔C3 (evaluator-optimizer). 🔒 P4.

Cubre: re-extracción UNA vez con feedback de C3; escala si persiste (no loopea); cap max_rondas=2 (default
1 = single-pass intacto); 🔒 P2 (el loop NO re-decide cobertura — el motor R1-R5 sigue siendo el único);
feedback = nombres de campo (sin PII); presupuesto de tokens acotado; corona (nunca terminal).
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.contracts.caso import Caso
from app.contracts.dictamen import Cotas
from app.contracts.enums import CalidadDoc, EstadoCaso, ResultadoCobertura, TipoClausula, TipoOrigen
from app.contracts.extraccion import AvisoNormalizado, CampoExtraido, EvidenciaOrigen, ExtraccionValidada
from app.contracts.poliza import Clausula, Poliza, RangoFechas
from app.contracts.verificacion import VerificacionAdversarial
from app.intake.c1 import intake_crear_caso
from app.orchestrator.c7 import UMBRAL_REEXTRACCION, orquestar_fnol
from app.policy.lookup import set_poliza_store


# ------------------------------------------------------------------ fixtures

@pytest.fixture
def hitl():
    def _trans(caso, nuevo, actor, motivo=None):
        d = caso.model_dump()
        d["estado"] = nuevo
        d["timestamp_actualizacion"] = datetime.now(timezone.utc)
        if motivo:
            d["motivo_escalamiento"] = motivo
        return Caso.model_validate(d)
    m = MagicMock()
    m.transicionar = MagicMock(side_effect=_trans)
    return m


@pytest.fixture
def caso():
    return intake_crear_caso(AvisoNormalizado(texto_crudo="Aviso: choque, póliza POL-T.", calidad=CalidadDoc.LIMPIO))


@pytest.fixture(autouse=True)
def _seed_poliza():
    hoy = date.today()
    clausulas = [Clausula(id=i, texto="x", tipo=t, referencia="r") for i, t in [
        ("V", TipoClausula.VIGENCIA), ("C", TipoClausula.COBERTURA),
        ("L", TipoClausula.LIMITE), ("D", TipoClausula.DEDUCIBLE)]]
    set_poliza_store({"POL-T": Poliza(
        numero="POL-T", vigencia=RangoFechas(desde=hoy - timedelta(days=365), hasta=hoy + timedelta(days=365)),
        coberturas_contratadas=["AUTO_COLISION"], exclusiones=[], suma_asegurada=Decimal("100000"),
        deducible=Decimal("1000"), es_soat=False, clausulas=clausulas)})
    yield
    set_poliza_store({})


def _campo(n, v):
    return CampoExtraido(nombre=n, valor=v, origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"),
                         confianza=0.9, ausente=False)


def _extraccion_buena():
    hoy = date.today()
    return ExtraccionValidada(campos=[
        _campo("numero_poliza", "POL-T"), _campo("fecha_siniestro", str(hoy)),
        _campo("tipo_siniestro", "AUTO_COLISION"), _campo("monto_reclamado", "50000")])


def _extraccion_mala():
    """Primera pasada 'dudosa': el monto no cuadra (lo que el Verificador señalará)."""
    hoy = date.today()
    return ExtraccionValidada(campos=[
        _campo("numero_poliza", "POL-T"), _campo("fecha_siniestro", str(hoy)),
        _campo("tipo_siniestro", "AUTO_COLISION"), _campo("monto_reclamado", "999999999")])


_USAGE = {"tokens_in": 300, "tokens_out": 80}
_VERIF_MALA = VerificacionAdversarial(confianza=0.5, inconsistencias=["monto_reclamado"], recomendacion="REVISA")
_VERIF_BUENA = VerificacionAdversarial(confianza=0.95, inconsistencias=[], recomendacion="ACEPTA")


def _cotas(max_rondas):
    return Cotas(max_rondas=max_rondas, presupuesto_tokens=50000)


# ------------------------------------------------------------------ el loop reflexivo

def test_baja_fidelidad_reextrae_una_vez_y_continua(caso, hitl):
    """C3 baja fidelidad → C2 re-extrae UNA vez con feedback → C3 acepta → LISTO_PARA_APROBAR."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_buena(), _USAGE)])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE), (_VERIF_BUENA, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        res = orquestar_fnol(caso, hitl, _cotas(2))

    assert c2.call_count == 2                         # re-extrajo exactamente una vez
    assert c3.call_count == 2                         # y re-verificó
    assert res.estado == EstadoCaso.LISTO_PARA_APROBAR
    # el dictamen final salió del MOTOR sobre la 2ª extracción (monto saneado)
    assert res.dictamen is not None
    assert res.extraccion.campos[-1].valor == "50000"


def test_feedback_lleva_campos_senalados_sin_pii(caso, hitl):
    """La crítica pasada a C2 en la re-extracción cita los campos señalados (sin PII)."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_buena(), _USAGE)])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE), (_VERIF_BUENA, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        orquestar_fnol(caso, hitl, _cotas(2))

    feedback = c2.call_args_list[1].kwargs.get("feedback", "")
    assert "monto_reclamado" in feedback           # cita el campo señalado
    assert "no inventes" in feedback.lower()        # instrucción anti-invención


def test_persiste_baja_fidelidad_escala_no_loopea(caso, hitl):
    """Si tras la re-extracción SIGUE mal → escala (REQUIERE_REVISION) y NO loopea (C2 llamado 2 veces máx)."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_mala(), _USAGE), (_extraccion_mala(), _USAGE)])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE), (_VERIF_MALA, _USAGE), (_VERIF_MALA, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        res = orquestar_fnol(caso, hitl, _cotas(2))

    assert res.estado == EstadoCaso.REQUIERE_REVISION
    assert c2.call_count == 2   # 🔒 cap DURO: a lo sumo una re-extracción (no loopea)


def test_max_rondas_1_no_reextrae_single_pass_intacto(caso, hitl):
    """Retro-compat P4: con max_rondas=1 NO hay re-extracción → escala en una sola pasada (como hoy)."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_buena(), _USAGE)])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE), (_VERIF_BUENA, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        res = orquestar_fnol(caso, hitl, _cotas(1))

    assert c2.call_count == 1   # sin re-extracción
    assert res.estado == EstadoCaso.REQUIERE_REVISION


def test_confianza_ok_pero_inconsistencia_no_reextrae(caso, hitl):
    """El disparo exige confianza < umbral. Si la confianza es alta, no re-extrae aunque haya señal."""
    verif_alta_con_inconsistencia = VerificacionAdversarial(
        confianza=0.9, inconsistencias=["monto_reclamado"], recomendacion="REVISA")
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_buena(), _USAGE)])
    c3 = MagicMock(side_effect=[(verif_alta_con_inconsistencia, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        res = orquestar_fnol(caso, hitl, _cotas(2))

    assert c2.call_count == 1   # confianza 0.9 ≥ umbral → no dispara
    assert res.estado == EstadoCaso.REQUIERE_REVISION
    assert UMBRAL_REEXTRACCION == 0.7


# ------------------------------------------------------------------ 🔒 P2 lock

def test_p2_loop_no_redecide_cobertura_motor_es_el_unico(caso, hitl):
    """🔒 P2: el loop re-extrae CAMPOS; el motor R1-R5 corre UNA vez DESPUÉS y es el único que dictamina."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_buena(), _USAGE)])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE), (_VERIF_BUENA, _USAGE)])
    motor_spy = MagicMock(wraps=__import__("app.rules.motor_r1_r5", fromlist=["motor_cobertura"]).motor_cobertura)
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None), \
         patch("app.orchestrator.c7.motor_cobertura", motor_spy):
        res = orquestar_fnol(caso, hitl, _cotas(2))

    # El motor se invocó UNA sola vez (no una por ronda del loop): el loop no re-decide cobertura.
    assert motor_spy.call_count == 1
    # Y corrió sobre la extracción RE-EXTRAÍDA (fields saneados), no la mala.
    extraccion_usada = motor_spy.call_args.args[0]
    assert next(c.valor for c in extraccion_usada.campos if c.nombre == "monto_reclamado") == "50000"
    assert res.dictamen.resultado in {
        ResultadoCobertura.CUBIERTO, ResultadoCobertura.CUBIERTO_PARCIAL, ResultadoCobertura.NO_CUBIERTO}


def test_reextraccion_falla_escala_fail_closed(caso, hitl):
    """Si la re-extracción revienta → REQUIERE_REVISION (fail-closed), no inventa ni loopea."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), RuntimeError("C2 down")])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        res = orquestar_fnol(caso, hitl, _cotas(2))

    assert res.estado == EstadoCaso.REQUIERE_REVISION
    assert c2.call_count == 2


# ------------------------------------------------------------------ corona (P1)

def test_corona_nunca_terminal_con_loop(caso, hitl):
    """Con el loop activo, el orquestador SIGUE sin producir estados terminales (P1)."""
    c2 = MagicMock(side_effect=[(_extraccion_mala(), _USAGE), (_extraccion_buena(), _USAGE)])
    c3 = MagicMock(side_effect=[(_VERIF_MALA, _USAGE), (_VERIF_BUENA, _USAGE)])
    with patch("app.orchestrator.c7.call_c2_extractor", c2), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", c3), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        res = orquestar_fnol(caso, hitl, _cotas(2))
    assert res.estado not in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
