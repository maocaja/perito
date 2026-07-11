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


def _validar_corregible(caso_id: str, usuario: Optional[str]):
    """Precondiciones de una corrección (P1 firma · 404 · 409 terminal · 400 sin extracción). Devuelve el caso."""
    if not usuario or not usuario.strip():
        raise HTTPException(status_code=400, detail="usuario requerido (firma válida, P1)")
    caso = get_caso_repository().get(caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if caso.estado in _TERMINALES:
        raise HTTPException(status_code=409, detail="El caso ya fue decidido; no se puede corregir (P1)")
    if caso.extraccion is None:
        raise HTTPException(status_code=400, detail="El caso no tiene extracción para corregir")
    return caso


def aplicar_correccion(caso: Caso, usuario: str, correcciones: dict) -> Caso:
    """Aplica correcciones de campos + re-dictamina DETERMINÍSTICO (motor R1-R5; C4 solo si cambió la póliza) y
    persiste. **Server-authoritative (P2: la cobertura la recalcula el MOTOR, jamás el cliente).** NUNCA terminal
    (P1); el campo corregido queda `origen=HUMANO` (auditable, P3). Reusada por el redirect clásico y el HTMX.

    Precondición: `caso` ya validado por `_validar_corregible` (firma/estado/extracción). Fail-closed: una
    corrección inválida → 400 (caso intacto), nunca 500."""
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
    return actualizado


# W20/A6: el `corregir` legacy (redirigía a `detalle`) se retiró junto con la página detalle. La corrección
# inline vive en `/workbench/corregir` (c11.py, HTMX, re-pinta el panel sin recarga).


# ============================================================================
# W9 · Acciones ampliadas del operador. 🔒 P1: ninguna alcanza estado terminal
# (APROBADO/RECHAZADO) salvo Radicar, que exige firma humana. Todas redirigen a la Workbench (PRG).
# ============================================================================

def _get_activo(caso_id: str):
    caso = get_caso_repository().get(caso_id)
    if caso is None:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    return caso


def _firma(usuario: Optional[str]) -> str:
    if not usuario or not usuario.strip():
        raise HTTPException(status_code=400, detail="usuario requerido (firma válida, P1)")
    return usuario.strip()


def _volver(caso_id: str, rol: str) -> RedirectResponse:
    # W10: `avanzar=1` → la workbench carga el SIGUIENTE caso de la cola (flujo "actúa → siguiente").
    return RedirectResponse(f"/workbench?rol={rol}&caso_id={caso_id}&avanzar=1", status_code=303)


def _persistir_update(caso: Caso, updates: dict) -> Caso:
    """Aplica cambios en campos NO frozen vía model_validate (defensivo: re-ejecuta validadores, patrón de
    `corregir`). NUNCA toca estado/aprobado_por (esos van por HITL)."""
    d = caso.model_dump()
    d.update(updates)
    d["timestamp_actualizacion"] = datetime.now(timezone.utc)
    return Caso.model_validate(d)


@router.post("/casos/{caso_id}/radicar", response_class=RedirectResponse)
def radicar(caso_id: str, usuario: Optional[str] = Form(None), rol: str = Form(RolUsuario.ANALISTA.value)):
    """Radicar = aprobación humana (reusa hitl.aprobar). 🔒 P1: exige `usuario`; solo desde LISTO_PARA_APROBAR."""
    from app.hitl.c8 import aprobar as hitl_aprobar
    firma = _firma(usuario)
    caso = _get_activo(caso_id)
    # 🔒 P1: refuerzo server-side del gate — solo se radica desde LISTO_PARA_APROBAR (no saltar revisión).
    if caso.estado != EstadoCaso.LISTO_PARA_APROBAR:
        raise HTTPException(status_code=409, detail="El caso no está listo para radicar (P1)")
    try:
        actualizado = hitl_aprobar(caso, firma)  # única vía a APROBADO (exige aprobado_por)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    get_caso_repository().save(actualizado)
    return _volver(caso_id, rol)


@router.post("/casos/{caso_id}/rechazar", response_class=RedirectResponse)
def rechazar(caso_id: str, usuario: Optional[str] = Form(None), motivo: Optional[str] = Form(None),
             rol: str = Form(RolUsuario.ANALISTA.value)):
    """Rechazar = negar el siniestro (→ RECHAZADO, `hitl.rechazar`). 🔒 P1: exige `usuario` (firma) + `motivo`;
    409 si el caso ya fue decidido. El humano SÍ puede negar, no solo aprobar (W20/A7)."""
    from app.hitl.c8 import rechazar as hitl_rechazar
    firma = _firma(usuario)
    if not motivo or not motivo.strip():
        raise HTTPException(status_code=400, detail="motivo requerido para rechazar")
    caso = _get_activo(caso_id)
    if caso.estado in _TERMINALES:
        raise HTTPException(status_code=409, detail="El caso ya fue decidido (P1)")
    try:
        actualizado = hitl_rechazar(caso, firma, motivo.strip())  # única vía a RECHAZADO (exige aprobado_por)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    get_caso_repository().save(actualizado)
    return _volver(caso_id, rol)


@router.post("/casos/{caso_id}/escalar", response_class=RedirectResponse)
def escalar(caso_id: str, usuario: Optional[str] = Form(None), motivo: Optional[str] = Form(None),
            rol: str = Form(RolUsuario.ANALISTA.value)):
    """Escalar a revisión humana (REQUIERE_REVISION). NO es terminal (P1). Vía HITL (transicionar)."""
    from app.hitl.c8 import transicionar
    firma = _firma(usuario)
    caso = _get_activo(caso_id)
    if caso.estado in _TERMINALES:
        raise HTTPException(status_code=409, detail="El caso ya fue decidido (P1)")
    razon = (motivo or "").strip() or f"Escalado por {firma}"
    actualizado = transicionar(caso, EstadoCaso.REQUIERE_REVISION, actor=firma, motivo=razon)
    get_caso_repository().save(actualizado)
    return _volver(caso_id, rol)


@router.post("/casos/{caso_id}/enviar_fraude", response_class=RedirectResponse)
def enviar_fraude(caso_id: str, usuario: Optional[str] = Form(None), rol: str = Form(RolUsuario.ANALISTA.value)):
    """Enviar a fraude = ROUTING al carril SIU. 🔒 P6: NO crea alerta, NO cambia dictamen ni estado; solo
    anota `derivado_siu_por`. Es una acción de trabajo, no un veredicto."""
    firma = _firma(usuario)
    caso = _get_activo(caso_id)
    get_caso_repository().save(_persistir_update(caso, {"derivado_siu_por": firma}))
    return _volver(caso_id, rol)


@router.post("/casos/{caso_id}/solicitar_docs", response_class=RedirectResponse)
def solicitar_docs(caso_id: str, usuario: Optional[str] = Form(None), rol: str = Form(RolUsuario.ANALISTA.value)):
    """Prepara el borrador de solicitud de documentos faltantes. Envío MOCK (rotulado): NO envía correo real;
    NO cambia estado. El borrador se compone de los campos faltantes."""
    from app.dashboard import vista_caso
    firma = _firma(usuario)
    caso = _get_activo(caso_id)
    falt = vista_caso.faltantes(caso)
    if not falt:
        borrador = "[demo · no enviado] No hay documentos/datos faltantes que solicitar."
    else:
        borrador = ("[demo · no enviado] Solicitud de documentos preparada por %s: por favor remita %s."
                    % (firma, ", ".join(falt)))
    get_caso_repository().save(_persistir_update(caso, {"solicitud_docs": borrador}))
    return _volver(caso_id, rol)


@router.post("/casos/{caso_id}/guardar_borrador", response_class=RedirectResponse)
def guardar_borrador(caso_id: str, usuario: Optional[str] = Form(None), nota: Optional[str] = Form(None),
                     rol: str = Form(RolUsuario.ANALISTA.value)):
    """Guarda una nota/borrador del operador. NO cambia estado (P1: nunca terminal)."""
    firma = _firma(usuario)
    caso = _get_activo(caso_id)
    texto = (nota or "").strip()
    get_caso_repository().save(_persistir_update(caso, {"nota_operador": f"{firma}: {texto}" if texto else None}))
    return _volver(caso_id, rol)
