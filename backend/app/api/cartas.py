"""Router de cartas al asegurado (Unit M, demo-scope). Capa ACTIVA (genera borrador + envía SMTP).

- **P1 (draft ≠ send):** el agente REDACTA un borrador; el humano lo firma y ENVÍA. `usuario` obligatorio
  → 400. Cero auto-envío.
- **P2/P7 (cobertura verbatim):** la carta de resolución se arma con plantilla determinística que cita el
  dictamen LITERAL (regla + cláusula). Si un LLM pule la prosa, un guardrail fail-closed verifica que la cita
  sobrevive; si no, se descarta el pulido y se usa la plantilla.
- **Demo-scope:** destinatario fijo al buzón demo (`settings.demo_gmail_address`); borrador on-demand (NO se
  persiste en `Caso`, cero cambios de contrato). Auditoría/persistencia real → unidad de producción.
"""

from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.config import settings
from app.contracts.enums import RolUsuario
from app.dashboard.c11 import _get_o_404, _TEMPLATES
from app.dashboard import vista_caso
from app.intake.mailbox import Mailbox

router = APIRouter(tags=["cartas"])

_CAMPO_ES = {
    "numero_poliza": "número de póliza", "fecha_siniestro": "fecha del siniestro",
    "tipo_siniestro": "tipo de siniestro", "monto_reclamado": "monto reclamado",
}


def _key_real() -> bool:
    k = (settings.anthropic_api_key or "").strip()
    return bool(k) and k.lower() != "test"


def plantilla_carta(caso, tipo: str) -> str:
    """Borrador determinístico. La resolución cita el dictamen LITERAL (P2/P7)."""
    cid = caso.id[:8]
    if tipo == "datos":
        faltantes = ", ".join(_CAMPO_ES.get(c, c) for c in vista_caso.faltantes(caso))
        return (
            "Estimado(a) asegurado(a):\n\n"
            f"Para continuar con el análisis de su siniestro {cid}, necesitamos el siguiente dato: {faltantes}.\n\n"
            "Por favor respóndanos adjuntando esta información para poder dictaminar la cobertura.\n\n"
            "Atentamente,\nEquipo de siniestros"
        )
    # resolución (estado terminal)
    d = caso.dictamen
    admitido = caso.estado.value == "APROBADO"
    veredicto = "ADMITIDA" if admitido else "NO ADMITIDA"
    fundamento = ""
    if d is not None:
        cl = f", cláusula {d.clausula.id} — {d.clausula.texto} ({d.clausula.referencia})" if d.clausula else ""
        fundamento = f"\n\nFundamento: {d.resultado.value} según la regla {d.regla_aplicada}{cl}."
    motivo = ""
    if not admitido and getattr(caso, "motivo_escalamiento", None):
        motivo = f"\n\nMotivo: {caso.motivo_escalamiento}"
    return (
        "Estimado(a) asegurado(a):\n\n"
        f"En relación con su siniestro {cid}, le informamos que, tras la revisión, su reclamación ha sido {veredicto}."
        f"{fundamento}{motivo}\n\n"
        "Atentamente,\nEquipo de siniestros"
    )


def cita_intacta(texto: str, caso) -> bool:
    """Guardrail P2/P7: la cita literal del dictamen Y el veredicto deben sobrevivir al pulido.

    Verifica regla + cláusula (cobertura) y, en un caso terminal, que el veredicto no se volteó
    (ADMITIDA ↔ NO ADMITIDA) — cierra el vector de inyección vía texto libre. Sin dictamen → True.
    """
    d = caso.dictamen
    if d is None:
        return True
    ok = d.regla_aplicada in texto
    if d.clausula:
        ok = ok and d.clausula.id in texto
    est = caso.estado.value
    if est == "APROBADO":
        ok = ok and ("ADMITIDA" in texto) and ("NO ADMITIDA" not in texto)
    elif est == "RECHAZADO":
        ok = ok and ("NO ADMITIDA" in texto)
    return ok


def pulir_prosa(texto: str, caso, tipo: str) -> str:
    """Pulido de prosa opcional (LLM). Fail-closed: sin key o si el guardrail falla → plantilla intacta.

    El guardrail de cobertura verbatim solo aplica a la carta de `resolucion` (la que cita el dictamen).
    """
    if not _key_real():
        return texto
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model=settings.extractor_model, max_tokens=700,
            messages=[{"role": "user", "content":
                "Reescribe esta carta a un asegurado en tono cálido y profesional, en español. NO cambies, "
                "elimines ni parafrasees ninguna cita de regla, cláusula, id, referencia ni el veredicto. "
                "Devuelve solo la carta:\n\n" + texto}],
        )
        pulido = "".join(getattr(b, "text", "") for b in resp.content).strip()
        if not pulido:
            return texto
        if tipo == "resolucion" and not cita_intacta(pulido, caso):
            return texto  # guardrail fail-closed (P2/P7): la cita no sobrevivió → plantilla
        return pulido
    except Exception:
        return texto


def _render_carta_drawer(request, caso, **extra):
    """W20/A7: la carta se muestra en el drawer de la Workbench (ya no re-renderiza la página detalle)."""
    ctx = {"caso": caso, **extra}
    return _TEMPLATES.TemplateResponse(request, "workbench_carta.html", ctx)


@router.post("/casos/{caso_id}/carta", response_class=HTMLResponse)
def preparar_carta(request: Request, caso_id: str, rol: str = Form(RolUsuario.ANALISTA.value)):
    """Genera el borrador on-demand y abre el drawer de carta con el textarea editable (P1: draft ≠ send)."""
    caso = _get_o_404(caso_id)
    tipo = vista_caso.tipo_carta(caso)
    if tipo is None:
        raise HTTPException(status_code=400, detail="No aplica carta para este estado")
    borrador = pulir_prosa(plantilla_carta(caso, tipo), caso, tipo)
    return _render_carta_drawer(request, caso, borrador=borrador, carta_tipo=tipo)


@router.post("/casos/{caso_id}/carta/enviar", response_class=HTMLResponse)
def enviar_carta(request: Request, caso_id: str,
                 usuario: Optional[str] = Form(None), contenido: Optional[str] = Form(None),
                 rol: str = Form(RolUsuario.ANALISTA.value)):
    """P1: envío = acción humana firmada. Fail-safe: un fallo de SMTP no cambia el caso (no 500)."""
    if not usuario or not usuario.strip():
        raise HTTPException(status_code=400, detail="usuario requerido (firma válida, P1)")
    caso = _get_o_404(caso_id)
    tipo = vista_caso.tipo_carta(caso)
    if tipo is None:
        raise HTTPException(status_code=400, detail="No aplica carta para este estado")
    cuerpo = (contenido or "").strip() or plantilla_carta(caso, tipo)
    try:
        Mailbox.from_settings().enviar(asunto=f"Su siniestro {caso.id[:8]} — Perito", cuerpo=cuerpo)
    except Exception as e:  # fail-safe (P): caso intacto, sin 500 — se re-muestra el borrador con el error
        return _render_carta_drawer(request, caso, borrador=cuerpo, carta_tipo=tipo,
                                    carta_error=f"No se pudo enviar la carta: {e}")
    return _render_carta_drawer(request, caso, carta_enviada=True)
