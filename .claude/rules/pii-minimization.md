# Regla: Minimización de PII (P5) — NO NEGOCIABLE

Habeas Data por diseño. Dos niveles, ambos P5:

1. **Minimización** — no incluir PII en el prompt de entrada al LLM (deny-by-default: solo lo operacional).
2. **Redacción** — si algo debe ir, remover los spans antes (`redact_pii_spans_es_co` / `redact_pii_extendida`).

Invariantes:
- **Ningún texto con PII llega a un LLM sin redacción previa.** Todo prompt (extractor C2, verificador C3,
  triage C0, razonamiento de fraude) parte de texto **ya redactado**.
- **Ningún adjunto con PII cruda se muestra ni se persiste:** se redacta, o se guarda **solo la huella**
  (nunca la imagen/media cruda con PII).
- **La evidencia de fraude/historia referencia solo `caso_id` opaco**, nunca PII (cédula/placa/nombre/media).
- **El remitente del correo se omite** (no se captura en `CorreoEntrante`).

**🚫 Prohibido:**
- Enviar `texto_crudo`/cuerpo de correo/adjunto **sin redactar** a un LLM.
- Persistir o mostrar media cruda con PII (solo huella).
- Filtrar PII a logs o a la evidencia de una alerta.

**⚠️ Gaps declarados (P7, no ocultos):** el NER de nombres/direcciones es **heurístico** (fase 1); la
redacción **visual** de imágenes (caras/cédulas/placas) es **fase 2** — hasta entonces las imágenes van
**solo como huella perceptual** (pHash, no el contenido visual crudo). No se promete redacción visual en fase 1.

**Verificado (fail-closed) por:** `test_u2_redaction.py`, `test_redaction_denybydefault.py`
(deny-by-default), `test_u7_triage.py` (cuerpo redactado antes del LLM), `test_u4_multimodal.py`
(inyección + redacción de adjunto).

Si una tarea te llevaría a violar esto, **detente y avísame** — no lo implementes.
Contexto completo: `specs/prd.md` (Principio P5) · spec de gobernanza: `specs/aidlc/evolution/gov-rules-p5-p6.md`.
