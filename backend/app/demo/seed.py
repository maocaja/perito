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
from app.intake.document_ai import procesar_adjuntos
from app.observability.tracer import Tracer
from app.observability.replay import get_replay_store
from app.dashboard.store import CasoRepository, get_caso_repository


# Aviso con PII embebida (a propósito, para demostrar redacción P5 en el detalle).
_AVISO_PII = (
    "Reporta Juan Pérez García, C.C. 1.098.765.432, celular 3115551234, "
    "correo juanp@example.com. Choque en la Calle 5 #10-23, Bogotá. "
    "Póliza POL-DEMO-0001, siniestro AUTO_COLISION, daños por $8.000.000."
)

# Adjuntos sintéticos por caso de auto (bytes distintos por caso → no dispara foto reutilizada en el seed).
# Se procesan igual que la ingesta de correo (M1): redactados y huellados, `origen="real"`. El caso de
# vivienda NO lleva adjuntos a propósito — así el `off`-demo también muestra el estado vacío honesto (P7).
_FOTO = b"\xff\xd8\xff\xe0"  # cabecera JPEG; el resto se distingue por caso

# Documentos de texto sintéticos (.txt → se leen y redactan como en la ingesta; el visor pinta el texto real).
_DENUNCIA_TXT = (
    "DENUNCIA POLICIAL (sintética)\n"
    "Vehículo involucrado: {vehiculo}, placa {placa}.\n"
    "Descripción: colisión reportada por el conductor en vía urbana.\n"
)
_SOAT_TXT = (
    "SOAT (sintético)\n"
    "Vehículo: {vehiculo}.\nPlaca: {placa}.\n"
    "Vigencia: 2026-01-01 a 2026-12-31.\n"
)


def _con_adjuntos(caso: Caso, crudos: list[tuple[str, bytes]]) -> Caso:
    """Cuelga adjuntos REALES sobre un caso sembrado, tal como lo haría la ingesta de correo (M1)."""
    return caso.model_copy(update={"adjuntos": procesar_adjuntos(crudos)})


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
        #    Auto con evidencia completa: foto + denuncia + SOAT (los .txt se leen y redactan como en la ingesta).
        _con_adjuntos(
            armar_caso(_AVISO_PII, extraccion_demo(), poliza_demo()),
            [("colision_delantera.jpg", _FOTO + b"caso1"),
             ("denuncia.txt", _DENUNCIA_TXT.format(placa="ABC123", vehiculo="Renault Logan 2021").encode()),
             ("soat.txt", _SOAT_TXT.format(placa="ABC123", vehiculo="Renault Logan 2021").encode())],
        ),
        # 2. Campos faltantes → REQUIERE_REVISION. Auto con una sola foto.
        _con_adjuntos(
            armar_caso(
                "Aviso incompleto: no se pudo leer la fecha del siniestro.",
                extraccion_demo(numero="POL-DEMO-0002", ausentes=("fecha_siniestro",)),
                poliza_demo(numero="POL-DEMO-0002"),
            ),
            [("dano_lateral.jpg", _FOTO + b"caso2")],
        ),
        # 3. Fraude → alerta (fecha anterior a vigencia). Auto con foto + denuncia.
        _con_adjuntos(
            armar_caso(
                "Reclamo con fecha sospechosa, C.C. 52.987.654.",
                extraccion_demo(numero="POL-DEMO-0003", fecha="2000-01-01"),
                poliza_demo(numero="POL-DEMO-0003"),
                con_alerta=True,
            ),
            [("colision_trasera.jpg", _FOTO + b"caso3"),
             ("denuncia.txt", _DENUNCIA_TXT.format(placa="XYZ789", vehiculo="Mazda 3 2020").encode())],
        ),
        # 4. Cobertura negativa → NO_CUBIERTO (tipo no contratado). Vivienda SIN adjuntos: el correo no
        #    trajo documentos → la galería muestra el estado vacío honesto (P7), nunca fotos de un auto.
        armar_caso(
            "Daño por agua en vivienda, tipo no contratado en la póliza de auto.",
            extraccion_demo(numero="POL-DEMO-0004", tipo="HOGAR_AGUA"),
            poliza_demo(numero="POL-DEMO-0004", coberturas=("AUTO_COLISION",)),
        ),
    ]
    for caso in casos:
        # Código de siniestro definitivo (consecutivo del store) ANTES de guardar/trazar → id estable.
        caso = caso.model_copy(update={"id": repo.reservar_codigo()})
        repo.save(caso)
        sembrar_traza_demo(caso)

    return repo
