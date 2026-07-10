"""Tests U6 — Fraude cross-claim (capa 4). 🔒 P6.

Cubre: foto reutilizada (pHash/Hamming), frecuencia, umbrales, confianza (P7), evidencia sin PII (P5),
reproducibilidad de la huella, y el invariante ABSOLUTO P6: ninguna señal cross-claim cambia el estado
ni deshabilita la firma — ni con foto idéntica (distancia 0).
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from pydantic import ValidationError

from app.contracts.dictamen import AlertaFraude
from app.contracts.enums import EstadoCaso
from app.contracts.extraccion import EvidenciaOrigen, TipoOrigen
from app.dashboard.store import get_caso_repository
from app.demo.seed import seed_demo_casos
from app.fraud.cross_claim import (
    CAPA_CROSS_CLAIM,
    FRECUENCIA_MIN,
    HAMMING_ALTA,
    construir_alerta_cross_claim,
    detectar_foto_reutilizada,
    detectar_frecuencia,
    huella_perceptual,
)
from app.fraud.historia import HuellaStore


# ---------------------------------------------------------------- helpers herméticos

def _campo(nombre, valor):
    return SimpleNamespace(nombre=nombre, valor=valor, ausente=False)


def _caso_fake(caso_id, numero_poliza, dias_atras=0):
    ts = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return SimpleNamespace(
        id=caso_id,
        extraccion=SimpleNamespace(campos=[_campo("numero_poliza", numero_poliza)]),
        timestamp_actualizacion=ts,
    )


class _FakeRepo:
    def __init__(self, casos):
        self._casos = casos

    def list(self, limite=None):
        return self._casos[: limite] if limite else list(self._casos)


# ---------------------------------------------------------------- huella reproducible

def test_huella_perceptual_reproducible():
    """pHash reproducible (P7): mismos bytes → misma huella; bytes idénticos → distancia 0."""
    a = huella_perceptual(b"foto-siniestro-123")
    b = huella_perceptual(b"foto-siniestro-123")
    assert a == b                       # determinístico, sin seed
    assert len(a) == 16 and int(a, 16) >= 0  # hex estable


def test_huella_perceptual_distingue():
    assert huella_perceptual(b"foto-A") != huella_perceptual(b"foto-B")


# ---------------------------------------------------------------- foto reutilizada

def test_foto_reutilizada_identica_emite_senal_citando_caso_previo():
    """Dos siniestros con la MISMA foto → señal citando el caso previo (distancia 0)."""
    store = HuellaStore()
    h = huella_perceptual(b"la-misma-foto")
    store.registrar(h, "caso-previo")
    señales = detectar_foto_reutilizada(h, store, caso_id="caso-actual")
    assert len(señales) == 1
    s = señales[0]
    assert "caso-previo" in s.evidencia.referencia
    assert "distancia 0" in s.evidencia.referencia
    assert s.severidad == "ALTA"
    assert 0.0 < s.confianza < 1.0  # P7: alta pero NUNCA veredicto


def test_foto_reutilizada_excluye_el_propio_caso():
    store = HuellaStore()
    h = huella_perceptual(b"foto")
    store.registrar(h, "caso-actual")  # el propio caso registró su huella
    assert detectar_foto_reutilizada(h, store, caso_id="caso-actual") == []


def test_foto_parcialmente_similar_senal_media():
    """Distancia 4-7 → severidad MEDIA (near-duplicado), confianza en [0,1)."""
    store = HuellaStore()
    store.registrar("0000000000000000", "caso-previo")   # 64 bits en 0
    # 0x1f = 0b11111 = 5 bits distintos → distancia de Hamming 5 (dentro de 4-7 → MEDIA)
    señales = detectar_foto_reutilizada("000000000000001f", store, "caso-actual")
    assert len(señales) == 1
    assert señales[0].severidad == "MEDIA"
    assert "distancia 5" in señales[0].evidencia.referencia
    assert 0.0 < señales[0].confianza < 1.0


def test_foto_distinta_sin_senal():
    """Distancia ≥ 8 (huellas no relacionadas) → no es señal."""
    store = HuellaStore()
    store.registrar(huella_perceptual(b"foto-A"), "caso-previo")
    señales = detectar_foto_reutilizada(huella_perceptual(b"otra-cosa-totalmente"), store, "caso-actual")
    assert señales == []


def test_sin_hash_no_consulta():
    assert detectar_foto_reutilizada("", HuellaStore(), "caso-actual") == []


# ---------------------------------------------------------------- frecuencia

def test_frecuencia_emite_senal_con_conteo():
    """≥ FRECUENCIA_MIN siniestros de la misma póliza en la ventana → señal con el conteo."""
    pol = "POL-999"
    # FRECUENCIA_MIN-1 previos + el actual = FRECUENCIA_MIN
    previos = [_caso_fake(f"c{i}", pol, dias_atras=30 * i) for i in range(FRECUENCIA_MIN - 1)]
    repo = _FakeRepo(previos)
    señales = detectar_frecuencia(repo, pol, caso_id="c-actual")
    assert len(señales) == 1
    assert f"{FRECUENCIA_MIN} siniestros" in señales[0].evidencia.referencia
    assert 0.0 < señales[0].confianza <= 0.9


def test_frecuencia_bajo_umbral_sin_senal():
    """Menos del umbral → no dispara."""
    pol = "POL-111"
    repo = _FakeRepo([_caso_fake("c0", pol)])  # 1 previo + actual = 2 < 3
    assert detectar_frecuencia(repo, pol, caso_id="c-actual") == []


def test_frecuencia_sin_poliza_no_consulta():
    assert detectar_frecuencia(_FakeRepo([]), None, "c-actual") == []


# ---------------------------------------------------------------- alerta agregada

def test_construir_alerta_cross_claim_agrega_capa_4():
    store = HuellaStore()
    h = huella_perceptual(b"foto-compartida")
    store.registrar(h, "caso-previo")
    alerta = construir_alerta_cross_claim(
        caso_id="caso-actual", hash_media=h, huella_store=store,
    )
    assert isinstance(alerta, AlertaFraude)
    assert alerta.capa == CAPA_CROSS_CLAIM
    assert alerta.severidad == "ALTA"
    assert 0.0 < alerta.confianza < 1.0
    assert len(alerta.inconsistencias) >= 1


def test_sin_senales_retorna_none():
    """P7: cero señales → None (nunca una alerta vacía)."""
    assert construir_alerta_cross_claim(caso_id="c", hash_media="", huella_store=HuellaStore()) is None
    assert construir_alerta_cross_claim(caso_id="c") is None  # sin repo ni store


def test_evidencia_sin_pii():
    """P5: la evidencia referencia solo caso_id (uuid opaco), nunca PII (cédula/placa/nombre)."""
    store = HuellaStore()
    h = huella_perceptual(b"foto")
    store.registrar(h, "caso-previo-uuid")
    alerta = construir_alerta_cross_claim(caso_id="actual", hash_media=h, huella_store=store)
    ref = alerta.inconsistencias[0].referencia
    assert "caso-previo-uuid" in ref
    # No hay marcadores de PII en la referencia.
    for pii in ("cédula", "cedula", "placa", "nombre", "cc ", "@"):
        assert pii not in ref.lower()


# ---------------------------------------------------------------- 🔒 P6 fail-closed (obligatorio)

def _caso_real_listo():
    """Un Caso REAL (no mock) en LISTO_PARA_APROBAR, desde el seed hermético (PERSISTENCE=memory)."""
    seed_demo_casos()
    for c in get_caso_repository().list():
        if c.estado == EstadoCaso.LISTO_PARA_APROBAR:
            return c
    raise AssertionError("el seed no produjo ningún caso LISTO_PARA_APROBAR")


def test_p6_foto_identica_no_cambia_estado_ni_firma():
    """🔒 P6 ABSOLUTO (fail-closed real): foto idéntica (distancia 0, la señal más fuerte) → alerta emitida,
    pero el estado del Caso NO cambia y la ruta de mutación de estado sigue blindada (RULE-CTR-05).
    """
    store = HuellaStore()
    h = huella_perceptual(b"foto-identica")
    store.registrar(h, "caso-previo")

    caso = _caso_real_listo()  # Caso REAL, no SimpleNamespace
    assert caso.estado == EstadoCaso.LISTO_PARA_APROBAR

    # La señal MÁS fuerte posible. La función recibe caso_id (str) y devuelve AlertaFraude:
    # es imposible por firma que reciba o retorne un Caso mutado.
    alerta = construir_alerta_cross_claim(caso_id=caso.id, hash_media=h, huella_store=store)
    assert isinstance(alerta, AlertaFraude) and alerta.severidad == "ALTA"

    # Adjuntar la alerta (como haría C6/C7, informativo) NO altera el estado.
    caso_con_alerta = caso.model_copy(update={"alerta_fraude": alerta})
    assert caso_con_alerta.estado == EstadoCaso.LISTO_PARA_APROBAR  # ⇏ estado terminal
    assert caso_con_alerta.alerta_fraude is alerta

    # 🔒 El único camino a un estado terminal está blindado: ni con la señal más fuerte adjunta
    # se puede escribir el estado por fuera de HITL (RULE-CTR-05 lanza).
    with pytest.raises(ValueError, match="frozen"):
        caso_con_alerta.estado = EstadoCaso.RECHAZADO


def test_contrato_rechaza_confianza_1_0():
    """🔒 P7 fail-closed: el contrato PROHÍBE confianza=1.0 (veredicto). Pydantic lo rechaza (lt=1.0)."""
    with pytest.raises(ValidationError):
        AlertaFraude(
            severidad="ALTA",
            inconsistencias=[EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia="x")],
            explicacion="x",
            confianza=1.0,
        )


def test_confianza_nunca_es_1_ni_supera_1():
    """P7: toda señal es sugerencia con confianza [0,1), nunca verdad absoluta."""
    store = HuellaStore()
    h = huella_perceptual(b"x")
    store.registrar(h, "prev")
    alerta = construir_alerta_cross_claim(caso_id="c", hash_media=h, huella_store=store)
    assert 0.0 <= alerta.confianza < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
