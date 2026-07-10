"""Tests U10 — Wiring del fraude cross-claim al pipeline. 🔒 P4 · P6.

Cubre: frecuencia visible via orquestador; 🔒 P6 (señal cross-claim ⇏ estado terminal, corona intacta);
merge intra+cross; retro-compat (sin señal → comportamiento de hoy); `combinar_alertas`; singleton + lock.
"""

import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.contracts.caso import Caso
from app.contracts.dictamen import AlertaFraude, Cotas
from app.contracts.enums import (
    CalidadDoc, EstadoCaso, ResultadoCobertura, TipoClausula, TipoOrigen,
)
from app.contracts.extraccion import (
    AvisoNormalizado, CampoExtraido, EvidenciaOrigen, ExtraccionValidada,
)
from app.contracts.poliza import Clausula, Poliza, RangoFechas
from app.dashboard.store import get_caso_repository, reset_caso_repository
from app.fraud.cross_claim import CAPA_CROSS_CLAIM, combinar_alertas
from app.fraud.historia import get_huella_store, reset_huella_store
from app.intake.c1 import intake_crear_caso
from app.orchestrator.c7 import orquestar_fnol
from app.policy.lookup import set_poliza_store


# ------------------------------------------------------------------ combinar_alertas (unit)

def _alerta(sev, conf, capa, refs):
    return AlertaFraude(
        severidad=sev, confianza=conf, capa=capa,
        inconsistencias=[EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia=r) for r in refs],
        explicacion=f"alerta {sev}")


def test_combinar_none_none_es_none():
    assert combinar_alertas(None, None) is None


def test_combinar_una_sola_pasa_igual():
    a = _alerta("MEDIA", 0.8, 1, ["X"])
    assert combinar_alertas(a, None) is a
    assert combinar_alertas(None, a) is a


def test_combinar_funde_max_y_une_inconsistencias():
    intra = _alerta("MEDIA", 0.99, 1, ["INTRA_1"])
    cross = _alerta("ALTA", 0.9, CAPA_CROSS_CLAIM, ["CROSS_1"])
    m = combinar_alertas(intra, cross)
    assert m.severidad == "ALTA"                     # max
    assert m.confianza == 0.99                        # max
    assert m.capa == CAPA_CROSS_CLAIM                 # max
    refs = {i.referencia for i in m.inconsistencias}
    assert refs == {"INTRA_1", "CROSS_1"}            # unidas, ninguna se pisa


# ------------------------------------------------------------------ singleton + lock

def test_get_huella_store_singleton():
    reset_huella_store()
    assert get_huella_store() is get_huella_store()


def test_huella_store_registro_concurrente_no_crashea():
    """Smoke de thread-safety: 200 registros desde 10 hilos no rompen el índice (lock)."""
    reset_huella_store()
    store = get_huella_store()
    store.clear()

    def _worker(n):
        for i in range(20):
            store.registrar(f"{n:04x}{i:012x}", f"caso-{n}-{i}")

    hilos = [threading.Thread(target=_worker, args=(n,)) for n in range(10)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    # 10 hilos × 20 = 200 registros, NINGUNO perdido por race (distancia_max=64 = todo matchea).
    encontrados = store.buscar("0000000000000000", distancia_max=64, limite=10_000)
    assert len(encontrados) == 200  # el lock evitó pérdidas por escritura concurrente
    store.clear()


# ------------------------------------------------------------------ integración via orquestador

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


def _campo(n, v):
    return CampoExtraido(nombre=n, valor=v, origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="s"),
                         confianza=0.9, ausente=False)


def _extraccion_polt():
    hoy = date.today()
    return ExtraccionValidada(campos=[
        _campo("numero_poliza", "POL-T"), _campo("fecha_siniestro", str(hoy)),
        _campo("tipo_siniestro", "AUTO_COLISION"), _campo("monto_reclamado", "50000")])


@pytest.fixture(autouse=True)
def _entorno():
    reset_caso_repository()
    reset_huella_store()
    hoy = date.today()
    clausulas = [Clausula(id=i, texto="x", tipo=t, referencia="r") for i, t in [
        ("V", TipoClausula.VIGENCIA), ("C", TipoClausula.COBERTURA),
        ("L", TipoClausula.LIMITE), ("D", TipoClausula.DEDUCIBLE)]]
    set_poliza_store({"POL-T": Poliza(
        numero="POL-T", vigencia=RangoFechas(desde=hoy - timedelta(days=365), hasta=hoy + timedelta(days=365)),
        coberturas_contratadas=["AUTO_COLISION"], exclusiones=[], suma_asegurada=Decimal("100000"),
        deducible=Decimal("1000"), es_soat=False, clausulas=clausulas)})
    yield
    reset_caso_repository()
    reset_huella_store()
    set_poliza_store({})


def _sembrar_casos_polt(n):
    """Guarda n casos previos de la póliza POL-T en el repo (para la señal de frecuencia)."""
    repo = get_caso_repository()
    for _ in range(n):
        c = intake_crear_caso(AvisoNormalizado(texto_crudo="prev POL-T", calidad=CalidadDoc.LIMPIO))
        repo.save(c.model_copy(update={"extraccion": _extraccion_polt()}))


def _orquestar_caso_polt(hitl):
    caso = intake_crear_caso(AvisoNormalizado(texto_crudo="Choque POL-T.", calidad=CalidadDoc.LIMPIO))
    with patch("app.orchestrator.c7.call_c2_extractor", return_value=(_extraccion_polt(), {"tokens_in": 400, "tokens_out": 100})), \
         patch("app.orchestrator.c7.call_c3_verifier_capa1",
               return_value=(__import__("app.contracts.verificacion", fromlist=["VerificacionAdversarial"]).VerificacionAdversarial(
                   confianza=0.95, inconsistencias=[], recomendacion="ACEPTA"), {"tokens_in": 300, "tokens_out": 80})), \
         patch("app.orchestrator.c7.construir_alerta_fraude", return_value=None):  # intra=None → aísla la señal cross-claim
        return orquestar_fnol(caso, hitl, Cotas(max_rondas=1, presupuesto_tokens=50000))


def test_frecuencia_visible_en_alerta_via_pipeline(hitl):
    """≥3 casos de la póliza → la alerta cross-claim (capa 4) aparece con la señal de frecuencia."""
    _sembrar_casos_polt(2)  # + el caso actual = 3
    res = _orquestar_caso_polt(hitl)
    assert res.alerta_fraude is not None
    assert res.alerta_fraude.capa == CAPA_CROSS_CLAIM
    assert any("FRECUENCIA" in i.referencia for i in res.alerta_fraude.inconsistencias)


def test_p6_senal_cross_claim_no_cambia_estado(hitl):
    """🔒 P6: aun con señal de frecuencia, el caso queda LISTO_PARA_APROBAR (no terminal); corona intacta."""
    _sembrar_casos_polt(2)
    res = _orquestar_caso_polt(hitl)
    assert res.alerta_fraude is not None                       # señal emitida
    assert res.estado == EstadoCaso.LISTO_PARA_APROBAR         # ⇏ estado terminal
    assert res.estado not in {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


def test_snapshot_ciclos_ignora_alerta_fraude(hitl):
    """🔒 P4 (regresión): la alerta_fraude NO entra al snapshot de ciclos → adjuntarla no es 'progreso'
    ni un falso 'sin progreso'. Blinda contra que alguien la agregue al hash a futuro.
    """
    from app.orchestrator.c7 import _snapshot_caso

    caso = intake_crear_caso(AvisoNormalizado(texto_crudo="x", calidad=CalidadDoc.LIMPIO))
    snap1 = _snapshot_caso(caso)
    con_alerta = caso.model_copy(update={"alerta_fraude": _alerta("MEDIA", 0.8, CAPA_CROSS_CLAIM, ["FRECUENCIA: 3"])})
    assert _snapshot_caso(con_alerta) == snap1  # alerta_fraude no afecta el snapshot


def test_retrocompat_sin_frecuencia_no_hay_senal(hitl):
    """Póliza con < 3 casos → sin señal cross-claim; el caso queda como hoy (sin alerta)."""
    _sembrar_casos_polt(1)  # + actual = 2 < 3
    res = _orquestar_caso_polt(hitl)
    assert res.alerta_fraude is None                           # intra=None y cross tampoco disparó
    assert res.estado == EstadoCaso.LISTO_PARA_APROBAR
    assert res.dictamen.resultado in {
        ResultadoCobertura.CUBIERTO, ResultadoCobertura.CUBIERTO_PARCIAL, ResultadoCobertura.NO_CUBIERTO}


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
