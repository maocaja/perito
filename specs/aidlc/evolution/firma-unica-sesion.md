# Unit de Evolución — Firma única de estación (identidad de sesión ligera)

> **Tipo:** cambio brownfield · **Fase AI-DLC:** Construction (Bolt) · **Estado:** 🟢 QUÉ + CÓMO ejecutado
> (rama `feat/workbench-firma-sesion`) · suite **656 verde** · pendiente code-review + PR.
> **Origen:** hallazgo de UX — un caso `REQUIERE_REVISION` mostraba **dos** campos "Firma del analista · Tu nombre"
> (corregir + escalar). Decisión del usuario: **D · identidad autenticada**, sabor **sesión ligera** (sin passwords).

## 1. Intent (el goal)
El analista **se identifica una vez** al entrar a la estación; cada acción se firma **automáticamente** con esa
identidad (sesión). Se elimina el campo "Tu nombre" de todas las acciones → adiós a la doble firma, y la
auditoría se **refuerza** (el firmante sale de la sesión, no de un texto libre que se puede falsear en la UI).

## 2. Qué cierra
- El **bug de UX** de dos firmas en pantalla (corregir + escalar) y la inconsistencia `required` duro vs. blando.
- Fortalece **P1/auditoría** (EU AI Act Art. 14): `aprobado_por` = identidad de sesión.

## 3. Criterios de completitud (verificables)
1. Entrar a `/workbench` **sin identidad en sesión** → **captura única** ("¿Quién eres?"); luego no vuelve a pedirla.
2. **Ninguna acción** de la UI (corregir, radicar, rechazar, escalar, fraude, solicitar_docs, borrador) muestra
   campo "Tu nombre".
3. El servidor **firma con la sesión**: `aprobado_por`/auditoría = `firmante` de sesión (fuente de verdad).
4. **Fail-closed (P1):** acción **sin firma** (ni sesión ni fallback) → **400**, nunca ejecuta.
5. El topbar muestra **"Firmando como: [nombre] · cambiar"** (identidad visible y cambiable).
6. **Suite verde** sin regresiones + tests nuevos del flujo de sesión.

## 4. Invariantes / NFR
- **P1 preservado y reforzado:** el gate de firma **no se relaja** — se mueve al chokepoint `_firma()`, ahora
  session-first; sigue siendo obligatorio (fail-closed a 400).
- **P5 (PII):** el nombre del firmante se sigue **redactando** en display/traza (`|redact`, como
  `aprobado_por` hoy — ver `test_confirmacion_redacta_firmante`).
- **Hermético:** los tests siguen sin red; la sesión se establece vía `POST /workbench/identificar` en el `TestClient`.
- **Sin lógica de dominio nueva:** motor/orquestador/HITL-core (`hitl/c8.py`) intactos; rutas protegidas sin tocar.

## 5. Diseño breve (el CÓMO — el Bolt)
- **`app/config.py`:** `session_secret: str` (dev por default; prod desde env).
- **`app/main.py`:** añadir `SessionMiddleware(secret_key=settings.session_secret)` (hoy solo hay CORS).
- **Chokepoint `app/api/hitl_actions.py::_firma`:** pasa a `_firma(request, usuario)` — **session-first**
  (`request.session.get("firmante")`), con `usuario` (form) como **fallback de compatibilidad** para callers
  programáticos/tests; si no hay ninguno → **400 (P1)**. Los 6 endpoints (radicar/rechazar/escalar/enviar_fraude/
  solicitar_docs/guardar_borrador) reciben `request: Request` y llaman `_firma(request, usuario)`. Igual
  `c11.py::workbench_corregir` (ya tiene `request`) vía `_validar_corregible(caso_id, firma)`.
- **Captura de identidad:** `POST /workbench/identificar` (form `firmante` + `next`) → `request.session["firmante"]`
  → redirect 303 a `next`. La UI la muestra **server-driven** cuando `not firmante` (o `?identificar=1` para "cambiar").
- **Templates:**
  - `base.html` (topbar): chip "Firmando como: {{ firmante|redact }} · cambiar" (link `?identificar=1`); y un
    **overlay de identificación** cuando `not firmante or request.query_params.identificar` (form → `/workbench/identificar`).
    El template lee `request.session` directo (no hay que hilar `firmante` por cada handler).
  - `workbench_caso.html`: eliminar los 3 inputs de firma — `wb-corregir-firma` (`:68`, `:159`) y el macro
    `firma_input`/`#wb-firma` (`:348`) — y los `hidden name="usuario"`; los forms envían sin firma (usa sesión).
    Quitar el JS que copiaba `#wb-firma` → `.wb-firma-in`.

## 6. Fuera de alcance / decisiones (P7)
- **Login real** (usuario+contraseña), multiusuario con permisos, SSO, expiración/rotación avanzada.
- **Fallback `usuario` (form):** se conserva como compat para callers no-UI/tests; **la UI usa solo la sesión**.
  Es una simplificación consciente de demo (no un agujero de la UI): el humano no puede teclear un nombre falso
  desde la estación. Documentado, no oculto.
- **D1 — Persistencia:** cookie de sesión (dura la sesión del navegador; Starlette la firma). **D2 — "cambiar":**
  link en el topbar (`?identificar=1`) que reabre la captura.

## 7. Cómo se validará el Bolt (gate de salida)
- **Tests nuevos:** identificarse → una acción usa la firma de sesión (`aprobado_por == firmante`); acción **sin**
  sesión **ni** `usuario` → **400**; el `workbench_caso.html` de acción **no** contiene el label "Firma del analista".
- **Suite base verde** (`make test`): los HITL existentes siguen pasando por el **fallback `usuario`**.
- **Verificación por ejecución:** `DEMO_LIVE=deterministic make run` → identificarse una vez → en un caso
  `REQUIERE_REVISION`: **ya no hay dos firmas**; corregir/escalar/radicar **sin re-escribir el nombre**.
- **`code-reviewer`** (foco: P1 fail-closed intacto, PII redactada, rutas protegidas) → PR.

## 8. Decisiones (resueltas con el usuario)
- **D — Sabor:** ✅ sesión ligera (sin passwords). **D1:** ✅ cookie de sesión. **D2:** ✅ "cambiar" en el topbar.
