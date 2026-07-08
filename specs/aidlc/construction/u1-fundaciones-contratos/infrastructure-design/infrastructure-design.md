# Infrastructure Design — U1 · Fundaciones & Contratos

> ⚠️ **ESTO ES ENTORNO DE DEV LOCAL, NO INFRA DE PRODUCCIÓN.** El encuadre es portafolio: **nada se despliega** (RES-02, P7). La infra de producción (cloud/IAM/red/escalado) es **N/A** por decisión del AJIT y ADR-002. Diseñar una topología de producción sería el anti-patrón "demo como producción" (P7).

## Infra de producción — N/A (declarado)
| Aspecto | Estado | Rationale |
|---|---|---|
| Cloud provider / compute | **N/A** | No se despliega; corre local (P7). |
| Networking (LB/API-GW/VPC) | **N/A** | Mismo origen (HTMX, ADR-001); sin red de prod. |
| IAM / least-privilege cloud | **N/A** | Sin recursos cloud (los N/A de SECURITY-06/07 ya declarados en requirements §7.1). |
| Escalado / multi-AZ / HA | **N/A** | Portafolio, una persona; no se promete HA (coherente con el SPOF del AJIT). |
| Messaging / colas | **N/A** | Monolito; orquestación in-proc (LangGraph). |

## Entorno de dev local (el único "infra" real de U1)

### Mapa de servicios (dev)
| Componente lógico (de logical-components) | Servicio (dev, contenedor) | Config base |
|---|---|---|
| `contracts` / `synthetic` / `rag` (app) | Proceso Python local (FastAPI scaffold) | ejecutado en host o contenedor de app |
| Almacén de casos/estados + índice de pólizas (C-U1-5 `rag`) | **PostgreSQL 16 + extensión pgvector** (contenedor) | volumen persistente; **dimensión del vector = parámetro de config** (PATTERN-U1-03, no hardcode) |
| Observabilidad (ADR-003) | **Langfuse** (contenedor) — o floor JSON si tarda | trazas por nodo; fallback declarado |

### Seguridad local (SECURITY-01 aplicado a lo local)
- **En reposo**: el volumen de Postgres puede cifrarse a nivel de disco del host (opcional en dev; se declara, no se sobre-afirma — es dev local).
- **En tránsito**: conexiones app↔Postgres dentro de la red de docker-compose (host local); TLS estricto es **N/A en dev local** (mismo host), se activaría en un despliegue real (que es Won't).
- **Secretos**: sin secretos reales en dev; credenciales de Postgres vía variables de entorno del `.env` local (que ya está en `.gitignore` / deny de lectura). Sin hardcodear (SECURITY-09/12 "no default credentials" — usar credenciales de dev explícitas, no las por defecto).
- **PII**: datos **sintéticos** ⇒ sin PII real (RES-03); el patrón de redacción (PATTERN-U1-01) se ejercita igual.

### Config parametrizada (C-U1-6)
- `EMBEDDING_DIM` — dimensión del vector pgvector (se fija al confirmar el embedding en U2/U3; PATTERN-U1-03).
- `FAKER_LOCALE = es_CO` — locale del generador.
- Credenciales de Postgres, endpoint de Langfuse — vía `.env`.

## Nota de alcance
Este spec es el **contrato del entorno de dev**; su **construcción** (el `docker-compose.yml` real + Dockerfiles/scaffolding) es entregable de **Code Generation** (Actividad 5). Aquí se fija qué servicios y qué config, para que Code Gen no improvise el entorno.
