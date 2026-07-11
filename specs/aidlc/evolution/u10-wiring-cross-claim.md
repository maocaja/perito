# U10 — Wiring del fraude cross-claim al pipeline 🔒 P4 · P6

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Producto · **LLM/det:** ⚙️ det · **Depende de:** U5 (historia), U6 (capa 4)
> **🔒 Toca `orchestrator/c7.py` (P4) + señal de fraude (P6) → OK explícito + code-reviewer antes del CÓMO.**

## 1. Intent

El fraude cross-claim (U6) está **construido y probado a nivel de módulo, pero invisible**: `c7.py:C6` solo
llama `construir_alerta_fraude` (capas 1-2 intra-caso). Esta Unit **cablea la capa 4** al pipeline para que
la señal aparezca en la bandeja del operador — *"3ª reclamación de esta póliza en 6 meses → revisar"*.

**Alcance realista (honesto, P7):** hoy solo la **frecuencia** tiene todos sus insumos (necesita
`numero_poliza`, que C2 ya extrae). **Foto reutilizada** y **co-ocurrencia** quedan **cableadas pero
latentes** — disparan cuando existan sus insumos (ingesta de adjuntos con huella / extracción rica de
entidad), sin inventar nada mientras tanto.

## 2. Criterios de completitud (verificables)

1. **Cableado en C6:** tras la alerta intra-caso, `c7.py` computa la alerta cross-claim con
   `construir_alerta_cross_claim(repo=get_caso_repository(), numero_poliza=…, huella_store=get_huella_store(),
   hash_media=<si existe>)` y **combina** ambas en un solo `caso.alerta_fraude`.
2. **Frecuencia visible:** una póliza con ≥ 3 casos en la ventana (12m) → la alerta lleva la señal de
   frecuencia con el conteo, y **se ve en la bandeja** (severidad + explicación).
3. **Merge de capas:** cuando disparan intra-caso (capas 1-2) **y** cross-claim (capa 4), la
   `AlertaFraude` resultante une las `inconsistencias`, `severidad = max`, `confianza = max`, y distingue la
   capa. Ninguna se pisa.
4. **Store de huellas compartido:** `get_huella_store()` (accesor único, patrón de `set_poliza_store`).
   In-memory hoy → **degrada avisando** sin Postgres (P7); el registro de huella se hace cuando el caso trae
   un `hash` de adjunto (hook listo, hoy infrecuente).
5. **Latentes declaradas:** foto reutilizada dispara cuando el pipeline tenga el `hash` del adjunto;
   co-ocurrencia cuando `casos_por_entidad` deje de devolver `[]`. Cableadas, no inventadas.

## 3. Invariantes / restricciones

- **🔒 P6 (absoluto):** la señal cross-claim **solo sugiere**. El bloque C6 ya es **no-escalante**; el wiring
  **no** cambia `caso.estado`, no deshabilita la firma, no bloquea — **ni con foto idéntica**. La corona
  (nunca terminal) queda intacta.
- **🔒 P4:** las consultas (`casos_por_poliza`, `HuellaStore.buscar`) ya llevan **cota dura**; el wiring **no
  añade loops** ni trabajo sin cota. El registro de huellas no crece sin límite (una por caso con adjunto).
- **P5:** se registra/consulta **solo la huella** (no media cruda); la evidencia cita solo `caso_id` opaco.
- **P2:** el fraude no toca la decisión de cobertura (sigue siendo del motor R1-R5).
- **P7:** frecuencia real hoy; foto/co-ocurrencia latentes; store in-memory degrada — todo declarado, sin
  sobreventa. Sin Postgres, la historia = la sesión (la frecuencia solo ve los casos de la corrida).

## 4. Fuera de alcance (esta Unit)

- **Ingesta de adjuntos al pipeline** (hoy C7 usa `aviso.texto_crudo`, no adjuntos) → unidad aparte.
- **Extracción rica** de entidad (placa/tercero) que alimenta co-ocurrencia.
- **Persistencia Postgres** del índice de huellas (hoy in-memory).
- **U4 fase-2 visual** (pHash perceptual real de imágenes).

## 5. Verificación (tests fail-closed)

- Póliza con ≥ 3 casos en la ventana → `caso.alerta_fraude` incluye la señal de frecuencia con el conteo,
  y **`caso.estado` NO cambia** + la firma sigue habilitada (🔒 P6).
- Intra-caso + cross-claim disparan juntos → una sola `AlertaFraude` con **ambas** evidencias (merge).
- El wiring **no** produce estado terminal (corona intacta) — aserción.
- Sin señal cross-claim (póliza con < 3 casos) → el comportamiento intra-caso de hoy queda **idéntico**
  (retro-compat; los tests de C6/orquestador siguen verde).
- `get_huella_store()` sin Postgres **avisa** (degrada), no revienta.

## 6. Notas CÓMO

- Nuevo accesor `get_huella_store()` (módulo `fraud/historia.py` o `fraud/`, patrón `set_poliza_store`).
- `c7.py:C6` importa `get_caso_repository` (consulta determinística) + `construir_alerta_cross_claim`.
- Helper `combinar_alertas(intra, cross) -> AlertaFraude | None` (une inconsistencias, `severidad`/`confianza`
  = max, explicación combinada). Determinístico, testeable.
- **Máxima cautela P4:** re-correr los evals de terminación (0 loops, dentro de cotas) tras tocar `c7.py`.

## 7. Precisiones tras code-review

- **🔴 Thread-safety del `HuellaStore` (P4/correctitud):** el poller corre en un **hilo daemon** y el
  orquestador/web en el principal → un `get_huella_store()` singleton in-memory con `_huellas` (lista mutable)
  tiene **race condition**. El CÓMO **protege `registrar`/`buscar` con un `Lock`** (como `_save_lock` del
  poller). En producción, el store va sobre Postgres con su propia sincronización. Se añade a §3.
- **🟠 Reloj en tests (evitar flakiness):** `casos_por_poliza` filtra por ventana con `datetime.now()`. Los
  tests **NO** dependen del reloj real: construyen casos con `timestamp_actualizacion` controlado (patrón
  `_caso_fake` de `test_u6_cross_claim.py`) o usan `ventana_dias` amplia. Sin `pytest-freezegun` (guardrail pip).
- **🟠 Merge de confianza = `max` (semántica explícita):** al combinar intra-caso (capas 1-2) + cross-claim
  (capa 4), `confianza = max` significa **"manda la señal más fuerte"** — es una sugerencia agregada, no un
  score calibrado. Un promedio ponderado queda como mejora futura (no en esta Unit). Igual `severidad = max`.
- **🟡 Evals de terminación a re-correr (nombrados):** tras tocar `c7.py`, re-correr `test_u4_c7_orchestrator.py`
  (corona + cotas `max_rondas`/`presupuesto_tokens`/ciclo) y `test_u9_loop_reflexivo.py` (bound del loop). Se
  añade a §6.
- **P6 reafirmado:** el bloque C6 sigue **no-escalante**; la alerta combinada es **informativa**. El wiring no
  añade ninguna transición de estado — la corona (`assert estado ∈ {LISTO, REQUIERE_REVISION}`) es la red.
