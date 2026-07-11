# W3 — Timeline visual de la IA (pasos + conteos de docs)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** R + **M** (conteos de docs)

## 1. Intent

Entender el caso es entender su historia. Un **timeline visual** de lo que hizo la IA:
*Correo recibido → leyó el correo → leyó 6 PDFs → leyó 14 fotografías → encontró la póliza → encontró la
cobertura → encontró inconsistencias → caso listo*. El operador ve **qué hizo la IA**, paso a paso.

## 2. Criterios de completitud (verificables)

1. **Pasos reales** desde la traza: reusa `actividad_agentes(traza)` / `verificacion_trayectoria` (C2→C3→C4→
   C5→C6, orquestador) — ya existen.
2. **Conteos de documentos** ("6 PDFs", "14 fotografías") — **provider `conteo_adjuntos(caso)`**: hoy devuelve
   conteos **mock/sembrados** (rotulados) porque los adjuntos aún no fluyen; **M1** los vuelve reales sin tocar
   la vista.
3. **Render como timeline** (pasos verticales con estado ✔/⚠), no como lista plana de logs.
4. **Estado final** ("Caso listo" / "Escalado") coherente con `caso.estado` (real).

## 3. Invariantes / restricciones

- **P7:** si un evento no está en la traza, **no se inventa** (hoy `actividad_agentes` ya es fail-closed). Los
  conteos mock van rotulados como demo.
- **P1:** describe lo que la IA hizo; no decide.

## 4. Fuera de alcance

- Lectura real de adjuntos y conteo real (eso es **M1**); aquí el provider + el render.

## 5. Verificación (tests fail-closed)

- El timeline refleja los pasos de la traza real (sin eventos fabricados).
- Los conteos mock llevan su rótulo de origen.
- Un caso escalado muestra el paso de escalamiento, no "Caso listo".

## 6. Notas CÓMO

Reusa `actividad_agentes`/`verificacion_trayectoria`; nuevo provider `conteo_adjuntos(caso)` (mock
intercambiable). Parcial `timeline` en la columna central; estilos de timeline en `style.css`.

## 7. Precisiones tras code-review (CÓMO)

- **🔴 P7 estados terminales:** el mapa de estado final del timeline incluye `APROBADO`/`RECHAZADO` (no solo
  LISTO/REQUIERE) → un caso resuelto muestra su estado real, no termina abrupto. Tests parametrizados por estado.
