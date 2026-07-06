---
name: review-pr
description: Revisa un PR (o el diff contra main) y reporta riesgos, regresiones, gaps de test y violaciones de los invariantes de Perito, por severidad. No modifica archivos.
---

# review-pr — Revisión de PR para Perito

Adaptación del skill del codelab (Estación 3) al dominio de Perito.

Revisa el PR o diff indicado por el usuario.

1. **Resume** los cambios clave.
2. **Invariantes primero** (lo más importante en Perito): busca violaciones de
   P1 (auto-decisión sin HITL), P2 (LLM decide cobertura), P4 (loop sin cotas),
   P5 (PII al LLM), P3 (dictamen/alerta sin evidencia), P6 (fraude sin explicación).
3. **Bugs, regresiones y riesgos de seguridad** (inyección de prompt, secretos).
4. **Gaps de testing**: estratos sin cubrir (happy, poliza-no-encontrada,
   cobertura-negativa, fraude, SOAT, documento-sucio).
5. Entrega hallazgos **por severidad** (CRITICAL/HIGH/MEDIUM/LOW) con `archivo:línea`
   y el principio violado cuando aplique.
6. **No modifiques archivos** durante la revisión.
