"""T3 Evals reales por estrato — EJECUTAN C4/C5/C6 contra inputs consistentes.

A diferencia de la versión tautológica previa (que aserta etiquetas del ground-truth),
cada eval CORRE el componente real y compara la salida contra el resultado esperado:
coverage-match (C5), grounding (C4), fraude precisión/recall (C6).
Fail-closed P1/P4/RULE-GEN-02 conservados. Todo determinístico (sin LLM).
"""

from decimal import Decimal

import pytest

from app.contracts.enums import ResultadoCobertura, EstadoCaso, CalidadDoc
from app.contracts.caso import Caso
from app.contracts.dictamen import Cotas
from app.contracts.dataset import GroundTruth
from app.contracts.extraccion import AvisoNormalizado
from app.contracts.poliza import ResultadoPoliza

from app.rules.motor_r1_r5 import motor_cobertura
from app.policy.lookup import call_c4_policy_lookup, set_poliza_store
from app.fraud.fraude import detectar_inconsistencias_fraude


TERMINALES = {
    ResultadoCobertura.CUBIERTO,
    ResultadoCobertura.CUBIERTO_PARCIAL,
    ResultadoCobertura.NO_CUBIERTO,
}


def _encontrada(poliza) -> ResultadoPoliza:
    return ResultadoPoliza(encontrada=True, poliza=poliza, candidatas=[])


# ---------- C5 Motor de cobertura (coverage-match REAL) ----------

class TestCoberturaMotor:
    """Estratos happy / cobertura-negativa / campos-faltantes: corre motor_cobertura."""

    def test_happy_cubierto(self, poliza_builder, extraccion_builder):
        """monto 50k / suma 100k / deducible 1k → pago 49k < monto → CUBIERTO_PARCIAL + cita cláusula."""
        dictamen = motor_cobertura(extraccion_builder(), _encontrada(poliza_builder()))
        # Resultado EXACTO derivado de R4/R5 (deducible reduce el pago): CUBIERTO_PARCIAL.
        assert dictamen.resultado == ResultadoCobertura.CUBIERTO_PARCIAL
        assert dictamen.clausula is not None  # RULE-CTR-03 real
        assert dictamen.deducible_calculado == Decimal("1000")

    def test_no_cubierto_tipo_no_contratado(self, poliza_builder, extraccion_builder):
        """R2: tipo_siniestro fuera de coberturas_contratadas → NO_CUBIERTO."""
        dictamen = motor_cobertura(
            extraccion_builder(tipo="HOGAR_AGUA"),
            _encontrada(poliza_builder(coberturas=("AUTO_COLISION",))),
        )
        assert dictamen.resultado == ResultadoCobertura.NO_CUBIERTO
        assert dictamen.regla_aplicada == "R2_COBERTURA"
        assert dictamen.clausula is not None

    def test_no_cubierto_fuera_vigencia(self, poliza_builder, extraccion_builder):
        """R1: fecha_siniestro fuera de vigencia → NO_CUBIERTO."""
        dictamen = motor_cobertura(
            extraccion_builder(fecha="2000-01-01"),
            _encontrada(poliza_builder()),
        )
        assert dictamen.resultado == ResultadoCobertura.NO_CUBIERTO
        assert dictamen.regla_aplicada == "R1_VIGENCIA"
        assert dictamen.clausula is not None

    def test_requiere_revision_campo_ausente(self, poliza_builder, extraccion_builder):
        """Campo obligatorio ausente → REQUIERE_REVISION (P4, no inventar)."""
        dictamen = motor_cobertura(
            extraccion_builder(ausentes=("fecha_siniestro",)),
            _encontrada(poliza_builder()),
        )
        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION
        assert dictamen.clausula is None

    def test_requiere_revision_poliza_no_encontrada(self, extraccion_builder):
        """Solo candidatas (encontrada=False) → REQUIERE_REVISION (RF-10, no forzar)."""
        rp = ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])
        dictamen = motor_cobertura(extraccion_builder(), rp)
        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION

    def test_terminal_siempre_cita_clausula(self, poliza_builder, extraccion_builder):
        """RULE-CTR-03 sobre casos REALES: todo terminal cita cláusula."""
        poliza = poliza_builder()
        for ext in (
            extraccion_builder(),                       # CUBIERTO/PARCIAL
            extraccion_builder(tipo="HOGAR_AGUA"),      # NO_CUBIERTO R2
            extraccion_builder(fecha="2000-01-01"),     # NO_CUBIERTO R1
        ):
            d = motor_cobertura(ext, _encontrada(poliza))
            if d.resultado in TERMINALES:
                assert d.clausula is not None


# ---------- C4 Policy Lookup (grounding REAL) ----------

class TestPolicyLookup:
    """Estrato poliza-no-encontrada: corre call_c4_policy_lookup."""

    def test_encontrada_match_exacto(self, poliza_builder, extraccion_builder):
        set_poliza_store({"POL-XYZ": poliza_builder(numero="POL-XYZ")})
        rp = call_c4_policy_lookup(extraccion_builder(numero="POL-XYZ"))
        assert rp.encontrada is True
        assert rp.poliza is not None and rp.poliza.numero == "POL-XYZ"

    def test_no_encontrada_sin_match(self, poliza_builder, extraccion_builder):
        set_poliza_store({"POL-AAA": poliza_builder(numero="POL-AAA")})
        rp = call_c4_policy_lookup(extraccion_builder(numero="POL-ZZZ"))
        assert rp.encontrada is False
        assert rp.poliza is None  # RULE-CTR-07: no forzar match


# ---------- C6 Fraude (detección determinística REAL) ----------

class TestFraudeC6:
    """Estrato fraude: corre detectar_inconsistencias_fraude y mide precisión/recall."""

    def test_detecta_fecha_anterior_vigencia(self, poliza_builder, extraccion_builder):
        inc = detectar_inconsistencias_fraude(extraccion_builder(fecha="2000-01-01"), poliza_builder())
        assert len(inc) > 0

    def test_detecta_monto_excede_suma(self, poliza_builder, extraccion_builder):
        inc = detectar_inconsistencias_fraude(extraccion_builder(monto="200000"), poliza_builder(suma="100000"))
        assert len(inc) > 0

    def test_caso_limpio_sin_inconsistencia(self, poliza_builder, extraccion_builder):
        """Precisión: un caso consistente NO dispara falsos positivos."""
        inc = detectar_inconsistencias_fraude(extraccion_builder(), poliza_builder())
        assert len(inc) == 0

    def test_precision_recall_perfectos_en_chequeos_duros(self, poliza_builder, extraccion_builder):
        """Sobre un set etiquetado, los chequeos determinísticos dan P=R=1.0."""
        poliza = poliza_builder(suma="100000")
        casos = [
            (extraccion_builder(), False),
            (extraccion_builder(fecha="2000-01-01"), True),
            (extraccion_builder(monto="500000"), True),
            (extraccion_builder(), False),
        ]
        tp = fp = fn = 0
        for ext, esperado in casos:
            detectado = len(detectar_inconsistencias_fraude(ext, poliza)) > 0
            if detectado and esperado:
                tp += 1
            elif detectado and not esperado:
                fp += 1
            elif not detectado and esperado:
                fn += 1
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        assert precision == 1.0
        assert recall == 1.0


# ---------- SOAT (RF-14 diferido, forward-compat) ----------

class TestSOAT:
    def test_soat_procesa_sin_logica_especial(self, poliza_builder, extraccion_builder):
        """RF-14 diferido: una póliza es_soat=True se procesa sin crash (forward-compat)."""
        dictamen = motor_cobertura(extraccion_builder(), _encontrada(poliza_builder(es_soat=True)))
        assert isinstance(dictamen.resultado, ResultadoCobertura)


# ---------- Documento sucio (DEGRADADO → extracción incompleta → escala) ----------

class TestDocumentoSucio:
    def test_degradado_extraccion_incompleta_escala(self, poliza_builder, extraccion_builder):
        aviso = AvisoNormalizado(texto_crudo="reporte parcialmente ilegible", calidad=CalidadDoc.DEGRADADO)
        assert aviso.calidad == CalidadDoc.DEGRADADO
        # Documento sucio → extracción con campo ausente → motor escala
        dictamen = motor_cobertura(
            extraccion_builder(ausentes=("monto_reclamado",)),
            _encontrada(poliza_builder()),
        )
        assert dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION


# ---------- Fail-closed P1 / P4 / RULE-GEN-02 (invariantes, rompen ruidoso) ----------

class TestFailClosedInvariantes:
    def test_p1_aprobado_sin_firma_raises(self):
        """P1/H-12a: terminal APROBADO sin aprobado_por → raises."""
        aviso = AvisoNormalizado(texto_crudo="test", calidad=CalidadDoc.LIMPIO)
        with pytest.raises(ValueError):
            Caso(estado=EstadoCaso.APROBADO, aviso=aviso, aprobado_por=None)

    def test_p1_recibido_sin_firma_ok(self):
        """P1: RECIBIDO (no terminal) permite aprobado_por=None."""
        aviso = AvisoNormalizado(texto_crudo="test", calidad=CalidadDoc.LIMPIO)
        caso = Caso(estado=EstadoCaso.RECIBIDO, aviso=aviso)
        assert caso.aprobado_por is None

    def test_p4_cotas_presupuesto_cero_raises(self):
        """P4: Cotas exige presupuesto_tokens > 0."""
        with pytest.raises(ValueError):
            Cotas(max_rondas=1, presupuesto_tokens=0)

    def test_rule_gen_02_fraude_sin_inconsistencia_raises(self):
        """RULE-GEN-02: etiqueta_fraude=True sin inconsistencia_esperada → raises."""
        with pytest.raises((ValueError, AssertionError)):
            GroundTruth(
                campos_esperados={},
                resultado_cobertura_esperado=ResultadoCobertura.CUBIERTO,
                etiqueta_fraude=True,
                inconsistencia_esperada=None,
            )
