"""Escenarios demo — fuente ÚNICA de verdad para armar casos-demo con evidencia real.

Compartido por el seeder (startup) y los presets de la ingesta (`api/ingest.py`), para no
duplicar la construcción de casos (D2 del spec). NO llama al LLM: la extracción se arma
consistente, el dictamen sale del **motor R1-R5 real** (P2), y la alerta usa las Capas 1-2
determinísticas de C6. El estado se deriva del dictamen y **NUNCA es terminal** (P1).
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


def clausulas_demo() -> list[Clausula]:
    return [
        Clausula(id="VIG-1", texto="Vigencia de la póliza", tipo=TipoClausula.VIGENCIA, referencia="Sec. 2.1"),
        Clausula(id="COB-1", texto="Cobertura de colisión", tipo=TipoClausula.COBERTURA, referencia="Sec. 3.2"),
        Clausula(id="LIM-1", texto="Límite de indemnización", tipo=TipoClausula.LIMITE, referencia="Sec. 4.1"),
        Clausula(id="DED-1", texto="Deducible aplicable", tipo=TipoClausula.DEDUCIBLE, referencia="Sec. 5.1"),
    ]


def poliza_demo(numero: str = "POL-DEMO-0001", coberturas=("AUTO_COLISION",), suma="100000", deducible="1000") -> Poliza:
    hoy = date.today()
    return Poliza(
        numero=numero,
        vigencia=RangoFechas(desde=hoy - timedelta(days=365), hasta=hoy + timedelta(days=365)),
        coberturas_contratadas=list(coberturas),
        exclusiones=[],
        suma_asegurada=Decimal(suma),
        deducible=Decimal(deducible),
        es_soat=False,
        clausulas=clausulas_demo(),
    )


def extraccion_demo(numero="POL-DEMO-0001", fecha=None, tipo="AUTO_COLISION", monto="50000", ausentes=()) -> ExtraccionValidada:
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


def armar_caso(aviso_texto: str, extraccion: ExtraccionValidada, poliza: Optional[Poliza] = None, con_alerta: bool = False) -> Caso:
    """Construye un Caso con evidencia real; estado derivado del dictamen del motor (nunca terminal).

    `poliza=None` → póliza NO encontrada → el motor escala a REQUIERE_REVISION (PRE_MOTOR).
    """
    aviso = AvisoNormalizado(texto_crudo=aviso_texto, calidad=CalidadDoc.LIMPIO)
    if poliza is None:
        resultado_poliza = ResultadoPoliza(encontrada=False, poliza=None, candidatas=[])
    else:
        resultado_poliza = ResultadoPoliza(encontrada=True, poliza=poliza, candidatas=[])
    dictamen = motor_cobertura(extraccion, resultado_poliza)
    alerta = _alerta_demo(extraccion, poliza) if (con_alerta and poliza is not None) else None

    if dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION:
        estado = EstadoCaso.REQUIERE_REVISION
        motivo = "Motor escaló: dato faltante o póliza no encontrada"
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


# --- Presets de escenario (para la ingesta demo determinística) ---

# escenario → etiqueta legible para la UI (orden preservado).
PRESETS: dict[str, str] = {
    "feliz": "Feliz — cobertura OK",
    "fraude": "Fraude — monto excede la suma asegurada",
    "cobertura-negativa": "Cobertura negativa — tipo no contratado",
    "no-encontrada": "Póliza no encontrada — escala",
}


def construir_caso_preset(escenario: str) -> Caso:
    """Arma un Caso-demo determinístico para uno de los 4 escenarios (sin LLM)."""
    if escenario == "feliz":
        return armar_caso(
            "Reporto un choque AUTO_COLISION. Póliza POL-DEMO-FELIZ. Daños por $5.000.000.",
            extraccion_demo(numero="POL-DEMO-FELIZ", monto="5000000"),
            poliza_demo(numero="POL-DEMO-FELIZ", suma="100000000"),
        )
    if escenario == "fraude":
        return armar_caso(
            "Choque AUTO_COLISION. Póliza POL-DEMO-FRAUDE. Reclamo daños por $15.000.000.",
            extraccion_demo(numero="POL-DEMO-FRAUDE", monto="15000000"),
            poliza_demo(numero="POL-DEMO-FRAUDE", suma="10000000"),
            con_alerta=True,
        )
    if escenario == "cobertura-negativa":
        return armar_caso(
            "Daño por agua en la vivienda, tipo HOGAR_AGUA. Póliza POL-DEMO-NEG. Daños por $3.000.000.",
            extraccion_demo(numero="POL-DEMO-NEG", tipo="HOGAR_AGUA", monto="3000000"),
            poliza_demo(numero="POL-DEMO-NEG", coberturas=("AUTO_COLISION",)),
        )
    if escenario == "no-encontrada":
        return armar_caso(
            "Choque AUTO_COLISION. Póliza POL-NO-EXISTE. Daños por $4.000.000.",
            extraccion_demo(numero="POL-NO-EXISTE", monto="4000000"),
            poliza=None,
        )
    raise ValueError(f"escenario de preset desconocido: {escenario}")
