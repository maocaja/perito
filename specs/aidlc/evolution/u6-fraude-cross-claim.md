# U6 — Fraude cross-claim (capa 4) 🔒 P6

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Producto · **LLM/det:** ⚙️ (detección) + 🤖 (explica) · **Depende de:** U4 (media), U5 (historia)
> **🔒 P6 → OK explícito + code-reviewer antes del CÓMO.**

## 1. Intent

La cuarta capa de fraude — la que da el **valor real** (patrones/redes, no solo intra-caso): **foto
reutilizada** de otro siniestro, **frecuencia** sospechosa (reporta cada N meses), **reclamaciones repetidas**,
**redes de co-ocurrencia** (mismo tercero/taller). Detección **determinística**; el LLM solo explica; el
humano/SIU decide.

## 2. Criterios de completitud (verificables)

1. **Foto reutilizada** (`pHash`): match perceptual (distancia de Hamming) contra el índice de U5 → señal
   *"foto idéntica al siniestro X (distancia d)"* + EXIF cross-check.
2. **Frecuencia** (`N siniestros en M meses` por asegurado/póliza) → señal con el conteo.
3. **Reclamación repetida** (similitud de relato contra el histórico) → señal.
4. **Co-ocurrencia** (misma entidad en múltiples casos) → señal.
5. **Todas son señales, con evidencia + confianza** ("distancia 3, revisar"), agregadas a `alerta_fraude` como
   **capa 4** — distinta de las capas 1-2 intra-caso.
6. **🔴 P6 absoluto:** ninguna señal cross-claim cambia el estado, deshabilita botones ni bloquea — **ni
   siquiera cuando la foto es idéntica**. Solo sugiere revisión / carril SIU. El LLM redacta el "por qué".

## 3. Invariantes / restricciones

- **🔒 P6:** solo sugiere; nunca decide/bloquea. Test fail-closed: señal cross-claim ⇏ estado terminal.
- **P7:** falsos positivos → sugerencia con evidencia y confianza, nunca veredicto.
- **P5:** compara huellas/identificadores, no media cruda.
- **Determinístico** en la detección; el LLM solo explica (no detecta).

## 4. Fuera de alcance

- Modelos ML de fraude entrenados; empezar por reglas/huellas determinísticas.
- Decisión SIU (eso es humano).

## 5. Verificación (tests fail-closed)

- Dos siniestros con la **misma foto** → señal de foto reutilizada citando el caso previo.
- Asegurado con N avisos en la ventana → señal de frecuencia con el conteo.
- **Ninguna** señal cross-claim (aunque distancia=0) cambia `caso.estado` ni deshabilita la firma.
- Las señales llevan evidencia + confianza (no verdad absoluta).

## 6. Notas CÓMO

Nuevo módulo en `fraud/` (capa 4) que consume U5 (historia + huellas) y U4 (media). `pHash` sobre stdlib/lib
ligera. Determinístico + explicación LLM mockeable. Alimenta prioridad/SIU (U1).

## 7. Precisiones tras code-review

- **`AlertaFraude.confianza`:** añadir campo `confianza: float [0,1]` a `contracts/dictamen.py` — toda señal
  (incl. cross-claim) lleva confianza; los falsos positivos son sugerencia con confianza, no verdad (P7).
- **Umbrales explícitos (configurables):** pHash **distancia Hamming ≤ 3 = ALTA, 4-7 = MEDIA, ≥8 = no señal**;
  frecuencia **≥ 3 siniestros en 12 meses = señal**; co-ocurrencia **≥ N casos** para evitar falsos positivos
  (taller legítimo aparece en muchos). Sin umbral mágico oculto.
- **🔒 Test fail-closed P6 (obligatorio):** dos casos con **foto idéntica (distancia 0)** → señal emitida, pero
  `caso.estado` **NO cambia** y la firma sigue habilitada. Ni la señal más fuerte decide.
- **pHash reproducible:** la lib elegida debe dar hashes estables (no seed aleatorio); verificar en test.
- **P5:** la explicación referencia solo `caso_id` (uuid opaco) del caso previo, nunca su PII.
