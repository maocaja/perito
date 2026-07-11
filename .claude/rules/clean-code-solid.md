# Regla: Clean Code + SOLID — NO NEGOCIABLE

Todo código nuevo (y todo lo que se toque) se escribe legible y bien diseñado. Se **verifica en el
code-reviewer de cada unit**.

## Nombres dicientes
- Funciones/variables dicen **QUÉ** hacen o **POR QUÉ**, no el "cómo" ni el tipo. Español del dominio
  (`dictamen`, `cobertura`, `siniestro`, `asegurado`), consistente.
- **🚫 Prohibido:** nombres crípticos o vacíos (`x`, `tmp`, `data`, `foo`, `d`, `res`), abreviaturas no obvias,
  `flag`/`aux` sin contexto.

## Funciones y estructura
- **Pequeñas, una sola responsabilidad (SRP)**; un solo nivel de abstracción por función.
- Sin **código muerto**, sin **duplicación** (DRY), sin **números mágicos** (constantes nombradas), sin
  comentarios que mienten. Los comentarios explican el **por qué**, no repiten el código.
- Cada función pública con **test**; comportamiento fail-closed.

## SOLID
- **S (SRP):** una razón para cambiar por módulo/función.
- **O (Open/Closed):** extensible sin modificar. Los `provider` mock→real: la vista/consumidor depende de la
  **interfaz**, no de la implementación.
- **L (Liskov):** las implementaciones reales (M1/M2/M3) sustituyen a los mocks respetando **el mismo contrato**
  (misma forma de retorno) — sin que el consumidor cambie.
- **I (Interface Segregation):** interfaces pequeñas y específicas (un provider por responsabilidad, no un
  god-object).
- **D (Dependency Inversion):** depender de **abstracciones** (contratos/`Protocol`/provider), no de detalles.
  **Esto ES la estrategia mock-first:** `documentos_de`/`campos_extraidos`/`ancla_evidencia`/`Correlacion` son
  las abstracciones; mock y real son intercambiables.

**🚫 Prohibido:** funciones-monstruo, lógica duplicada, magic numbers, dead code, god-objects, acoplar la UI a
una implementación concreta en vez de a su interfaz.

Contexto: aplica a todo el build del **Claims Workbench** (`specs/aidlc/evolution/ROADMAP-workbench.md`).
