"""Seeder demo — puebla el CasoRepository con casos representativos.

Arma ~5 Casos en distintos estados con EVIDENCIA REAL: la extracción se
construye consistente, la póliza se arma completa, y el dictamen sale del
motor C5 real (`motor_cobertura`). La alerta de fraude usa las Capas 1-2
determinísticas de C6 (SIN el LLM de Capa 3, para no llamar API en startup).

Es scaffolding DEMO (no el flujo real intake→orquestador, que es T5). El
`aviso.texto_crudo` incluye PII a propósito para que el detalle demuestre la
redacción P5.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from app.contracts.caso import Caso
from app.contracts.dictamen import AlertaFraude
from app.contracts.enums import EstadoCaso, TipoClausula, TipoOrigen, CalidadDoc, ResultadoCobertura
from app.contracts.extraccion import (
    AvisoNormalizado,
    CampoExtraido,
    EvidenciaOrigen,
    ExtraccionValidada,
)
from app.contracts.poliza import Poliza, Clausula, RangoFechas, ResultadoPoliza

from app.rules.motor_r1_r5 import motor_cobertura
from app.fraud.fraude import detectar_inconsistencias_fraude, calcular_severidad
from app.observability.tracer import Tracer
from app.observability.replay import get_replay_store
from app.dashboard.store import CasoRepository, get_caso_repository


# Aviso con PII embebida (a propósito, para demostrar redacción P5 en el detalle).
_AVISO_PII = (
    "Reporta Juan Pérez García, C.C. 1.098.765.432, celular 3115551234, "
    "correo juanp@example.com. Choque en la Calle 5 #10-23, Bogotá. "
    "Póliza POL-DEMO-0001, siniestro AUTO_COLISION, daños por $8.000.000."
)


def _clausulas() -> list[Clausula]:
    return [
        Clausula(id="VIG-1", texto="Vigencia de la póliza", tipo=TipoClausula.VIGENCIA, referencia="Sec. 2.1"),
        Clausula(id="COB-1", texto="Cobertura de colisión", tipo=TipoClausula.COBERTURA, referencia="Sec. 3.2"),
        Clausula(id="LIM-1", texto="Límite de indemnización", tipo=TipoClausula.LIMITE, referencia="Sec. 4.1"),
        Clausula(id="DED-1", texto="Deducible aplicable", tipo=TipoClausula.DEDUCIBLE, referencia="Sec. 5.1"),
    ]


def _poliza(numero: str = "POL-DEMO-0001", coberturas=("AUTO_COLISION",), suma="100000", deducible="1000") -> Poliza:
    hoy = date.today()
    return Poliza(
        numero=numero,
        vigencia=RangoFechas(desde=hoy - timedelta(days=365), hasta=hoy + timedelta(days=365)),
        coberturas_contratadas=list(coberturas),
        exclusiones=[],
        suma_asegurada=Decimal(suma),
        deducible=Decimal(deducible),
        es_soat=False,
        clausulas=_clausulas(),
    )


def _extraccion(numero="POL-DEMO-0001", fecha=None, tipo="AUTO_COLISION", monto="50000", ausentes=()) -> ExtraccionValidada:
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
                origen=None if es_ausente else EvidenciaOrigen(tipo=TipoOrigen.SPAN, referencia=f"span:{nombre}"),
                confianza=None if es_ausente else 0.9,
                ausente=es_ausente,
            )
        )
    return ExtraccionValidada(campos=campos)


def _alerta_demo(extraccion: ExtraccionValidada, poliza: Poliza) -> Optional[AlertaFraude]:
    """Capas 1-2 de C6 (determinísticas), sin el LLM de Capa 3."""
    inconsistencias = detectar_inconsistencias_fraude(extraccion, poliza)
    if not inconsistencias:
        return None
    return AlertaFraude(
        severidad=calcular_severidad(inconsistencias),
        inconsistencias=inconsistencias,
        explicacion="[demo] Inconsistencia detectada por chequeo determinístico (Capa 1).",
    )


def _armar_caso(aviso_texto: str, extraccion: ExtraccionValidada, poliza: Poliza, con_alerta: bool = False) -> Caso:
    """Construye un Caso con evidencia real y estado derivado del dictamen del motor."""
    aviso = AvisoNormalizado(texto_crudo=aviso_texto, calidad=CalidadDoc.LIMPIO)
    resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza, candidatas=[])
    dictamen = motor_cobertura(extraccion, resultado_poliza)
    alerta = _alerta_demo(extraccion, poliza) if con_alerta else None

    # Estado derivado: REQUIERE_REVISION escala; terminal-de-cobertura → listo para humano.
    if dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION:
        estado = EstadoCaso.REQUIERE_REVISION
        motivo = "Motor escaló: dato faltante o póliza incompleta"
    else:
        estado = EstadoCaso.LISTO_PARA_APROBAR
        motivo = None

    return Caso(
        estado=estado,
        aviso=aviso,
        extraccion=extraccion,
        poliza_match=resultado_poliza,
        dictamen=dictamen,
        alerta_fraude=alerta,
        motivo_escalamiento=motivo,
    )


def _sembrar_traza(caso: Caso) -> None:
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
        _armar_caso(_AVISO_PII, _extraccion(), _poliza()),
        # 2. Campos faltantes → REQUIERE_REVISION.
        _armar_caso(
            "Aviso incompleto: no se pudo leer la fecha del siniestro.",
            _extraccion(numero="POL-DEMO-0002", ausentes=("fecha_siniestro",)),
            _poliza(numero="POL-DEMO-0002"),
        ),
        # 3. Fraude → alerta (fecha anterior a vigencia).
        _armar_caso(
            "Reclamo con fecha sospechosa, C.C. 52.987.654.",
            _extraccion(numero="POL-DEMO-0003", fecha="2000-01-01"),
            _poliza(numero="POL-DEMO-0003"),
            con_alerta=True,
        ),
        # 4. Cobertura negativa → NO_CUBIERTO (tipo no contratado).
        _armar_caso(
            "Daño por agua en vivienda, tipo no contratado en la póliza de auto.",
            _extraccion(numero="POL-DEMO-0004", tipo="HOGAR_AGUA"),
            _poliza(numero="POL-DEMO-0004", coberturas=("AUTO_COLISION",)),
        ),
    ]
    for caso in casos:
        repo.save(caso)
        _sembrar_traza(caso)

    return repo
