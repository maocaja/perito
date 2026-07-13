# Regla: Minimización de PII (P5) — NO NEGOCIABLE

Habeas Data por diseño. La minimización se aplica en la **frontera de máquina** (LLM, logs, persistencia de
media cruda), **NO hacia el operador humano autorizado**. Ley 1581: principio de "acceso y circulación
restringida" = conocimiento **restringido a terceros AUTORIZADOS**, no oculto a quien tiene finalidad legítima.

**Dos destinos, dos reglas:**
1. **Al LLM / logs / persistencia (máquina):** minimizar y redactar SIEMPRE (deny-by-default). El modelo no
   necesita PII → nunca la ve (`redact_pii_spans_es_co` / `redact_pii_extendida`).
2. **Al operador (encargado del tratamiento con finalidad legítima):** ve el **dato real** en su vista —
   campos estructurados (cédula/teléfono/placa) y el **correo original** — porque lo necesita para trabajar
   (verificar identidad, contactar, cruzar fraude). Ocultárselo lo empuja a canales no auditados (peor).

Invariantes:
- **Ningún texto con PII llega a un LLM sin redacción previa.** Todo prompt (extractor C2, verificador C3,
  triage C0, razonamiento de fraude) parte de texto **ya redactado**.
- **Ningún adjunto con PII cruda se persiste** (solo la **huella**, nunca la imagen/media cruda). La media
  real que se muestra en el visor proviene **solo** de assets de demo sintéticos (`demo_assets/`), jamás de
  la media de un correo real.
- **La evidencia de fraude/historia (texto DERIVADO) referencia solo `caso_id` / se redacta**, nunca PII —
  es texto generado, se mantiene conservador aunque los campos del operador muestren el dato.
- **El remitente del correo se omite** (no se captura en `CorreoEntrante`). **PII nunca a logs.**

**⚖️ Enmascarar + revelar-por-rol + log de acceso** (dynamic data masking, RBAC) es la evolución correcta
**cuando** aparezca: (a) más de un rol con necesidades distintas, (b) auditoría de cumplimiento, o (c)
producción con datos reales. Con un único operador autorizado sobre datos sintéticos **no se justifica** —
mantener simple (mostrar en claro al operador). Decisión de gobernanza: no relajar la frontera de máquina.

**🚫 Prohibido:**
- Enviar `texto_crudo`/cuerpo de correo/adjunto **sin redactar** a un LLM.
- Persistir media cruda con PII (solo huella) o servir la media de un correo real en el visor.
- Filtrar PII a logs o a la evidencia (texto derivado) de una alerta.

**⚠️ Gaps declarados (P7, no ocultos):** el NER de nombres/direcciones es **heurístico** (fase 1); la
redacción **visual** de imágenes (caras/cédulas/placas) es **fase 2** — hasta entonces las imágenes van
**solo como huella perceptual** (pHash, no el contenido visual crudo). No se promete redacción visual en fase 1.

**Verificado (fail-closed) por:** `test_u2_redaction.py`, `test_redaction_denybydefault.py`
(deny-by-default), `test_u7_triage.py` (cuerpo redactado antes del LLM), `test_u4_multimodal.py`
(inyección + redacción de adjunto).

Si una tarea te llevaría a violar esto, **detente y avísame** — no lo implementes.
Contexto completo: `specs/prd.md` (Principio P5) · spec de gobernanza: `specs/aidlc/evolution/gov-rules-p5-p6.md`.
