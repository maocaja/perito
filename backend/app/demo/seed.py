"""Seeder demo — puebla el CasoRepository con casos representativos al arrancar.

Usa el helper compartido `app.demo.scenarios` (misma construcción que los presets de la
ingesta, sin duplicar). Arma ~4 Casos en distintos estados con EVIDENCIA REAL: extracción
consistente, póliza completa, dictamen del motor C5 real, alerta de las Capas 1-2 de C6.

Es scaffolding DEMO (no el flujo real intake→orquestador). El `aviso.texto_crudo` del primer
caso incluye PII a propósito para que el detalle demuestre la redacción P5.
"""

from typing import Optional

from app.contracts.caso import Caso
from app.demo.scenarios import armar_caso, extraccion_demo, poliza_demo
from app.observability.tracer import Tracer
from app.observability.replay import get_replay_store
from app.dashboard.store import CasoRepository, get_caso_repository


# Aviso con PII embebida (a propósito, para demostrar redacción P5 en el detalle).
_AVISO_PII = (
    "Reporta Juan Pérez García, C.C. 1.098.765.432, celular 3115551234, "
    "correo juanp@example.com. Choque en la Calle 5 #10-23, Bogotá. "
    "Póliza POL-DEMO-0001, siniestro AUTO_COLISION, daños por $8.000.000."
)


def sembrar_traza_demo(caso: Caso) -> None:
    """Siembra una traza demo por nodo en el ReplayStore (para el panel de cumplimiento)."""
    tracer = Tracer(caso.id)
    tracer.emit("intake", "Caso recibido", latencia_ms=2.0)
    tracer.emit("extractor", "Extracción completada", tokens_in=420, tokens_out=110, latencia_ms=850.0)
    tracer.emit("policy", "Grounding de póliza", latencia_ms=5.0)
    tracer.emit("motor", f"Dictamen {caso.dictamen.resultado.value if caso.dictamen else 'N/A'}", latencia_ms=1.0)
    if caso.alerta_fraude:
        tracer.emit("fraude", "Inconsistencias detectadas", tokens_in=300, tokens_out=90, latencia_ms=640.0)
    get_replay_store().save(tracer, caso.estado.value, caso.motivo_escalamiento)


def seed_demo_casos(repo: Optional[CasoRepository] = None) -> CasoRepository:
    """Puebla el store con casos demo representativos por estrato (+ trazas C9)."""
    repo = repo or get_caso_repository()
    repo.clear()
    get_replay_store().clear()

    casos = [
        # 1. Happy → LISTO_PARA_APROBAR + CUBIERTO_PARCIAL (con PII para demo de redacción P5).
        armar_caso(_AVISO_PII, extraccion_demo(), poliza_demo()),
        # 2. Campos faltantes → REQUIERE_REVISION.
        armar_caso(
            "Aviso incompleto: no se pudo leer la fecha del siniestro.",
            extraccion_demo(numero="POL-DEMO-0002", ausentes=("fecha_siniestro",)),
            poliza_demo(numero="POL-DEMO-0002"),
        ),
        # 3. Fraude → alerta (fecha anterior a vigencia).
        armar_caso(
            "Reclamo con fecha sospechosa, C.C. 52.987.654.",
            extraccion_demo(numero="POL-DEMO-0003", fecha="2000-01-01"),
            poliza_demo(numero="POL-DEMO-0003"),
            con_alerta=True,
        ),
        # 4. Cobertura negativa → NO_CUBIERTO (tipo no contratado).
        armar_caso(
            "Daño por agua en vivienda, tipo no contratado en la póliza de auto.",
            extraccion_demo(numero="POL-DEMO-0004", tipo="HOGAR_AGUA"),
            poliza_demo(numero="POL-DEMO-0004", coberturas=("AUTO_COLISION",)),
        ),
    ]
    for caso in casos:
        repo.save(caso)
        sembrar_traza_demo(caso)

    return repo
