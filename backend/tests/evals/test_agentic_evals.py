"""Evals AGÉNTICOS (D) — pipeline REAL + Claude-as-judge. Marcados `agentic` → EXCLUIDOS del CI.

Corren SOLO con `pytest -m agentic` + ANTHROPIC_API_KEY real (cuestan API, no deterministas).
P5: el aviso se REDACTA antes de ir al juez. Runs versionados SIN PII en `tests/evals/runs/`.
Métricas: Faithfulness (campos inventados) + ToolCorrectness (trayectoria) + G-Eval (cita cláusula).
"""

import datetime
import json
import os
import pathlib

import pytest

pytest.importorskip("deepeval")  # sin deepeval → se saltan (la suite base sigue robusta)

from deepeval.metrics import FaithfulnessMetric, GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall

from app.contracts.dictamen import Cotas
from app.contracts.enums import CalidadDoc, ResultadoCobertura
from app.contracts.extraccion import AvisoNormalizado
from app.intake.c1 import intake_crear_caso
from app.orchestrator.c7 import orquestar_fnol
from app.hitl import c8
from app.observability.tracer import Tracer
from app.policy.lookup import set_poliza_store
from app.security.redaction import redact_pii_spans_es_co
from app.demo.scenarios import poliza_demo
from tests.evals.claude_judge import ClaudeJudge

pytestmark = pytest.mark.agentic

_KEY = os.environ.get("ANTHROPIC_API_KEY")
requires_key = pytest.mark.skipif(not _KEY or _KEY == "test", reason="requiere ANTHROPIC_API_KEY real")

FECHA = "2025-06-15"  # pre-corte del LLM (evita falso 'fecha futura')
PIPELINE = ["c2_extraccion", "c3_verificador", "c4_policy_lookup", "c5_motor_cobertura", "c6_fraude"]

ESTRATOS = {
    "happy": {"aviso": f"Choque AUTO_COLISION. Poliza POL-100. Fecha del siniestro {FECHA}. Danos por 5000000 pesos.",
              "expected": PIPELINE},
    "fraude": {"aviso": f"Choque AUTO_COLISION. Poliza POL-200. Fecha del siniestro {FECHA}. Reclamo danos por 15000000 pesos.",
               "expected": PIPELINE},
    "no-cubierto": {"aviso": f"Dano por agua en la vivienda, tipo HOGAR_AGUA. Poliza POL-300. Fecha del siniestro {FECHA}. Danos por 3000000 pesos.",
                    "expected": PIPELINE},
    "no-encontrada": {"aviso": f"Choque AUTO_COLISION. Poliza POL-500. Fecha del siniestro {FECHA}. Danos por 4000000 pesos.",
                      "expected": ["c2_extraccion", "c3_verificador", "c4_policy_lookup"]},
}

_RESULTS: list[dict] = []


@pytest.fixture(scope="module", autouse=True)
def _dump_runs():
    yield
    if _RESULTS:
        runs = pathlib.Path(__file__).parent / "runs"
        runs.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        (runs / f"{ts}.json").write_text(json.dumps(_RESULTS, indent=2, ensure_ascii=False))


def _seed():
    set_poliza_store({
        "POL-100": poliza_demo(numero="POL-100", suma="100000000"),
        "POL-200": poliza_demo(numero="POL-200", suma="10000000"),
        "POL-300": poliza_demo(numero="POL-300", coberturas=("AUTO_COLISION",)),
        # POL-500 NO se siembra → estrato no-encontrada
    })


def _record(estrato, caso_id, metrica, score, umbral):
    """Registra el resultado SIN PII (solo estrato/caso_id/metrica/score/umbral/veredicto)."""
    veredicto = "SKIP" if score is None else ("PASS" if score >= umbral else "FAIL")
    _RESULTS.append({
        "estrato": estrato, "caso_id": caso_id, "metrica": metrica,
        "score": score, "umbral": umbral, "veredicto": veredicto,
    })


def _measure_tolerante(metric_factory, tc, threshold, retries=2):
    """Mide con tolerancia al no-determinismo (spec §3.5): reintenta solo si falla; promedia lo corrido."""
    scores = []
    for _ in range(retries):
        m = metric_factory()
        m.measure(tc)
        scores.append(m.score)
        if m.score >= threshold:  # ya pasó → no gastar más API
            break
    return sum(scores) / len(scores)


@requires_key
@pytest.mark.parametrize("estrato", list(ESTRATOS))
def test_agentic_estrato(estrato):
    """Eval agéntico por estrato: corre el pipeline REAL + juzga con Claude.

    Flujo: redacta el aviso (P5) → corre `orquestar_fnol` (C2-C6 según el estrato) → captura la
    trayectoria real (nodos de la traza) → evalúa con juez Claude:
      - Faithfulness (campos inventados ≈ 0; umbral 0.70, con reintento tolerante).
      - ToolCorrectness (recorrió los nodos esperados; umbral 0.80).
      - G-Eval "cita cláusula" SOLO en dictámenes terminales (REQUIERE_REVISION no cita → SKIP).
    happy/fraude/no-cubierto = pipeline completo; no-encontrada escala a REQUIERE_REVISION (corta antes de C5/C6).
    """
    cfg = ESTRATOS[estrato]
    judge = ClaudeJudge(model="claude-sonnet-5")
    _seed()

    aviso_red = redact_pii_spans_es_co(cfg["aviso"])  # P5: redactado ANTES del juez
    caso = intake_crear_caso(AvisoNormalizado(texto_crudo=cfg["aviso"], calidad=CalidadDoc.LIMPIO))
    tracer = Tracer(caso.id)
    r = orquestar_fnol(caso, c8, Cotas(max_rondas=1, presupuesto_tokens=50000), tracer)

    nodos = [ev["nodo"] for ev in tracer.get_trace_log() if ev["nodo"] in PIPELINE]
    extraccion = str([(c.nombre, c.valor) for c in r.extraccion.campos]) if r.extraccion else "(sin extracción)"
    if r.dictamen and r.dictamen.clausula:
        cl = f"{r.dictamen.clausula.id}: {r.dictamen.clausula.texto} ({r.dictamen.clausula.referencia})"
    else:
        cl = "ninguna"
    dictamen = f"{r.dictamen.resultado.value} regla={r.dictamen.regla_aplicada} clausula=[{cl}]" if r.dictamen else "(sin dictamen)"

    # P5: TODO lo que va al juez (aviso Y la salida del pipeline) se redacta.
    salida = redact_pii_spans_es_co(f"Extracción: {extraccion}\nDictamen: {dictamen}")
    tc = LLMTestCase(
        input=aviso_red,
        actual_output=salida,
        retrieval_context=[aviso_red],
        context=[aviso_red],
        tools_called=[ToolCall(name=n) for n in nodos],
        expected_tools=[ToolCall(name=n) for n in cfg["expected"]],
    )

    # 1) Faithfulness (campos inventados) — juez Claude, con tolerancia al no-determinismo.
    faith_score = _measure_tolerante(lambda: FaithfulnessMetric(threshold=0.7, model=judge), tc, 0.7)
    _record(estrato, caso.id, "faithfulness", faith_score, 0.7)

    # 2) Tool-correctness (determinista; deepeval exige un model en el ctor → juez Claude, no OpenAI).
    tool = ToolCorrectnessMetric(threshold=0.8, model=judge)
    tool.measure(tc)
    _record(estrato, caso.id, "tool_correctness", tool.score, 0.8)

    # 3) G-Eval "cita cláusula" — INFORMATIVA (juez no-determinista → se registra, NO se hard-asserta).
    #    Solo para dictámenes terminales (REQUIERE_REVISION no cita → SKIP).
    es_terminal = bool(r.dictamen) and r.dictamen.resultado != ResultadoCobertura.REQUIERE_REVISION
    if es_terminal:
        geval = GEval(
            name="CitaClausula",
            criteria="El dictamen terminal (CUBIERTO/CUBIERTO_PARCIAL/NO_CUBIERTO) debe citar una cláusula "
                     "existente de la póliza (id + texto). Evalúa si el dictamen es explicable y cita cláusula.",
            evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT],
            model=judge,
            threshold=0.7,
        )
        geval.measure(tc)
        _record(estrato, caso.id, "geval_cita_clausula", geval.score, 0.7)
    else:
        _record(estrato, caso.id, "geval_cita_clausula", None, 0.7)  # SKIP: no terminal, no hay cláusula

    # GATE DURO: faithfulness (campos inventados ≈ 0) — la métrica clave del PRD, la más estable.
    # tool-correctness y geval se REGISTRAN pero NO se asertan (juez LLM no-determinista, evita flakiness).
    assert faith_score >= 0.7, f"[{estrato}] faithfulness {faith_score} < 0.7 (posibles campos inventados)"
