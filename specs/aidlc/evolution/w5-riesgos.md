# W5 — Riesgos ("míralo", no "fraude") 🔒 P6

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** R · **🔒 P6 → OK explícito + code-reviewer antes del CÓMO.**

## 1. Intent

El operador no quiere que le digan "fraude". Quiere que le digan **"míralo"**. Reencuadra la alerta como
**Riesgos**: *"Se detectaron 3 posibles inconsistencias"* → cada una clickable: *"La fecha del PDF difiere del
correo", "La placa difiere en una fotografía", "El valor estimado es muy superior al promedio"*. Sugerencia,
no veredicto.

## 2. Criterios de completitud (verificables)

1. **Panel "Riesgos"** (columna derecha) que lista las `inconsistencias` de `alerta_fraude` (reusa `senal_fraude`
   / `confianza_riesgo`), con severidad + confianza — datos reales de U6/fraude.
2. **Framing "míralo":** título "Riesgos a revisar", nunca "Fraude confirmado"; cada ítem invita a mirar, no
   dictamina.
3. **Cada riesgo es clickable** → resalta la evidencia relacionada (enlaza a W12 cuando exista; hoy ancla al
   campo/documento con el **provider** de evidencia, mock rotulado).
4. **Confianza visible** por señal (< 1.0 siempre, P7).

## 3. Invariantes / restricciones

- **🔒 P6 (absoluto):** el panel **solo sugiere**. No cambia `caso.estado`, no deshabilita la firma, no
  bloquea — ni con la señal más fuerte. Cero lenguaje de veredicto.
- **P7:** toda señal lleva confianza (nunca 1.0); un falso positivo es sugerencia, no verdad.
- **P5:** la evidencia referencia el origen (campo/doc/`caso_id`), nunca PII cruda.

## 4. Fuera de alcance

- Nueva detección de fraude (eso ya vive en U6/`fraud/`); W5 es **presentación/reencuadre**.

## 5. Verificación (tests fail-closed)

- El panel de Riesgos **no** contiene palabras de veredicto/decisión; el caso con riesgo sigue `LISTO_PARA_
  APROBAR` y la firma habilitada (🔒 P6, aserción).
- Refleja las inconsistencias reales de `alerta_fraude`; si no hay, muestra "Sin riesgos detectados".
- Ninguna confianza mostrada = 1.0.

## 6. Notas CÓMO

Reusa `alerta_fraude`/`senal_fraude`/`confianza_riesgo`. Parcial "riesgos" en la columna derecha. Reencuadre
de copy (no lógica). El click enlaza al provider de evidencia (W12).

## 7. Precisiones tras code-review (CÓMO)

- **🔒 P6 verificado (no teatro):** test aísla el form de "Radicar" y confirma que un caso LISTO con riesgo
  sigue LISTO y sin `disabled` → la señal no decide.
- **P5 defensa en profundidad:** la `referencia` cruda se **redacta en el dict** (`_red`), no solo en el
  template; `_riesgo_legible` calcula del prefijo (sin PII). Guard defensivo `not fr.inconsistencias` → "no hay
  riesgos". Clave `lista` (no `items`, colisiona con `dict.items` en Jinja).
