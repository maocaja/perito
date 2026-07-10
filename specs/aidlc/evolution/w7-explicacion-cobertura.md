# W7 — Explicación "por qué" de la cobertura

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** R · **Invariante:** P2

## 1. Intent

No solo *decir* "Cobertura válida", sino **explicar por qué**: *"La póliza incluye Daño Material. Vigente hasta
12/08/2026. Deducible 10%."* Todo resumido, citando la regla y la cláusula.

## 2. Criterios de completitud (verificables)

1. **Explicación estructurada** del dictamen: resultado + **regla aplicada** + **cláusula citada** + (U3
   product-aware) **cobertura aplicada / sublímite / deducible / vigencia** — todo ya está en `Dictamen` y
   `Poliza`/`CoberturaContratada`.
2. **Lenguaje humano** ("Cubierto parcial porque…") derivado del enum del motor, **sin re-decidir** (P2).
3. Panel junto al dictamen en la columna central/derecha.

## 3. Invariantes / restricciones

- **🔒 P2:** la explicación **presenta** la decisión del motor R1-R5; **no la re-calcula ni la altera**. Cita
  literal de la regla y la cláusula (auditabilidad P2/P3).
- **P1:** informativo; el humano decide.
- **P7:** si falta un dato del dictamen (p.ej. sin cláusula en REQUIERE_REVISION), se dice, no se inventa.

## 4. Fuera de alcance

- Cambiar el motor o las reglas (P2 protegido); W7 es **presentación**.

## 5. Verificación (tests fail-closed)

- La explicación cita la **misma** regla/cláusula/resultado que el `Dictamen` (no diverge del motor).
- Un dictamen `REQUIERE_REVISION` sin cláusula → la explicación lo refleja, no fabrica cláusula.
- El deducible/sublímite mostrado coincide con `dictamen`/`poliza` (U3).

## 6. Notas CÓMO

Nuevo view-model `explicacion_cobertura(caso)` sobre `dictamen`/`poliza` (determinístico, presentacional).
Reusa `_label_cobertura`/`_nivel_cobertura`. Parcial junto al dictamen.

## 7. Precisiones tras code-review (CÓMO)

- **🔒 P2 verificado:** test comprueba que `explicacion_cobertura` cita el MISMO resultado/regla/deducible que
  `Dictamen` (no diverge). **P5 defensa:** `_frase_cobertura` redacta los valores con `_red`. P1: sin
  `PALABRAS_PROHIBIDAS`.
