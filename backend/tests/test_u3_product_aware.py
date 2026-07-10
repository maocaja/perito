"""Tests U3 — cobertura product-aware (motor R1-R5 por cobertura).

Verifica: sublímite/deducible/exclusiones POR cobertura, R3 exclusiones (antes era `pass`), tope SOAT en
SMMLV, cita específica en el Dictamen, y retro-compat con el modelo plano. P2: cero LLM; el motor decide.
"""

from datetime import date
from decimal import Decimal

from app.contracts.enums import ResultadoCobertura, TipoClausula
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen, ExtraccionValidada, TipoOrigen
from app.contracts.poliza import Clausula, CoberturaContratada, Poliza, RangoFechas, ResultadoPoliza
from app.rules.motor_r1_r5 import motor_cobertura, SMMLV_2026


def _clausulas():
    return [
        Clausula(id="VIG-1", texto="Vigencia 2026", tipo=TipoClausula.VIGENCIA, referencia="Sec 2.1"),
        Clausula(id="COB-1", texto="Coberturas del producto", tipo=TipoClausula.COBERTURA, referencia="Sec 3"),
        Clausula(id="EXC-1", texto="Exclusiones", tipo=TipoClausula.EXCLUSION, referencia="Sec 4"),
        Clausula(id="DED-1", texto="Deducible", tipo=TipoClausula.DEDUCIBLE, referencia="Sec 5"),
    ]


def _poliza_pa(coberturas, producto="Hogar"):
    return ResultadoPoliza(encontrada=True, poliza=Poliza(
        numero="POL-PA-1",
        vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2026, 12, 31)),
        suma_asegurada=Decimal("1"), deducible=Decimal("1"),  # planos irrelevantes (product-aware gana)
        clausulas=_clausulas(), producto=producto, coberturas=coberturas))


def _extraccion(tipo, monto):
    def campo(n, v):
        return CampoExtraido(nombre=n, valor=v, confianza=1.0, ausente=False,
                             origen=EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia=f"span:{n}"))
    return ExtraccionValidada(campos=[
        campo("numero_poliza", "POL-PA-1"), campo("fecha_siniestro", "2026-06-01"),
        campo("tipo_siniestro", tipo), campo("monto_reclamado", str(monto))])


def test_sublimite_por_cobertura():
    """Cada cobertura aplica SU sublímite (no la suma de la póliza)."""
    cobs = [
        CoberturaContratada(nombre="HOGAR_AGUA", sublimite=Decimal("10000000"), deducible=Decimal("0")),
        CoberturaContratada(nombre="HOGAR_INCENDIO", sublimite=Decimal("200000000"), deducible=Decimal("0")),
    ]
    # Agua con monto 50M → limitado a 10M (sublímite de AGUA)
    d = motor_cobertura(_extraccion("HOGAR_AGUA", 50000000), _poliza_pa(cobs))
    assert d.sublimite_aplicado == Decimal("10000000")
    assert d.cobertura_aplicada == "HOGAR_AGUA"
    assert d.resultado == ResultadoCobertura.CUBIERTO_PARCIAL  # 50M reclamado, 10M cubierto
    # Incendio con monto 50M → NO limitado (sublímite 200M) → cubierto
    d2 = motor_cobertura(_extraccion("HOGAR_INCENDIO", 50000000), _poliza_pa(cobs))
    assert d2.sublimite_aplicado == Decimal("200000000")
    assert d2.resultado == ResultadoCobertura.CUBIERTO


def test_r3_exclusion_real():
    """R3 (antes `pass`): si el tipo está excluido de la cobertura → NO_CUBIERTO regla R3_EXCLUSION."""
    cobs = [CoberturaContratada(nombre="HOGAR_AGUA", sublimite=Decimal("10000000"),
                                deducible=Decimal("0"), exclusiones=["HOGAR_AGUA"])]
    d = motor_cobertura(_extraccion("HOGAR_AGUA", 5000000), _poliza_pa(cobs))
    assert d.resultado == ResultadoCobertura.NO_CUBIERTO
    assert d.regla_aplicada == "R3_EXCLUSION"


def test_soat_tope_smmlv():
    """SOAT: el límite efectivo topa en n·SMMLV, no en el sublímite nominal."""
    # sublímite nominal ENORME (10.000M) > tope 800·SMMLV (~1.299M) → el tope SMMLV manda
    cobs = [CoberturaContratada(nombre="SOAT_GASTOS_MEDICOS", sublimite=Decimal("10000000000"),
                                deducible=Decimal("0"), tope_smmlv=800)]
    d = motor_cobertura(_extraccion("SOAT_GASTOS_MEDICOS", 10000000000), _poliza_pa(cobs, producto="SOAT"))
    assert d.sublimite_aplicado == Decimal(800) * SMMLV_2026  # topado en SMMLV, no en el nominal


def test_cobertura_no_contratada_no_cubierto():
    """Product-aware: un tipo sin cobertura en el producto → NO_CUBIERTO (R2)."""
    cobs = [CoberturaContratada(nombre="HOGAR_AGUA", sublimite=Decimal("10000000"), deducible=Decimal("0"))]
    d = motor_cobertura(_extraccion("HOGAR_INCENDIO", 5000000), _poliza_pa(cobs))
    assert d.resultado == ResultadoCobertura.NO_CUBIERTO
    assert d.regla_aplicada == "R2_COBERTURA"


def _poliza_plana(coberturas, suma, deducible, exclusiones=None):
    return ResultadoPoliza(encontrada=True, poliza=Poliza(
        numero="POL-PLANO", vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2026, 12, 31)),
        coberturas_contratadas=coberturas, exclusiones=exclusiones or [],
        suma_asegurada=suma, deducible=deducible, clausulas=_clausulas()))


def test_retro_compat_valores_exactos():
    """Retro-compat EXACTA (modelo plano): montos y resultado concretos, no genéricos."""
    plano = _poliza_plana(["AUTO_COLISION"], Decimal("10000000"), Decimal("500000"))
    # monto 5M < suma 10M, deducible 500k → pago 4.5M < reclamado 5M → PARCIAL, deducible aplicado 500k
    d = motor_cobertura(_extraccion("AUTO_COLISION", 5000000), plano)
    assert d.resultado == ResultadoCobertura.CUBIERTO_PARCIAL
    assert d.deducible_calculado == Decimal("500000")
    assert d.cobertura_aplicada is None  # plano no cita cobertura específica
    # monto 5M, deducible 0 → pago 5M == reclamado → CUBIERTO
    d2 = motor_cobertura(_extraccion("AUTO_COLISION", 5000000), _poliza_plana(["AUTO_COLISION"], Decimal("10000000"), Decimal("0")))
    assert d2.resultado == ResultadoCobertura.CUBIERTO


def test_r3_no_dispara_sin_exclusiones():
    """Retro-compat: sin exclusiones, R3 NO cambia el resultado (antes era `pass`, sigue sin bloquear)."""
    plano = _poliza_plana(["AUTO_COLISION"], Decimal("10000000"), Decimal("0"), exclusiones=[])
    d = motor_cobertura(_extraccion("AUTO_COLISION", 5000000), plano)
    assert d.regla_aplicada != "R3_EXCLUSION"


def test_producto_no_modelado_escala():
    """P7/§7: producto declarado, no modelado y sin coberturas → REQUIERE_REVISION (no finge cobertura)."""
    p = ResultadoPoliza(encontrada=True, poliza=Poliza(
        numero="POL-X", vigencia=RangoFechas(desde=date(2026, 1, 1), hasta=date(2026, 12, 31)),
        coberturas_contratadas=["VIDA_MUERTE"], suma_asegurada=Decimal("1"), deducible=Decimal("0"),
        clausulas=_clausulas(), producto="Vida"))  # 'Vida' no está en PRODUCTOS_MODELADOS
    d = motor_cobertura(_extraccion("VIDA_MUERTE", 1000000), p)
    assert d.resultado == ResultadoCobertura.REQUIERE_REVISION
    assert d.regla_aplicada == "PRODUCTO_NO_MODELADO"


def test_motor_no_usa_llm():
    """P2 fail-closed: el motor es puro — no IMPORTA ni instancia el cliente LLM (el docstring puede citarlo)."""
    import inspect
    import app.rules.motor_r1_r5 as m
    src = inspect.getsource(m)
    assert "import anthropic" not in src
    assert "from anthropic" not in src
    assert "Anthropic(" not in src
