"""C7 Orchestrator Tests (U4).

CORONA TEST: assert caso_final.estado in {LISTO_PARA_APROBAR, REQUIERE_REVISION}
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch
from datetime import date, timedelta
from decimal import Decimal

from app.contracts.caso import Caso
from app.contracts.enums import (
    EstadoCaso,
    CalidadDoc,
    ResultadoCobertura
)
from app.contracts.dictamen import Cotas
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.orchestrator.c7 import orquestar_fnol


@pytest.fixture
def hitl_service_mock():
    """Mock HITL service."""
    def mock_transicionar(caso, nuevo_estado, actor, motivo=None):
        # Simulate state transition
        caso_dict = caso.model_dump()
        caso_dict["estado"] = nuevo_estado
        caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
        if motivo:
            caso_dict["motivo_escalamiento"] = motivo
        return Caso.model_validate(caso_dict)
    
    mock = MagicMock()
    mock.transicionar = MagicMock(side_effect=mock_transicionar)
    return mock


@pytest.fixture
def aviso_limpio():
    """Clean aviso (LIMPIO)."""
    return AvisoNormalizado(
        texto_crudo="Reclamo de siniestro total.",
        calidad=CalidadDoc.LIMPIO
    )


@pytest.fixture
def caso_recibido(aviso_limpio):
    """Caso in RECIBIDO state."""
    return intake_crear_caso(aviso_limpio)


@pytest.fixture
def cotas_standard():
    """Standard cotas: max_rondas=1, presupuesto_tokens=20000."""
    return Cotas(
        max_rondas=1,
        presupuesto_tokens=20000
    )


def _extraccion_consistente():
    from app.contracts.extraccion import ExtraccionValidada, CampoExtraido, EvidenciaOrigen
    from app.contracts.enums import TipoOrigen
    hoy = date.today()
    def campo(n, v):
        return CampoExtraido(nombre=n, valor=v, origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"), confianza=0.9, ausente=False)
    return ExtraccionValidada(campos=[
        campo("numero_poliza", "POL-T"), campo("fecha_siniestro", str(hoy)),
        campo("tipo_siniestro", "AUTO_COLISION"), campo("monto_reclamado", "50000"),
    ])


@pytest.fixture(autouse=True)
def mock_pipeline():
    """Mockea los componentes LLM (C2/C3/C6) y siembra una póliza para C4/C5 reales.

    Sin esto, el orquestador haría llamadas LLM reales. Con esto, el pipeline
    determinístico (C4/C5) corre de verdad y el flujo llega a LISTO_PARA_APROBAR.
    """
    from app.contracts.poliza import Poliza, Clausula, RangoFechas
    from app.contracts.enums import TipoClausula
    from app.contracts.verificacion import VerificacionAdversarial
    from app.policy.lookup import set_poliza_store

    hoy = date.today()
    clausulas = [Clausula(id=i, texto="x", tipo=t, referencia="r") for i, t in [
        ("V", TipoClausula.VIGENCIA), ("C", TipoClausula.COBERTURA),
        ("L", TipoClausula.LIMITE), ("D", TipoClausula.DEDUCIBLE)]]
    pol = Poliza(numero="POL-T", vigencia=RangoFechas(desde=hoy - timedelta(days=365), hasta=hoy + timedelta(days=365)),
                 coberturas_contratadas=["AUTO_COLISION"], exclusiones=[], suma_asegurada=Decimal("100000"),
                 deducible=Decimal("1000"), es_soat=False, clausulas=clausulas)
    set_poliza_store({"POL-T": pol})

    # C3 capa2 NO se mockea: es determinística (sin LLM), corre real para validar la integración.
    with patch("app.orchestrator.c7.call_c2_extractor", return_value=(_extraccion_consistente(), {"tokens_in": 400, "tokens_out": 100})), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1", return_value=(VerificacionAdversarial(confianza=0.95, inconsistencias=[], recomendacion="ACEPTA"), {"tokens_in": 300, "tokens_out": 80})), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):
        yield


def test_orquestador_happy_path(caso_recibido, hitl_service_mock, cotas_standard):
    """Happy path REAL: C2(mock)→C3(mock)→C4(real)→C5(real motor)→C6(mock) → LISTO_PARA_APROBAR.

    El dictamen sale del motor real; la póliza la encuentra C4 real (store sembrado).
    """
    resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)

    assert resultado.estado == EstadoCaso.LISTO_PARA_APROBAR
    assert resultado.extraccion is not None and len(resultado.extraccion.campos) == 4
    assert resultado.poliza_match is not None and resultado.poliza_match.encontrada is True
    assert resultado.dictamen is not None and resultado.dictamen.resultado == ResultadoCobertura.CUBIERTO_PARCIAL


def test_orquestador_nunca_produce_aprobado(caso_recibido, hitl_service_mock, cotas_standard):
    """Orquestador NUNCA produce APROBADO (P1 HITL)."""
    resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)
    
    assert resultado.estado != EstadoCaso.APROBADO, \
        "Orquestador es prohibido producir APROBADO (es terminal, requiere humano)"


def test_orquestador_nunca_produce_rechazado(caso_recibido, hitl_service_mock, cotas_standard):
    """Orquestador NUNCA produce RECHAZADO (P1 HITL)."""
    resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)
    
    assert resultado.estado != EstadoCaso.RECHAZADO, \
        "Orquestador es prohibido producir RECHAZADO (es terminal, requiere humano)"


def test_orquestador_transiciones_a_en_proceso(caso_recibido, hitl_service_mock, cotas_standard):
    """Orquestador ALWAYS transitions RECIBIDO → EN_PROCESO on entry."""
    resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)
    
    # Verify the first transition happened (transicionar was called)
    assert resultado.estado != EstadoCaso.RECIBIDO, \
        "Orquestador debe transicionar desde RECIBIDO"


def test_orquestador_corona_test_all_paths(caso_recibido, hitl_service_mock, cotas_standard):
    """CORONA TEST: all paths must end in {LISTO_PARA_APROBAR, REQUIERE_REVISION}."""
    # This is the fundamental P1 guard rail
    resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)
    
    assert resultado.estado in {
        EstadoCaso.LISTO_PARA_APROBAR,
        EstadoCaso.REQUIERE_REVISION
    }, "CORONA TEST: orquestador violó P1 (produjo terminal)"


def test_orquestador_respeta_max_rondas(caso_recibido, hitl_service_mock):
    """Orquestador respeta cotas internos (verificable via mock call count)."""
    # Cotas debe tener max_rondas ≥ 1 (Pydantic gt=0)
    cotas = Cotas(max_rondas=1, presupuesto_tokens=20000)
    
    resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas)
    
    # Verify loop entered and transicionar called at least once
    assert hitl_service_mock.transicionar.call_count >= 1, \
        "Orquestador debe llamar transicionar al menos una vez"


def test_orquestador_fail_closed_on_exception(caso_recibido, hitl_service_mock, cotas_standard):
    """Orquestador es fail-closed: excepciones internas → RuntimeError (nunca silent)."""
    # Mock transicionar to raise on second call
    call_count = [0]
    
    def raise_on_second_call(caso, nuevo_estado, actor, motivo=None):
        call_count[0] += 1
        if call_count[0] > 1:
            raise ValueError("Simulated internal error")
        caso_dict = caso.model_dump()
        caso_dict["estado"] = nuevo_estado
        caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
        if motivo:
            caso_dict["motivo_escalamiento"] = motivo
        return Caso.model_validate(caso_dict)
    
    hitl_service_mock.transicionar = MagicMock(side_effect=raise_on_second_call)
    
    # Orquestador should catch and re-raise as RuntimeError
    with pytest.raises(RuntimeError):
        orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)


def test_orquestador_c2_falla_escala(caso_recibido, hitl_service_mock, cotas_standard):
    """Si C2 (extracción) falla → REQUIERE_REVISION (fail-closed, no inventar)."""
    from app.llm.extractor import ExtractorError
    with patch("app.orchestrator.c7.call_c2_extractor", side_effect=ExtractorError("boom")):
        resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)
    assert resultado.estado == EstadoCaso.REQUIERE_REVISION


def test_orquestador_confianza_baja_escala(caso_recibido, hitl_service_mock, cotas_standard):
    """Si C3 verificación confianza < umbral → REQUIERE_REVISION (P4 escala, no cierra)."""
    from app.contracts.verificacion import VerificacionAdversarial
    with patch("app.orchestrator.c7.call_c3_verifier_capa1",
               return_value=(VerificacionAdversarial(confianza=0.30, inconsistencias=[], recomendacion="REVISA"),
                             {"tokens_in": 10, "tokens_out": 5})):
        resultado = orquestar_fnol(caso_recibido, hitl_service_mock, cotas_standard)
    assert resultado.estado == EstadoCaso.REQUIERE_REVISION
