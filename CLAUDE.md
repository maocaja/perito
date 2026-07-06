# Perito — CLAUDE.md (rama spec/aidlc-inception)

> ⚠️ **Esta versión de CLAUDE.md solo existe en la rama `spec/aidlc-inception`.**
> En `main` vive el CLAUDE.md agent-ready normal. Aquí activamos el framework AI-DLC
> para la fase Inception (Estación 4). Al terminar, cosechamos los artefactos a
> `specs/aidlc/` y NO mergeamos este archivo a main.

## Workflow activo: AI-DLC (AWS Labs v0.1.8)

**PRIORITY: sigue el workflow de AI-DLC.** Lee y aplica:
`.aidlc/aws-aidlc-rules/core-workflow.md`

Los detalles de cada fase se resuelven desde `.aidlc-rule-details/`
(convención Claude Code). Los artefactos generados van SIEMPRE en `aidlc-docs/`.

## Contexto de dominio del producto

El "qué" y el "porqué" de Perito están en:
- `PRD.md` (copia del PRD de la Estación 2 — el input de AI-DLC)
- `AGENTS.md` (contexto de negocio, arquitectura y **principios no negociables P1-P7**)

**Importante para la Inception:** los principios de Perito deben respetarse al
generar requisitos, historias, diseño y unidades:
- **P1 HITL** — el agente nunca decide un siniestro solo.
- **P2** — la cobertura la decide un motor de reglas determinístico, no el LLM.
- **P4** — terminación acotada (límites de rondas/tokens).
- Encuadre **portafolio honesto** (no producto de mercado).

## Nota
Proyecto **greenfield** (sin código de app todavía) → AI-DLC salta reverse-engineering
y arranca en Requirements Analysis tras Workspace Detection.
