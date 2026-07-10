# U5 — Historia de siniestros + consultas cross-claim

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Producto · **LLM/det:** ⚙️ determinístico · **Depende de:** C1 (Postgres/persistencia)

## 1. Intent

Habilitar la **base para el fraude cross-claim** (U6): una capa de **consulta sobre la historia de siniestros**
que ya se persiste (C1). Perito hoy procesa cada FNOL **aislado**; esta Unit le da la capacidad de **mirar el
pasado** — sin ser "memoria conversacional" (es un store de datos, no un chat).

## 2. Criterios de completitud (verificables)

1. **Consultas cross-claim** sobre `CasoRepository` (C1): por **asegurado/póliza** (para frecuencia), por
   **entidad** (placa, teléfono, tercero, taller — co-ocurrencia), por **ventana temporal**.
2. **Índice de huellas de media** (tabla `hash_perceptual → caso_id`): se guarda la **huella, no la imagen**
   (P5). Poblado por U4 (multimodal); esta Unit define el store y la consulta de match.
3. **Passive / solo lectura de patrones:** devuelve **señales candidatas** (frecuencia N en M meses, entidad
   repetida, hash coincidente) — **no decide nada** (P6).
4. **Rendimiento:** las consultas están acotadas (índices, límites) — no escanean todo sin cota (P4-style).

## 3. Invariantes / restricciones

- **P5:** se guardan **huellas e identificadores mínimos**, no media cruda ni PII innecesaria; redacción en logs.
- **P6:** entrega señales, no veredictos; U6 las usa como sugerencia.
- **Depende de C1:** funciona con `PERSISTENCE=postgres`; con `memory` degrada (historia = la sesión).

## 4. Fuera de alcance

- La lógica de fraude en sí (U6) y la generación de huellas de imagen (U4).
- Grafo de red completo (empezar por co-ocurrencia simple).

## 5. Verificación (tests fail-closed)

- Consulta por asegurado devuelve sus siniestros previos en la ventana.
- El índice de huellas guarda hash, **no** la imagen.
- Las consultas respetan cotas (no escaneo ilimitado).

## 6. Notas CÓMO

Extiende `persistence/`/`CasoRepository` con consultas cross-claim + una tabla de huellas. Determinístico,
sin LLM. Habilita U6.

## 7. Precisiones tras code-review

- **Esquema:** nueva tabla `hash_perceptual (hash_value PK, caso_id FK, creado_at)` + contrato
  `HuellaPerceptual`. Se guarda el **hash**, jamás la imagen (P5).
- **Métodos de consulta (con cotas P4 duras):** `casos_por_asegurado(id, ventana, limite=N)`,
  `casos_por_entidad(clave, limite=N)`, `match_huella(hash, distancia_max)`. **Todas con `LIMIT`** (hoy
  `list()` no tiene → se agrega). Aserción: ninguna consulta devuelve sin cota.
- **Footprint, no Caso (P5):** las consultas devuelven `{caso_id, asegurado_id, entidad, fecha, hash}` —
  **nunca** `Caso.aviso.texto_crudo` ni PII cruda hacia U6.
- **C1 explícito:** requiere `PERSISTENCE=postgres`; con `memory` la historia = la sesión (degrada, avisa en log).
