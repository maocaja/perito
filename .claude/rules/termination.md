# Regla: Terminación acotada (P4) — NO NEGOCIABLE

- Todo flujo del orquestador tiene **límites duros**: máximo de rondas + presupuesto de tokens + detección de ciclos.
- El orquestador (`backend/app/orchestrator/`) es **dueño de la política de terminación y escalamiento**.
- Ante dato faltante/ambiguo o póliza sin match: **escalar a humano** (`REQUIERE_REVISION`) — nunca inventar ni loopear.
- LangGraph es propenso a loops (33.8%); los caps los ponemos **nosotros**, por encima del framework.

**🚫 Prohibido:**
- Loops sin límite de rondas/tokens.
- Relajar o quitar los caps de terminación.
- Rellenar un campo a la fuerza para "cerrar" el caso.

**⚠️ Cambios a la capa de terminación requieren mi confirmación explícita.**
Contexto completo: `specs/prd.md` (Principio P4, Segmentos 5 y 7).
