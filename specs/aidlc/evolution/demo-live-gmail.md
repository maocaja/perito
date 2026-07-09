# Unit de Evolución — Demo en vivo: Gmail → bandeja viva → HITL (H)

> **Tipo:** spec a nivel de cambio (brownfield, NO re-Inception) · **Fase AI-DLC:** Construction (Bolt) ·
> **Estado:** 🟡 QUÉ propuesto — pendiente de validación humana + code-reviewer antes del CÓMO.
> **Construye sobre:** Unit G (`full-demo-showcase.md`) — reusa el mismo cableado del pipeline y los 4 escenarios.

## 1. Intent

Convertir la demo de "un comando en consola" (Unit G) en la **demo de un sistema agéntico en vivo**: correos FNOL
**llegan a un Gmail**, Perito los **procesa solo** (los agentes corren), y en el **dashboard** el operador ve la
**bandeja llenarse en tiempo real**, entra a un caso, ve **qué hizo cada agente**, y **cierra con su firma (HITL)**.
Es el arco que los expertos comerciales marcaron: *el stream es el gancho; la venta es un caso end-to-end + el
operador vaciando la cola; el aha es un resultado (triado en segundos, cláusula citada, humano firma), no "miren, agentes".*

## 2. Qué cierra

- El gap de **"ver el trabajo en el front"** (hoy el front es demo-grade y estático, ADR-001). Hace **visible en vivo**
  el ciclo agéntico completo + el **HITL como manejador de objeciones** ("¿decide solo?" → el caso se **detiene**
  en LISTO_PARA_APROBAR esperando la firma).

## 3. Criterios de completitud (verificables)

1. **Generador (`make demo-mail`)** — envía FNOL **sintéticos** (rotando los 4 escenarios de Unit G) al Gmail demo
   por **SMTP**, ~**5/min por un tiempo acotado** (`MAIL_TOTAL`, ej. 15 → ~3 min), y termina. **On-demand** (control
   de costo). Cada correo lleva un **marcador de escenario en el asunto** (ej. `[DEMO:fraude]`) que el modo
   `deterministic` usa para mapear al preset (review 🟡 #6).
2. **Poller (`DEMO_LIVE`, 3 modos)** — la app corre un **hilo de fondo** que cada ~Ns lee los correos **no leídos**
   (IMAP), arma el aviso, lo procesa, `save + replay`, y **marca el correo como leído**. Tres modos (control de costo):
   - **`off`** (default) — poller apagado, app normal, **cero costo, sin key**.
   - **`deterministic`** — reconoce el escenario del correo (asunto/marcador) y arma el caso con **presets** (sin LLM)
     → **ensayo del front GRATIS** (llegadas, detalle, HITL) sin `ANTHROPIC_API_KEY`.
   - **`real`** — **pipeline real** (`intake → orquestar_fnol`, agentes Claude) → el show en vivo (requiere key).
   **Idempotencia / fail-closed (P4, review 🟠 #1):** si procesar un correo lanza excepción → se registra el error +
   el caso queda **REQUIERE_REVISION** (escala, no inventa) y el correo se marca **leído SIEMPRE** → nunca se
   reprocesa, nunca loopea. Un correo malo no bloquea el buzón.
3. **Bandeja viva** — `/casos` **auto-refresca** (HTMX `hx-trigger="every 3s"`); los casos **aparecen a medida que
   se procesan**, con su estado (LISTO_PARA_APROBAR / REQUIERE_REVISION) y chip de fraude.
4. **Detalle "qué hizo cada agente"** — el detalle (`/casos/{id}`) muestra la **traza por nodo** (C2 extractor →
   C3 verifier → C4 → C5 motor+cláusula → C6 fraude) con resultado + tokens (del ReplayStore/Tracer) — la narración
   de la consola, pero en la UI. Aviso **redactado** (P5, ya existe).
5. **HITL finale** — el operador **Aprueba / Corrige / Rechaza** desde el detalle (ya existe); **solo el humano llega
   a terminal** con `aprobado_por` (P1). El caso se **detiene** esperando la firma — nunca se auto-cierra.
6. **P5 / P7 / costo** — correos **sintéticos** (sin PII real); el poller no loguea cuerpos crudos; el generador es
   on-demand y el poller gated; `docs/DEMO.md` documenta el costo (~USD 3.6/h si corre continuo) y **cómo pararlo**.
7. **Sin deps nuevas** — `imaplib` / `smtplib` / `email` (stdlib), polling de HTMX, hilo de `threading` (stdlib).

## 4. Invariantes / NFR

- **P1 (HITL):** el poller **prepara** (deja el caso en LISTO_PARA_APROBAR / REQUIERE_REVISION); **jamás** aprueba/
  rechaza. Solo el operador, desde el detalle, alcanza terminal (firma). El poller NUNCA firma.
- **P2:** la cobertura la decide el motor R1-R5; el poller no toca dictámenes.
- **P4:** el poller **no loopea sin límite** — procesa los no-leídos que haya y **duerme** N segundos; respeta las
  Cotas del orquestador por caso. El generador manda un total **acotado** y termina.
- **P5:** correos sintéticos + el detalle redacta el aviso (ya). El parser no persiste ni loguea el cuerpo crudo.
- **P7 (honestidad + costo):** buzón de demo dedicado con contenido sintético (no se finge tráfico real de clientes);
  el costo se declara y el "encendido" es explícito. **Riesgo #2 blindado:** default `off`; ensayo en `deterministic`
  (gratis, sin key); `real` solo para el show; el generador manda un **total acotado** (`MAIL_TOTAL`, ~15) y se para
  solo; el poller **duerme** entre ciclos (no hay loop caliente). Costo real por demo ≈ USD 0.20-0.40.
- **Passive:** el poller/mailbox viven en `api/`/`ingest/` (capa activa), NO en `dashboard/` (sigue passive).

## 5. Diseño breve (el CÓMO — se detalla en el Bolt)

- **`backend/app/ingest/mailbox.py`** (nuevo) — IMAP: leer no-leídos → **el aviso = cuerpo (+ asunto)**, redactados
  con `redact_pii_spans_es_co`; **el remitente (email = PII) se OMITE del aviso** (review 🟠 #2, el redactor actual no
  cubre headers de correo). Marcar leído. SMTP: enviar (lo usa el generador). Solo stdlib.
- **`backend/demo_mail.py`** (nuevo, `make demo-mail`) — genera y envía los 4 escenarios rotando (reusa los avisos de
  `demo_run.py` / `scenarios`), ~5/min, total acotado. On-demand.
- **Poller** — `app/ingest/poller.py`, arrancado desde el **lifespan de FastAPI** (no `@app.on_event`, deprecado),
  **gated por `settings.demo_live`** (si `off` → NO arranca el hilo). Hilo daemon con loop `leer no-leídos → por cada
  uno: procesar → repo.save + replay.save → marcar leído → sleep(N)`. **Branch por modo:** `real` → `intake →
  orquestar_fnol` (reusa `demo_run._correr_escenario`); `deterministic` → mapea el marcador del asunto →
  `construir_caso_preset` + `sembrar_traza_demo` (sin LLM; default `feliz` si no hay marcador).
  - **Concurrencia (review 🟠 #3):** el poller es un hilo en el **mismo proceso** que el web → comparte el
    `CasoRepository` (in-memory o Postgres) sin cruce de procesos; `save` se protege con un `threading.Lock` (demo-grade).
  - **Fail-safe de arranque (review 🟡 #4):** si `demo_live != off` pero faltan `DEMO_GMAIL_*` → loguea un warning y
    **NO arranca** el poller (la app levanta normal). Nunca tumba el arranque por config de demo.
- **`dashboard/templates/bandeja.html`** — `hx-trigger="every 3s"` en el contenedor de la tabla (o `load` + polling);
  auto-refresh sin recargar la página.
- **`dashboard/templates/detalle.html`** — sección **"Traza de agentes"** que itera el replay del caso (nodo →
  resultado → tokens). Reusa `get_replay_store().load(caso_id)`.
- **`app/config.py` + `env.example`** — nuevos campos: `demo_live` (str: `off`|`deterministic`|`real`, default `off`),
  `demo_gmail_address`, `demo_gmail_app_password` (SECRETO), `imap_host` (default `imap.gmail.com`), `smtp_host`
  (`smtp.gmail.com`), `poll_interval_s` (default 5), `mail_total` (default 15). Públicos en `env.example`; el secreto
  lo pone el usuario. `make test` fuerza `DEMO_LIVE=off` (hermético — el poller nunca arranca en tests).
- **Reuso:** `intake_crear_caso`, `orquestar_fnol`, `get_caso_repository`, `get_replay_store`, `scenarios`, el
  detalle/bandeja existentes, la redacción P5. Ningún módulo de dominio nuevo.

## 6. Fuera de alcance (corte fino)

- OAuth / Gmail API (usamos **IMAP + app-password**). Adjuntos / OCR de imágenes (el aviso es texto). Múltiples
  buzones o etiquetas. Correos de **clientes reales** (P5/P7). WebSockets / animaciones / SPA (ADR-001 → HTMX polling).
  Multi-rol / auth real. Todo eso queda para polish posterior.

## 7. Cómo se validará el Bolt

- **`make demo-mail`** → los correos **llegan al Gmail demo** (verificable en la bandeja de Gmail).
- **`make run` con `DEMO_LIVE=1`** (key real) → en `/casos` los casos **aparecen en vivo**; el detalle muestra la
  **traza de agentes**; el operador **cierra con HITL**. Se graba/pega como evidencia (como los smokes B1/C1).
- **Tests automatizables (`make test`, con IMAP mockeado — review 🟡 #5):** parser de correo (`email` → aviso, remitente
  omitido), generador (marca el asunto + arma los 4 escenarios), **poller con mock IMAP** (procesa, marca leído, un
  correo que falla → REQUIERE_REVISION + marcado leído), poller **gated** (`demo_live=off` → no arranca), estructural
  (mailbox/poller NO importan `dashboard`). Fixture `backend/tests/mocks/imap_mock.py`. `make test` fuerza `DEMO_LIVE=off`.
- **Smokes manuales (evidencia):** `make demo-mail` → correos en el Gmail demo · `make run DEMO_LIVE=deterministic` →
  `/casos` auto-refresca (gratis) · detalle muestra la traza de agentes · el operador cierra con HITL.
- **`code-reviewer`** (P1 el poller nunca firma, P5 sintético+redacción, passive, costo/flag) → **PR**.

## 8. Decisiones (resueltas con el usuario)

- **D1 — Fuente de correos:** ✅ **Gmail demo real + generador sintético** (IMAP + **app-password**, no OAuth).
  Plomería real, contenido controlado (sin PII, repetible).
- **D2 — Front:** ✅ **evolucionar el dashboard HTMX** (polling `every 3s`), respetando ADR-001. **Sin SPA.**
- **D3 — Alcance:** ✅ **corte fino vertical** (correos → agentes → bandeja viva → detalle con traza → HITL); luego polish.
- **D4 — Poller + costo:** ✅ **hilo de fondo, gated por `DEMO_LIVE` (off/deterministic/real)**; generador **on-demand**
  con **tope** (`MAIL_TOTAL`). Ensayo del front en `deterministic` (gratis, sin key); `real` solo para el show. Costo
  real por demo ≈ USD 0.20-0.40 (riesgo #2 blindado).
- **D5 — Deps:** ✅ **cero nuevas** (imaplib/smtplib/email/threading stdlib + HTMX polling).

## 9. Lo que pone el usuario (setup, una vez)

- Un **Gmail dedicado/desechable** (NO el personal): la app-password de Gmail da **acceso total** a la cuenta (no es
  scopeable), por eso debe ser un buzón que puedas quemar y revocar sin consecuencias. Activar **2FA** → crear **app-password**.
- En `.env` (secretos): `DEMO_GMAIL_ADDRESS=...` y `DEMO_GMAIL_APP_PASSWORD=...`. Lo público (hosts, `POLL_INTERVAL_S`,
  `MAIL_TOTAL`, `DEMO_LIVE=off`) va en `env.example`. El `.env` ya está gitignorado (`.env` + `.env.*`). ✅

## 10. Panel comercial incorporado (research 2026-07-09)

- 🎤 **Sales Engineer (show-don't-tell):** el HITL detenido ES el manejo de objeción → §3.5. · 🖥️ **Demo interactiva
  (Navattic/Karumi):** 1-6 pasos, 2-4 aha, no ahogar (5/min es gancho, foco en 1 caso) → §1, §7. · 📖 **Founder
  (Tell-Show-Tell):** aha = resultado, no feature → el arco cierra con el operador vaciando la cola → §1. ·
  🏢 **VP Siniestros (compradora):** compra trazabilidad + HITL auditable → §3.4-3.5.
- Fuentes: Navattic *Interactive demos 2026* · Reprise *Software demo best practices* · clickinsights *Tell-Show-Tell* ·
  Perspective AI *AI tools for sales engineers 2026* · Karumi/Saleo *agentic demos* · Storylane *demo presentation 2026*.

## 11. Ajustes del review incorporados (code-reviewer)

Validación a dos ojos previa al Bolt. Hallazgos plegados:

- 🟠 **#1 Idempotencia (P4):** correo que falla → REQUIERE_REVISION + **marcar leído SIEMPRE** (no loop) → §3.2.
- 🟠 **#2 PII del remitente (P5):** el remitente (email) se **omite** del aviso; cuerpo/asunto redactados → §5 mailbox.
- 🟠 **#3 Arranque + concurrencia:** poller en **lifespan** de FastAPI (no `@app.on_event`); **mismo proceso** →
  comparte el `CasoRepository` sin cruce; `save` con `threading.Lock` → §5 poller.
- 🟡 **#4 Fail-safe de arranque:** `demo_live != off` sin creds → warning + no arranca (la app levanta) → §5 poller.
- 🟡 **#5 Estrategia de tests:** automatizables con **mock IMAP** vs. smokes manuales, explícitos → §7.
- 🟡 **#6 Mapeo `deterministic`:** por **marcador en el asunto** (`[DEMO:<escenario>]`) → §3.1, §5.
- 🟡 **#7/#8/#9:** intervalo justificado en `env.example`; Gmail **desechable** (app-password = acceso total, no
  scopeable); `.env` ya gitignorado → §9.
- *Corregidas 2 imprecisiones del reviewer:* el repo es `dashboard/store.py` (no `infrastructure/repository.py`); las
  app-passwords de Gmail **no** son scopeables (mitigación real = buzón dedicado, no "permisos mínimos").
- ✅ **Confirmados sin cambio:** P1 (poller nunca firma; solo el operador llega a terminal), P2 (motor decide),
  passive (poller en `ingest/`), cero deps nuevas, honestidad P7 + costo blindado (off default, tope, `deterministic` gratis).
