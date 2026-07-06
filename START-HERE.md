# 🚀 START HERE — AI-DLC Inception (Estación 4)

> Estás en la rama `spec/aidlc-inception`. El framework AI-DLC ya está montado.
> Este archivo es solo tu guía de arranque — no lo lee el framework.

## 1. Confirma que estás en la rama correcta
```bash
git branch --show-current    # debe decir: spec/aidlc-inception
```

## 2. Abre Claude Code
```bash
claude
```

## 3. Pega este prompt de inicio (exacto)

Usando AI-DLC, construiremos Perito, un copiloto agéntico de admisión y triage de
siniestros de seguros (FNOL) que extrae datos de avisos caóticos, valida cobertura
contra la póliza con reglas determinísticas, señala fraude con evidencia y deja la
decisión a un humano (HITL). Es un proyecto de portafolio, greenfield.
Con base en el Product Requirements Document (PRD) @PRD.md.

## 4. Cómo trabajar con el framework
- Responde sus preguntas con precisión.
- Genera un artefacto → **léelo** → aprueba (NO des "sí a todo").
- En cada gate donde se detiene, `/clear` para arrancar contexto fresco (tip oficial AWS).
- Respeta los principios de Perito (P1 HITL, P2 cobertura por reglas, P4 terminación) —
  están en `AGENTS.md` y en el `CLAUDE.md` de esta rama.

## Las 6 fases (en orden)
00 Workspace Detection → 01 Requirements → 02 User Stories (Gherkin) →
03 Workflow Planning → 04 Application Design → 05 Units Generation
→ luego Arquitectura Just-in-Time (C4 + NFR + ADRs)

Los artefactos se generan en `aidlc-docs/inception/`.

## Cuando termines
Vuelve a una sesión conmigo (o desde `~/dev/hardcoreIA`) y pide "cosechar los
artefactos AI-DLC a specs/aidlc/ y mergear a main". El estado del proyecto está
en mi memoria (fnol-claims-agent.md).
