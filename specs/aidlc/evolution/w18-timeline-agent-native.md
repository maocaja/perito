# W18 — Timeline agent-native (un nodo por AGENTE real)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1b hi-fi
> **LLM/det:** — (front) · **Depende de:** W3 · **Datos:** R · **🔴 Invariante: NO mock de agentes/rastro**

## 1. Intent

El Timeline es donde la **orquesta se ve**. Un nodo por **agente REAL** de la traza — Intake → Email/Extracción
→ (Document AI) → (Evidence Correlator) → Policy Validation → Consistency & Risk → Summary → Caso listo — con
su hora, tokens y confianza **reales**. Su objetivo es **crear confianza**: no esconder el trabajo de la IA,
mostrarlo. Horizontal, como el mockup.

## 2. Criterios de completitud (verificables)

1. **Un paso por nodo REAL de la traza** (`ReplayStore`/`Tracer`): mapea cada `nodo` a su agente nombrado
   ("Intake", "Extracción", "Validación de póliza", "Riesgo", "Resumen"…) con hora + tokens + confianza reales.
2. **🔴 Cero mock de agentes:** los pasos de agentes salen SIEMPRE de la traza; si un agente no corrió, **no
   aparece** (no se inventa un paso). El único mock permitido son los **conteos de archivos** (adjuntos, hasta
   M1) — rotulados `demo` y visualmente separados del rastro de agentes.
3. **Render horizontal** (como el mockup) con checks por paso; estado final coherente con `caso.estado`.
4. **Agentes futuros aparecen cuando existan:** Document AI (M1), Evidence Correlator (M3) se suman al mapa
   sin tocar la vista cuando emitan eventos de traza.

## 3. Invariantes / restricciones

- **🔴 P7 / blindaje agéntico:** el rastro de agentes es **real, no negociable**. Mockear un paso de agente =
  perder el enfoque. Solo el conteo de docs es demo (y rotulado).
- **P4:** el timeline lee la traza (no re-ejecuta agentes); sin la traza degrada a "no disponible".

## 4. Fuera de alcance

- Ejecutar agentes nuevos (eso es M1/M3); aquí el **render** del rastro real que ya emiten.

## 5. Verificación (tests fail-closed)

- Con una traza real, cada nodo se mapea a su agente con hora/tokens reales; sin traza → "no disponible".
- Un agente que NO corrió no aparece (no hay paso fabricado) — aserción.
- Los conteos de docs (mock) van rotulados y separados del rastro de agentes.

## 6. Notas CÓMO

Upgrade de `timeline`/`actividad_agentes` (W3) para mapear cada nodo → agente nombrado con métricas reales;
render horizontal en el centro. Mapa `nodo → agente` extensible (M1/M3 se agregan sin tocar la vista).

## 7. Precisiones tras code-review

- **🟠 Separación visual del mock (P7) — reconciliado con la imagen:** el mockup de referencia **intercala**
  "Leyó 6 archivos" en el flujo horizontal, así que la primera versión NO separa en un bloque aparte (eso
  contradiría la imagen). En su lugar, los pasos de conteo (mock) se rinden **inline pero inequívocamente
  distintos**: dot **dashed** + badge **`demo`** + `title` "dato de demostración". Los pasos de **agentes**
  salen SOLO de `actividad_agentes(traza)` (nunca fabricados). Un bloque "Datos iniciales" separado queda como
  opción de pulido si el conteo crece. (Supera la precisión previa que pedía grupo aparte.)

### Tras el CÓMO
- **Reviewer: 0 críticos, blindaje agéntico intacto** (pasos de agente solo de la traza; agente-no-corrió no
  aparece; agente-nuevo aparece por el mapa `_NODOS` extensible sin tocar la vista). Clean Code/SOLID (OCP en
  `_NODOS`). Ajustes: guard de `nodo` vacío, docstring P4, test robusto por nombre de agente. Render horizontal
  con tokens reales por paso.
- **Upgrade sobre W3:** `timeline()` se refactoriza para (a) mapear cada `nodo` de la traza → agente nombrado
  vía una tabla `nodo→agente` **extensible**, y (b) separar el bloque demo. Test: un agente que **no corrió**
  no aparece (cero pasos fabricados); M1/M3, al emitir eventos de traza, aparecen **sin tocar la vista** (test
  con traza mock que incluye un nodo nuevo → se renderiza).
