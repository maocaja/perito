# User Stories Assessment — Perito

## Request Analysis
- **Original Request**: Construir Perito (copiloto agéntico FNOL, greenfield), alcance Must M1-M10.
- **User Impact**: **Direct** — analista (usuario final, sale en la demo), operador/cumplimiento, admin/dev.
- **Complexity Level**: **Complex** — sistema agéntico multi-módulo, multi-persona, lógica de negocio con múltiples escenarios y reglas.
- **Stakeholders**: Analista de admisión/triage · Cumplimiento/Legal · Líder de Siniestros (contexto) · Admin/Dev.

## Assessment Criteria Met
- [x] **High Priority — New User Features**: funcionalidad nueva con la que el usuario interactúa (bandeja HITL, aprobar/corregir/rechazar).
- [x] **High Priority — Multi-Persona Systems**: 3 roles activos en el MVP (Analista, Operador/Cumplimiento, Admin/Dev).
- [x] **High Priority — Complex Business Logic**: R1-R5, terminación acotada, fraude, escalamiento — múltiples escenarios/reglas.
- [x] **Benefits**: los criterios de aceptación en **Gherkin** se reutilizan como escenarios de eval por estrato (happy · campos-faltantes · póliza-no-encontrada · cobertura-negativa · fraude · documento-sucio) → testabilidad directa.

## Decision
**Execute User Stories**: **Yes** (ya confirmado por el usuario en Q4=A, con Gherkin).
**Reasoning**: sistema multi-persona con lógica compleja y necesidad de UAT; los Given/When/Then son la especificación testable que alimenta los evals. Overhead ampliamente compensado.

## Expected Outcomes
- Historias por rol con criterios de aceptación Gherkin trazables a RF/RNF y a principios P1-P7.
- Mapa historia ↔ estrato de eval (reutilización directa como escenarios de test).
- Alineación de los invariantes no negociables (P1/P2/P4) como escenarios explícitos (incl. caminos de escalamiento y fail-closed).
