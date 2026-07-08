# Unit de Evolución — Persistencia real con Postgres (C1)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Alcance decidido:** C1 (casos/pólizas en Postgres). **C2 (pgvector RAG) DIFERIDO** — necesita modelo de
> embeddings (dep/costo) y el motor no lo usa (cita cláusulas estructuradas de la `Poliza`).

## 1. Intent (el goal)

Reemplazar los dos stores **in-memory** (`CasoRepository`, `_POLIZA_STORE`) por **Postgres real**, detrás de
la **misma interfaz**, para que casos y pólizas **persistan entre reinicios**. Gated por config: sin
configurar → sigue in-memory (tests/demo sin fricción); con Postgres → persistencia real.

## 2. Qué cierra (trazabilidad)

- **RNF-15** (cifrado en tránsito TLS + en reposo para el almacén de casos/pólizas; SECURITY-01).
- Parte de M8 (persistencia HITL) y M10 (almacén de pólizas). **RF-29 (pgvector RAG) queda para C2 (diferido).**

## 3. Criterios de completitud (verificables)

1. **Gating por config:** `settings.persistence` ∈ {`"memory"` (default), `"postgres"`}. Con `"memory"` → impl
   actual (cero cambios de comportamiento). Con `"postgres"` + `database_url` → impl Postgres.
2. **Misma interfaz (cero cambios a callers):** `get_caso_repository()` sigue devolviendo un objeto con
   `save/get/list/clear`; `call_c4_policy_lookup()` sigue funcionando igual. Dashboard, ingesta, seeder, motor
   **no cambian**.
3. **Persistencia real:** con Postgres, un caso guardado **sobrevive un reinicio** del proceso (verificable con
   un smoke: guardar → reconectar → `get()` lo encuentra).
4. **Tests siguen in-memory:** la suite corre con `persistence="memory"` (default) — **sin Postgres, sin
   fricción, 163 verde**. Un test extra verifica que la selección de backend responde a la config.
5. **RNF-15:** la conexión exige **TLS** (`sslmode=require` en el `database_url`); el cifrado en reposo lo
   provee el proveedor (Neon lo trae por defecto). Documentado, no hardcodeado.
6. **Fail-closed al arranque:** si `persistence="postgres"` y la DB no conecta → **error ruidoso al inicio**
   (a diferencia de la observabilidad fail-open: perder persistencia SÍ es un fallo de negocio). NO cae silencioso a memoria.

## 4. Invariantes / NFR que DEBE respetar

- **Persistencia pasiva (P1):** el store **NO muta `estado`** — persiste la instancia `Caso` que produjo HITL
  (`model_validate`). Igual que hoy.
- **No lógica de dominio nueva:** el repo Postgres solo serializa/deserializa; el motor/orquestador/HITL no cambian.
- **P2/frontera:** `policy/lookup.py` conserva su lógica determinística (exact + difflib); solo cambia **de dónde
  lee** las pólizas (memoria vs Postgres). Cero LLM.
- **Fail-closed** (persistencia) vs fail-open (observabilidad): distinción consciente.

## 5. Diseño breve (el CÓMO a alto nivel — se detalla en el Bolt)

- **`app/persistence/db.py`** (NUEVO): engine SQLAlchemy (lazy, gated), `init_db()` (crea tablas `create_all` al
  arranque; sin alembic para el demo), sesión. `database_url` desde `settings` (con `sslmode=require`).
- **Tablas (JSONB):** `casos(id PK, estado, timestamp_actualizacion, data JSONB)` y `polizas(numero PK, data JSONB)`.
  El objeto Pydantic va en `data` serializado con **`model_dump_json()`** y reconstruido con
  **`Modelo.model_validate_json(...)`** — **NO** `model_dump()`/`model_validate()` (fallan con datetime-tz /
  Decimal / enums). *(BLOCKER #1 del review.)* `model_validate_json` **re-ejecuta los validators** → reconstruir un
  estado terminal exige `aprobado_por` (**P1 intacto: no se revive un APROBADO sin firma desde la DB**).
- **`CasoRepository` → interfaz (Protocol/ABC) + 2 impls:** `save/get/list/clear`. `InMemoryCasoRepository`
  (la actual, renombrada) y `PostgresCasoRepository`. **`get_caso_repository()` = factory cacheada** que devuelve
  `PostgresCasoRepository(engine)` si `settings.persistence == "postgres"`, si no la in-memory. **Callers intactos**
  (verificado: `dashboard/c11.py`, `api/ingest.py`, `demo/seed.py`).
- **`PostgresCasoRepository.list()` ordena EN SQL** (`ORDER BY timestamp_actualizacion DESC`, `WHERE estado=` si
  se filtra) — no en Python. *(MEDIUM #4.)*
- **Pólizas (mismo patrón):** fuente `PolizaSource` con 2 impls (memoria = `_POLIZA_STORE` + `set_poliza_store`
  para tests; Postgres = query sobre `polizas`). `call_c4_policy_lookup`/`_lookup_exact`/`_lookup_candidates` leen
  de la fuente activa (según `settings.persistence`); la **lógica determinística (exact + difflib) NO cambia** —
  solo el origen de los datos. *(BLOCKER #3.)*
- **`app/config.py`:** añadir `persistence: str = "memory"`. **TLS (RNF-15):** el `database_url` debe incluir
  `sslmode=require` (responsabilidad del usuario; `init_db()` lo advierte si falta). *(MINOR #8.)*
- **`pyproject`:** declarar `sqlalchemy>=2.0` explícito (hoy transitivo vía pgvector). *(MINOR #7.)*
- **Deps:** `psycopg[binary]` + `sqlalchemy` (ya disponibles). Smoke con **Neon** (Postgres serverless, TLS +
  cifrado en reposo por defecto; sin Docker — mismo criterio que Langfuse Cloud, apropiado para demo P7).

## 6. Fuera de alcance

- **C2 pgvector RAG + embeddings** (diferido / feature aparte). **Alembic/migraciones** (create_all basta para demo).
- Postgres para las trazas de Langfuse (Langfuse trae el suyo, es otra cosa).

## 7. Cómo se validará el Bolt (gate de salida)

- **De-risk primero:** smoke mínimo contra un Postgres real (Neon) — conectar + crear tablas + round-trip de un
  caso — antes de cablear a fondo. Confirma el `database_url`/TLS.
- **Tests (ejecutan, in-memory):** default `persistence="memory"` → suite 163 verde sin DB · un test que, con
  `persistence="postgres"` monkeypatcheado + un fake/session mock, verifica que `get_caso_repository()` devuelve
  la impl Postgres (sin requerir DB real en CI).
- **Smoke de persistencia real (manual, con Neon):** guardar un caso → recrear el repo/engine → `get()` lo trae.
- **Verificación por ejecución** + `code-reviewer` (foco: interfaz intacta, passive, fail-closed, TLS) → **PR**.

## 8. Decisiones (resueltas con el usuario)

- **D1 — Serialización:** ✅ **JSONB** (objeto Pydantic completo en `data`; filtrado por columnas planas). No ORM mapeado a mano.
- **D2 — DB caída al arranque:** ✅ **fail-closed** (error ruidoso), no fallback silencioso a memoria — persistencia es requisito.
- **D3 — Proveedor del smoke:** ✅ **Neon** (serverless, sin Docker, TLS + cifrado en reposo por defecto).
- **D4 — `sqlalchemy`:** ✅ declararlo explícito en `pyproject`.

## 9. Veredicto del review (code-reviewer, incorporado)

Alineado con RNF-15/M8/M10; diferir C2 correcto; interfaz intacta (callers verificados: `c11.py`, `ingest.py`,
`seed.py`); `settings` con `extra="forbid"` compatible; `sqlalchemy` disponible. **Ajustes incorporados:**
1. 🔴 **Serialización** → `model_dump_json()`/`model_validate_json()` (no `model_dump`/`model_validate`) — §5.
2. 🔴 **Factory de casos** → interfaz Protocol/ABC + `get_caso_repository()` elige impl por config — §5.
3. 🔴 **Fuente de pólizas** → `PolizaSource` con 2 impls, lógica determinística intacta — §5.
4. 🟡 **`list()` ordena EN SQL** — §5. 🟡 **Tests** con fixture que fuerza `persistence="memory"` — §7.
5. 🟢 **P1**: `model_validate_json` re-ejecuta validators (no revive terminal sin firma) — documentado §5.
6. 🟢 **sqlalchemy** explícito en pyproject · **TLS** `sslmode=require` responsabilidad del usuario (§5).
