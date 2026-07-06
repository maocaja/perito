# Regla: Human-in-the-Loop (P1) — NO NEGOCIABLE

- El agente **NUNCA** cierra, aprueba ni niega un siniestro por sí solo.
- Todo estado terminal (`APROBADO` / `RECHAZADO`) requiere **aprobación humana registrada** (campo `aprobado_por`).
- El agente **propone y prepara**; el humano **decide y firma**.
- El fraude solo **sugiere revisión**, nunca bloquea ni decide.

**🚫 Prohibido:**
- Crear cualquier camino de código que alcance un estado terminal sin intervención humana.
- Presentar el sistema como "decisor".

Si una tarea te llevaría a violar esto, **detente y avísame** — no lo implementes.
Contexto completo: `specs/prd.md` (Principio P1, Segmento 6).
