# Domain Entities — U1 · Fundaciones & Contratos

> Diseño **technology-agnostic**: describe el modelo de dominio compartido (entidades + value objects). Se realizará como **contratos Pydantic tipados** en Code Generation (H-17). Sin infraestructura, sin código aquí.
> Decisiones: Q1-A (todos los contratos compartidos), Q2-A (entidad `Caso` + enum aquí; transiciones en U4).

## Bounded Context
**Fundaciones & Contratos**: el modelo de datos **compartido** de Perito (los contratos que fluyen entre todos los módulos) + la infraestructura de datos sintéticos de demo/eval. Es la fundación de round-trip y type-safety de la que dependen U2-U5. Límite: define **el dato y sus invariantes de forma**, no el comportamiento de negocio de otras unidades (cobertura=U3, terminación/HITL=U4).

---

## Entities

### Caso *(única entidad con identidad propia)*
- **Identidad**: `caso_id` (UUID).
- **Atributos**:
  - `caso_id: UUID`
  - `estado: EstadoCaso` — ver 🔒 abajo.
  - `aviso: AvisoNormalizado`
  - `extraccion: ExtraccionValidada | None`
  - `poliza_match: ResultadoPoliza | None`
  - `dictamen: Dictamen | None`
  - `alerta_fraude: AlertaFraude | None`
  - `aprobado_por: Usuario | None` — se fija SOLO en transición terminal por humano (P1).
  - `es_duplicado: bool`
  - `creado_en`, `actualizado_en` (timestamps).
- **Comportamientos (en U1)**: solo construcción y lectura. **NO** expone mutación de estado.
- 🔒 **Regla dura de `estado` (nota de endurecimiento Q2)**: `Caso.estado` **NO tiene setter público**. La **única vía de mutación** del estado es la **máquina de estados de `hitl` (U4)** vía `_transicion_valida`. En U1 el campo se declara inmutable desde fuera de `hitl`; abrir un setter libre violaría P1 ("estado inmutable salvo vía hitl"). Toda transición terminal (`APROBADO`/`RECHAZADO`) exige `aprobado_por` (se detalla en U4).
- **Aggregate**: `Caso` es la **raíz** del aggregate; incluye por composición `AvisoNormalizado`, `ExtraccionValidada`, `Dictamen`, `AlertaFraude`.

---

## Value Objects  *(los contratos compartidos — sin identidad, definidos por su valor)*

### EstadoCaso *(enum)*
- **Valor**: uno de — **en alcance (Must)**: `RECIBIDO`, `EN_PROCESO`, `LISTO_PARA_APROBAR`, `REQUIERE_REVISION`, `EN_REVISION`, `APROBADO`, `RECHAZADO`.
- **Declarados pero diferidos** (cola SLA = Should): `ESPERANDO_INFO`, `CERRADO_SIN_ACCION` — el enum los reconoce (Apéndice C del PRD) pero sus transiciones no se implementan en esta iteración.
- **Validación**: cerrado — un valor fuera del enum es inválido (PBT-03).

### AvisoNormalizado
- **Valor**: representación interna uniforme del aviso FNOL (texto/PDF/foto normalizados) + `calidad: CalidadDoc` (marca de "documento sucio").
- **Validación**: preserva referencia al origen para trazabilidad (P3).

### CalidadDoc *(enum)*
- **Valor**: `LIMPIO` · `DEGRADADO` (foto de baja calidad / documento sucio) · `ILEGIBLE`.
- **Validación**: cerrado; marca de estrato `documento-sucio` (H-01). Un aviso `DEGRADADO`/`ILEGIBLE` se acepta sin descartarse (H-01), pero puede llevar a campos `ausente` (P4).

### EvidenciaOrigen
- **Valor**: puntero al origen de un dato — `tipo: {span, pagina, region}` + `referencia`.
- **Validación**: no vacío cuando acompaña a un campo confirmado.

### CampoExtraido
- **Valor que encapsula**: un campo extraído + su procedencia — `nombre`, `valor`, `origen: EvidenciaOrigen`, `confianza`, `ausente: bool`.
- **Reglas**: si `ausente = True`, `valor` es nulo y NO se inventa (P4); todo campo confirmado enlaza a `origen` (P3).

### ExtraccionValidada
- **Valor**: `campos: list[CampoExtraido]` que valida contra el contrato tipado.
- **Reglas**: una extracción que no cumple el contrato se **rechaza** (no avanza) — fail-closed (H-17 🔒, H-02 🔒).

### RangoFechas
- **Valor**: `desde: Fecha`, `hasta: Fecha`.
- **Reglas**: `desde ≤ hasta`. VO de apoyo (usado por `Poliza.vigencia`; base de R1 vigencia en U3).

### Poliza
- **Valor**: `numero`, `vigencia: RangoFechas`, `coberturas_contratadas: list`, `exclusiones: list`, `suma_asegurada: Decimal`, `deducible: Decimal`, `es_soat: bool` (forward-compat, RF-14), `clausulas: list[Clausula]`.
- **Reglas**: `suma_asegurada ≥ 0`, `deducible ≥ 0`.

### ResultadoPoliza *(contrato de grounding — P4)*
- **Valor**: `encontrada: bool`, `poliza: Poliza | None`, `candidatas: list[Poliza]`.
- **Semántica (RF-10, no forzar match)**: si `encontrada = True` ⇒ `poliza ≠ None`. Si `encontrada = False` ⇒ `poliza = None` y `candidatas` puede traer las cercanas — **nunca** se promueve una candidata a match a la fuerza (P4). *(El comportamiento de búsqueda es U2; el invariante de contrato vive en U1.)*
- **Usado por**: `Caso.poliza_match`.

### Clausula
- **Valor**: `id`, `texto`, `tipo: {vigencia, cobertura, exclusion, limite, deducible}`, `referencia`.
- **Reglas**: recuperable por `policy_rag`; es la fuente citada de todo dictamen (P3).

### Dictamen
- **Valor**: `resultado: ResultadoCobertura`, `regla_aplicada: str` (R1..R5), `clausula: Clausula`, `deducible_calculado: Decimal`.
- **Reglas (invariantes de contrato — se enforzan aquí aunque el cálculo sea U3)**:
  - `clausula` **obligatoria** — un `Dictamen` sin cláusula es **inválido** (H-08 🔒, P2/P3).
  - `deducible_calculado ≥ 0` (PBT-03).

### ResultadoCobertura *(enum)*
- **Valor**: `CUBIERTO` · `CUBIERTO_PARCIAL` · `NO_CUBIERTO` · `REQUIERE_REVISION`. Cerrado (PBT-03).

### AlertaFraude
- **Valor**: `severidad`, `inconsistencias: list[EvidenciaOrigen]`, `explicacion: str`.
- **Reglas**: `inconsistencias` **no vacío** — una alerta sin evidencia es **inválida** (H-09 🔒, P6). No produce transición de estado (P1).

### Cotas
- **Valor**: `max_rondas: int > 0`, `presupuesto_tokens: int > 0`.
- **Reglas**: caps duros del orquestador (P4, se usan en U4).

### Usuario *(linchpin de P1 — la identidad que firma)*
- **Valor**: `usuario_id`, `rol: RolUsuario`. **Mínimo**, coherente con **auth real = Won't** (selector de rol stub, RNF-14) — no password, no sesión aquí.
- **Reglas**: es el valor obligatorio de `Caso.aprobado_por` en toda transición terminal (P1). Sin `Usuario` no hay firma → no hay estado terminal (todo el fail-closed de P1 / RULE-CTR-05 descansa en este contrato).

### RolUsuario *(enum)*
- **Valor**: `ANALISTA` · `CUMPLIMIENTO` · `ADMIN`. Cerrado. (Ajustador fuera del MVP — persona de contexto.)
- **Uso**: autorización server-side por rol (SECURITY-08); el front nunca la valida (ADR-001).

### FilaEntrada *(contrato abstracto del generador — Q3-A)*
- **Valor**: los campos mínimos que el generador necesita de una fila de dataset, **de forma abstracta**. Kaggle es un **adaptador** que produce `FilaEntrada`; no se acopla al esquema Kaggle (respeta Plan B del riesgo #1).
- **Campos** (indicativos): `datos_siniestro`, `etiqueta_fraude: bool`, `metadatos`.

### GroundTruth
- **Valor**: la verdad esperada de un caso sintético — `campos_esperados`, `poliza_esperada`, `resultado_cobertura_esperado: ResultadoCobertura`, `etiqueta_fraude: bool`, `inconsistencia_esperada: EvidenciaOrigen | None`.
- **Reglas**: si `etiqueta_fraude = True`, `inconsistencia_esperada` **no puede ser None** (liga con RULE-GEN-02 🔒).

---

## Aggregates
- **Raíz**: `Caso`. **Incluye**: `AvisoNormalizado`, `ExtraccionValidada`, `Dictamen`, `AlertaFraude`.
- **Consistencia garantizada por la raíz**: el estado del `Caso` solo cambia por la máquina de `hitl` (U4); los sub-objetos se adjuntan por el orquestador (U4) durante el flujo.

## Frontend
**N/A** — U1 no tiene UI (las historias de pantalla H-19/20/21 son de U4/U5).

## Nota de realización
Estos VOs se implementan como **modelos Pydantic** en Code Generation (H-17). El diseño aquí es agnóstico de tecnología; el mapeo a Pydantic + las propiedades PBT se detallan en `business-logic-model.md` (§ Propiedades testables) y en la Actividad 5.
