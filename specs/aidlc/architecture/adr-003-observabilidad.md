# ADR-003 · Observabilidad: Langfuse (target) + floor JSON (fallback)

- **Estado**: Aceptado (2026-07-06)
- **Fase**: AJIT

## Contexto
P3 (trazabilidad) es invariante: traza por nodo (latencia/tokens/modelo/IO) + costo/caso + replay + export PIA (H-14, H-15). El PRD §8 fija un **floor de observabilidad**: si integrar Langfuse tarda, el mínimo es trace JSON estructurado + panel simple. La herramienta real es el target, no un requisito bloqueante del núcleo.

## Decisión
**Langfuse/OTel como target; trace JSON estructurado + panel simple como fallback declarado.** La observabilidad se diseña detrás de una **interfaz de instrumentación** (`observability.instrumentar(evento)`) para que el backend no dependa del proveedor concreto — Langfuse o floor son intercambiables detrás de esa interfaz.

## Consecuencias
**Positivas**: el núcleo irrenunciable (Must #2-#8) no se bloquea si Langfuse se atrasa; P3 se cumple con el floor; la interfaz de instrumentación evita acoplamiento al vendor.

**Negativas / a vigilar**: el floor JSON da menos ergonomía de replay/visualización que Langfuse. Aceptable — declarado en el PRD, no se sobre-afirma (P7).

**Reversibilidad**: alta — cambiar de floor a Langfuse (o viceversa) es cambiar la implementación detrás de la interfaz de instrumentación, sin tocar los nodos instrumentados.
