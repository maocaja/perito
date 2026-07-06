# Personas — Perito

> Fuente: PRD §3 (Personas), §9 (Roles). Idioma es-CO. Las personas activas del MVP tienen historias en `stories.md`; el Ajustador es persona de contexto (sin historias, exclusión explícita — honestidad P7).

---

## P-A · Diana — Analista de admisión/triage  *(USUARIO FINAL — sale en la demo)*
- **Rol MVP**: Analista (bandeja: aprobar / corregir / rechazar).
- **Objetivo (JTBD)**: que le quiten la transcripción mecánica **sin quitarle el juicio ni el control**.
- **Le importa**: casos estructurados con evidencia a la vista, decidir rápido y con respaldo, no sentirse reemplazada.
- **Frustraciones**: avisos caóticos (correos coloquiales, PDFs, fotos), transcribir a mano, cobertura propensa a error.
- **Éxito para ella**: abrir un caso limpio con dictamen + evidencia citada y **firmar en ~40s**; corregir un campo y que quede registrado.
- **Relación con invariantes**: es quien **firma** (P1); consume dictámenes citados (P3) y alertas de fraude explicables (P6).

## P-O · Andrés — Cumplimiento / Operador  *(veto de confianza)*
- **Rol MVP**: Operador/Cumplimiento (panel, configuración de umbrales, export).
- **Objetivo (JTBD)**: mostrar a auditoría/regulador **cómo y por qué** se admitió cada siniestro.
- **Le importa**: Habeas Data, PIA, trazabilidad, responsabilidad, sesgo; costo/caso y presupuesto de tokens.
- **Frustraciones**: cajas negras sin traza; riesgo regulatorio (Circular SIC 002/2024, Ley 1581).
- **Éxito para él**: tablero de métricas + trazas por nodo; ante auditoría, **exportar evidencia para el PIA**; versionar reglas sin romper accuracy.
- **Relación con invariantes**: dueño de la evidencia de P3 (trazabilidad), P5 (Habeas Data/PII), P4 (presupuesto/cotas).

## P-D · Admin / Dev  *(construye y opera el sistema)*
- **Rol MVP**: Admin/Dev (acceso total; construye infra, contratos, evals, orquestador).
- **Objetivo**: un sistema agéntico auditable, con contratos tipados, terminación acotada y evals versionados.
- **Le importa**: contratos Pydantic + validación, terminación acotada (caps propios sobre LangGraph), datos sintéticos válidos (fraude inyectado), red-team de inyección/sesgo, security baseline.
- **Éxito para él**: pipeline reproducible con seed, PBT sobre el motor determinístico, trazas instrumentadas, invariantes con aserción fail-closed.
- **Relación con invariantes**: implementa y **prueba** los caps de P4, el determinismo de P2, la minimización de PII de P5 y la resistencia a inyección (P1).

---

## P-X · Ajustador (río abajo)  *(PERSONA DE CONTEXTO — FUERA DEL MVP, cero historias)*
- **Rol**: recibe casos limpios río abajo. **No es comprador ni usuario del MVP.**
- **Por qué se documenta**: honestidad de alcance (P7). El PRD §3 lo marca como afectado no comprador, con **riesgo de sabotaje** ("no sentirse reemplazado").
- **Exclusión explícita**: el enrutamiento al ajustador es **Won't** (PRD §8). No genera historias en esta Inception.
- **Mitigación de diseño (heredada)**: encuadre "copiloto, no reemplazo" (Perito prepara, el humano decide).

---

## Mapa Persona ↔ Epics (detalle de historias en `stories.md`)
| Persona | Epics con historias |
|---|---|
| P-A Diana (Analista) | E1 Admisión/Extracción · E2 Grounding/Escalamiento · E3 Cobertura · E4 Fraude · E5 HITL |
| P-O Andrés (Cumplimiento) | E6 Observabilidad/Evals/Compliance |
| P-D Admin/Dev | E7 Infra & Contratos · E8 Seguridad/Red-team |
| P-X Ajustador | — (contexto, sin historias) |
