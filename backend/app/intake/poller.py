"""app/intake/poller.py — poller de correo para la demo en vivo (Unit H).

Hilo daemon que, GATED por `settings.demo_live`, lee los correos no-leídos del buzón demo y arma un
caso por correo:
- `real` → pipeline real (`intake → orquestar_fnol`, agentes Claude) + traza (→ Langfuse si on).
- `deterministic` → mapea el marcador `[DEMO:<escenario>]` del asunto → preset (sin LLM, gratis).

INVARIANTES:
- **P1 (HITL):** el poller **PREPARA** (deja el caso en LISTO_PARA_APROBAR / REQUIERE_REVISION);
  **NUNCA firma** ni alcanza terminal. Solo el operador cierra desde el detalle.
- **P4 (idempotencia / no-loop):** cada correo se marca leído **SIEMPRE** (éxito o error) → no se
  reprocesa; un correo que falla queda como REQUIERE_REVISION (escala, no inventa); el loop duerme.
- **Fail-safe de arranque:** si falta credencial, loguea y NO arranca (la app levanta igual).
- **Concurrencia:** hilo en el MISMO proceso que el web → comparte el repo; `save` bajo `Lock`.
"""

import logging
import re
import threading
import time

from app.config import settings

logger = logging.getLogger(__name__)

_SCENARIO_RE = re.compile(r"\[DEMO:([a-z-]+)\]", re.IGNORECASE)
_save_lock = threading.Lock()
_started = False


def _escenario_de_asunto(asunto: str) -> str:
    """Extrae el escenario del marcador del asunto; default 'feliz' si no hay marcador."""
    m = _SCENARIO_RE.search(asunto or "")
    return m.group(1).lower() if m else "feliz"


def iniciar_poller() -> bool:
    """Arranca el hilo del poller si `demo_live != off` y hay credenciales.

    Fail-safe: si falta algo, loguea y NO arranca (la app sigue normal). Devuelve True si arrancó.
    """
    global _started
    if settings.demo_live == "off" or _started:
        return False
    if not settings.demo_gmail_address or not settings.demo_gmail_app_password:
        logger.warning(
            "DEMO_LIVE=%s pero faltan DEMO_GMAIL_* → poller NO arranca (la app sigue normal).",
            settings.demo_live,
        )
        return False
    if settings.demo_live == "real":
        _sembrar_polizas()
    threading.Thread(target=_loop, name="perito-mail-poller", daemon=True).start()
    _started = True
    logger.info("Poller de correo arrancado (modo=%s, cada %ss).", settings.demo_live, settings.poll_interval_s)
    return True


def _sembrar_polizas() -> None:
    """Modo real: siembra las pólizas de los escenarios para que C4 (lookup) las encuentre."""
    from app.policy.lookup import set_poliza_store
    from demo_run import ESCENARIOS

    set_poliza_store({e["poliza"].numero: e["poliza"] for e in ESCENARIOS if e["poliza"]})


def _procesar_lote(mb) -> int:
    """Procesa los no-leídos de un `mb` abierto. Marca leído SIEMPRE (idempotencia P4). Testeable."""
    n = 0
    for correo in mb.fetch_unseen():
        try:
            _procesar(correo)
        except Exception:
            logger.exception("Poller: correo %s falló al procesar.", correo.uid)
        finally:
            try:
                mb.marcar_leido(correo.uid)  # SIEMPRE (éxito o error) → no se reprocesa, no loopea
            except Exception:
                logger.exception("Poller: no pude marcar leído %s.", correo.uid)
        n += 1
    return n


def _loop() -> None:
    from app.intake.mailbox import Mailbox

    while True:
        try:
            with Mailbox.from_settings() as mb:
                _procesar_lote(mb)
        except Exception:
            logger.exception("Poller: ciclo falló (IMAP?). Reintento en %ss.", settings.poll_interval_s)
        time.sleep(settings.poll_interval_s)


def _ingerir_adjuntos(caso, correo):
    """M1: adjuntos del correo → `Adjunto`s colgados del caso + huellas registradas (foto reutilizada, U6).

    Registra las huellas ANTES de orquestar (el cross-claim del propio caso se auto-excluye por `excluir_id`).
    Passive (P6/P5): leer/redactar/huellar/indexar; no decide ni persiste media cruda. Devuelve el caso (con
    adjuntos si los hubo) — si no hay adjuntos, el caso vuelve intacto y los providers caen al mock (P7)."""
    from app.intake.document_ai import procesar_adjuntos, registrar_huellas

    # Defensivo a propósito: el poller recibe correos externos (y dobles de test) que pueden no traer el campo.
    adjuntos = procesar_adjuntos(getattr(correo, "adjuntos", []) or [])
    if not adjuntos:
        return caso
    registrar_huellas(adjuntos, caso.id)
    return caso.model_copy(update={"adjuntos": adjuntos})


def _correlacionar_evidencia(caso, tracer):
    """M3: cruza fuentes (correo ↔ adjuntos) tras M1/M2. Adjunta el overlay `correlaciones` y emite el evento
    de traza (Timeline W18). 🔒 P6: informativo — no toca estado. Latente (P7): vacío si no hay ≥2 fuentes."""
    from app.agents.evidence_correlator import correlacionar

    correlaciones = correlacionar(caso)
    if not correlaciones:
        return caso
    divergencias = sum(1 for c in correlaciones if not c.coincide)
    if tracer is not None:
        tracer.emit("evidence_correlator",
                    f"Cruzó fuentes en {len(correlaciones)} campo(s); {divergencias} inconsistencia(s)")
    return caso.model_copy(update={"correlaciones": correlaciones})


def _fusionar_entidades_del_correo(caso):
    """Modo deterministic: fusiona en la extracción del preset los campos ricos que M2 (`extraer_entidades`,
    determinístico — NO mock) saca del cuerpo del correo. Da PARIDAD con `real` (donde el extractor ya los
    fusiona, extractor.py). Sin colisión: los nombres ricos son disjuntos de los 4 base; se omite un nombre
    ya presente (no-duplicación). Passive/P5: `extraer_entidades` es determinístico y no manda PII a un LLM."""
    from app.contracts.extraccion import ExtraccionValidada
    from app.intake.entidades import extraer_entidades

    if not caso.extraccion or not caso.aviso:
        return caso
    presentes = {c.nombre for c in caso.extraccion.campos}
    ricos = [c for c in extraer_entidades(caso.aviso.texto_crudo) if c.nombre not in presentes]
    if not ricos:
        return caso
    return caso.model_copy(update={"extraccion": ExtraccionValidada(campos=list(caso.extraccion.campos) + ricos)})


def _procesar(correo) -> None:
    """Un correo → un caso, guardado + trazado. NUNCA alcanza terminal (P1)."""
    from app.dashboard.store import get_caso_repository

    if settings.demo_live == "deterministic":
        from app.contracts.enums import CalidadDoc
        from app.contracts.extraccion import AvisoNormalizado
        from app.demo.scenarios import construir_caso_preset
        from app.demo.seed import sembrar_traza_demo

        key = _escenario_de_asunto(correo.asunto)
        try:
            caso = construir_caso_preset(key)
        except ValueError:
            caso = construir_caso_preset("feliz")
        # Conserva el CORREO tal cual llegó como aviso (el operador debe ver lo que entró); la
        # extracción/dictamen son del preset (sin LLM). Números de póliza alineados → sin desajuste.
        caso = caso.model_copy(update={"aviso": AvisoNormalizado(texto_crudo=correo.cuerpo, calidad=CalidadDoc.LIMPIO)})
        caso = _fusionar_entidades_del_correo(caso)  # M2: campos ricos del cuerpo (paridad con real)
        caso = _ingerir_adjuntos(caso, correo)  # M1: adjuntos reales sobre el caso preset (si el correo trae)
        caso = _correlacionar_evidencia(caso, None)  # M3: overlay cross-fuente (sin traza en modo preset)
        with _save_lock:
            get_caso_repository().save(caso)
        sembrar_traza_demo(caso)
        return

    # modo real — mismo cableado que demo_run (tier real), fail-closed a REQUIERE_REVISION (P1/P4).
    # C0 Triage (U7): clasifica el correo ANTES del pipeline. Solo un NO_SINIESTRO con confianza
    # suficiente se desvía a una cola aparte (no crea caso FNOL). Todo lo demás — incluido el
    # escalamiento por baja confianza — sigue al pipeline: nunca se pierde un aviso (P1/P4).
    from app.intake.triage import RutaCorreo, rutear, triage

    ruta = rutear(triage(correo.asunto, correo.cuerpo))
    if ruta is RutaCorreo.COLA_NO_SINIESTRO:
        logger.info("Triage: correo %s → NO_SINIESTRO → cola aparte (sin caso FNOL).", correo.uid)
        return

    from app.contracts.dictamen import Cotas
    from app.contracts.enums import CalidadDoc, EstadoCaso
    from app.contracts.extraccion import AvisoNormalizado
    from app.hitl import c8
    from app.intake.c1 import intake_crear_caso
    from app.observability.replay import get_replay_store
    from app.observability.tracer import Tracer
    from app.orchestrator.c7 import orquestar_fnol

    caso = intake_crear_caso(AvisoNormalizado(texto_crudo=correo.cuerpo, calidad=CalidadDoc.LIMPIO))
    caso = _ingerir_adjuntos(caso, correo)  # M1: adjuntos leídos/redactados/huellados antes de orquestar
    tracer = Tracer(caso.id)
    try:
        caso = orquestar_fnol(caso, c8, Cotas(max_rondas=1, presupuesto_tokens=50000), tracer)
    except Exception as e:  # fail-closed: escala, no inventa (P4); nunca terminal (P1)
        caso = caso.model_copy(update={
            "estado": EstadoCaso.REQUIERE_REVISION,
            "motivo_escalamiento": f"Orquestación falló: {e}",
        })
    caso = _correlacionar_evidencia(caso, tracer)  # M3: cruza fuentes (informativo, P6) + traza W18
    with _save_lock:
        get_caso_repository().save(caso)
    get_replay_store().save(tracer, caso.estado.value, caso.motivo_escalamiento)
