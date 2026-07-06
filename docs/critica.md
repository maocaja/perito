# Deep Research — CRÍTICA (riesgos y modos de falla)

> **Proyecto:** Perito — co-piloto de IA para admisión y triage de siniestros (FNOL).
> **Fecha:** julio 2026. **Método:** fan-out de búsquedas web → 24 fuentes → 106 afirmaciones extraídas → 25 verificadas adversarialmente (voto 3-0 = unánime). 20 confirmadas, 5 refutadas.
> **Objetivo del ejercicio:** encontrar por qué esto podría fracasar. No está endulzado.

---

## Veredicto

Perito enfrenta **cuatro amenazas convergentes**, todas confirmadas con alta confianza. Ninguna mata el proyecto **como ejercicio académico/portafolio**, pero todas son razones reales por las que un producto comercial en este espacio fracasaría — y por eso mismo son munición para demostrar criterio en la presentación.

---

## Riesgos priorizados (confirmados)

### 1. Comoditización: el core system ya trae esto nativo
- **Duck Creek lanzó "Agentic FNOL" el 28-abr-2026** con exactamente el alcance de Perito: captura del siniestro, **verificación de póliza/cobertura**, **detección temprana de fraude en admisión** y **enrutamiento**. *(voto 3-0)*
- Los tres hyperscalers (AWS, Google, Azure) construyen stacks verticales completos (silicio → modelos → agentes → workflow); el *lock-in* se mueve a "modelos, agentes, vector stores y automatización de workflow". *(3-0)*
- **Implicación:** un motor genérico de terceros queda como un wrapper absorbible por el core o la nube.
- *Matiz honesto:* la versión más fuerte de este argumento —"el core tiene ventaja estructural de datos nativa imposible de igualar"— **fue REFUTADA (0-3)**. El riesgo de comoditización por superposición de alcance sí se sostiene; la superioridad estructural absoluta, no.
- Fuentes: [Duck Creek / PRNewswire](https://www.prnewswire.com/apac/news-releases/duck-creek-launches-insurance-native-agentic-ai-platform-and-unveils-new-applications-to-transform-underwriting-and-claims-302755161.html), [Constellation Research](https://www.constellationr.com/insights/news/google-cloud-aws-microsoft-azure-ai-vertical-integration-race)

### 2. El pitch de "te quitamos el riesgo" es falso: la responsabilidad es indelegable
- Bajo el **NAIC Model Bulletin**, "las leyes estatales aplican sin importar si la decisión la toma un humano, un algoritmo o un tercero"; **comprar IA no transfiere la obligación al vendedor**. Los reguladores "miran a través" del vendor en las auditorías. *(3-0, x3 afirmaciones)*
- **Implicación:** Perito reduce error *operativo*, no exposición *estatutaria*. No se puede vender como "te blindamos legalmente".
- Fuentes: [NAIC AI Issue Brief](https://content.naic.org/sites/default/files/ai-issue-brief.pdf), [actuary.info](https://actuary.info/insights/ai-regulation-insurance-naic-2026), [Crowell](https://www.crowell.com/en/insights/client-alerts/naic-intensifies-ai-regulatory-focus-what-health-insurance-payors-need-to-know)

### 3. Precedente litigioso masivo por automatizar dictámenes/fraude
- **Cigna (PxDx)** — algoritmo negando claims en masa "short-circuiting physician review", ~1.2 s por solicitud.
- **UnitedHealth (nH Predict)** — demanda colectiva; el tribunal **negó el dismissal (13-feb-2025)**, dejando avanzar breach-of-contract y mala fe.
- **State Farm** — demanda por **sesgo racial algorítmico** en claims; **sobrevivió a la moción de desestimación**.
- **Implicación:** automatizar denegación/fraude es un imán de demandas por denegación, discriminación y mala fe — el modo de falla legal más caro de la categoría. *(3-0, x5 afirmaciones)*
- *Matiz:* la mayoría del precedente es de seguros de **SALUD/utilization management**, no P&C ni el FNOL de daños que ataca Perito — analogía fuerte, no idéntica. El "90% de error" de nH Predict es en realidad una tasa de reversión en apelación reencuadrada por los demandantes; son **alegaciones no adjudicadas**.
- Fuentes: [ArentFox Schiff](https://www.afslaw.com/perspectives/health-care-counsel-blog/health-insurers-sued-over-use-artificial-intelligence-deny), [Healthcare Finance News](https://www.healthcarefinancenews.com/news/class-action-lawsuit-against-unitedhealths-ai-claim-denials-advances), [Insurance Business Mag](https://www.insurancebusinessmag.com/us/news/claims/state-farm-hit-with-lawsuit-as-policyholders-claim-aidriven-discrimination-552156.aspx)

### 4. El propio mercado asegurador excluye el riesgo de IA de sus pólizas
- **Berkley** introdujo una exclusión "absoluta" de IA en D&O/E&O/fiduciaria (ene-2026); **AIG y Great American** presentaron las suyas; el endoso **ISO CG 40 47** (ene-2026) subyace a ~82% de pólizas P&C.
- Las exclusiones niegan cobertura por "errores de automatización de decisiones" y "alucinaciones del modelo". Los *deployers* enfrentan un *coverage gap* donde "las indemnizaciones del vendor son a menudo su única fuente de recuperación". *(3-0, x3 afirmaciones)*
- **Implicación:** la responsabilidad recae íntegra sobre quien despliega — y potencialmente sobre el vendor (Perito) vía indemnizaciones.
- Fuente: [Lexology / Fenwick-Honigman](https://www.lexology.com/library/detail.aspx?g=b76e0dba-d9a8-44f1-9f5d-6fbd0a22f6b6)

---

## Riesgos secundarios (confirmados con menor peso)

### 5. Sabotaje silencioso de los ajustadores (change management)
- Los ajustadores que se sienten reemplazados "sabotean o eluden silenciosamente la IA": las métricas de adopción se ven sanas (el sistema se toca) pero los resultados no mejoran. La adopción de IA en claims sigue fragmentada — **solo ~7% de aseguradoras** logran éxito escalable pese a que 58-82% usan alguna herramienta de IA. *(voto 2-1, fuente advisory)*
- Fuente: [CAIC Playbook](https://getcaic.org/playbooks/ai-in-claims-operations.html)

### 6. Integración con cores legacy (mainframe/AS400)
- Requiere puentes RPA o intermediarios de data-lake que añaden sobrecarga operativa; >70% de tasa de fracaso en transformaciones de core. Doble filo: en cores legacy la integración es cara y frágil; en cores modernos el vendor ya trae el agente nativo (riesgo #1). *(3-0)*
- Fuente: [CAIC Playbook](https://getcaic.org/playbooks/ai-in-claims-operations.html)

### 7. Capa de compliance costosa y de ciclo largo
- El NAIC Model Bulletin (adoptado por **24+ estados y D.C.** hacia inicios de 2026) exige un programa escrito de uso responsable de IA (gobernanza, gestión de riesgo, auditoría) y evaluaciones recurrentes contra leyes antidiscriminación. Eleva la barra, el costo y **alarga el ciclo de venta B2B**. *(3-0, x4 afirmaciones)*
- Fuentes: [Quarles](https://www.quarles.com/newsroom/publications/nearly-half-of-states-have-now-adopted-naic-model-bulletin-on-insurers-use-of-ai), [actuary.info](https://actuary.info/insights/ai-regulation-insurance-naic-2026)

---

## Afirmaciones REFUTADAS (importante — no usarlas como argumento)

La verificación adversarial mató estas 5 (no las cites como verdad):
1. ❌ "El NAIC impone requisitos de gobernanza **vinculantes** desde 2023" — es *guidance* interpretativa ("expected to"), no estatuto autoejecutable. *(0-3)*
2. ❌ "El core tiene ventaja estructural de datos nativa insuperable sobre un wrapper" — *(0-3)*
3. ❌ "Saltarse la fase piloto es la causa #1 de fracaso de proyectos de claims-AI" — *(0-3)*
4. ❌ "Fraude y settlement automático están **explícitamente** clasificados como alto riesgo por el NAIC" — *(0-3)*
5. ❌ "~24 estados adoptaron el bulletin a mar-2026" (cifra/fecha imprecisa) — *(1-2)*

---

## Caveats de esta investigación (leer antes de usarla)

- **Sesgo geográfico grave:** casi toda la evidencia sobreviviente es de **EE.UU.** (NAIC, litigios federales, exclusiones norteamericanas). **Ningún claim confirmado aporta evidencia directa sobre Colombia/LATAM** — ni SFC, ni Ley 1581, ni madurez de datos, presupuesto, digitalización o informalidad. Esos riesgos siguen siendo plausibles pero **no verificados aquí**.
- **Sesgo de vertical:** gran parte del precedente litigioso es de seguros de **salud**, no P&C/daños.
- **Temporalidad:** todo está fechado a mediados de 2026 y el panorama (adopciones estatales, lanzamientos de core, exclusiones ISO) se mueve trimestralmente.
- **Calidad de fuentes:** varias son secundarias (bufetes, prensa especializada, un playbook advisory), no documentos primarios.

---

## Preguntas abiertas (para completar antes de la Estación 2)

1. ¿Cuál es el régimen regulatorio real y vinculante para IA en seguros en **Colombia** (Circulares SFC, SARLAFT para fraude, PII bajo Ley 1581)? ¿Difiere lo suficiente del marco NAIC/EU como para cambiar el análisis?
2. ¿Hay precedentes de litigio/sanción/rechazo de pilotos de IA en aseguradoras de Colombia/LATAM, o el riesgo es hasta ahora solo importado de EE.UU.?
3. ¿Tamaño real del mercado direccionable y madurez de datos de las aseguradoras colombianas? ¿La informalidad y baja penetración hacen inviable el ACV para ventas B2B de ciclo largo?
4. **La más importante para el diseño:** ¿un copiloto *human-in-the-loop estrecho* (solo asistencia, sin dictamen automático de denegación) evade la clasificación de alto riesgo y el grueso de la exposición litigiosa? ¿O el mero enrutamiento/marcado de fraude ya dispara los deberes de gobernanza y las exclusiones?

---

## Cómo esto refuerza (no debilita) el proyecto como portafolio

Cada riesgo confirmado tiene una respuesta ya incorporada en el diseño de Perito, y **decir esto en la demo es lo que demuestra criterio de ingeniería**:
- Comoditización → es un proyecto de práctica, no una startup; el objetivo es el motor agéntico, no ganar el mercado.
- Responsabilidad indelegable + litigios → **HITL obligatorio, nunca dictamen autónomo de denegación**; el humano decide. Esto es exactamente lo que la pregunta abierta #4 sugiere como mitigación.
- Determinismo en cobertura + citas a cláusula + trazas auditables → responde al riesgo regulatorio con arquitectura, no con marketing.
- La honestidad sobre el sesgo EE.UU./salud y sobre lo que la evidencia **no** probó (LATAM) es en sí misma la señal de madurez que un Staff/Principal busca.
