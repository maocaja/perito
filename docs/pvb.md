# Product Vision Board — Perito

> **Estado:** borrador de trabajo (Estación 1, Hardcore AI C3). **Deep research de validación y crítica completados** → ver `research/validacion.md` y `research/critica.md`.
> Regla del curso respetada: no invento cifras. Ojo — la validación **refutó** casi todas las cifras puntuales de FNOL (venían de blogs de vendors); por eso este PVB se apoya en el *patrón* y en cifras que sí sobrevivieron verificación, y marca con ⏳/TBD lo que sigue sin fuente primaria.

---

## PRODUCTO

**Nombre del producto:** Perito

**Descripción en una línea (qué hace y para quién):** Co-piloto de IA que convierte un aviso de siniestro caótico (correo, PDF, fotos, audio) en un caso estructurado, validado contra la póliza y enrutado al ajustador — para equipos de siniestros de aseguradoras.

---

## 1. PROBLEMA

**Problema que resuelvo:** La admisión y triage del aviso de siniestro (FNOL) se hace hoy de forma manual: una persona lee reportes desordenados y en formatos heterogéneos (correos, PDFs, fotos, audios), transcribe los datos a mano, verifica cobertura contra la póliza, evalúa señales de fraude y decide a qué ajustador asignarlo. Es lento, propenso a error, y demora el ciclo de siniestros — lo que golpea la satisfacción del asegurado y el costo operativo. Perito automatiza la extracción, la verificación y el enrutamiento, y deja el juicio final a un humano.

**Evidencia del dolor (verificada):** El intake sigue mayormente manual — **STP en P&C por debajo del 10%** (Neudesic, Aite-Novarica) y **solo 7% de aseguradoras han escalado IA con éxito** (BCG 2025). La automatización reduce tiempos de días a minutos, pero solo en el subconjunto de siniestros simples elegibles para STP.
> ⚠️ Cifras puntuales de FNOL (ej. "4-12h → 5-15min") **refutadas** en verificación — no se usan. Falta fuente primaria de costo/tiempo en Colombia (⏳ pregunta abierta).

**¿Sobrevive a 2-3 generaciones de modelos foundation?**
- [x] **Sí — es un problema de WORKFLOW/INTEGRACIÓN/COMPLIANCE, no de OUTPUT.** La validación lo confirma: el valor durable **no está en la extracción cruda** (eso se commoditiza con mejores modelos multimodales, y el core ya lo trae — ver riesgo de comoditización), sino en la orquestación: reglas de cobertura determinísticas, integración con el core, **cumplimiento Habeas Data (Circular SIC 002/2024)** y HITL auditable.

**Durability Score (1-5):** 4 — el dolor y el foso de workflow/compliance son reales; se descuenta 1 por la fuerte comoditización del componente de extracción (Duck Creek Agentic FNOL, abr-2026).

---

## 2. SEGMENTO TARGET

**¿Para quién es este producto?** Equipos de operaciones de siniestros en aseguradoras medianas de Colombia/LATAM que manejan **ramos masivos de alto volumen y valor bajo-medio** (autos/SOAT, hogar), con intake todavía manual o semi-digital, y sin un core moderno (tipo Guidewire) que ya lo automatice. Usuario final: el analista de admisión / triage de siniestros. *(afinar tamaño/segmento con research)*

**¿Quién controla el veto de confianza?** El **oficial de cumplimiento** y el **líder del área de siniestros**, con el **regulador (Superintendencia Financiera de Colombia)** de fondo. Aunque el analista ame la herramienta, un dictamen de cobertura errado o un manejo indebido de datos personales (Ley 1581) puede matar la adopción. Por eso el diseño es human-in-the-loop y determinístico en la decisión de cobertura.

---

## 3. MOAT PRIMARIO

**Moat primario:** [x] **Trust Moat** — reliability, trazabilidad y compliance que un wrapper genérico no iguala.

**¿Qué trust única poseemos o podemos construir?** Cada dictamen es **auditable y determinístico donde importa**: la validación de cobertura corre sobre reglas (no sobre el juicio blando de un LLM), cita la cláusula de póliza que aplicó, y queda registrada en una traza completa. El agente **nunca cierra un siniestro solo** (HITL). Esa combinación — determinismo + trazabilidad con citas + humano en el loop + manejo correcto de PII — es la ventaja defensible, no el pipeline en sí.

**Anclaje regulatorio real (verificado):** la **Circular SIC 002/2024** (Ley 1581/Habeas Data) exige un **estudio de impacto de privacidad documentado antes de diseñar** el sistema de IA. Perito lo incorpora como parte del producto (PIA + trazas + HITL) → el trust deja de ser marketing y pasa a ser cumplimiento demostrable. Este ángulo local es difícil de replicar por un vendor global genérico.

> Nota honesta (contexto de portafolio): no hay un *data moat* real en un proyecto de práctica; el ángulo defendible es el trust. Y ojo — la crítica confirmó que **la responsabilidad legal es indelegable** (NAIC): Perito reduce error operativo, NO transfiere responsabilidad. El pitch nunca debe ser "te quitamos el riesgo".

---

## 4. ARENA COMPETITIVA

**Arena:** [x] **Disruptor (AI-Disrupted)** — reimaginar el workflow existente de intake/triage de siniestros para hacerlo 10x más rápido. No es Pioneer: el mercado de automatización de siniestros ya existe.

**¿Cómo sobrevives o complementas a los gigantes?** No compito contra los core systems ni los hyperscalers: **me enchufo como la capa de intake especializada** en documentos caóticos en español y realidades locales (SOAT, formatos colombianos), donde las soluciones globales son débiles. Complemento, no reemplazo.

> ⚠️ **Riesgo de comoditización confirmado (crítica):** Duck Creek lanzó **"Agentic FNOL" el 28-abr-2026** con el alcance *exacto* de Perito (captura + verificación de cobertura + fraude en admisión + enrutamiento), y los hyperscalers construyen stacks verticales completos. **Como producto comercial, el core lo absorbe.** Por eso Perito es honestamente un **proyecto de portafolio** (demostrar ingeniería agéntica), no una apuesta de mercado — y el único wedge defendible sería la especialización local (es-CO, SOAT, Circular SIC), no ganarle al core en features.
> Competidores reales verificados: Shift Technology (fraude, Azure), Tractable, CCC, Sapiens, ZestyAI, SimplifAI.

---

## 5. UX PARADIGM

**Paradigma:** [x] **Agent (con Human-in-the-Loop)** — la IA ejecuta el pipeline de intake/triage dentro de límites, pero **para en el punto de decisión** y un humano aprueba, corrige o rechaza.

**¿Por qué este paradigma?** Es una decisión de **alto riesgo** (dictaminar cobertura, marcar fraude). La autonomía total rompe la confianza y choca con el regulador; un simple asistente pasivo desperdicia la automatización. El punto óptimo es un agente que hace el 90% del trabajo mecánico y entrega un caso listo para que el humano ratifique. La supervisión humana **es** parte del producto, no un parche.

---

## 6. AI DECISION TRIANGLE

**Optimizo primariamente para:** [x] **Capability (precisión)** — son decisiones de riesgo (cobertura, fraude), donde un error tiene costo legal/regulatorio.

**Trade-offs que acepto:** Acepto más costo y latencia en el paso de razonamiento de cobertura a cambio de precisión y trazabilidad. Compenso el costo con **LLM por capas**: extracción masiva barata (Haiku), grueso (Sonnet), y el modelo más capaz (Opus) reservado solo para la cobertura ambigua. No optimizo para "tiempo real": un FNOL puede tardar segundos-minutos sin romper el valor.

---

## 7. MODELO ECONÓMICO

**Modelo de pricing:** [x] **Usage-Based** — por siniestro procesado (con posible tier híbrido para volumen).

**¿El pricing escala a 10x usuarios?** [x] Sí — cada siniestro adicional genera ingreso y el costo marginal (inference por capas) es bajo y controlable.

**Costo estimado por usuario/mes:** ⏳ TBD *(depende del costo por siniestro; se estima tras definir el pipeline y el mix de modelos)*
**Revenue por usuario/mes:** ⏳ TBD
**Gross margin proyectado:** ⏳ TBD

> Nota: en un proyecto de portafolio el pricing es ilustrativo. Se completa con benchmarks del research de validación (qué cobran los vendors de claims automation).

---

## 8. MÉTRICAS DE ÉXITO

**Métricas de usuario:**
1. **Tiempo de ciclo intake → asignación** (reducción vs. proceso manual).
2. **Touchless intake rate**: % de FNOL procesados sin intervención humana.

**Métricas específicas de AI:**
1. **Accuracy de extracción de campos** vs. ground truth (target alto; medible con el dataset).
2. **Precisión/recall del dictamen de cobertura** y **tasa de casos escalados a humano** (calibración del HITL).

---

## 9. RIESGOS CRÍTICOS

**1. ¿Commoditización en 12 meses? — ALTO (confirmado).** Duck Creek "Agentic FNOL" (abr-2026) ya cubre el alcance de Perito de forma nativa en el core. Como negocio, el riesgo es existencial. Mitigación (y reencuadre honesto): Perito es un **proyecto de portafolio** para demostrar ingeniería agéntica, no una startup que deba ganar el mercado; el único wedge comercial defendible sería la capa local (es-CO, SOAT, Circular SIC).

**2. ¿Replicable en 6 semanas con la misma API?** El pipeline base, sí. Lo difícil de replicar: reglas de cobertura confiables, trazabilidad auditable con citas, integración al core, cumplimiento del PIA de la Circular SIC 002/2024, y calibración de fraude **sin sesgo** (ver State Farm). Ahí está la barrera, no en llamar al LLM.

**3. Si tienes éxito a escala, ¿cómo se rompe la confianza primero?** Un **dictamen de cobertura o un flag de fraude errado/sesgado** → responsabilidad legal. Precedente real y verificado: **Cigna (PxDx)**, **UnitedHealth (nH Predict**, dismissal negado feb-2025**)**, **State Farm (sesgo racial algorítmico**, sobrevivió desestimación**)**. Y **la responsabilidad es indelegable** (NAIC) — el asegurador responde aunque la decisión la tome la IA. Mitigación de diseño: **HITL obligatorio, nunca denegación autónoma**, determinismo en cobertura, citas a cláusula, logs auditables. (La pregunta abierta clave: un copiloto HITL *estrecho* que solo asiste —sin dictar denegación— esquiva el grueso de la exposición.)

---

## Checklist de entrega

- [x] Producto seleccionado (idea propia — Perito)
- [x] Deep research de validación completado y estudiado → `research/validacion.md`
- [x] Deep research de crítica completado y estudiado → `research/critica.md`
- [x] Información documentada en Markdown (README + PVB + 2 research)
- [x] Product Vision Board completado con evidencia citada
- [~] Listo para presentar en la Estación 2 *(base sólida; quedan 4 preguntas abiertas de fuente primaria — ver abajo)*

### Pendientes de fuente primaria (opcional, para robustecer)
1. Costo/tiempo verificable del triage manual de FNOL en Colombia (las cifras de blogs fueron refutadas).
2. Postura de la **Superintendencia Financiera** (no solo SIC) sobre IA en siniestros; interacción con **SOAT**.
3. Tasa real de adopción de IA en aseguradoras Colombia/LATAM (fuente primaria: Fasecolda/Celent).
4. Fricción técnica real de integración con core systems locales.

---

*Hardcore AI by 30X — Cohorte 3 — Perito — Julio 2026*
