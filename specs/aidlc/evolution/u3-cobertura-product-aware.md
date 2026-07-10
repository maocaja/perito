# U3 — Cobertura product-aware 🔒 P2

> **Change-level spec (QUÉ)** · **Estado:** 🟡 propuesto · **Programa:** `ROADMAP-fnol-completo.md`
> **Fase:** Demo (2-3 productos) · **LLM/det:** ⚙️ determinístico · **Depende de:** —
> **🔒 Toca `rules/` + `contracts/` (P2) → requiere OK explícito del humano + code-reviewer antes del CÓMO.**

## 1. Intent

La cobertura **no es generalizable**: cada producto tiene su **catálogo de coberturas** (básicas + opcionales),
con **sublímites, deducibles y exclusiones por cobertura**, y reglas propias (SOAT topa en SMMLV). El motor
plano de hoy (una `suma_asegurada` y un `deducible` únicos) es una simplificación de demo. Esta Unit lo hace
**product-aware** — profundizando P2, sin que el LLM decida nada.

## 2. Criterios de completitud (verificables)

1. **Modelo de datos product-aware:** `Producto` con catálogo de `Cobertura {nombre, sublímite, deducible,
   exclusiones}`; la `Poliza` referencia un producto y los valores contratados por cobertura. Reemplaza los
   `coberturas_contratadas: list[str]` + `suma_asegurada`/`deducible` planos.
2. **R1-R5 operan por cobertura** (el esqueleto no cambia): R1 vigencia · R2 ¿el evento mapea a una cobertura
   **de este producto**? · R3 exclusión de esa cobertura/producto · R4 **sublímite de esa cobertura** (+ topes
   especiales: SOAT→SMMLV) · R5 **deducible de esa cobertura**.
3. **El dictamen cita la cobertura + la cláusula + el sublímite aplicado** (P2 profundizada).
4. **Ejemplares (P7):** modela Autos, Hogar y SOAT con su estructura real; productos no modelados →
   `REQUIERE_REVISION` (escala, no inventa cobertura).
5. **El LLM sigue sin decidir** — solo alimenta campos; las reglas product-aware dictaminan.

## 3. Invariantes / restricciones

- **🔒 P2:** cobertura por reglas determinísticas, cero LLM; cada dictamen cita regla + cobertura + cláusula.
- **P7:** solo productos modelados; los demás escalan, no se inventan.
- **Compatibilidad:** migrar los datos demo/presets al nuevo modelo sin romper los estratos de eval existentes.
- **Retro-compat de evals:** re-correr los evals de cobertura por estrato tras el cambio (RNF).

## 4. Fuera de alcance

- Catálogo exhaustivo de todos los productos del mercado.
- Cálculo actuarial de reservas (más allá del sublímite/deducible determinístico).

## 5. Verificación (tests fail-closed)

- Hogar "daño por agua" aplica el **sublímite de esa cobertura**, no la suma de la póliza.
- SOAT topa el beneficio en **SMMLV** (regla específica).
- Un producto no modelado → `REQUIERE_REVISION` (no inventa cobertura).
- Ningún camino hace que el LLM decida cobertura (aserción fail-closed).
- Los estratos de eval de cobertura siguen verdes con el nuevo modelo.

## 6. Notas CÓMO

Toca `contracts/poliza.py` (nuevo modelo Cobertura/Producto), `rules/motor_r1_r5.py` (operar por cobertura),
`demo/scenarios.py` (datos ejemplares), evals de cobertura. **Máxima cautela: es la joya del CORE y ruta
protegida.** Un solo Bolt con revisión reforzada.

## 7. Precisiones tras code-review (contratos concretos)

- **Modelo (anidado, no store global):** la `Poliza` **anida** su cobertura contratada (evita un store de
  productos separado que complique C1):
  ```
  CoberturaContratada { nombre: str, sublimite: Money, deducible: Money, exclusiones: list[str] }
  Poliza { ..., producto: str, coberturas: list[CoberturaContratada], es_soat: bool }  # reemplaza coberturas_contratadas/suma/deducible planos
  ```
- **R3 exclusiones (hoy `pass` en `motor_r1_r5.py`):** se implementa — el evento se rechaza si mapea a una
  exclusión de su cobertura. Es un criterio nuevo, no un no-op.
- **R4 sublímite:** `min(monto, cobertura.sublimite)` (de LA cobertura), no la suma de la póliza.
- **SOAT:** producto `"SOAT"` con coberturas de tope en **SMMLV** (constante `SMMLV_2026`); R4 aplica
  `min(monto, n_smmlv * SMMLV)`. Añadir `TipoSiniestro` SOAT (ej. `SOAT_GASTOS_MEDICOS`) al enum.
- **Dictamen extendido (cita específica, P3):** añadir `cobertura_aplicada: str` y `sublimite_aplicado: Money`
  a `contracts/dictamen.py` — el dictamen cita la cobertura concreta, no solo "R2".
- **Guardián de "producto no modelado":** el **motor (R2)** — si el producto/cobertura no está en el catálogo
  modelado → `REQUIERE_REVISION` con `regla_aplicada = "PRODUCTO_NO_MODELADO"` (fail-closed, P7).
- **Migración:** reescribir `poliza_demo()`/presets al nuevo modelo y **re-correr los evals de cobertura por
  estrato** (aserción: siguen verdes). Fixtures de `fixtures_u3_motor.py` migradas en el mismo Bolt.
- **Ejemplares:** Autos, Hogar **y SOAT** (hoy solo AUTO existe) — agregar Hogar y SOAT a `scenarios.py`.
