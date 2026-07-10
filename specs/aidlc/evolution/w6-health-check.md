# W6 — Health Check (% completo + checklist unificado)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** R

## 1. Intent

Como un CI/CD del caso: *"Caso 92% completo — ✔ Cliente · ✔ Cobertura · ✔ Vehículo · ✔ Fecha · ⚠ Licencia
ilegible · ⚠ Falta tarjeta propiedad · ✔ Denuncia · ✔ Fotografías"*. **No descubrir errores al final.**

## 2. Criterios de completitud (verificables)

1. **% de completitud** derivado determinísticamente de los checks (campos presentes/ausentes + documentos +
   verificación) — reusa `checklist_documentos`, `checklist_aprobacion`, `faltantes`, `_presentes`.
2. **Lista de checks** con estado ✔ / ⚠ / ✗ y detalle honesto (por qué falla) — sin fabricar (P7: si un dato
   falta, el detalle lo dice).
3. Ítems que dependen de adjuntos ("Licencia ilegible", "Fotografías") usan el **provider** documental (mock
   rotulado hasta W11/M1).
4. Panel en la columna derecha (o bajo el header), siempre visible.

## 3. Invariantes / restricciones

- **P1:** el `%` y los ✔ son **informativos** (azúcar de UI); el gate real de aprobación sigue en `hitl`
  (mismo principio que `checklist_aprobacion`).
- **P7:** cero fabricación; el detalle refleja el estado real; los checks mock van rotulados.

## 4. Fuera de alcance

- Validación real de legibilidad de documentos (depende de M1); aquí el agregado + el %.

## 5. Verificación (tests fail-closed)

- El `%` es reproducible desde los checks (no un número mágico).
- Ningún check inventa un dato ausente; los faltantes aparecen como ⚠/✗ con su detalle.
- El panel nunca habilita/deshabilita la firma por sí mismo (P1).

## 6. Notas CÓMO

Nuevo view-model `health_check(caso, traza)` que agrega los checks existentes + calcula `%`. Parcial en la
columna derecha.

## 7. Precisiones tras code-review (CÓMO)

- **P7 honesto:** solo `CUBIERTO` es ✔; `CUBIERTO_PARCIAL`/`NO_CUBIERTO`/`REQUIERE_REVISION` → ⚠ (no un falso
  "todo bien"). Los ítems de documentos van `na` + rotulados demo y **no** cuentan al `%` (reproducible).
