# W2 — Header del caso (tipo + asegurado + confianza% + tiempo estimado)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 1
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** R + **M** (asegurado, tiempo estimado)

## 1. Intent

Al abrir el caso, el operador entiende **en 2 segundos** qué es, sin leer nada:
*"Accidente Automóvil · Juan Pérez · Alta confianza (97%) · Tiempo estimado para revisar: 1 min 34 s"*.
Ya me ahorraste tiempo.

## 2. Criterios de completitud (verificables)

1. **Tipo de siniestro** — de `clasificar(caso)` (real).
2. **Asegurado** — nombre del asegurado. **Provider `asegurado_de(caso)`**: hoy devuelve el valor **mock/
   sembrado** (rotulado, P7) porque C2 aún no extrae nombre; **M2** lo reemplaza por el real sin tocar la vista.
3. **Confianza del caso (%)** — de `hallazgos_verificador(caso, traza)` (real); nivel visual (alta/media/baja).
4. **Tiempo estimado para revisar** — **provider `tiempo_estimado(caso)`**: heurística honesta (según
   completitud/faltantes/riesgos), rotulada como **estimado**. No promete exactitud (P7).
5. Se muestra en la parte superior de la columna central de la Workbench (W1).

## 3. Invariantes / restricciones

- **P7:** el asegurado mock y el tiempo estimado van **rotulados** (badge/atributo `origen="demo"` para el
  mock; "estimado" para el tiempo). No se presentan como dato duro verificado.
- **P1:** informativo; no decide nada.
- **P5:** si el asegurado real (M2) trae PII, se muestra según la política de display (redacción donde aplique).

## 4. Fuera de alcance

- Extracción real del asegurado (eso es **M2**); aquí solo el provider + la presentación.

## 5. Verificación (tests fail-closed)

- El header muestra tipo/confianza reales del `Caso`.
- El asegurado mock lleva su rótulo de origen (no se confunde con real).
- El tiempo estimado nunca se presenta sin la etiqueta "estimado".
- Un caso sin confianza disponible → "n/d", no un número inventado (P7).

## 6. Notas CÓMO

View-models nuevos en `vista_caso.py`: `asegurado_de(caso)` (provider mock/intercambiable),
`tiempo_estimado(caso)`. Parcial de header en la columna central de `workbench.html`.

## 7. Precisiones tras code-review (CÓMO)

- **Edge cases cubiertos:** `asegurado_de` con campo `asegurado_nombre` **ausente/vacío** → cae al mock demo
  (no lo fuerza a real). Nombre demo determinístico por `caso.id` (estable, no aleatorio). Descartado por
  bajo valor: guard `caso.id is None` (`id` es `Field(min_length=1)` con default UUID) y TypedDict de retorno.
