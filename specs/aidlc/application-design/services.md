# Capa de Servicio — Perito (Application Design)

> Servicios = fronteras de orquestación y puntos de entrada (FastAPI). El **OrchestrationService** es el corazón agéntico (dueño de P4). Los servicios coordinan componentes; **no** contienen la lógica de dominio (que vive en los componentes).

---

## S1 · IntakeService
- **Responsabilidad**: punto de entrada de avisos FNOL; delega en `intake` (C1) y arranca el flujo.
- **Endpoints**: `POST /casos` (crear desde aviso).
- **Orquesta**: C1 → dispara `OrchestrationService.procesar`.
- **Persona**: Analista (indirecto) / sistema entrante.

## S2 · OrchestrationService  *(núcleo agéntico — dueño de P4)*
- **Responsabilidad**: ejecutar el grafo LangGraph bajo **terminación acotada**; secuenciar extractor→verifier→policy_lookup→(motor)→fraud; decidir escalamiento.
- **Patrón de orquestación**:
  1. `extractor.extraer` → `verifier.verificar`.
  2. Si verifier **no confirma** → `chequear_cotas` → continuar/escala.
  3. Si confirma → `policy_lookup.buscar_poliza`.
  4. Si **sin match** → `chequear_cotas` → candidatas/escala.
  5. Si match → **`invocar_cobertura` (único llamador de `coverage_rules.dictaminar`)** → `fraud_signals.analizar_fraude`.
  6. Ensambla Caso + dictamen + evidencia → entrega a HITL (`LISTO_PARA_APROBAR`) o escala (`REQUIERE_REVISION`).
- **Dueño de invariante**: **P4** (caps de rondas/tokens + detección de ciclos, fail-closed).
- **No hace**: no decide cobertura (llama al motor), no alcanza estados terminales (solo escala).

## S3 · HITLService  *(dueño de P1)*
- **Responsabilidad**: bandeja + máquina de estados; expone aprobar/corregir/rechazar.
- **Endpoints**: `GET /casos` (bandeja), `POST /casos/{id}/abrir|aprobar|corregir|rechazar`.
- **Orquesta**: C8 (hitl) + persistencia; registra correcciones en C9 (observability/evals).
- **Dueño de invariante**: **P1** — terminal solo con `aprobado_por`. Selector de rol **stub** (auth real = Won't).

## S4 · ObservabilityService  *(dueño de P3/P5 operativos)*
- **Responsabilidad**: instrumentación transversal, panel de métricas, evals por estrato, export PIA, test-gate de reglas.
- **Endpoints**: `GET /observabilidad/trazas/{caso}`, `GET /observabilidad/metricas`, `POST /evals/run`, `GET /pia/export/{caso}`.
- **Orquesta**: C9 (observability) sobre todos los nodos; C10 para trazabilidad de cláusula.
- **Persona**: Cumplimiento/Operador (Andrés).

## S5 · AdminService  *(dev/infra)*
- **Responsabilidad**: gestión de datos sintéticos (CT1), indexación de pólizas (C10), configuración de umbrales/cotas.
- **Endpoints**: `POST /admin/generar-dataset`, `POST /admin/indexar-polizas`, `PUT /admin/config` (umbrales fraude, presupuesto tokens).
- **Persona**: Admin/Dev.

---

## Patrones de orquestación (resumen)
- **Control-plane único**: el `OrchestrationService` es el único que dirige el flujo agéntico y el único que invoca el motor determinístico. Ningún servicio "atajo" llega a cobertura sin pasar por él.
- **Separación command/query**: escritura de estado terminal solo por `HITLService` con actor humano; lectura/observabilidad por `ObservabilityService`.
- **Fail-closed transversal**: ante error en cualquier servicio, denegar/detener (SECURITY-15, P4) — nunca avanzar el caso a ciegas.
- **Deny-by-default**: endpoints requieren rol (stub) server-side (SECURITY-08).

## C11 · dashboard (cliente UI — no es servicio de dominio)
- **Rol**: front demo-grade (FastAPI+templates/HTMX, ADR-001). **Consume** `HITLService` (S3) y `ObservabilityService` (S4) por REST; renderiza bandeja, detalle con evidencia enlazada y panel de cumplimiento (H-19/H-20/H-21).
- **No contiene lógica de dominio**: solo muestra estado y dispara acciones.
- 🚫 **Regla dura**: no consume `coverage_rules` (P2) ni escribe estado terminal (P1) — la decisión terminal la ejecuta `hitl` con `aprobado_por`. Con HTMX el front es server-rendered dentro del backend (mismo origen, authz server-side; ver ADR-001).

## Mapa Servicio → Componentes → Persona → Invariante dueño
| Servicio | Componentes | Persona | Invariante dueño |
|---|---|---|---|
| IntakeService | C1 | Sistema/Analista | P3 |
| **OrchestrationService** | C2,C3,C4,**C5 (invoca)**,C6,C7 | — | **P4** |
| **HITLService** | C8 | Analista | **P1** |
| ObservabilityService | C9,C10 | Cumplimiento | P3, P5 |
| AdminService | CT1,C10 | Admin/Dev | P7 (infra honesta) |
