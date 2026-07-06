# ADR-002 · Monolito modular (un solo despliegue)

- **Estado**: Aceptado (2026-07-06)
- **Fase**: AJIT

## Contexto
Perito se descompuso en 10 componentes + front (C1-C11) y 5 unidades (U1-U5). Falta fijar el modelo de despliegue: **monolito modular** vs **microservicios**. Encuadre: greenfield, **construible por una persona** (PRD §2), portafolio, e **Infrastructure Design = SKIP** (nada se despliega, P7).

## Decisión
**Monolito modular: un único servicio desplegable** (`backend/`), donde cada unidad es un **módulo lógico** (`backend/app/{contracts,intake,agents,rules,fraud,orchestrator,hitl,rag,observability,synthetic,dashboard,api}/`). Regla de simplicidad del AJIT: si un monolito modular resuelve el problema, no se proponen microservicios.

## Consecuencias
**Positivas**: coherente con Units y C4; sin infra de orquestación de servicios (que además es SKIP); fronteras P2/P4/P1 preservadas a nivel de **módulo/import** (`agents/` no importa `rules/`; solo `hitl/` muta `Caso.estado`); un solo ciclo de build/test.

**Negativas / a vigilar**: no escala a equipos grandes ni a despliegue independiente por servicio — **irrelevante** para el encuadre (una persona, portafolio). Si algún día fuera producto real con equipo, se reevaluaría (PRD §13 "+90", donde dejaría de ser portafolio).

**Reversibilidad**: las fronteras de módulo ya son límites limpios; una futura extracción a servicios partiría de esos módulos. No es objetivo ahora.
