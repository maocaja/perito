# Deep Research — VALIDACIÓN (¿tiene fundamento real?)

> **Proyecto:** Perito — co-piloto de IA para admisión y triage de siniestros (FNOL).
> **Fecha:** julio 2026. **Método:** fan-out de búsquedas web → fuentes → afirmaciones extraídas → 25 verificadas adversarialmente. **Solo 7 confirmadas, 18 refutadas** — señal de que buena parte de las cifras "de marketing" sobre FNOL no resisten verificación. Lo que quedó es lo que sí se sostiene.

---

## Veredicto

**Fundamento MODERADO-POSITIVO.** La idea se sostiene, pero **por el patrón y el contexto, no por cifras puntuales de FNOL** (casi todas esas cifras fueron refutadas por venir de blogs de vendors sin respaldo primario). El valor durable de Perito **no está en la extracción cruda** (eso se commoditiza con mejores modelos multimodales) sino en la **orquestación del workflow**: integración con core, motor de reglas de cobertura, cumplimiento Habeas Data y HITL auditable. Es decir: es un problema de **WORKFLOW/INTEGRACIÓN/COMPLIANCE**, no de OUTPUT.

---

## Hallazgos confirmados (verificación adversarial)

### 1. El problema es real y estructural — el intake sigue siendo manual
- **Solo 7% de las aseguradoras han escalado IA con éxito** (BCG 2025; "67% probando genAI, solo 7% ha escalado").
- Las tasas de **procesamiento directo (STP) en P&C siguen por debajo del 10%**, con ~60% de aseguradoras sin ningún STP.
- **Implicación:** el trabajo manual de intake domina el baseline. El dolor existe. *(voto 3-0)*
- Fuentes: BCG 2025 vía eMarketer, Neudesic, Aite-Novarica.

### 2. El stack técnico de Perito está probado en producción
- **Shift Technology** usa Azure OpenAI (extracción generativa) + AI Vision (OCR) + Document Intelligence (layout) para clasificar y extraer datos de documentos de siniestros, a escala de **2.6B+ pólizas/siniestros**.
- **Implicación:** el núcleo (LLM multimodal + IDP sobre documentos caóticos de siniestros) no es especulativo. *(3-0)*
- *Caveat:* son case studies de vendor/marketing, y el uso principal de Shift es detección de fraude — la etiqueta "FNOL intake" es una generalización leve. El núcleo técnico sí es exacto y vigente.
- Fuente: [Microsoft/Shift case study](https://www.microsoft.com/en/customers/story/23202-shift-technology-azure-ai-vision).

### 3. La automatización de siniestros genera valor documentado
- Reduce tiempos de resolución **de días a minutos** — pero **solo en el subconjunto de siniestros simples elegibles para STP** (no la norma; STP P&C <10%).
- Casos reales: aseguradora de viajes US (hasta 3 semanas → minutos en el 57% automatizado); Aviva ($80M+/año en valor por optimización de claims con IA). *(3-0)*
- **Implicación:** la afirmación sobrevive como **capacidad direccional**, no como "todos los siniestros en minutos".
- Fuentes: LatamFintech, Shift, Decerto, SG Analytics 2026, Aviva.

### 4. Tendencia de mercado favorable
- IA generativa en seguros: **~28% CAGR**, ~$1.39B (2025) → ~$1.77B (2026) → ~$4.83B (2030) según TBRC. *(cifras 2025/2026: 3-0; proyección 2030: 2-1)*
- **Implicación / caveat clave:** los **números absolutos divergen mucho** entre firmas (TBRC $4.83B/2030 vs Allied $14.4B/2032). Lo robusto es **la magnitud del CAGR (~28-34%)**, no el número absoluto. Usar el CAGR, no la cifra puntual.
- Fuente: [TBRC](https://www.thebusinessresearchcompany.com/report/generative-ai-in-insurance-global-market-report).

### 5. Colombia SÍ tiene régimen regulatorio aplicable (foso + requisito)
- **Circular Externa 002 de la SIC (21-ago-2024)** fija lineamientos para el tratamiento de datos personales en sistemas de IA, anclada en **Habeas Data** (Art. 15 Constitución) y **Leyes 1266/2008 y 1581/2012**. Cubre aseguradoras que traten datos de reclamantes/asegurados. *(3-0)*
- **Exige un estudio de impacto de privacidad (PIA) documentado PREVIO al diseño** del sistema de IA, con 3 componentes: (1) descripción del tratamiento, (2) evaluación de riesgos a los titulares, (3) medidas de protección/seguridad. Se dispara cuando el producto entraña **alto riesgo** — un agente FNOL que ingiere datos personales sensibles plausiblemente cruza ese umbral. *(3-0)*
- **Implicación:** esto **refuerza** que Perito es un problema durable de workflow/compliance — el cumplimiento es parte del producto, no un extra. Y es un ángulo local defendible.
- *Caveat:* "vinculante" es una caracterización algo fuerte — es un instrumento de **lineamientos interpretativos** bajo la Ley 1581, no un estatuto de IA autónomo (Colombia no lo tiene).
- Fuentes: [Circular SIC 002/2024 (normograma Cancillería)](https://www.cancilleria.gov.co/normograma/compilacion/docs/circular_superindustria_0002_2024.htm), Holland & Knight, Deloitte, Cuatrecasas, Dentons.

---

## ⚠️ Cifras REFUTADAS — NO usarlas como fundamento

La verificación adversarial **mató 18 de 25 afirmaciones**, casi todas cifras puntuales de FNOL sacadas de blogs de vendors. **No las cites:**
- ❌ "Procesar FNOL manual retrasa la asignación 4-12 h vs 5-15 min con automatización" *(0-3, blog)*
- ❌ "Intake manual = 8-15 horas-persona por 100 siniestros, -80% con automatización" *(0-3, blog)*
- ❌ "Ciclo promedio de claim auto P&C = 14-21 días (NAIC 2024)" *(0-3)*
- ❌ "43% de aseguradoras LATAM ya con genAI en producción" *(1-2)*
- ❌ "19% de aseguradoras LATAM con IA agéntica operativa" *(0-3)*
- ❌ "Mercado IA-en-claims $0.46B→$0.97B a 16.2% CAGR" *(0-3)* — nota: esta cifra sí apareció en la corrida parcial anterior; la verificación completa la refutó.
- ❌ "65% cita legacy IT / 70% cita barreras de personas y proceso" *(0-3)*
- ❌ "Mercado IA-en-seguros $10.36B (2025) → $154.39B (2034) a 35.7%" *(1-2)*

**Lección:** el fundamento descansa en el **patrón** (dolor real + stack probado + tendencia + foso regulatorio), NO en números específicos de reducción de tiempo/costo de FNOL. Si necesitas esas cifras para el PVB, hay que conseguirlas de fuente primaria.

---

## Caveats de esta investigación

- **Temporalidad:** vigente a julio 2026; las cifras de mercado son forecasts de vendors que divergen. Usar el CAGR, no el absoluto.
- **Fuentes débiles:** la mejor evidencia técnica (Shift) también es marketing; la evidencia cuantitativa específica de FNOL fue mayoritariamente refutada.
- **LATAM/Colombia mal documentado:** las cifras atractivas de adopción LATAM fueron refutadas. La adopción concreta permanece pobremente documentada.
- **No se halló evidencia primaria** sobre SOAT ni sobre la postura específica de la **Superintendencia Financiera** (distinta de la SIC) respecto a IA en siniestros.

---

## Preguntas abiertas (para cerrar antes de la Estación 2)

1. ¿Costo/tiempo real y **verificable** (fuente primaria, no blog) del triage manual de FNOL, y volúmenes por aseguradora en Colombia/LATAM?
2. ¿Postura de la **Superintendencia Financiera** (no solo la SIC) sobre IA en siniestros, y cómo interactúa el **SOAT** con la automatización de FNOL?
3. ¿Tasa real de adopción de IA/IA agéntica en aseguradoras de Colombia/LATAM 2026, con fuente primaria (Celent/Fasecolda)?
4. ¿Cómo se integran técnicamente estos agentes con core systems (Guidewire/Duck Creek u homólogos locales)? Esa fricción de integración es el **verdadero foso** frente a la commoditización de la extracción.

---

## Conclusión para el PVB

El fundamento alcanza para justificar Perito **como proyecto de portafolio** con honestidad: el dolor es real, el stack está probado, hay tendencia y hay un ángulo regulatorio colombiano concreto (Circular SIC 002/2024) que además **encaja con el diseño** (compliance y HITL como parte del producto). Lo que NO se puede afirmar son cifras específicas de ROI de FNOL — y decir esa limitación abiertamente es parte de la señal de criterio.
