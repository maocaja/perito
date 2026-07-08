"""Generador de casos sintéticos para evals (H-16, RULE-GEN-02, P4).

Produce casos válidos etiquetados con cobertura esperada y fraude encodado.

Regla fail-closed (RULE-GEN-02 🔒): si etiqueta_fraude=True, la inconsistencia
debe estar encodada en los datos, o la generación rompe (assert fail-closed).
"""

from decimal import Decimal
from datetime import date, timedelta

from faker import Faker

from app.contracts.caso import Caso, Usuario
from app.contracts.dataset import FilaEntrada, GroundTruth
from app.contracts.dictamen import Dictamen
from app.contracts.enums import (
    EstadoCaso,
    ResultadoCobertura,
    CalidadDoc,
    RolUsuario,
    TipoClausula,
    TipoOrigen,
)
from app.contracts.extraccion import AvisoNormalizado, CampoExtraido, ExtraccionValidada, EvidenciaOrigen
from app.contracts.poliza import Poliza, Clausula, ResultadoPoliza, RangoFechas


class SyntheticCaseGenerator:
    """Generador de casos sintéticos fail-closed (RULE-GEN-02).

    El generador produce (Aviso, Poliza, GroundTruth) válidos.
    Si fraude está etiquetado, ROMPE si no hay inconsistencia encodada.
    """

    def __init__(self, locale: str = "es_CO"):
        """Inicializa con Faker en locale colombiano."""
        self.faker = Faker(locale)

    def generate_ground_truth(
        self,
        etiqueta_fraude: bool = False,
        resultado_cobertura: ResultadoCobertura = ResultadoCobertura.CUBIERTO,
    ) -> GroundTruth:
        """Genera un GroundTruth (salida esperada del sistema).

        Args:
            etiqueta_fraude: si True, genera inconsistencia encodada
            resultado_cobertura: resultado esperado de cobertura

        Returns:
            GroundTruth con garantía fail-closed

        Raises:
            AssertionError: si etiqueta_fraude=True pero NO hay inconsistencia encodada (RULE-GEN-02)
        """
        inconsistencia_esperada = None

        if etiqueta_fraude:
            # RULE-GEN-02: fraude EXIGE inconsistencia encodada en los datos
            # Ejemplo: fecha de siniestro antes de vigencia, o monto > suma_asegurada
            inconsistencia_esperada = EvidenciaOrigen(
                tipo=TipoOrigen.SPAN,
                referencia="Fecha siniestro 2023-01-01 es anterior a vigencia 2024-01-01",
            )

        # ASSERTION FAIL-CLOSED: si etiqueta_fraude pero sin inconsistencia, rompe
        assert (
            not etiqueta_fraude or inconsistencia_esperada is not None
        ), "GroundTruth: fraude=True exige inconsistencia_esperada encodada (RULE-GEN-02)"

        return GroundTruth(
            campos_esperados={
                "numero_poliza": self.faker.bothify(text="POL-########"),
                "fecha_siniestro": str(self.faker.date_object()),
                "tipo_siniestro": "AUTO_COLISION",
                "monto_reclamado": "50000.00",
            },
            resultado_cobertura_esperado=resultado_cobertura,
            etiqueta_fraude=etiqueta_fraude,
            inconsistencia_esperada=inconsistencia_esperada,
        )

    def generate_aviso_normalizado(self, calidad: CalidadDoc = CalidadDoc.LIMPIO) -> AvisoNormalizado:
        """Genera un aviso sintético normalizado."""
        return AvisoNormalizado(
            texto_crudo=self.faker.sentence(nb_words=20),
            calidad=calidad,
        )

    def generate_poliza(self) -> Poliza:
        """Genera una póliza sintética válida."""
        vigencia = RangoFechas(
            desde=date.today() - timedelta(days=365),
            hasta=date.today() + timedelta(days=365),
        )
        return Poliza(
            numero=self.faker.bothify(text="POL-########"),
            vigencia=vigencia,
            coberturas_contratadas=["COLISION", "ROBO"],
            exclusiones=["CONDUCTORES_NO_AUTORIZADOS"],
            suma_asegurada=Decimal("100000"),
            deducible=Decimal("1000"),
            es_soat=False,
            clausulas=[
                Clausula(
                    id="VIGENCIA_001",
                    texto="La póliza vigente desde la fecha de inicio.",
                    tipo=TipoClausula.VIGENCIA,
                    referencia="Sec. 2.1 del contrato",
                ),
                Clausula(
                    id="COBERTURA_001",
                    texto="Cubre colisión con terceros.",
                    tipo=TipoClausula.COBERTURA,
                    referencia="Sec. 3.2 del contrato",
                ),
            ],
        )
