# W11 — Centro de documentos (galería) · **provider MOCK**

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-workbench.md` · **Fase:** 2
> **LLM/det:** — (front) · **Depende de:** — · **Datos:** **M** (provider intercambiable) · **Invariante:** P5

## 1. Intent

No carpetas: una **galería**. 📷 Foto Frente · 📷 Foto Derecha · 📷 Motor · 📄 SOAT · 📄 Licencia · 📄 Denuncia.
Cada documento con su estado: **Extraído · Validado · Relacionado**. El operador ve de un vistazo qué llegó.

## 2. Criterios de completitud (verificables)

1. **Provider `documentos_de(caso) -> list[Documento]`** con la interfaz que consumirá M1: `{nombre, tipo
   (foto/pdf/…), etiqueta, estado (extraído/validado/relacionado), huella, origen}`. **Hoy devuelve datos
   sembrados/mock** por caso demo (rotulados P7); **M1** lo reemplaza por adjuntos reales sin tocar la vista.
2. **Galería** (grid de miniaturas/íconos por tipo) en la columna central, con los 3 estados por documento.
3. **Auto-etiquetado** (IMG_4231 → "Foto Vehículo Frente") en el mock; real vía M1/U4 §6.
4. Un documento se puede seleccionar → alimenta W12 (evidencia/visor).

## 3. Invariantes / restricciones

- **P5:** la galería muestra **miniaturas/íconos rotulados**, **nunca PII cruda**; para imágenes reales
  (M1) se muestra la versión redactada o solo la huella (política de fase-2).
- **P7:** todo el contenido mock lleva `origen="demo"`; no se presenta como documento real del asegurado.

## 4. Fuera de alcance

- Lectura/persistencia real de adjuntos (M1). Visor con salto a la fuente (W12).

## 5. Verificación (tests fail-closed)

- El provider mock devuelve documentos con los 3 estados y su rótulo de origen.
- Ningún documento expone PII cruda en la galería (P5).
- La interfaz del provider es la misma que consumirá M1 (contrato estable).

## 6. Notas CÓMO

Nuevo `dashboard/providers/documentos.py` (o view-model) con `documentos_de(caso)` (mock intercambiable) +
contrato `Documento`. Galería en `workbench.html`; assets demo embebidos/íconos.

## 7. Precisiones tras code-review

- **🟡 Contrato `Documento` explícito** (para que M1 conecte sin incompatibilidad):
  `Documento: {nombre: str, tipo: str ("foto"|"pdf"|"audio"|…), etiqueta: str, estado:
  "extraído"|"validado"|"relacionado", huella: str|None, origen: str}`. En el mock, `origen="demo"`. El
  provider `documentos_de(caso) -> list[Documento]` es la interfaz estable que M1 implementa con datos reales.

### Tras el CÓMO
- **Clean/DIP:** provider en `dashboard/documentos.py` (SRP); el template usa el filtro Jinja `icono_tipo`
  (fuente única tipo→ícono, DRY/OCP), no un hardcode. **P5 defensivo:** la galería expone **etiqueta + índice**,
  NUNCA el nombre crudo del archivo (M1 podría traer PII en el nombre) — test que lo verifica. Contrato
  `Documento` frozen = interfaz que M1 llena (Liskov). Tests de `icono_de` y lista vacía añadidos.
