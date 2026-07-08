"""T3 Evals Harness — inputs consistentes + ejecución de componentes reales.

A diferencia de la versión tautológica previa, estos builders producen
(extraccion, poliza) CONSISTENTES para que los evals EJECUTEN C4/C5/C6 reales
y comparen la salida contra el resultado esperado (coverage-match, fraude P/R).

El generador sintético se mantiene para los tests de RULE-GEN-02.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.contracts.enums import TipoClausula
from app.contracts.extraccion import ExtraccionValidada, CampoExtraido
from app.contracts.poliza import Poliza, Clausula, RangoFechas
from app.synthetic.generator import SyntheticCaseGenerator


def _clausulas_completas() -> list[Clausula]:
    """Cláusulas que el motor R1-R5 cita: VIGENCIA, COBERTURA, LIMITE, DEDUCIBLE.

    El motor exige la cláusula DEDUCIBLE (R5), así que una póliza sin ella
    escalaría a REQUIERE_REVISION. Estas 4 permiten llegar a un dictamen terminal.
    """
    return [
        Clausula(id="VIG-1", texto="Vigencia de la póliza", tipo=TipoClausula.VIGENCIA, referencia="Sec. 2.1"),
        Clausula(id="COB-1", texto="Cobertura de colisión", tipo=TipoClausula.COBERTURA, referencia="Sec. 3.2"),
        Clausula(id="LIM-1", texto="Límite de indemnización", tipo=TipoClausula.LIMITE, referencia="Sec. 4.1"),
        Clausula(id="DED-1", texto="Deducible aplicable", tipo=TipoClausula.DEDUCIBLE, referencia="Sec. 5.1"),
    ]


def build_poliza(
    numero: str = "POL-0001",
    coberturas=("AUTO_COLISION",),
    suma: str = "100000",
    deducible: str = "1000",
    vigencia_dias: int = 365,
    es_soat: bool = False,
) -> Poliza:
    """Póliza consistente con las 4 cláusulas que el motor cita."""
    hoy = date.today()
    return Poliza(
        numero=numero,
        vigencia=RangoFechas(
            desde=hoy - timedelta(days=vigencia_dias),
            hasta=hoy + timedelta(days=vigencia_dias),
        ),
        coberturas_contratadas=list(coberturas),
        exclusiones=[],
        suma_asegurada=Decimal(suma),
        deducible=Decimal(deducible),
        es_soat=es_soat,
        clausulas=_clausulas_completas(),
    )


def build_extraccion(
    numero: str = "POL-0001",
    fecha: str | None = None,
    tipo: str = "AUTO_COLISION",
    monto: str = "50000",
    ausentes=(),
) -> ExtraccionValidada:
    """ExtraccionValidada consistente. `ausentes` = nombres marcados ausente=True (valor=None)."""
    fecha = fecha if fecha is not None else str(date.today())
    valores = {
        "numero_poliza": numero,
        "fecha_siniestro": fecha,
        "tipo_siniestro": tipo,
        "monto_reclamado": monto,
    }
    campos = []
    for nombre, valor in valores.items():
        es_ausente = nombre in ausentes
        campos.append(
            CampoExtraido(
                nombre=nombre,
                valor=None if es_ausente else valor,
                ausente=es_ausente,
            )
        )
    return ExtraccionValidada(campos=campos)


@pytest.fixture
def poliza_builder():
    """Factory: construye pólizas consistentes por estrato."""
    return build_poliza


@pytest.fixture
def extraccion_builder():
    """Factory: construye extracciones consistentes por estrato."""
    return build_extraccion


@pytest.fixture(scope="session")
def generator():
    """Generador sintético (para tests de RULE-GEN-02)."""
    return SyntheticCaseGenerator(locale="es_CO")
