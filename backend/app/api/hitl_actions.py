"""Router de acciones HITL post-orquestación (F1 / H-20). Capa ACTIVA (corre el motor), NO passive.

`POST /casos/{id}/corregir` — el analista corrige campos mal extraídos → re-dictamen DETERMINÍSTICO
(motor R1-R5 + fraude capas 1-2; C4 lookup solo si cambió la póliza) → LISTO_PARA_APROBAR / REQUIERE_REVISION.
NUNCA terminal (P1); requiere firma (`usuario`); 409 si el caso ya fue decidido. El campo corregido queda con
`origen = HUMANO` (auditable, P3). Vive en `api/` (no en el dashboard passive).
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

from app.contracts.caso import Caso
from app.contracts.dictamen import AlertaFraude
from app.contracts.enums import EstadoCaso, ResultadoCobertura, RolUsuario, TipoOrigen
from app.contracts.extraccion import CampoExtraido, EvidenciaOrigen, ExtraccionValidada
from app.rules.motor_r1_r5 import motor_cobertura
from app.policy.lookup import call_c4_policy_lookup
from app.fraud.fraude import calcular_severidad, detectar_inconsistencias_fraude
from app.dashboard.store import get_caso_repository

router = APIRouter(tags=["hitl"])

_CAMPOS = ("numero_poliza", "fecha_siniestro", "tipo_siniestro", "monto_reclamado")
_TERMINALES = {EstadoCaso.APROBADO, EstadoCaso.RECHAZADO}


def _alerta_capas12(extraccion: ExtraccionValidada, poliza) -> Optional[AlertaFraude]:
    """Fraude determinístico (capas 1-2, sin LLM) — igual que el seeder."""
    inc = detectar_inconsistencias_fraude(extraccion, poliza)
    if not inc:
        return None
    return AlertaFraude(
        severidad=calcular_severidad(inc),
        inconsistencias=inc,
        explicacion="[corrección] Inconsistencia detectada por chequeo determinístico (Capa 1).",
    )


@router.post("/casos/{caso_id}/corregir", response_class=RedirectResponse)
def corregir(
    caso_id: str,
    usuario: Optional[str] = Form(None),
    rol: str = Form(RolUsuario.ANALISTA.value),
    numero_poliza: Optional[str] = Form(None),
    fecha_siniestro: Optional[str] = Form(None),
    tipo_siniestro: Optional[str] = Form(None),
    monto_reclamado: Optional[str] = Form(None),
):
    """Corrige campos + re-dictamina (determinístico). P1: firma obligatoria, nunca terminal, 409 si decidido."""
    if not usuario or not usuario.strip():
        raise HTTPException(status_code=400, detail="usuario requerido (firma válida, P1)")
    caso = get_caso_repository().get(caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if caso.estado in _TERMINALES:
        raise HTTPException(status_code=409, detail="El caso ya fue decidido; no se puede corregir (P1)")
    if caso.extraccion is None:
        raise HTTPException(status_code=400, detail="El caso no tiene extracción para corregir")

    correcciones = {
        "numero_poliza": numero_poliza, "fecha_siniestro": fecha_siniestro,
        "tipo_siniestro": tipo_siniestro, "monto_reclamado": monto_reclamado,
    }
    base = {c.nombre: c for c in caso.extraccion.campos}

    campos: list[CampoExtraido] = []
    cambiados: list[str] = []
    for nombre in _CAMPOS:
        nuevo = (correcciones.get(nombre) or "").strip()
        if nuevo == "—":  # placeholder de "ausente" en el form → no es corrección
            nuevo = ""
        original = base.get(nombre)
        if nuevo and (original is None or str(original.valor) != nuevo):
            campos.append(CampoExtraido(
                nombre=nombre, valor=nuevo, confianza=1.0, ausente=False,
                origen=EvidenciaOrigen(tipo=TipoOrigen.HUMANO, referencia=f"corrección humana: {usuario}"),
            ))
            cambiados.append(nombre)
        elif original is not None:
            campos.append(original)
        else:
            campos.append(CampoExtraido(nombre=nombre, valor=None, ausente=True))  # W1: completitud (4 campos)
    extraccion = ExtraccionValidada(campos=campos)

    # C4 si cambió la póliza O si no hay grounding previo (B1: evita motor con poliza_match None).
    if "numero_poliza" in cambiados or caso.poliza_match is None:
        poliza_match = call_c4_policy_lookup(extraccion)
    else:
        poliza_match = caso.poliza_match

    # B2: fail-closed — una corrección inválida NO corrompe el caso (400, caso intacto), nunca 500.
    try:
        dictamen = motor_cobertura(extraccion, poliza_match)
        alerta = _alerta_capas12(extraccion, poliza_match.poliza) if (poliza_match and poliza_match.encontrada) else None
        estado = (EstadoCaso.REQUIERE_REVISION
                  if dictamen.resultado == ResultadoCobertura.REQUIERE_REVISION
                  else EstadoCaso.LISTO_PARA_APROBAR)

        # model_validate re-ejecuta validators (P1: no terminal → aprobado_por sigue None y es válido).
        caso_dict = caso.model_dump()
        caso_dict["extraccion"] = extraccion.model_dump()
        caso_dict["poliza_match"] = poliza_match.model_dump() if poliza_match else None
        caso_dict["dictamen"] = dictamen.model_dump()
        caso_dict["alerta_fraude"] = alerta.model_dump() if alerta else None
        caso_dict["estado"] = estado
        # B3: auditoría a nivel de caso (además del origen HUMANO por campo).
        caso_dict["motivo_escalamiento"] = (
            f"Corregido por {usuario}: {', '.join(cambiados)}" if cambiados else caso.motivo_escalamiento
        )
        caso_dict["timestamp_actualizacion"] = datetime.now(timezone.utc)
        actualizado = Caso.model_validate(caso_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Corrección inválida: {e}")

    get_caso_repository().save(actualizado)
    return RedirectResponse(f"/casos/{caso_id}?rol={rol}", status_code=303)
