"""Tests U5 — historia + consultas cross-claim. Cotas P4, footprints sin PII (P5), huellas por distancia."""

from app.fraud.historia import (
    casos_por_poliza, Footprint, HuellaStore, _hamming_hex, LIMITE_CONSULTA,
)
from app.demo.seed import seed_demo_casos
from app.dashboard.store import get_caso_repository


def _repo():
    seed_demo_casos()
    return get_caso_repository()


# ---------- Consultas cross-claim ----------

def test_casos_por_poliza_footprint_sin_pii():
    """Devuelve Footprints (caso_id, póliza, fecha) — NUNCA el Caso con texto_crudo (P5)."""
    repo = _repo()
    poliza = next((_p for c in repo.list() if (_p := next(
        (x.valor for x in c.extraccion.campos if x.nombre == "numero_poliza" and not x.ausente), None))), None)
    fps = casos_por_poliza(repo, poliza)
    assert all(isinstance(f, Footprint) for f in fps)
    assert all(not hasattr(f, "texto_crudo") and not hasattr(f, "aviso") for f in fps)  # sin PII


def test_casos_por_poliza_respeta_cota():
    """P4: la consulta nunca devuelve más que `limite`."""
    repo = _repo()
    poliza = next((_p for c in repo.list() if (_p := next(
        (x.valor for x in c.extraccion.campos if x.nombre == "numero_poliza" and not x.ausente), None))), None)
    fps = casos_por_poliza(repo, poliza, limite=1)
    assert len(fps) <= 1


def test_casos_por_poliza_ventana():
    """Fuera de la ventana temporal no aparece."""
    repo = _repo()
    poliza = next((_p for c in repo.list() if (_p := next(
        (x.valor for x in c.extraccion.campos if x.nombre == "numero_poliza" and not x.ausente), None))), None)
    assert casos_por_poliza(repo, poliza, ventana_dias=-1) == []  # ventana en el pasado → nada


def test_poliza_vacia_no_consulta():
    assert casos_por_poliza(_repo(), "") == []


# ---------- Huellas perceptuales ----------

def test_hamming_hex():
    assert _hamming_hex("ff", "ff") == 0
    assert _hamming_hex("ff", "fe") == 1   # un bit distinto
    assert _hamming_hex("ff", "fff") == 10**9  # longitudes distintas → inf


def test_hamming_hex_invalido_no_crashea():
    """Fail-closed: hex inválido/vacío → inf (no crashea)."""
    assert _hamming_hex("gg", "ff") == 10**9   # no es hex
    assert _hamming_hex("", "ff") == 10**9     # vacío


def test_casos_por_entidad_stub_vacio():
    """Por entidad hoy devuelve [] (placa/tercero requieren extracción rica de U4, P7)."""
    from app.fraud.historia import casos_por_entidad
    assert casos_por_entidad(_repo(), "ABC123") == []


def test_huella_match_por_distancia():
    """Foto reutilizada: una huella idéntica (distancia 0) o cercana se detecta; lejana no."""
    st = HuellaStore()
    st.registrar("aabbccdd", "SIN-1")
    st.registrar("00000000", "SIN-2")
    m = st.buscar("aabbccdd", distancia_max=3)  # idéntica
    assert m and m[0][0] == "SIN-1" and m[0][1] == 0
    assert st.buscar("ffffffff", distancia_max=3) == []  # muy lejana → sin match


def test_huella_excluye_el_propio_caso():
    st = HuellaStore()
    st.registrar("aabbccdd", "SIN-1")
    assert st.buscar("aabbccdd", excluir_id="SIN-1") == []  # no se auto-detecta
