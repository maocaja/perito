# W12 — Evidencia clickable → salto a la fuente (NotebookLM) 🔒 P5 · **provider MOCK**

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 2
> **LLM/det:** — (front) · **Depende de:** W11 · **Datos:** **M** · **🔒 P5 → OK + code-reviewer antes del CÓMO.**

## 1. Intent

El cambio enorme: no campos, **evidencia**. *Fecha del accidente → PDF página 3 ✔ · Placa → Fotografía 8 ✔ ·
Nombre → Correo original ✔ · Ciudad → Denuncia ✔.* Todo clickable: al hacer click, **el documento salta
exactamente donde encontró eso** — como NotebookLM.

## 2. Criterios de completitud (verificables)

1. **Cada campo extraído enlaza a su fuente:** reusa `CampoExtraido.origen` (tipo + referencia) — ya existe.
   Se enriquece con un **provider `ancla_evidencia(campo) -> {documento, pagina/coord, offset}`** cuya interfaz
   consumirá M1/M2; **hoy devuelve anclas mock/sembradas** (rotuladas P7).
2. **Visor de documento** (columna central) que, al hacer click en un campo, abre el documento del provider y
   **resalta la ubicación** (página/coordenada/offset). Con datos mock hasta M1.
3. **Bidireccional:** desde la galería (W11) y desde los Riesgos (W5) también se salta a la evidencia.
4. **Fail-closed:** si un campo no tiene ancla, se muestra "sin fuente localizada", no un salto falso (P7).

## 3. Invariantes / restricciones

- **🔒 P5:** el visor muestra el documento **redactado** (PII tapada) o el mock; **nunca** PII cruda. Las
  coordenadas/anclas no filtran PII.
- **P3:** el enlace preserva la trazabilidad campo↔origen (auditabilidad).
- **P7:** anclas mock rotuladas; ausencia de ancla se declara, no se finge.

## 4. Fuera de alcance

- OCR/coordenadas reales sobre documentos (M1/M2). Redacción visual real (fase-2).

## 5. Verificación (tests fail-closed)

- Un campo con `origen` real enlaza a su fuente; sin ancla → "sin fuente localizada" (no salto falso).
- El visor nunca muestra PII cruda (P5, aserción sobre el contenido servido).
- La interfaz del provider de anclas es la que consumirá M1/M2 (contrato estable).

## 6. Notas CÓMO

Provider `ancla_evidencia(campo)` (mock intercambiable) + visor (parcial) en la columna central que resalta la
ubicación. Reusa `CampoExtraido.origen`. Assets demo redactados.

## 7. Precisiones tras code-review

- **🟡 Semántica de `ancla_evidencia` (fail-closed explícito):** `ancla_evidencia(campo) ->
  {documento_id, pagina, coord} | None`. El visor **solo abre si retorna no-None**; si es `None`, el click
  muestra "sin fuente localizada" (toast/modal), **nunca un salto falso** (P7). Igual para W5: un riesgo sin
  ancla tiene el click deshabilitado/con aviso, no un salto inventado.

### Tras el CÓMO
- **🔴 P5 corregido (reviewer):** el `title` del origen en la tabla de datos ahora pasa por `|redact` (una
  referencia real podría traer PII). El visor cita el documento por **etiqueta** (no nombre crudo); fail-closed
  (sin ancla → "sin fuente localizada", test). **Clean Code:** constantes de zona nombradas (sin magic numbers);
  `pagina`/`linea` con `is not none` (0 válido). `Ancla`/`ancla_de` = interfaz estable que M1/M2 llenan (DIP).
