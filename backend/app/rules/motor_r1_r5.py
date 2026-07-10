"""Motor R1-R5 de cobertura determinística (U3).

INVARIANTES P2-P4:
- Función pura: motor_cobertura(extraccion, poliza) → Dictamen (sin state, I/O, mutación)
- Cero imports de anthropic (P2: LLM-free)
- Todo Dictamen cita regla_aplicada + clausula (P3)
- Cascada paso único (sin loops): early-exit R1/R2/R3, R4/R5 siempre computan
- Decimal ROUND_HALF_UP para pesos colombianos (COP, enteros 0 decimales)
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.contracts.dictamen import Dictamen
from app.contracts.enums import ResultadoCobertura, TipoClausula, TipoSiniestro
from app.contracts.extraccion import CampoExtraido, ExtraccionValidada
from app.contracts.money import Money
from app.contracts.poliza import Clausula, CoberturaContratada, Poliza, ResultadoPoliza

# Salario Mínimo Mensual Legal Vigente (Colombia). Valor EJEMPLAR para el tope SOAT (P7: ilustrativo).
SMMLV_2026 = Decimal("1623500")

# Productos con catálogo de cobertura modelado. Un producto declarado FUERA de este set y sin `coberturas`
# explícitas no se puede validar → escala (P7: no se finge cobertura). El modelo plano (producto=None) NO
# se ve afectado (retro-compat).
PRODUCTOS_MODELADOS = {"Autos", "Hogar", "SOAT"}


def _cobertura_efectiva(poliza: Poliza, tipo_siniestro: str) -> Optional[CoberturaContratada]:
    """Cobertura del producto que aplica al siniestro (product-aware). None si no hay match o no es product-aware."""
    for cob in poliza.coberturas:
        if cob.nombre == tipo_siniestro:
            return cob
    return None


def redondear_monto(monto: Decimal) -> Decimal:
    """Redondeo determinístico para COP (pesos colombianos, enteros sin centavos).

    ROUND_HALF_UP: 10.5 → 11, 10.4 → 10 (determinístico, reproducible).

    Args:
        monto: Decimal a redondear

    Returns:
        Decimal redondeado a entero (0 decimales)
    """
    if monto is None:
        return Decimal(0)
    return monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def obtener_clausula(
    poliza: Poliza,
    tipo_clausula: TipoClausula
) -> Optional[Clausula]:
    """Extrae cláusula de tipo especificado, determinísticamente.

    Si hay múltiples cláusulas del mismo tipo, elige la de ID más bajo
    (ordenadas por ID para reproducibilidad, no por dict-hash).

    Args:
        poliza: Póliza con sus cláusulas
        tipo_clausula: Tipo de cláusula a extraer (VIGENCIA, COBERTURA, etc.)

    Returns:
        Clausula del tipo solicitado (ordenada por ID), o None si no existe
    """
    candidatas = [c for c in poliza.clausulas if c.tipo == tipo_clausula]
    if not candidatas:
        return None
    return sorted(candidatas, key=lambda c: c.id)[0]


def _get_campo(extraccion: ExtraccionValidada, nombre: str) -> Optional[CampoExtraido]:
    """Busca un campo extraído por nombre.

    Args:
        extraccion: ExtraccionValidada
        nombre: Nombre del campo

    Returns:
        CampoExtraido si existe, None si no
    """
    for campo in extraccion.campos:
        if campo.nombre == nombre:
            return campo
    return None


def motor_cobertura(
    extraccion: ExtraccionValidada,
    resultado_poliza: ResultadoPoliza
) -> Dictamen:
    """Motor R1-R5 de cobertura determinístico (paso único, función pura).

    INVARIANTES:
    - Función pura: sin state, I/O, mutación externa
    - Resultado siempre ∈ ResultadoCobertura enum
    - Todo Dictamen con resultado terminal (CUBIERTO/PARCIAL/NO_CUBIERTO) cita clausula
    - REQUIERE_REVISION solo si data ausente, póliza incompleta, o candidatas
    - Cascada: early-exit R1/R2/R3; R4/R5 siempre computan
    - Decimal ROUND_HALF_UP (enteros COP)

    Args:
        extraccion: ExtraccionValidada con campos extraídos
        resultado_poliza: ResultadoPoliza (póliza encontrada + clausulas)

    Returns:
        Dictamen con resultado, monto, regla y cláusula

    Raises:
        Never (fail-closed: siempre retorna Dictamen válido)
    """

    # --- Precondición: póliza encontrada ---
    if not resultado_poliza.encontrada or resultado_poliza.poliza is None:
        # Candidatas solo, no hay póliza confirmada (RF-10, P4)
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,  # No hay cláusula en escalamiento
            deducible_calculado=Decimal(0)
        )

    poliza = resultado_poliza.poliza

    # --- R1: Vigencia ---
    fecha_siniestro_campo = _get_campo(extraccion, "fecha_siniestro")
    if not fecha_siniestro_campo or fecha_siniestro_campo.ausente:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,
            deducible_calculado=Decimal(0)
        )

    fecha_siniestro = None
    try:
        if fecha_siniestro_campo.valor:
            fecha_siniestro = date.fromisoformat(fecha_siniestro_campo.valor)
    except (ValueError, TypeError):
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,
            deducible_calculado=Decimal(0)
        )

    clausula_vigencia = obtener_clausula(poliza, TipoClausula.VIGENCIA)
    if not clausula_vigencia:
        return Dictamen(
            resultado=ResultadoCobertura.REQUIERE_REVISION,
            regla_aplicada="PRE_MOTOR",
            clausula=None,
            deducible_calculado=Decimal(0)
        )

    # R1 check
    if not (poliza.vigencia.desde <= fecha_siniestro <= poliza.vigencia.hasta):
        return Dictamen(
            resultado=ResultadoCobertura.NO_CUBIERTO,
            regla_aplicada="R1_VIGENCIA",
            clausula=clausula_vigencia,
            deducible_calculado=Decimal(0)
        )

    # --- R2: Cobertura contratada (product-aware si poliza.coberturas; si no, modelo plano) ---
    def _revision() -> Dictamen:
        return Dictamen(resultado=ResultadoCobertura.REQUIERE_REVISION, regla_aplicada="PRE_MOTOR",
                        clausula=None, deducible_calculado=Decimal(0))

    tipo_siniestro_campo = _get_campo(extraccion, "tipo_siniestro")
    if not tipo_siniestro_campo or tipo_siniestro_campo.ausente:
        return _revision()

    tipo_siniestro = tipo_siniestro_campo.valor
    clausula_cobertura = obtener_clausula(poliza, TipoClausula.COBERTURA)
    if not clausula_cobertura:
        return _revision()

    # Producto declarado pero NO modelado y sin catálogo de coberturas → no se puede validar, escala (P7, §7).
    if poliza.producto and poliza.producto not in PRODUCTOS_MODELADOS and not poliza.coberturas:
        return Dictamen(resultado=ResultadoCobertura.REQUIERE_REVISION,
                        regla_aplicada="PRODUCTO_NO_MODELADO", clausula=None, deducible_calculado=Decimal(0))

    # Valores EFECTIVOS: de la cobertura del producto (U3) o del modelo plano (retro-compat).
    if poliza.coberturas:  # product-aware
        cob = _cobertura_efectiva(poliza, tipo_siniestro)
        if cob is None:
            return Dictamen(resultado=ResultadoCobertura.NO_CUBIERTO, regla_aplicada="R2_COBERTURA",
                            clausula=clausula_cobertura, deducible_calculado=Decimal(0))
        eff_sublimite, eff_deducible = cob.sublimite, cob.deducible
        eff_exclusiones, eff_tope_smmlv, cobertura_nombre = cob.exclusiones, cob.tope_smmlv, cob.nombre
    else:  # plano (retro-compat)
        if tipo_siniestro not in poliza.coberturas_contratadas:
            return Dictamen(resultado=ResultadoCobertura.NO_CUBIERTO, regla_aplicada="R2_COBERTURA",
                            clausula=clausula_cobertura, deducible_calculado=Decimal(0))
        eff_sublimite, eff_deducible = poliza.suma_asegurada, poliza.deducible
        eff_exclusiones, eff_tope_smmlv, cobertura_nombre = poliza.exclusiones, None, None

    # --- R3: Exclusiones (ahora SÍ evalúa; antes era `pass`) ---
    if tipo_siniestro in eff_exclusiones:
        clausula_exclusion = obtener_clausula(poliza, TipoClausula.EXCLUSION) or clausula_cobertura
        return Dictamen(resultado=ResultadoCobertura.NO_CUBIERTO, regla_aplicada="R3_EXCLUSION",
                        clausula=clausula_exclusion, deducible_calculado=Decimal(0),
                        cobertura_aplicada=cobertura_nombre)

    # --- R4: Límite (sublímite de LA cobertura; SOAT topa en SMMLV) ---
    monto_reclamado_campo = _get_campo(extraccion, "monto_reclamado")
    if not monto_reclamado_campo or monto_reclamado_campo.ausente:
        return _revision()
    try:
        monto_reclamado = Decimal(monto_reclamado_campo.valor) if monto_reclamado_campo.valor else None
    except Exception:
        return _revision()
    if monto_reclamado is None:
        return _revision()

    limite_efectivo = eff_sublimite
    if eff_tope_smmlv is not None:  # SOAT: tope legal en salarios mínimos
        limite_efectivo = min(limite_efectivo, Decimal(eff_tope_smmlv) * SMMLV_2026)
    monto_tras_limite = redondear_monto(min(monto_reclamado, limite_efectivo))

    # --- R5: Deducible (de LA cobertura) ---
    clausula_deducible = obtener_clausula(poliza, TipoClausula.DEDUCIBLE)
    if not clausula_deducible:
        return _revision()
    pago_final = redondear_monto(max(Decimal(0), monto_tras_limite - eff_deducible))
    deducible_aplicado = redondear_monto(min(eff_deducible, monto_tras_limite))

    # PARCIAL si el pago es MENOR que lo reclamado (por sublímite o por deducible); CUBIERTO si se paga todo.
    if pago_final == Decimal(0):
        resultado = ResultadoCobertura.CUBIERTO
    elif pago_final < redondear_monto(monto_reclamado):
        resultado = ResultadoCobertura.CUBIERTO_PARCIAL
    else:
        resultado = ResultadoCobertura.CUBIERTO

    return Dictamen(
        resultado=resultado,
        regla_aplicada="R5_DEDUCIBLE",
        clausula=clausula_deducible,
        deducible_calculado=deducible_aplicado,
        cobertura_aplicada=cobertura_nombre,
        sublimite_aplicado=redondear_monto(limite_efectivo),
    )

