# U9 — Loop reflexivo C2↔C3 (evaluator-optimizer) 🔒 P4

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Interno · **LLM/det:** 🤖 · **Depende de:** —
> **🔒 Toca `orchestrator/` (P4) → OK explícito + code-reviewer antes del CÓMO.**

## 1. Intent

Subir el **techo agéntico real** (el único upgrade auténtico según los expertos): hoy el pipeline es de **una
pasada** (`max_rondas=1`); cuando C3 detecta baja fidelidad, **escala** — no re-extrae. Darle a C3 **poder de
feedback**: su crítica dispara **una** re-extracción de C2. Convierte a Perito de *pipeline* en **agente
reflexivo** (evaluator-optimizer), el patrón #1 de 2026.

## 2. Criterios de completitud (verificables)

1. **Loop acotado C2↔C3:** si C3 marca baja fidelidad en un campo → C2 **re-extrae UNA vez** con la crítica de
   C3 como feedback, con **`max_rondas=2` (cap duro) + detección de ciclo**. Si sigue mal → **escala** (como hoy).
2. **Visible:** el "antes → después" aparece en el feed de actividad ("Extractor corrigió `monto` tras crítica
   del Verificador").
3. **P2 intacto:** la reflexión es sobre **extracción de campos**, NUNCA sobre cobertura.
4. **P4 intacto:** el cap lo pones **por encima** de LangGraph; no se relaja ni se quita.

## 3. Invariantes / restricciones

- **🔒 P4:** máximo de rondas + presupuesto de tokens + detección de ciclos — duros. Sin loops sin cota.
- **P2:** el loop no re-decide cobertura; el motor R1-R5 sigue siendo el único que dictamina.
- **P1:** sigue preparando; el humano decide.
- **Costo:** una ronda extra como máximo; presupuesto de tokens acotado.

## 4. Fuera de alcance

- Reflexión en otros nodos (solo C2↔C3).
- Más de una ronda de re-extracción.

## 5. Verificación (tests fail-closed)

- Baja fidelidad → una re-extracción con feedback; si persiste → escala (no loopea).
- `max_rondas=2` respetado; ciclo detectado corta.
- El loop **no** toca la decisión de cobertura (aserción).
- Presupuesto de tokens acotado (no consumo ilimitado).

## 6. Notas CÓMO

Toca `orchestrator/c7.py` (la capa de terminación). **Máxima cautela (P4).** Un Bolt con revisión reforzada;
re-correr los evals de terminación (0 loops, dentro de cotas).

## 7. Precisiones tras code-review

- **Contrato de "crítica" C3→C2:** C3 ya emite `inconsistencias` (`list[str]` = nombres de campo señalados,
  en `VerificacionAdversarial`) + `confianza`. La crítica que se pasa a C2 = **los nombres de campo señalados**
  (saneados: una línea, acotados) — como feedback textual al re-prompt del extractor. No se inventa un contrato
  nuevo; se reusa lo que C3 ya produce. *(Corrección tras CÓMO: el contrato real es `list[str]`, no
  `list[EvidenciaOrigen]`; la evidencia rica vive en `SeñalEscalamiento`, no en la crítica.)*
- **Umbral de "baja fidelidad" (explícito):** re-extrae si `verif.confianza < UMBRAL_REEXTRACCION (0.7)` **y**
  hay al menos una inconsistencia sobre un campo. Configurable; no mágico.
- **`max_rondas=2`:** cambio en `Cotas` (default sigue 1; el loop reflexivo usa 2). No relaja P4 — es un cap
  mayor pero **duro**.
- **🐛 Detección de ciclos (bug preexistente, se corrige aparte en tarea de higiene):** hoy usa `id()` del
  objeto → nunca coincide tras `model_copy`. Se cambia a **hash de contenido** (`sha256` de
  `extraccion` serializada). U9 **depende** de esa corrección (si no, el loop no tendría corte por ciclo real).
- **🔒 Lock P2:** al re-extraer, **NUNCA se limpia `caso.dictamen`** ni se re-decide cobertura por el loop; el
  motor R1-R5 sigue siendo el único que dictamina, después del loop. Aserción fail-closed.
- **Semántica de ronda:** C2 original → C3; si baja fidelidad → C2 re-extrae con feedback → C3; si sigue mal →
  escala. Máximo una re-extracción. *(Corrección tras CÓMO: la re-extracción reflexiva ocurre **intra-ronda**
  —dentro de la misma iteración del while, acotada por el flag estructural `reextraido`—, no como una "ronda 2"
  separada del contador. El cap `max_rondas≥2` es el **switch de habilitación**; `reextraido` es el bound duro.)*
- **Orden:** construir **después de U3** (U3 vuelve `tipo_siniestro` product-aware; el loop no debe alterar la
  cobertura al re-extraer el tipo — el lock P2 lo garantiza).
