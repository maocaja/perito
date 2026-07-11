# M1 — *(Mejora)* Ingesta de adjuntos real al pipeline + contrato `Adjunto` 🔒 P5

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** M (mejora)
> **LLM/det:** 🤖+⚙️ · **Depende de:** U4 · **Datos:** R · **🔒 P5 → OK + code-reviewer antes del CÓMO.**

## 1. Intent

Reemplazar los **providers mock** de W3/W11/W12 por datos **reales**: que los adjuntos (PDF/imagen) del correo
**fluyan al pipeline**, se lean (U4 multimodal), se redacten (P5) y se guarde su **huella**. La UF/UI **no
cambia** — se conecta el mismo contrato que hoy sirve el mock.

## 2. Criterios de completitud (verificables)

1. **Contrato `Adjunto`** en `Caso` (nombre, tipo, texto-redactado, huella `pHash`, origen/ancla) — la misma
   forma que consume `documentos_de`/`conteo_adjuntos`/`ancla_evidencia` (W11/W3/W12).
2. **El poller/intake adjunta** los archivos del correo al `Caso`; `intake/multimodal` los lee (PDF-texto hoy;
   imagen/audio fase-2), **redacta** y produce la huella.
3. **Registro de huella** en `HuellaStore` (U6) → activa **foto reutilizada** cross-claim real.
4. Los conteos/galería/anclas pasan a ser **reales** sin tocar las vistas (mismo provider).

## 3. Invariantes / restricciones

- **🔒 P5:** ningún adjunto con PII cruda se muestra/persiste; se redacta o se guarda solo la huella. Regla
  `pii-minimization.md`.
- **P4:** cotas de nº/tamaño de adjuntos por caso; timeouts.
- **Seguridad:** contenido de adjunto = input no confiable, aislado del prompt de decisión (ya en U4).

## 4. Fuera de alcance

- Redacción visual perfecta de imágenes (fase-2); OCR/audio pesado (fase-2).

## 5. Verificación (tests fail-closed)

- Un adjunto con PII → se redacta antes de mostrarse/persistirse; imagen cruda no se persiste (solo huella).
- Los providers de W11/W12/W3 devuelven datos reales con la **misma interfaz** (los tests de esas units siguen
  verde al cambiar mock→real).
- Dos casos con la misma foto → foto reutilizada real dispara (U6).

## 6. Notas CÓMO

Contrato `Adjunto`; extensión del poller/`intake/c1`/`multimodal`; registro en `HuellaStore`. Reemplaza los
providers mock por la implementación real. **Toca intake + persistencia → P5.**

## 7. Precisiones tras code-review

**Ronda CÓMO (2026-07-10, 0 críticos — aprobado):**
- **P5 (aplicado):** el redactor de dominio preserva números a propósito (pólizas/montos, P2), así que un
  filename como `Documento_52987654.pdf` no se redactaba. Se añadió `document_ai._redactar_nombre` (redactor
  de dominio + enmascarado de dígitos ≥6) — fail-closed sobre el nombre, sin tocar el redactor global.
- **Clean Code (aplicado):** se quitó el `getattr(caso, "adjuntos", None) or []` redundante en los providers
  (el campo tiene `default_factory`); se **conserva** el `getattr` en el poller (recibe correos externos y
  dobles de test que pueden no traer el campo — su quita rompía 2 tests).
- **Doc (aplicado):** documentada la fórmula de `_confianza_por_distancia` en `cross_claim.py`.
- **Dedup (propio):** `registrar_huellas` de-duplica huellas repetidas en un caso (una foto adjunta dos veces
  no duplica la evidencia de fraude).

**Alcance confirmado (diferido a M2, honesto P7):**
- La **alimentación del texto de adjuntos al extractor C2** (`combinar_para_extraccion`, ya existe) es de M2
  (extracción rica), no de M1 — M1 entrega documentos + huella + galería/conteos reales.
- Las **anclas de evidencia con coordenadas reales** (OCR página/zona) son fase-2/M2; M1 deja `ancla_de` en
  su forma actual.
- El **generador de correos demo** (`demo_mail.py`) aún manda solo texto → para VER M1 en vivo hay que
  adjuntar una foto/PDF (wiring opcional del demo, fuera del contrato M1).
