# U8 — Entity resolution (fallback lookup)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Producto · **LLM/det:** ⚙️ (búsqueda) + 🤖 (extrae claves) · **Depende de:** U4 (extracción rica)

## 1. Intent

El paso 3 del operador: cuando **no viene el número de póliza**, buscar por **placa, cédula o nombre**. Hoy C4
solo busca por número. Esta Unit agrega el **fallback determinístico** por claves alternativas.

## 2. Criterios de completitud (verificables)

1. **Extracción de claves alternativas** (del bundle multimodal, U4): placa, cédula, nombre del asegurado.
2. **Búsqueda fallback determinística** en el store de pólizas: si no hay número o no hace match → buscar por
   placa → cédula → nombre. Retorna candidatas **sin forzar match** (P4).
3. **Ambigüedad → escala:** múltiples candidatas o ninguna → `REQUIERE_REVISION` (no elige a ciegas).
4. **Passive respecto a cobertura:** solo resuelve la póliza; no decide cobertura ni estado.

## 3. Invariantes / restricciones

- **P4:** nunca fuerza un match; ante ambigüedad, escala.
- **P2:** no toca la decisión de cobertura (eso es C5/U3).
- **P5:** las claves (cédula/placa) son PII → redacción en display/logs.

## 4. Fuera de alcance

- Deduplicación difusa avanzada de nombres (empezar por match exacto/normalizado).

## 5. Verificación (tests fail-closed)

- Sin número de póliza pero con placa que hace match → resuelve la póliza.
- Múltiples candidatas → `REQUIERE_REVISION` (no elige).
- Ninguna → escala, no inventa.

## 6. Notas CÓMO

Extiende `policy/lookup` (C4) con búsqueda por claves alternativas. Determinístico; las claves salen de U4.
