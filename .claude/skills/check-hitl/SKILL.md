---
name: check-hitl
description: Audita el código de Perito para verificar el invariante Human-in-the-Loop (P1). Úsalo antes de un commit/PR o cuando toques el flujo de estados o el orquestador. Verifica que ningún camino alcanza una decisión terminal sin aprobación humana.
---

# check-hitl — Auditoría del invariante Human-in-the-Loop (P1)

Skill de dominio de Perito. Verifica que **el agente nunca decide solo** — el principio no negociable P1 (ver `.claude/rules/hitl.md` y `specs/prd.md`).

## Cuándo usarla
- Antes de commitear/abrir un PR que toque `orchestrator/`, `agents/`, `api/` o el modelo de estados.
- Cuando agregues un estado terminal o un camino de decisión nuevo.

## Qué verificar (procedimiento)

1. **Estados terminales protegidos.** Busca dónde se asigna `APROBADO`, `RECHAZADO` o `CERRADO_SIN_ACCION`. Cada transición a un terminal DEBE:
   - venir de una acción humana explícita, y
   - registrar `aprobado_por` (o el actor humano equivalente).
   ```
   grep -rn "APROBADO\|RECHAZADO\|CERRADO_SIN_ACCION" backend/app
   ```

2. **Ningún auto-cierre.** Verifica que no exista lógica que mueva un caso a un terminal desde un nodo del agente sin pasar por el HITL. Cualquier `estado = APROBADO` dentro de `agents/` u `orchestrator/` sin intervención humana es una **violación crítica**.

3. **El fraude no bloquea.** El `fraud_signals` solo debe **recomendar** revisión, nunca cambiar el estado a rechazado/cerrado por sí mismo.

4. **La cobertura no decide el cierre.** Un dictamen `NO_CUBIERTO` NO cierra el siniestro solo — pasa a revisión humana.

## Salida esperada
- Lista de cada transición a estado terminal, con `archivo:línea`.
- Para cada una: ✅ tiene aprobación humana registrada, o 🔴 VIOLACIÓN P1 (auto-decisión).
- Si hay ≥1 violación: recomendar bloquear el merge.

## Regla
No edites código en esta auditoría — solo reporta. Si encuentras una violación, descríbela y sugiere la corrección (insertar el paso HITL), pero espera confirmación.
