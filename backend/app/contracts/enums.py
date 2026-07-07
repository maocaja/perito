"""Enums cerrados de Perito (RULE-CTR-06 / PBT-03: salida siempre ∈ enum)."""

from enum import Enum


class EstadoCaso(str, Enum):
    """Estados del caso (Apéndice C del PRD)."""

    # --- En alcance (Must) ---
    RECIBIDO = "RECIBIDO"
    EN_PROCESO = "EN_PROCESO"
    LISTO_PARA_APROBAR = "LISTO_PARA_APROBAR"
    REQUIERE_REVISION = "REQUIERE_REVISION"
    EN_REVISION = "EN_REVISION"
    APROBADO = "APROBADO"          # terminal — exige aprobado_por (P1)
    RECHAZADO = "RECHAZADO"        # terminal — exige aprobado_por (P1)
    # --- Declarados pero DIFERIDOS (cola SLA = Should; transiciones no implementadas) ---
    ESPERANDO_INFO = "ESPERANDO_INFO"
    CERRADO_SIN_ACCION = "CERRADO_SIN_ACCION"


# Estados terminales (P1: solo alcanzables vía hitl con aprobado_por).
ESTADOS_TERMINALES: frozenset[EstadoCaso] = frozenset(
    {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}
)


class ResultadoCobertura(str, Enum):
    """Salidas válidas del motor de cobertura (P2). El cálculo es U3."""

    CUBIERTO = "CUBIERTO"
    CUBIERTO_PARCIAL = "CUBIERTO_PARCIAL"
    NO_CUBIERTO = "NO_CUBIERTO"
    REQUIERE_REVISION = "REQUIERE_REVISION"


class CalidadDoc(str, Enum):
    """Marca de calidad del aviso (estrato documento-sucio, H-01)."""

    LIMPIO = "LIMPIO"
    DEGRADADO = "DEGRADADO"
    ILEGIBLE = "ILEGIBLE"


class RolUsuario(str, Enum):
    """Roles del MVP (auth real = Won't; selector de rol stub, RNF-14)."""

    ANALISTA = "ANALISTA"
    CUMPLIMIENTO = "CUMPLIMIENTO"
    ADMIN = "ADMIN"


class TipoOrigen(str, Enum):
    """Tipo de puntero de evidencia (P3)."""

    SPAN = "SPAN"
    PAGINA = "PAGINA"
    REGION = "REGION"


class TipoClausula(str, Enum):
    """Tipo de cláusula de póliza (mapea a R1-R5)."""

    VIGENCIA = "VIGENCIA"
    COBERTURA = "COBERTURA"
    EXCLUSION = "EXCLUSION"
    LIMITE = "LIMITE"
    DEDUCIBLE = "DEDUCIBLE"
