# U1 — Clasificación + Prioridad + Routing

> **Change-level spec (QUÉ)** · Fase AI-DLC: Construction · **Estado:** 🟡 propuesto.
> **Programa:** `ROADMAP-fnol-completo.md` · **Fase:** Demo · **LLM/det:** ⚙️ determinístico · **Depende de:** —

## 1. Intent

Dar a la bandeja el aire de un **core de seguros real**: cada caso queda **clasificado** (producto/tipo),
con una **prioridad** (alta/media/baja) y un **equipo destino** — tres decisiones **determinísticas y
citables** que hoy no existen. Reproduce los pasos 10, 14 y 15 del flujo real del operador.

## 2. Criterios de completitud (verificables)

1. **Clasificación** (`clasificar(caso) -> {producto, tipo}`): deriva el producto (Autos/Hogar/Vida/SOAT/…) y
   el tipo de evento del `tipo_siniestro` extraído + señales del caso. Determinístico (tabla/prefijos); si no
   mapea → "sin clasificar" (no inventa, P7).
2. **Prioridad** (`prioridad(caso) -> {nivel, motivo}`): reglas duras — lesionados/fallecidos → **ALTA**;
   vehículo inmovilizado / monto alto → **MEDIA**; daño menor → **BAJA**. Cada nivel **cita la regla que lo
   disparó** (P2-style). Passive.
3. **Routing** (`equipo(caso) -> str`): mapping producto/tipo → equipo (Vida/Autos/Hogar/Fraude/Ajustadores).
   Si hay señal de fraude → sugiere **carril SIU** (sin cambiar estado, P6).
4. **UI:** la bandeja muestra prioridad (chip de color) y equipo; **se puede ordenar por prioridad** sin
   romper el orden cronológico del efecto en vivo (orden secundario/toggle).
5. **Nada decide el siniestro:** clasificación/prioridad/routing **preparan**, no aprueban ni niegan (P1).

## 3. Invariantes / restricciones

- **P1:** solo prepara; no toca el estado del caso ni la decisión.
- **P2/P7:** prioridad y routing son **reglas citables**, no LLM; sin match → neutral, no inventa.
- **P6:** el carril SIU por fraude es sugerencia, no bloqueo.
- **Solo `dashboard/`** (+ un módulo passive de reglas de presentación). No toca `rules/` de cobertura.

## 4. Fuera de alcance

- Reglas de prioridad por producto exhaustivas (un set razonable, ampliable).
- El checklist de documentos (U2) y el motor de cobertura (U3).

## 5. Verificación (tests fail-closed)

- Un caso con lesionados → prioridad ALTA citando la regla; daño menor → BAJA.
- Routing mapea producto→equipo; fraude → sugiere SIU sin cambiar estado.
- Clasificación sin match → "sin clasificar" (no inventa).
- La prioridad/routing **no** mutan `caso.estado`.

## 5b. Alcance v1 (tras review de implementación)

- **Prioridad v1** se basa en las señales YA disponibles: **fraude + escalamiento + dictamen**.
  `lesionados/fallecidos`, `vehículo inmovilizado` y `monto alto` requieren la **extracción rica de U4** →
  se incorporan a las reglas cuando U4 exista (no se inventan campos, P7).
- **Orden por prioridad:** implementado como **toggle opt-in** (`?orden=prioridad`); el default sigue siendo
  cronológico para no romper el efecto "en vivo".

## 6. Notas CÓMO

View-models passive en `vista_caso.py` (`clasificar`, `prioridad`, `equipo`) + chips en `bandeja.html`/detalle
+ CSS. Reusa `ramo_de`/`senal_fraude` de Unit K/L. Cero backend de dominio.
