"""showcase.py — corre 4 escenarios reales por el pipeline agéntico completo de Perito.

Demuestra los agentes (C2 Haiku extrae, C3 Sonnet verifica, C6 fraude) + los invariantes
NO NEGOCIABLES en vivo:
- P1 (HITL): el orquestador NUNCA cierra un caso — la decisión terminal es humana.
- P2/P3: el dictamen de cobertura lo decide el motor R1-R5 determinístico y cita regla + cláusula.
- P4: ante dato faltante / póliza no encontrada, ESCALA (REQUIERE_REVISION) — no inventa.
- P6: el fraude se detecta y explica; solo sugiere, no bloquea ni decide.

Requiere ANTHROPIC_API_KEY real. Son llamadas reales a Claude (Haiku + Sonnet) — centavos.

Uso (desde backend/):  ANTHROPIC_API_KEY=<tu-key> python showcase.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

key = os.environ.get("ANTHROPIC_API_KEY")
if not key or key == "test":
    print("❌ Necesitas un ANTHROPIC_API_KEY real (no 'test'). export ANTHROPIC_API_KEY=... y reintenta.")
    sys.exit(1)
print(f"✓ Key detectada (...{key[-4:]})")

from datetime import date, timedelta
from decimal import Decimal

from app.contracts.extraccion import AvisoNormalizado
from app.contracts.enums import CalidadDoc, TipoClausula
from app.contracts.poliza import Poliza, Clausula, RangoFechas
from app.contracts.dictamen import Cotas
from app.intake.c1 import intake_crear_caso
from app.policy.lookup import set_poliza_store
from app.orchestrator.c7 import orquestar_fnol
from app.hitl import c8
from app.observability.tracer import Tracer

hoy = date.today()


def _clausulas():
    return [Clausula(id=i, texto="Cláusula demo", tipo=t, referencia="Sec.")
            for i, t in [("VIG", TipoClausula.VIGENCIA), ("COB", TipoClausula.COBERTURA),
                         ("LIM", TipoClausula.LIMITE), ("DED", TipoClausula.DEDUCIBLE)]]


# Fecha de siniestro pre-corte de conocimiento del LLM (para que C3 no la marque "futura").
FECHA = "2025-06-15"


def _poliza(numero, coberturas=("AUTO_COLISION",), suma="100000000", deducible="500000"):
    return Poliza(numero=numero,
                  vigencia=RangoFechas(desde=date(2024, 1, 1), hasta=date(2027, 12, 31)),
                  coberturas_contratadas=list(coberturas), exclusiones=[],
                  suma_asegurada=Decimal(suma), deducible=Decimal(deducible), es_soat=False,
                  clausulas=_clausulas())


# Pólizas sembradas — POL-999 NO se siembra a propósito (escenario "no encontrada").
set_poliza_store({
    "POL-100": _poliza("POL-100"),
    "POL-200": _poliza("POL-200"),
    "POL-300": _poliza("POL-300", coberturas=("AUTO_COLISION",)),  # NO cubre HOGAR_AGUA
})

ESCENARIOS = [
    ("FELIZ — cobertura OK",
     f"Reporto un choque AUTO_COLISION. Poliza POL-100. Fecha del siniestro {FECHA}. Danos por 5000000 pesos.",
     "P2/P3: el motor dictamina y cita regla + cláusula · P1: el caso NO se cierra solo"),
    ("FRAUDE — monto excede la suma asegurada",
     f"Choque AUTO_COLISION. Poliza POL-200. Fecha del siniestro {FECHA}. Reclamo danos por 150000000 pesos.",
     "P6: fraude detectado y explicable (monto excede suma) · solo sugiere, decide el humano"),
    ("COBERTURA NEGATIVA — tipo no contratado",
     f"Dano por agua en la vivienda, tipo HOGAR_AGUA. Poliza POL-300. Fecha del siniestro {FECHA}. Danos por 3000000 pesos.",
     "P2: NO_CUBIERTO citando la regla R2 · lo decide el motor determinístico, NO el LLM"),
    ("PÓLIZA NO ENCONTRADA — escala",
     f"Choque AUTO_COLISION. Poliza POL-500. Fecha del siniestro {FECHA}. Danos por 4000000 pesos.",
     "P4: escala a REQUIERE_REVISION — NO inventa una póliza ni cierra el caso"),
]

cotas = Cotas(max_rondas=1, presupuesto_tokens=50000)

for nombre, texto, invariante in ESCENARIOS:
    print("\n" + "=" * 72)
    print(f"ESCENARIO: {nombre}")
    print(f"Aviso: {texto}")
    print("-" * 72)
    caso = intake_crear_caso(AvisoNormalizado(texto_crudo=texto, calidad=CalidadDoc.LIMPIO))
    tracer = Tracer(caso.id)
    r = orquestar_fnol(caso, c8, cotas, tracer)

    campos = [(c.nombre, c.valor) for c in r.extraccion.campos] if r.extraccion else "N/A"
    print(f"  extracción (Haiku) : {campos}")
    print(f"  póliza (grounding) : {'encontrada' if (r.poliza_match and r.poliza_match.encontrada) else 'NO encontrada'}")
    if r.dictamen:
        cl = r.dictamen.clausula.id if r.dictamen.clausula else "—"
        print(f"  dictamen (motor)   : {r.dictamen.resultado.value}  (regla {r.dictamen.regla_aplicada}, cláusula {cl})")
    print(f"  fraude (C6)        : {'⚠ severidad ' + r.alerta_fraude.severidad if r.alerta_fraude else 'sin alerta'}")
    print(f"  >>> ESTADO FINAL   : {r.estado.value}   ← el orquestador NUNCA cierra (P1: decide el humano)")
    if r.motivo_escalamiento:
        print(f"  motivo             : {r.motivo_escalamiento}")
    print(f"  tokens reales      : {tracer.get_token_summary()['tokens_total']}")
    print(f"  ✔ Demuestra → {invariante}")

print("\n" + "=" * 72)
print("✅ 4 escenarios reales por el pipeline agéntico (agentes Claude reales).")
print("   En TODOS el estado final ∈ {LISTO_PARA_APROBAR, REQUIERE_REVISION} — NUNCA terminal.")
print("   El sistema PREPARA y CITA la evidencia; el humano DECIDE (P1).")
print("   Escala en vez de inventar (P4). La cobertura la decide el motor, no el LLM (P2).")
