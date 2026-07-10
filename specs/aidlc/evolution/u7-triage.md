# U7 — Triage (front door)

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Demo/Producto · **LLM/det:** 🤖 LLM · **Depende de:** —

## 1. Intent

El **front door** del operador (paso 2): de 80-200 correos/día, **no todos son siniestros** (preguntas,
quejas, seguimiento, docs de un caso viejo). Un agente que **clasifica el correo** — siniestro nuevo /
pertenece a un caso existente / no-siniestro — y **enruta**, sin decidir el siniestro.

## 2. Criterios de completitud (verificables)

1. **Clasificación de entrada** (`triage(correo) -> {clase, confianza}`): `SINIESTRO_NUEVO` ·
   `PERTENECE_A_CASO` · `NO_SINIESTRO` (queja/comercial/seguimiento).
2. **Ruteo:** `SINIESTRO_NUEVO` → pipeline FNOL; `PERTENECE_A_CASO` → adjunta al expediente (si se identifica);
   `NO_SINIESTRO` → cola aparte / no crea caso.
3. **Confianza + escalamiento (P4/P7):** baja confianza o ambigüedad → **escala a humano**, no fuerza una clase.
4. **P1:** el triage decide **ruta**, no el siniestro. No aprueba/niega nada.

## 3. Invariantes / restricciones

- **P1:** clasifica y rutea; no decide el resultado del siniestro.
- **P7/P4:** ante duda, escala; no inventa la clase.
- **Seguridad:** el correo es input no confiable (inyección) → aislado del prompt de decisión.
- **Costo:** modelo barato (Haiku) para clasificar; escalar solo si ambiguo.

## 4. Fuera de alcance

- Matching perfecto a expediente existente (usa entity resolution U8 cuando exista).
- Respuesta automática a no-siniestros.

## 5. Verificación (tests fail-closed)

- Un correo de queja → `NO_SINIESTRO` (no crea caso FNOL).
- Un aviso claro → `SINIESTRO_NUEVO`.
- Ambiguo/baja confianza → escala a humano, no fuerza clase.
- El triage no alcanza ningún estado terminal.

## 6. Notas CÓMO

Nodo `C0 triage` antes de C2 (o en el poller de intake). LLM clasificador mockeable (hermético). Toca
`intake/` + `llm/`. Alimenta el ruteo de la bandeja.

## 7. Precisiones tras code-review

- **🔒 P5 (bloqueante):** hoy el poller pasa `correo.cuerpo` **crudo** (puede traer cédula/placa/nombre). El
  triage LLM **debe recibir el cuerpo YA redactado** (`redact_pii_spans_es_co` + NER de U4). **No** enviar PII
  cruda al clasificador. Test: un cuerpo con cédula no llega cruda al prompt del triage.
- **Fase Producto** (no demo): depende de la redacción de cuerpo (llega con U4). Se corrige la fase en el roadmap.
- **Inyección:** el cuerpo es input no confiable → delimitado/etiquetado en el prompt del clasificador.
