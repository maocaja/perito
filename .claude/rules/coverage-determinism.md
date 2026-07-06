# Regla: Cobertura determinística (P2) — NO NEGOCIABLE

- La decisión de cobertura la toma el **motor de reglas** (`backend/app/rules/`), **NUNCA el LLM**.
- El LLM solo **alimenta los campos** extraídos; las reglas **R1-R5** dictaminan.
- Cada dictamen **cita la regla aplicada y la cláusula** de la póliza.
- Salidas válidas: `CUBIERTO` · `CUBIERTO_PARCIAL` · `NO_CUBIERTO` · `REQUIERE_REVISION`.

**🚫 Prohibido:**
- Usar el LLM para decidir si algo está cubierto.
- Un dictamen de cobertura sin una regla asociada y su cláusula.

**⚠️ Cambios a `backend/app/rules/` requieren mi confirmación explícita** (afectan dictámenes a escala).
Contexto completo: `specs/prd.md` (Principio P2, Segmento 5).
