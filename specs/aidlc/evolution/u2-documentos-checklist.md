# U2 — Documentos requeridos + Checklist por producto

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Demo (parcial) · **LLM/det:** ⚙️ determinístico · **Depende de:** U4 (para "qué llegó")

## 1. Intent

Reproducir el paso 8 del operador (el que "consume muchísimo tiempo"): cada **producto** exige una **lista de
documentos distinta** (denuncia, SOAT, historia clínica, factura, fotos…). Un **checklist determinístico** que
muestra qué documentos se requieren y (cuando haya multimodal, U4) cuáles llegaron y cuáles **faltan**.

## 2. Criterios de completitud (verificables)

1. **Catálogo determinístico** producto → documentos requeridos (`documentos_requeridos(producto) -> list`).
   Modela 2-3 productos reales como ejemplares (Autos, Hogar, SOAT); productos no modelados → lista vacía +
   "catálogo no disponible" (P7, no inventa).
2. **Checklist** (`checklist_documentos(caso) -> list[{doc, requerido, presente}]`): marca requeridos.
   **Pre-U4** (sin adjuntos): muestra los requeridos como lista informativa ("presente" desconocido).
   **Post-U4:** marca `presente` según los documentos detectados en los adjuntos.
3. **Faltantes de documentos** feed a la recomendación/carta (Unit M pedir-datos puede nombrar el documento
   faltante, no solo el campo).
4. **Passive:** no decide cobertura ni estado (P1/P2).

## 3. Invariantes / restricciones

- **P7:** catálogo solo de productos modelados; sin match → "no disponible", nunca una lista inventada.
- **P1:** informa qué falta; no bloquea ni decide.
- **Solo `dashboard/`** + una tabla de datos de catálogo. No toca `rules/` de cobertura.

## 4. Fuera de alcance

- Detección de qué documento es cada adjunto → **depende de U4** (multimodal). Pre-U4 solo lista requeridos.
- Validez legal/formato de cada documento.

## 5. Verificación (tests fail-closed)

- Un caso Hogar → checklist con los docs de Hogar; SOAT → los de SOAT (distintos).
- Producto no modelado → "catálogo no disponible" (no inventa).
- El checklist no muta estado ni decide cobertura.

## 6. Notas CÓMO

Tabla de catálogo (`documentos por producto`) + view-model passive `checklist_documentos`. UI en el detalle.
La integración "qué llegó" se enchufa cuando U4 exponga los documentos detectados.
