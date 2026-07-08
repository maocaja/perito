# Metodología — cómo se construyó Perito con AI-DLC

Nota honesta sobre el proceso (P7 — encuadre de portafolio). Este documento aclara
qué hizo el framework AI-DLC y qué se ejecutó de otra forma, para que los artefactos
cosechados aquí no impliquen que el runner del framework ejecutó todo end-to-end.

## AI-DLC se usó para DEFINIR

El framework AWS Labs **AI-DLC** se usó en su fase de **Inception** y como **metodología**:
- **Requisitos, user stories (Gherkin), unidades de trabajo (U1-U5), diseño de aplicación** — el "qué" y el "porqué". Esos artefactos están en `specs/aidlc/` (requirements, user-stories, units, application-design).
- **Los gates de diseño por unidad** (Functional Design, NFR Design) — el "cómo" a nivel de arquitectura/estrategia, no de código línea a línea. Están en `specs/aidlc/construction/`.

Esto es fiel a cómo funciona el spec-driven development (Kiro, GitHub Spec Kit, AI-DLC):
el spec/diseño define la estrategia; el código se escribe en la fase de implementación.

## La EJECUCIÓN de Construction se hizo con verificación real (no con el runner)

El **código** (U1-U5, `backend/`) se implementó con Claude Code bajo un modelo de
**"la IA propone, el humano decide y valida"** (el propio principio de AI-DLC), con
**verificación por ejecución** en cada paso:

- Cada cambio: suite completa `pytest backend/tests/` (nunca un subconjunto), `git status`
  limpio, y diff-review del scope antes de cada commit.
- Invariantes **P1-P7** verificados con aserciones fail-closed reales, no con dashboards.
- Ningún commit en rojo; ningún "✅ completado" sin ejecutar.

Este rigor fue necesario: al ejecutar el workflow, el runner del framework tendió a
**narrar "hecho/verde/verificado" sin verificar** — se detectaron y corrigieron regresiones
silenciosas (contratos de fundación debilitados, módulos sin versionar, redactores
duplicados) que solo la verificación por ejecución cazó. Por eso la barrera real fue la
revisión, no el auto-reporte del runner.

## Integración LLM validada contra la API real (de-risk)

Los agentes (C2 extractor Haiku, C3 verificador Sonnet, C6 fraude) se validaron **contra
la API real de Anthropic** antes de cablear el orquestador — un enfoque de-risk componente
por componente. Esto cazó bugs de integración que los mocks escondían (schemas de
structured-output con `minimum`/`maximum` no soportados, y desalineación de nombres de
campo entre extractor y motor). El pipeline end-to-end real —intake → extracción →
verificación → grounding → motor de cobertura → fraude → `LISTO_PARA_APROBAR`— corre con
caps de terminación (P4) y trazas de costo/tokens reales, dejando la decisión terminal
al humano (P1).

## Qué NO se cosechó a `main` — y dónde vive

`main` es el **producto** (código + specs). El **proceso** AI-DLC vive en otro lado:

- **Rama `spec/aidlc-inception`** (tag **`aidlc-process`**): contiene el **runtime del
  framework** (`.aidlc/`), el `CLAUDE.md` que activa AI-DLC, y el **historial granular**
  (los ~34 commits paso a paso de la construcción, con los fixes y el teatro que se cazó).
  En `main` ese trabajo llegó como **una sola cosecha limpia**, no como los 34 commits.

- ⚠️ **Si necesitas VER o ACTUALIZAR el proceso AI-DLC** (los `.aidlc/` rules, el estado del
  framework, la historia detallada): **ve a la rama `spec/aidlc-inception` / tag
  `aidlc-process`. NO lo recrees en `main`** — `main` mantiene su `CLAUDE.md` agent-ready y
  no debe cargar el andamiaje del framework (es proceso, no producto).

- El **producto** (todo `backend/` + `specs/aidlc/`) sí está 100% en `main` — el código es
  idéntico al de la rama.

## Lecciones

1. Con un runner LLM autónomo, **no confíes en su auto-reporte**: verifica por ejecución
   (suite completa + `git status` + snippets de invariantes).
2. **Toca fundación (`contracts/`) → corre la suite completa**, nunca un glob que esconda
   regresiones.
3. **Valida la integración LLM contra la API real temprano**: los mocks esconden bugs de
   shape de API.
