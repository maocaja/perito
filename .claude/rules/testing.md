# Regla: Testing y Evals

- Framework: **pytest** (métricas deterministas) + **DeepEval** (métricas agénticas: tool correctness).
- Los evals se organizan por **ESTRATO** (ver `specs/prd.md` Segmento 11):
  `happy` · `campos-faltantes` · `poliza-no-encontrada` · `cobertura-negativa` · `fraude` · `SOAT` · `documento-sucio`.
- Cada función de dominio: al menos **1 happy path + 1 caso de error**.
- Naming: `test_<comportamiento>_when_<condicion>`.

**Métricas clave** (`specs/prd.md` Segmento 10): accuracy de extracción, coverage-match, precisión/recall de fraude vs. etiqueta, campos inventados ≈0, % dentro de cotas (0 loops).

**Invariantes de seguridad (P1-P6):** se testean con **aserciones fail-closed** (que rompan ruidosamente si se violan), no solo con números de dashboard.

⚠️ Validez del eval de fraude: solo es válido si el documento sintético **encoda la inconsistencia** de las filas etiquetadas como fraude.
