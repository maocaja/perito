# ADR-001 · Stack del Frontend

- **Estado**: Aceptado (2026-07-06)
- **Fase**: AJIT (transición Inception → Construction)
- **Decisión de**: arquitecto (usuario) + AI-DLC

## Contexto
Perito necesita una UI para hacer **visible** el flujo HITL y la auditabilidad (bandeja, detalle de caso con evidencia enlazada, panel de cumplimiento — H-19/H-20/H-21). El encuadre es **portafolio, una persona, demo-grade**: el peso de ingeniería vive en el backend agéntico (P1-P7); la UI es la **vitrina**, no la tesis. El tablero visual rico es **Should** (diferido); auth real es **Won't** (selector de rol stub, RNF-14). Riesgo #2 = scope creep / tool sprawl; P7 = no fingir producción.

Opciones evaluadas: **FastAPI + templates/HTMX** vs **React + Vite**.

## Decisión
**FastAPI + templates/HTMX.**

Trade-offs (solo las dimensiones que aplican a Perito):

| Dimensión | FastAPI+HTMX ✅ | React+Vite |
|---|---|---|
| Topología | 1 caja, server-rendered (`FE→API` interno) | 2 cajas, SPA (`Browser→API` directo) |
| CORS | No aplica (mismo origen) | Necesario (orígenes explícitos, nunca `*`) |
| Authz rol-stub (RNF-14/SECURITY-08) | Server-side por construcción | Obligatorio server-side + riesgo de filtrar a la SPA |
| Toolchains | 1 (Python) | 2 (Python + Node/Vite) |
| Velocidad a la demo | Mayor | Menor |
| Interactividad rica | Suficiente (tablero rico = Should) | Solo se justificaría si la UI fuera la tesis (no lo es) |

React sería sobre-ingeniería contra riesgo #2 y P7.

## Consecuencias
**Positivas**: un solo toolchain y despliegue; autorización server-side por construcción (el rol-stub nunca se valida en cliente); camino más corto a la demo; el borde de datos del diagrama C4 (Segmento 2) queda correcto tal cual (server-rendered).

**Negativas / a vigilar**: HTMX devuelve **fragmentos HTML**, no JSON; una futura UI rica (React) querría JSON → habría rework en la capa de vista.

**Reversibilidad (lock-in bajo — clave de esta decisión)**: se mantiene el **dominio devolviendo contratos Pydantic tipados** y HTMX como **capa de vista delgada** (templates que renderizan esos objetos). Por tanto una migración futura a React = **exponer wrappers JSON sobre los mismos servicios** (los contratos ya hacen round-trip a JSON — RNF-24/PBT-02) + construir la SPA, **sin tocar la lógica de dominio**. El borde de dominio no cambia; solo se añade un contenedor + endpoints JSON **si (y cuando)** el tablero rico salga de Should. → "HTMX ahora" es una decisión de **bajo costo de salida**.

**Impacto en C4**: el diagrama de contenedores (Segmento 2) refleja esta decisión (Frontend = vistas server-rendered dentro del backend, no contenedor separado). Si algún día se migra a React, se actualiza al borde `Browser→API` + CORS.
